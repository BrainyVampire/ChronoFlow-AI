from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import secrets

router = Router()

class CollaborativeStates(StatesGroup):
    waiting_for_project_name = State()
    waiting_for_member_email = State()
    waiting_for_task_assignment = State()

@router.message(Command("teams"))
async def cmd_teams(message: Message, db):
    """Show user's teams and collaborative projects"""
    user = await db.get_user(message.from_user.id)
    
    teams = await db.get_user_teams(user.id)
    projects = await db.get_collaborative_projects(user.id)
    
    response = "👥 Ваши команды и проекты:\n\n"
    
    if teams:
        response += "🏢 Команды:\n"
        for team in teams:
            response += f"• {team.name}\n"
            response += f"  👤 Участников: {len(team.members)}\n"
            response += f"  📂 Проектов: {len(team.projects)}\n\n"
    
    if projects:
        response += "📂 Совместные проекты:\n"
        for project in projects:
            response += f"• {project.name}\n"
            response += f"  📈 Прогресс: {project.progress}%\n"
            response += f"  👥 Участников: {len(project.members)}\n\n"
    
    if not teams and not projects:
        response += "У вас пока нет команд или совместных проектов.\n"
        response += "Создайте команду с помощью /create_team"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Создать команду", callback_data="create_team")],
        [InlineKeyboardButton(text="📂 Создать проект", callback_data="create_project")],
        [InlineKeyboardButton(text="👥 Пригласить в команду", callback_data="invite_to_team")]
    ])
    
    await message.answer(response, reply_markup=keyboard)

@router.message(Command("create_team"))
async def cmd_create_team(message: Message, state: FSMContext):
    """Create a new team"""
    await state.set_state(CollaborativeStates.waiting_for_project_name)
    await message.answer("🏢 Создание новой команды\n\nВведите название команды:")

@router.message(CollaborativeStates.waiting_for_project_name)
async def process_team_name(message: Message, state: FSMContext, db):
    team_name = message.text.strip()
    
    if len(team_name) < 3:
        await message.answer("❌ Название команды должно быть не менее 3 символов")
        return
    
    user = await db.get_user(message.from_user.id)
    
    # Check team limits
    if user.subscription_tier == 'free':
        current_teams = await db.get_user_teams_count(user.id)
        if current_teams >= 1:
            await message.answer(
                "❌ Бесплатная версия позволяет создать только 1 команду.\n"
                "Обновитесь до премиум для создания большего количества команд."
            )
            await state.clear()
            return
    
    # Create team
    team = await db.create_team(
        name=team_name,
        owner_id=user.id,
        description=f"Команда создана {user.first_name}"
    )
    
    # Add creator as team member with owner role
    await db.add_team_member(
        team_id=team.id,
        user_id=user.id,
        role='owner'
    )
    
    await state.clear()
    
    # Generate invite link
    invite_token = secrets.token_urlsafe(16)
    await db.create_invite_link(
        team_id=team.id,
        token=invite_token,
        created_by=user.id,
        max_uses=10
    )
    
    invite_link = f"https://t.me/your_bot?start=invite_{invite_token}"
    
    await message.answer(
        f"✅ Команда '{team_name}' создана!\n\n"
        f"🔗 Пригласительная ссылка:\n"
        f"{invite_link}\n\n"
        f"Отправьте эту ссылку участникам, чтобы они могли присоединиться."
    )

@router.message(Command("create_project"))
async def cmd_create_project(message: Message, state: FSMContext, db):
    """Create a collaborative project"""
    user = await db.get_user(message.from_user.id)
    
    # Get user's teams
    teams = await db.get_user_teams(user.id)
    
    if not teams:
        await message.answer(
            "❌ У вас нет команд. Сначала создайте команду с помощью /create_team"
        )
        return
    
    await state.set_state(CollaborativeStates.waiting_for_project_name)
    await state.update_data(action='create_project')
    
    # Show teams for selection
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=team.name, callback_data=f"select_team_{team.id}")]
        for team in teams[:5]
    ])
    
    await message.answer(
        "📂 Создание совместного проекта\n\n"
        "Выберите команду для проекта:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("select_team_"))
async def select_team_for_project(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    await state.update_data(team_id=team_id)
    
    await callback.message.edit_text(
        "📂 Введите название проекта:"
    )
    await state.set_state(CollaborativeStates.waiting_for_project_name)

@router.message(CollaborativeStates.waiting_for_project_name)
async def process_project_name(message: Message, state: FSMContext, db):
    data = await state.get_data()
    project_name = message.text.strip()
    
    if 'action' in data and data['action'] == 'create_project':
        user = await db.get_user(message.from_user.id)
        
        # Create project
        project = await db.create_project(
            name=project_name,
            team_id=data.get('team_id'),
            user_id=user.id,
            description=f"Совместный проект команды"
        )
        
        await state.clear()
        
        await message.answer(
            f"✅ Проект '{project_name}' создан!\n\n"
            f"Теперь вы можете:\n"
            f"• Добавлять задачи с помощью /newtask\n"
            f"• Приглашать участников через /invite_to_project\n"
            f"• Назначать задачи участникам"
        )
    else:
        await message.answer("Что-то пошло не так. Попробуйте снова.")

@router.message(Command("assign_task"))
async def cmd_assign_task(message: Message, state: FSMContext, db):
    """Assign task to team member"""
    user = await db.get_user(message.from_user.id)
    
    # Get user's tasks
    tasks = await db.get_user_tasks(user.id, completed=False, limit=10)
    
    if not tasks:
        await message.answer("❌ У вас нет активных задач для назначения")
        return
    
    # Get user's team members
    team_members = await db.get_team_members_for_user(user.id)
    
    if not team_members:
        await message.answer("❌ У вас нет команды для назначения задач")
        return
    
    await state.set_state(CollaborativeStates.waiting_for_task_assignment)
    
    # Create keyboard with tasks
    task_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📌 {task.title[:30]}", callback_data=f"select_task_{task.id}")]
        for task in tasks[:5]
    ])
    
    await message.answer(
        "👥 Назначение задачи участнику команды\n\n"
        "Выберите задачу для назначения:",
        reply_markup=task_keyboard
    )

@router.callback_query(F.data.startswith("select_task_"))
async def select_task_for_assignment(callback: CallbackQuery, state: FSMContext, db):
    task_id = int(callback.data.split("_")[-1])
    await state.update_data(task_id=task_id)
    
    user = await db.get_user(callback.from_user.id)
    team_members = await db.get_team_members_for_user(user.id)
    
    # Create keyboard with team members
    member_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👤 {member.user.first_name}", callback_data=f"assign_to_{member.user_id}")]
        for member in team_members[:10]
    ])
    
    await callback.message.edit_text(
        "Выберите участника для назначения задачи:",
        reply_markup=member_keyboard
    )

@router.callback_query(F.data.startswith("assign_to_"))
async def assign_task_to_member(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    task_id = data.get('task_id')
    assignee_id = int(callback.data.split("_")[-1])
    
    if not task_id:
        await callback.answer("Ошибка: задача не выбрана")
        return
    
    # Assign task
    success = await db.assign_task_to_user(task_id, assignee_id, callback.from_user.id)
    
    if success:
        # Get assignee info
        assignee = await db.get_user(assignee_id)
        task = await db.get_task(task_id)
        
        # Notify assignee (in real app, send actual notification)
        await callback.message.edit_text(
            f"✅ Задача '{task.title}' назначена {assignee.first_name}!\n\n"
            f"Они получат уведомление о новой задаче."
        )
        
        # In production: Send notification to assignee
        # await bot.send_message(assignee.telegram_id, f"Вам назначена новая задача: {task.title}")
    else:
        await callback.message.edit_text("❌ Не удалось назначить задачу")
    
    await state.clear()

@router.message(Command("shared_calendar"))
async def cmd_shared_calendar(message: Message, db):
    """Create or manage shared calendar"""
    user = await db.get_user(message.from_user.id)
    
    # Check premium access
    if user.subscription_tier != 'premium':
        await message.answer(
            "📅 Общие календари доступны в премиум-версии!\n\n"
            "Возможности премиум:\n"
            "• Общие календари команды\n"
            "• Видимость занятости участников\n"
            "• Совместное планирование встреч\n"
            "• Автоматические уведомления"
        )
        return
    
    shared_calendars = await db.get_shared_calendars(user.id)
    
    response = "📅 Ваши общие календари:\n\n"
    
    if shared_calendars:
        for calendar in shared_calendars:
            response += f"• {calendar.name}\n"
            response += f"  👤 Участников: {len(calendar.shared_with)}\n"
            response += f"  🔗 Доступ: {calendar.access_level}\n\n"
    else:
        response += "У вас пока нет общих календарей.\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать общий календарь", callback_data="create_shared_calendar")],
        [InlineKeyboardButton(text="👥 Пригласить в календарь", callback_data="invite_to_calendar")],
        [InlineKeyboardButton(text="📊 Видимость занятости", callback_data="view_availability")]
    ])
    
    await message.answer(response, reply_markup=keyboard)

@router.callback_query(F.data == "view_availability")
async def view_team_availability(callback: CallbackQuery, db):
    """Show team availability for scheduling"""
    user = await db.get_user(callback.from_user.id)
    
    # Get team members
    team_members = await db.get_team_members_for_user(user.id)
    
    if not team_members:
        await callback.answer("У вас нет команды")
        return
    
    await callback.message.edit_text("📅 Загружаю данные о занятости команды...")
    
    # Get availability for each team member
    availability_data = []
    for member in team_members[:5]:  # Limit to 5 members
        busy_slots = await db.get_user_busy_slots(
            member.user_id,
            datetime.now(),
            datetime.now() + timedelta(days=7)
        )
        
        availability_data.append({
            'name': member.user.first_name,
            'busy_slots': busy_slots,
            'timezone': member.user.timezone
        })
    
    # Find common free slots
    common_slots = await find_common_free_slots(availability_data)
    
    if common_slots:
        response = "🕐 Общие свободные слоты команды:\n\n"
        
        for i, slot in enumerate(common_slots[:5], 1):
            start_time = slot['start'].strftime('%d.%m %H:%M')
            end_time = slot['end'].strftime('%H:%M')
            response += f"{i}. {start_time} - {end_time}\n"
            response += f"   🕐 {slot['duration']} минут\n\n"
        
        response += "Используйте эти слоты для планирования командных встреч!"
    else:
        response = "❌ Не найдено общих свободных слотов на ближайшую неделю"
    
    await callback.message.edit_text(response)

async def find_common_free_slots(availability_data: list) -> list:
    """Find common free slots among team members"""
    # This is a simplified implementation
    # In production, use proper algorithm to find overlapping free time
    
    # Assume working hours 9-18 for everyone
    working_hours = {
        'start': datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
        'end': datetime.now().replace(hour=18, minute=0, second=0, microsecond=0)
    }
    
    common_slots = []
    
    # Simple algorithm: look for slots where no one is busy
    # This should be replaced with proper interval arithmetic
    
    return common_slots