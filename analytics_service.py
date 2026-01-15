import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, extract, and_, or_

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def calculate_user_productivity(self, user_id: int, 
                                        days_back: int = 30) -> Dict:
        """Calculate comprehensive productivity metrics"""
        from database.models import Task, TimeEntry
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get tasks in period
        tasks_query = await self.db.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.created_at >= start_date,
                Task.created_at <= end_date
            )
        )
        tasks = tasks_query.scalars().all()
        
        # Get time entries
        time_query = await self.db.execute(
            select(TimeEntry)
            .where(
                TimeEntry.user_id == user_id,
                TimeEntry.start_time >= start_date,
                TimeEntry.start_time <= end_date
            )
        )
        time_entries = time_query.scalars().all()
        
        # Calculate metrics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.is_completed)
        
        total_time = sum((te.duration or 0) for te in time_entries)
        
        # Calculate completion rate
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Calculate average completion time
        completed_with_dates = [t for t in tasks if t.is_completed and t.completion_date and t.created_at]
        if completed_with_dates:
            avg_completion_hours = np.mean([
                (t.completion_date - t.created_at).total_seconds() / 3600
                for t in completed_with_dates
            ])
        else:
            avg_completion_hours = 0
        
        # Calculate productivity by hour
        hourly_productivity = await self._calculate_hourly_productivity(user_id, days_back)
        
        # Calculate category distribution
        category_distribution = {}
        for task in tasks:
            cat = task.category or "Uncategorized"
            category_distribution[cat] = category_distribution.get(cat, 0) + 1
        
        # Calculate priority distribution
        priority_distribution = {}
        for task in tasks:
            priority = task.priority or 3
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days_back
            },
            "task_metrics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": round(completion_rate, 2),
                "pending_tasks": total_tasks - completed_tasks
            },
            "time_metrics": {
                "total_time_tracked_hours": round(total_time / 3600, 2),
                "avg_daily_hours": round(total_time / (days_back * 3600), 2),
                "avg_completion_hours": round(avg_completion_hours, 2)
            },
            "distributions": {
                "by_category": category_distribution,
                "by_priority": priority_distribution
            },
            "hourly_productivity": hourly_productivity,
            "streaks": await self._calculate_streaks(user_id)
        }
    
    async def _calculate_hourly_productivity(self, user_id: int, days_back: int) -> Dict:
        """Calculate productivity by hour of day"""
        from database.models import TimeEntry
        
        hourly_data = {}
        
        for hour in range(24):
            hour_start = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            # Query time entries in this hour
            query = await self.db.execute(
                select(func.sum(TimeEntry.duration))
                .where(
                    TimeEntry.user_id == user_id,
                    TimeEntry.start_time >= hour_start - timedelta(days=days_back),
                    TimeEntry.start_time <= hour_end,
                    TimeEntry.duration.isnot(None)
                )
            )
            total_duration = query.scalar() or 0
            
            # Query tasks completed in this hour
            from database.models import Task
            task_query = await self.db.execute(
                select(func.count(Task.id))
                .where(
                    Task.user_id == user_id,
                    Task.completion_date >= hour_start - timedelta(days=days_back),
                    Task.completion_date < hour_end,
                    Task.is_completed == True
                )
            )
            tasks_completed = task_query.scalar() or 0
            
            hourly_data[hour] = {
                "hour": f"{hour:02d}:00",
                "total_minutes": round(total_duration / 60, 2),
                "tasks_completed": tasks_completed,
                "productivity_score": self._calculate_productivity_score(total_duration, tasks_completed)
            }
        
        return hourly_data
    
    def _calculate_productivity_score(self, duration: int, tasks_completed: int) -> float:
        """Calculate a productivity score 0-100"""
        if duration == 0:
            return 0
        
        # Weighted score: 70% based on focused time, 30% based on tasks completed
        time_score = min(duration / (8 * 3600) * 70, 70)  # Max 8 hours of focused work
        task_score = min(tasks_completed / 10 * 30, 30)   # Max 10 tasks per hour
        
        return round(time_score + task_score, 2)
    
    async def _calculate_streaks(self, user_id: int) -> Dict:
        """Calculate completion streaks"""
        from database.models import Task
        
        # Get all completed tasks with completion dates
        query = await self.db.execute(
            select(Task.completion_date)
            .where(
                Task.user_id == user_id,
                Task.is_completed == True,
                Task.completion_date.isnot(None)
            )
            .order_by(Task.completion_date)
        )
        
        completion_dates = [r[0].date() for r in query.fetchall()]
        
        if not completion_dates:
            return {"current": 0, "longest": 0, "history": []}
        
        # Calculate streaks
        streaks = []
        current_streak = 1
        longest_streak = 1
        
        for i in range(1, len(completion_dates)):
            days_diff = (completion_dates[i] - completion_dates[i-1]).days
            
            if days_diff == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            elif days_diff > 1:
                streaks.append(current_streak)
                current_streak = 1
        
        streaks.append(current_streak)
        current_streak = self._get_current_streak(completion_dates)
        
        return {
            "current": current_streak,
            "longest": longest_streak,
            "history": streaks[-30:]  # Last 30 streaks
        }
    
    def _get_current_streak(self, dates: List) -> int:
        """Calculate current streak from today"""
        if not dates:
            return 0
        
        today = datetime.now().date()
        dates_set = set(dates)
        
        streak = 0
        current_date = today
        
        while current_date in dates_set:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak
    
    async def generate_weekly_report(self, user_id: int) -> Dict:
        """Generate weekly productivity report"""
        metrics = await self.calculate_user_productivity(user_id, 7)
        
        # Compare with previous week
        previous_week_metrics = await self.calculate_user_productivity(
            user_id, 
            start_date=datetime.now() - timedelta(days=14),
            end_date=datetime.now() - timedelta(days=7)
        )
        
        # Calculate improvements
        current_completion = metrics["task_metrics"]["completion_rate"]
        previous_completion = previous_week_metrics["task_metrics"]["completion_rate"]
        completion_change = current_completion - previous_completion
        
        current_time = metrics["time_metrics"]["total_time_tracked_hours"]
        previous_time = previous_week_metrics["time_metrics"]["total_time_tracked_hours"]
        time_change = current_time - previous_time
        
        # Find peak productivity hours
        hourly = metrics["hourly_productivity"]
        peak_hours = sorted(
            [(h, data["productivity_score"]) for h, data in hourly.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Generate insights
        insights = []
        
        if completion_change > 0:
            insights.append(f"🎯 Ваша продуктивность выросла на {abs(completion_change):.1f}%")
        elif completion_change < 0:
            insights.append(f"📉 Продуктивность снизилась на {abs(completion_change):.1f}%")
        
        if time_change > 0:
            insights.append(f"⏱️ Вы работали на {abs(time_change):.1f} часов больше")
        
        if peak_hours:
            insights.append(f"🏆 Пик продуктивности: {', '.join([h[0] for h in peak_hours])}")
        
        # Calculate focus score
        focus_score = self._calculate_focus_score(metrics)
        
        return {
            "period": "weekly",
            "date": datetime.now().isoformat(),
            "metrics": metrics,
            "comparison": {
                "completion_rate_change": round(completion_change, 2),
                "time_tracked_change": round(time_change, 2)
            },
            "insights": insights,
            "recommendations": await self._generate_recommendations(metrics),
            "focus_score": focus_score,
            "achievements": await self._check_achievements(user_id, metrics)
        }
    
    def _calculate_focus_score(self, metrics: Dict) -> float:
        """Calculate overall focus score 0-100"""
        completion_rate = metrics["task_metrics"]["completion_rate"]
        avg_daily_hours = metrics["time_metrics"]["avg_daily_hours"]
        
        # Normalize scores
        completion_score = min(completion_rate / 100 * 60, 60)  # 60% weight
        time_score = min(avg_daily_hours / 8 * 40, 40)  # 40% weight, max 8 hours/day
        
        return round(completion_score + time_score, 2)
    
    async def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        completion_rate = metrics["task_metrics"]["completion_rate"]
        avg_completion_hours = metrics["time_metrics"]["avg_completion_hours"]
        
        if completion_rate < 50:
            recommendations.append("📌 Попробуйте разбивать большие задачи на подзадачи")
            recommendations.append("⏰ Устанавливайте реалистичные дедлайны")
        
        if avg_completion_hours > 24:
            recommendations.append("⏳ Задачи занимают слишком много времени. Делегируйте или упрощайте")
        
        # Check hourly productivity
        hourly = metrics["hourly_productivity"]
        low_productivity_hours = [
            h for h, data in hourly.items() 
            if data["productivity_score"] < 30 and 9 <= int(h.split(':')[0]) <= 17
        ]
        
        if low_productivity_hours:
            recommendations.append(f"🎯 Сконцентрируйтесь на работе в часы: {', '.join(low_productivity_hours[:3])}")
        
        return recommendations
    
    async def _check_achievements(self, user_id: int, metrics: Dict) -> List[Dict]:
        """Check and award achievements"""
        achievements = []
        
        completion_rate = metrics["task_metrics"]["completion_rate"]
        current_streak = metrics["streaks"]["current"]
        total_time = metrics["time_metrics"]["total_time_tracked_hours"]
        
        # Completion achievements
        if completion_rate >= 90:
            achievements.append({
                "name": "Перфекционист",
                "description": "Выполнено 90%+ задач за неделю",
                "icon": "🏆"
            })
        elif completion_rate >= 75:
            achievements.append({
                "name": "Продуктивный",
                "description": "Выполнено 75%+ задач за неделю",
                "icon": "⭐"
            })
        
        # Streak achievements
        if current_streak >= 7:
            achievements.append({
                "name": "Неделя продуктивности",
                "description": "7 дней подряд с выполненными задачами",
                "icon": "🔥"
            })
        elif current_streak >= 3:
            achievements.append({
                "name": "Начало пути",
                "description": "3 дня подряд с выполненными задачами",
                "icon": "🚀"
            })
        
        # Time tracking achievements
        if total_time >= 40:
            achievements.append({
                "name": "Трудоголик",
                "description": "40+ часов работы за неделю",
                "icon": "💼"
            })
        elif total_time >= 20:
            achievements.append({
                "name": "Баланс",
                "description": "20+ часов продуктивной работы",
                "icon": "⚖️"
            })
        
        return achievements