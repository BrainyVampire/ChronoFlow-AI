from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import re

router = Router()

class AIAssistantStates(StatesGroup):
    waiting_for_natural_input = State()
    waiting_for_schedule_preferences = State()
    waiting_for_insight_type = State()

@router.message(Command("ai_schedule"))
async def cmd_ai_schedule(message: Message, state: FSMContext, db, ai_service):
    """AI-powered scheduling assistant"""
    user = await db.get_user(message.from_user.id)
    
    # Check premium access
    if user.subscription_tier != 'premium':
        await message.answer(
            "🤖 AI-ассистент доступен в премиум-версии!\n\n"
            "Обновите подписку для доступа к:\n"
            "• Умному планированию\n"
            "• Анализу продуктивности\n"
            "• Автоматической категоризации\n"
            "• Персональным рекомендациям\n\n"
            "Используйте /premium для обновления"
        )
        return
    
    await state.set_state(AIAssistantStates.waiting_for_natural_input)
    
    await message.answer(
        "🤖 AI-ассистент планирования\n\n"
        "Опишите ваши задачи на день в свободной форме:\n\n"
        "Примеры:\n"
        "• \"Встреча с клиентом в 14:00, подготовка отчета к 18:00\"\n"
        "• \"Завтра: утренняя пробежка в 7:00, работа с 9 до 12, обед, встреча в 15:00\"\n"
        "• \"Нужно сделать: позвонить маме, купить продукты, закончить проект\""
    )

@router.message(AIAssistantStates.waiting_for_natural_input)
async def process_natural_input(message: Message, state: FSMContext, db, ai_service):
    """Process natural language input"""
    await message.answer("🤔 Анализирую ваш запрос...")
    
    # Get user context
    user = await db.get_user(message.from_user.id)
    user_context = {
        'timezone': user.timezone,
        'working_hours': user.settings.get('working_hours', '9:00-18:00') if user.settings else '9:00-18:00'
    }
    
    # Parse with AI
    parsed_tasks = await ai_service.parse_natural_language(message.text, user_context)
    
    if not parsed_tasks:
        await message.answer("❌ Не удалось разобрать ваш запрос. Попробуйте сформулировать иначе.")
        await state.clear()
        return
    
    # Get busy slots from calendar
    busy_slots = await db.get_user_busy_slots(
        user.id,
        datetime.now(),
        datetime.now() + timedelta(days=2)
    )
    
    # Get AI scheduling suggestions
    suggestions = await ai_service.suggest_optimal_schedule(
        [parsed_tasks] if isinstance(parsed_tasks, dict) else parsed_tasks,
        busy_slots,
        user_context
    )
    
    # Present suggestions
    if suggestions:
        response = "🎯 Предлагаемое расписание:\n\n"
        
        for i, slot in enumerate(suggestions[:5], 1):
            start_time = datetime.fromisoformat(slot['start_time'])
            response += f"{i}. {start_time.strftime('%H:%M')} - {slot['task_title']}\n"
            if slot.get('estimated_duration'):
                end_time = start_time + timedelta(minutes=slot['estimated_duration'])
                response += f"   ⏱️ До {end_time.strftime('%H:%M')}\n"
            response += "\n"
        
        # Add action buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять расписание", callback_data="accept_schedule"),
                InlineKeyboardButton(text="✏️ Настроить", callback_data="adjust_schedule")
            ],
            [
                InlineKeyboardButton(text="📅 Посмотреть в календаре", callback_data="view_in_calendar")
            ]
        ])
        
        await message.answer(response, reply_markup=keyboard)
    else:
        await message.answer(
            "✅ Задачи разобраны! Но для составления расписания "
            "нужно знать ваши занятые слоты.\n\n"
            "Подключите календарь через /connect_calendar"
        )
    
    await state.clear()

@router.message(Command("ai_insights"))
async def cmd_ai_insights(message: Message, db, ai_service, analytics_service):
    """Get AI-generated insights"""
    user = await db.get_user(message.from_user.id)
    
    if user.subscription_tier != 'premium':
        await message.answer("Эта функция доступна в премиум-версии")
        return
    
    await message.answer("📊 Анализирую вашу продуктивность...")
    
    # Get analytics data
    analytics = await analytics_service.calculate_user_productivity(user.id, 30)
    
    # Get recent tasks
    tasks = await db.get_user_tasks(user.id, limit=20)
    
    # Generate insights
    insights = await ai_service.generate_task_insights(
        [{'title': t.title, 'category': t.category, 'priority': t.priority} for t in tasks],
        analytics
    )
    
    if insights:
        await message.answer(
            f"🎯 AI-инсайты по вашей продуктивности:\n\n"
            f"{insights.get('insights', 'Нет данных для анализа')}\n\n"
            f"📅 Сгенерировано: {insights.get('generated_at', '')}"
        )
    else:
        await message.answer("❌ Не удалось сгенерировать инсайты. Попробуйте позже.")

@router.message(Command("auto_categorize"))
async def cmd_auto_categorize(message: Message, db, ai_service):
    """Auto-categorize uncategorized tasks"""
    user = await db.get_user(message.from_user.id)
    
    # Get uncategorized tasks
    tasks = await db.get_uncategorized_tasks(user.id)
    
    if not tasks:
        await message.answer("✅ Все ваши задачи уже категоризированы!")
        return
    
    await message.answer(f"🤖 Автоматически категоризирую {len(tasks)} задач...")
    
    # Categorize with AI
    categorized = await ai_service.auto_categorize_tasks(
        [{'title': t.title, 'description': t.description} for t in tasks]
    )
    
    # Update tasks in database
    updated_count = 0
    for i, task in enumerate(tasks):
        if i < len(categorized):
            await db.update_task(task.id, category=categorized[i]['category'])
            updated_count += 1
    
    await message.answer(
        f"✅ Автоматически категоризировано {updated_count} задач!\n\n"
        f"Используйте /tasks для просмотра обновленного списка."
    )

@router.message(Command("smart_reminders"))
async def cmd_smart_reminders(message: Message, db, ai_service, scheduler):
    """Set up smart reminders for upcoming tasks"""
    user = await db.get_user(message.from_user.id)
    
    # Get upcoming tasks without reminders
    tasks = await db.get_upcoming_tasks_without_reminders(user.id, hours=24*7)
    
    if not tasks:
        await message.answer("✅ У всех предстоящих задач уже есть напоминания!")
        return
    
    await message.answer(f"🎯 Настраиваю умные напоминания для {len(tasks)} задач...")
    
    # Generate and set smart reminders
    for task in tasks:
        reminders = await ai_service.generate_smart_reminders({
            'title': task.title,
            'due_date': task.due_date,
            'priority': task.priority,
            'estimated_duration': task.estimated_duration
        })
        
        # Schedule reminders
        for reminder in reminders:
            await scheduler.add_task_reminder(
                task.id,
                user.id,
                reminder['time'],
                send_reminder,
                minutes_before=reminder['minutes_before']
            )
        
        # Update task with reminder times
        reminder_times = [r['time'].isoformat() for r in reminders]
        await db.update_task(task.id, reminder_times=reminder_times)
    
    await message.answer(
        f"✅ Настроены умные напоминания!\n\n"
        f"Напоминания будут учитывать:\n"
        f"• Приоритет задачи\n"
        f"• Сложность и продолжительность\n"
        f"• Время до дедлайна"
    )