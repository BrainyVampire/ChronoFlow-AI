import openai
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        self.model = "gpt-4"  # or "gpt-3.5-turbo" for faster/cheaper responses
    
    async def parse_natural_language(self, text: str, user_context: Dict = None) -> Dict:
        """
        Parse natural language input into structured task data
        Example: "Meeting with John tomorrow at 3pm about project"
        """
        prompt = self._create_parsing_prompt(text, user_context)
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a task parsing assistant. Extract task details from natural language."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                functions=[
                    {
                        "name": "create_task",
                        "description": "Create a task from parsed information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Task title"},
                                "description": {"type": "string", "description": "Task description"},
                                "due_date": {"type": "string", "description": "Due date in ISO format"},
                                "priority": {"type": "integer", "description": "Priority 1-5"},
                                "category": {"type": "string", "description": "Task category"},
                                "estimated_duration": {"type": "integer", "description": "Duration in minutes"},
                                "tags": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["title"]
                        }
                    }
                ],
                function_call={"name": "create_task"}
            )
            
            # Parse response
            message = response.choices[0].message
            if message.function_call:
                return json.loads(message.function_call.arguments)
            
        except Exception as e:
            logger.error(f"Error parsing natural language: {e}")
        
        return {"title": text}
    
    def _create_parsing_prompt(self, text: str, user_context: Dict) -> str:
        """Create prompt for natural language parsing"""
        context_str = ""
        if user_context:
            context_str = f"\nUser context: Timezone: {user_context.get('timezone', 'UTC')}, "
            context_str += f"Working hours: {user_context.get('working_hours', '9-18')}"
        
        return f"""
        Parse the following task description into structured data:
        
        Input: "{text}"
        {context_str}
        
        Today's date: {datetime.now().strftime('%Y-%m-%d')}
        
        Extract:
        1. Title (concise, clear)
        2. Description (if mentioned)
        3. Due date and time (convert to ISO 8601)
        4. Priority (1-5, 1 is highest)
        5. Category (work, personal, health, etc.)
        6. Estimated duration in minutes
        7. Relevant tags
        
        Handle relative dates like:
        - "tomorrow" -> next day
        - "next week" -> 7 days from now
        - "in 3 days" -> 3 days from now
        - "at 3pm" -> today at 3pm unless specified otherwise
        """
    
    async def suggest_optimal_schedule(self, tasks: List[Dict], 
                                      busy_slots: List[Dict],
                                      preferences: Dict) -> List[Dict]:
        """
        Suggest optimal schedule using AI
        """
        prompt = self._create_scheduling_prompt(tasks, busy_slots, preferences)
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a scheduling assistant. Optimize task scheduling based on priorities, deadlines, and available time."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            schedule_text = response.choices[0].message.content
            return self._parse_schedule_response(schedule_text)
            
        except Exception as e:
            logger.error(f"Error suggesting schedule: {e}")
            return []
    
    def _create_scheduling_prompt(self, tasks: List[Dict], busy_slots: List[Dict], 
                                preferences: Dict) -> str:
        """Create prompt for scheduling optimization"""
        tasks_str = "\n".join([
            f"- {t['title']} (Priority: {t['priority']}, Duration: {t['estimated_duration']}min, "
            f"Deadline: {t['due_date']})"
            for t in tasks
        ])
        
        busy_str = "\n".join([
            f"- {s['start']} to {s['end']}: {s['description']}"
            for s in busy_slots
        ])
        
        return f"""
        Optimize task scheduling with these constraints:
        
        Tasks to schedule:
        {tasks_str}
        
        Busy slots (cannot schedule here):
        {busy_str}
        
        User preferences:
        - Preferred working hours: {preferences.get('working_hours', '9:00-18:00')}
        - Timezone: {preferences.get('timezone', 'UTC')}
        - Break between tasks: {preferences.get('break_between_tasks', 15)} minutes
        - Focus on high priority tasks first
        
        Create a schedule that:
        1. Respects deadlines
        2. Prioritizes high-priority tasks
        3. Fits within working hours
        4. Includes breaks
        5. Avoids scheduling during busy slots
        
        Return schedule in JSON format with start times for each task.
        """
    
    async def generate_task_insights(self, tasks: List[Dict], analytics: Dict) -> Dict:
        """
        Generate insights and recommendations based on task history
        """
        prompt = f"""
        Analyze task history and provide insights:
        
        Task Statistics:
        - Total tasks: {analytics.get('total_tasks', 0)}
        - Completion rate: {analytics.get('completion_rate', 0)}%
        - Average completion time: {analytics.get('avg_completion_time', 0)} hours
        
        Recent tasks:
        {json.dumps(tasks[-10:], indent=2)}
        
        Provide:
        1. Productivity patterns
        2. Suggestions for improvement
        3. Estimated time for upcoming tasks
        4. Warning about potential overload
        5. Recommendations for delegation
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a productivity coach analyzing task patterns."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            return {
                "insights": response.choices[0].message.content,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {}
    
    async def auto_categorize_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """
        Auto-categorize tasks using AI
        """
        # Batch process tasks for efficiency
        categorized = []
        
        for task in tasks:
            if not task.get('category'):
                category = await self._predict_category(task['title'], task.get('description', ''))
                task['category'] = category
                categorized.append(task)
        
        return categorized
    
    async def _predict_category(self, title: str, description: str) -> str:
        """Predict task category using AI"""
        prompt = f"""
        Categorize this task:
        Title: {title}
        Description: {description}
        
        Choose from: work, personal, health, education, finance, home, social, shopping, other
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You categorize tasks into predefined categories."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            category = response.choices[0].message.content.strip().lower()
            return category
            
        except Exception as e:
            logger.error(f"Error predicting category: {e}")
            return "other"
    
    async def generate_smart_reminders(self, task: Dict) -> List[Dict]:
        """
        Generate smart reminder times based on task properties
        """
        reminders = []
        
        # Base reminders
        base_times = [5, 15, 30, 60]  # minutes before
        
        # Adjust based on task priority
        if task.get('priority', 3) <= 2:  # High priority
            base_times.extend([120, 360])  # 2 hours, 6 hours before
        
        # Add reminder for complex tasks
        if task.get('estimated_duration', 0) > 120:  # More than 2 hours
            base_times.extend([1440, 2880])  # 1 day, 2 days before
        
        for minutes in base_times:
            reminder_time = task['due_date'] - timedelta(minutes=minutes)
            if reminder_time > datetime.now():
                reminders.append({
                    'minutes_before': minutes,
                    'time': reminder_time,
                    'message': self._generate_reminder_message(task, minutes)
                })
        
        return reminders
    
    def _generate_reminder_message(self, task: Dict, minutes_before: int) -> str:
        """Generate personalized reminder message"""
        if minutes_before >= 1440:
            days = minutes_before // 1440
            return f"📅 Напоминание: {task['title']} через {days} дней"
        elif minutes_before >= 60:
            hours = minutes_before // 60
            return f"⏰ Напоминание: {task['title']} через {hours} часов"
        else:
            return f"🔔 Напоминание: {task['title']} через {minutes_before} минут"