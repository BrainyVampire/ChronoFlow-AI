import io
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import seaborn as sns
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        matplotlib.use('Agg')  # Non-interactive backend
        sns.set_style("whitegrid")
    
    async def generate_productivity_report_pdf(self, analytics_data: Dict, 
                                             user_info: Dict) -> bytes:
        """Generate PDF productivity report"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2C3E50')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#3498DB')
        )
        
        # Title
        story.append(Paragraph("Отчет о продуктивности", title_style))
        story.append(Spacer(1, 12))
        
        # User info and period
        user_text = f"Пользователь: {user_info.get('name', '')}<br/>"
        user_text += f"Период: {analytics_data['period']['start']} - {analytics_data['period']['end']}<br/>"
        user_text += f"Всего дней: {analytics_data['period']['days']}"
        story.append(Paragraph(user_text, styles["Normal"]))
        story.append(Spacer(1, 20))
        
        # Key metrics section
        story.append(Paragraph("Ключевые метрики", heading_style))
        
        metrics = analytics_data["task_metrics"]
        metrics_table = [
            ["Метрика", "Значение"],
            ["Всего задач", str(metrics["total_tasks"])],
            ["Выполнено задач", str(metrics["completed_tasks"])],
            ["Процент выполнения", f"{metrics['completion_rate']}%"],
            ["Среднее время выполнения", f"{analytics_data['time_metrics']['avg_completion_hours']} ч"]
        ]
        
        table = Table(metrics_table, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Generate and add charts
        charts = await self._generate_charts(analytics_data)
        
        for chart_name, chart_data in charts.items():
            story.append(Paragraph(chart_name, heading_style))
            chart_img = Image(chart_data, width=6*inch, height=3*inch)
            story.append(chart_img)
            story.append(Spacer(1, 20))
        
        # Insights section
        if "insights" in analytics_data:
            story.append(Paragraph("Инсайты", heading_style))
            for insight in analytics_data["insights"][:5]:  # Top 5 insights
                story.append(Paragraph(f"• {insight}", styles["Normal"]))
                story.append(Spacer(1, 5))
        
        # Recommendations section
        if "recommendations" in analytics_data:
            story.append(Paragraph("Рекомендации", heading_style))
            for rec in analytics_data["recommendations"][:3]:  # Top 3 recommendations
                story.append(Paragraph(f"→ {rec}", styles["Normal"]))
                story.append(Spacer(1, 5))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    async def _generate_charts(self, analytics_data: Dict) -> Dict:
        """Generate charts for the report"""
        charts = {}
        
        # 1. Completion rate chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        categories = list(analytics_data["distributions"]["by_category"].keys())[:8]
        values = list(analytics_data["distributions"]["by_category"].values())[:8]
        
        bars = ax.bar(categories, values, color=sns.color_palette("viridis", len(categories)))
        ax.set_title("Распределение задач по категориям")
        ax.set_ylabel("Количество задач")
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png', dpi=100)
        chart_buffer.seek(0)
        charts["Распределение по категориям"] = chart_buffer
        plt.close(fig)
        
        # 2. Hourly productivity chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        hourly_data = analytics_data["hourly_productivity"]
        hours = [data["hour"] for data in hourly_data.values()]
        scores = [data["productivity_score"] for data in hourly_data.values()]
        
        ax.plot(hours, scores, marker='o', linewidth=2, color='#E74C3C')
        ax.fill_between(hours, scores, alpha=0.3, color='#E74C3C')
        ax.set_title("Продуктивность по часам")
        ax.set_ylabel("Оценка продуктивности")
        ax.set_xlabel("Время суток")
        ax.grid(True, alpha=0.3)
        
        # Highlight peak hours
        max_score = max(scores)
        max_index = scores.index(max_score)
        ax.annotate(f'Пик: {max_score}', 
                   xy=(hours[max_index], max_score),
                   xytext=(hours[max_index], max_score + 10),
                   arrowprops=dict(arrowstyle='->', color='black'))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png', dpi=100)
        chart_buffer.seek(0)
        charts["Продуктивность по часам"] = chart_buffer
        plt.close(fig)
        
        # 3. Priority distribution pie chart
        fig, ax = plt.subplots(figsize=(8, 8))
        
        priority_data = analytics_data["distributions"]["by_priority"]
        labels = [f"Приоритет {p}" for p in sorted(priority_data.keys())]
        sizes = [priority_data[p] for p in sorted(priority_data.keys())]
        colors_list = ['#FF6B6B', '#FFA726', '#42A5F5', '#66BB6A', '#AB47BC']
        
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            colors=colors_list[:len(sizes)],
            autopct='%1.1f%%',
            startangle=90
        )
        
        ax.set_title("Распределение по приоритетам")
        
        plt.tight_layout()
        
        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png', dpi=100)
        chart_buffer.seek(0)
        charts["Распределение по приоритетам"] = chart_buffer
        plt.close(fig)
        
        return charts
    
    async def generate_weekly_digest(self, user_id: int, analytics_data: Dict) -> str:
        """Generate weekly digest text for messaging"""
        metrics = analytics_data["task_metrics"]
        time_metrics = analytics_data["time_metrics"]
        streaks = analytics_data["streaks"]
        
        digest = f"📊 Еженедельный дайджест\n\n"
        digest += f"📈 За неделю вы:\n"
        digest += f"• Создали {metrics['total_tasks']} задач\n"
        digest += f"• Выполнили {metrics['completed_tasks']} ({metrics['completion_rate']}%)\n"
        digest += f"• Отследили {time_metrics['total_time_tracked_hours']} часов работы\n"
        digest += f"• Среднее время выполнения: {time_metrics['avg_completion_hours']} ч\n\n"
        
        if streaks['current'] > 0:
            digest += f"🔥 Текущая серия: {streaks['current']} дней подряд!\n"
            digest += f"🏆 Самая длинная серия: {streaks['longest']} дней\n\n"
        
        # Top categories
        categories = analytics_data["distributions"]["by_category"]
        if categories:
            top_category = max(categories.items(), key=lambda x: x[1])
            digest += f"🏷️ Самые активные категории:\n"
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]:
                digest += f"• {cat}: {count} задач\n"
            digest += "\n"
        
        # Peak hours
        hourly = analytics_data["hourly_productivity"]
        peak_hours = sorted(
            [(h, data["productivity_score"]) for h, data in hourly.items()],
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        if peak_hours:
            digest += f"⏰ Пик продуктивности:\n"
            for hour, score in peak_hours:
                digest += f"• {hour}: оценка {score}/100\n"
        
        return digest