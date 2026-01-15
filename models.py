from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text, Float, Table, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

# Association tables for many-to-many relationships
task_collaborators = Table(
    'task_collaborators', Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id')),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role', String(20), default='viewer'),  # owner, editor, viewer
    Column('joined_at', DateTime, default=datetime.utcnow)
)

shared_calendar_members = Table(
    'shared_calendar_members', Base.metadata,
    Column('calendar_id', Integer, ForeignKey('calendars.id')),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role', String(20), default='member'),
    Column('joined_at', DateTime, default=datetime.utcnow)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    phone = Column(String(20))
    
    # Subscription
    subscription_tier = Column(String(20), default='free')  # free, premium, business
    subscription_until = Column(DateTime, nullable=True)
    features = Column(JSON, default=lambda: {})
    
    # Settings
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="ru")
    notification_settings = Column(JSON, default=lambda: {
        'email': False,
        'push': True,
        'telegram': True,
        'digest_frequency': 'daily'  # daily, weekly, never
    })
    
    # Analytics
    total_tasks_created = Column(Integer, default=0)
    total_tasks_completed = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    calendars = relationship("Calendar", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("TaskTemplate", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("UserAnalytics", back_populates="user", uselist=False)
    api_keys = relationship("APIKey", back_populates="user")
    teams = relationship("TeamMember", back_populates="user")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime, nullable=False)
    
    # Task details
    priority = Column(Integer, default=3)  # 1-5, where 1 is highest
    category = Column(String(100))
    tags = Column(ARRAY(String), default=[])
    estimated_duration = Column(Integer)  # minutes
    actual_duration = Column(Integer)  # minutes
    
    # Status
    status = Column(String(20), default='pending')  # pending, in_progress, completed, cancelled
    completion_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    
    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(JSON, nullable=True)  # RRULE string or custom rule
    recurrence_end_date = Column(DateTime, nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    
    # Calendar integration
    calendar_event_id = Column(String(500), nullable=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id"), nullable=True)
    
    # Meeting integration
    meeting_id = Column(String(500), nullable=True)
    meeting_type = Column(String(20), nullable=True)  # zoom, google_meet, teams
    meeting_url = Column(String(500), nullable=True)
    
    # AI data
    ai_generated = Column(Boolean, default=False)
    ai_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reminder_times = Column(JSON, default=lambda: [])
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    calendar = relationship("Calendar", back_populates="tasks")
    subtasks = relationship("SubTask", back_populates="parent_task", cascade="all, delete-orphan")
    parent_task = relationship("Task", remote_side=[id], backref="recurring_instances")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")
    collaborators = relationship("User", secondary=task_collaborators, backref="collaborative_tasks")

class SubTask(Base):
    __tablename__ = "subtasks"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    title = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    
    parent_task = relationship("Task", back_populates="subtasks")

class TaskTemplate(Base):
    __tablename__ = "task_templates"
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    default_duration = Column(Integer, default=60)
    default_priority = Column(Integer, default=3)
    default_category = Column(String(100))
    default_tags = Column(ARRAY(String), default=[])
    default_reminders = Column(JSON, default=lambda: [5, 15, 30])
    recurrence_rule = Column(JSON, nullable=True)
    is_public = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="templates")

class Calendar(Base):
    __tablename__ = "calendars"
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Calendar info
    service = Column(String(50), nullable=False)  # google, outlook, yandex, apple
    calendar_id = Column(String(500), nullable=False)
    name = Column(String(255))
    description = Column(Text)
    color = Column(String(7), default="#4285F4")
    timezone = Column(String(50))
    
    # Permissions
    is_primary = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    sync_enabled = Column(Boolean, default=True)
    sync_direction = Column(String(10), default='bidirectional')  # to_calendar, from_calendar, bidirectional
    
    # OAuth tokens (encrypted)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime)
    
    # Webhook
    webhook_id = Column(String(500), nullable=True)
    webhook_expiry = Column(DateTime, nullable=True)
    resource_id = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="calendars")
    tasks = relationship("Task", back_populates="calendar")
    shared_with = relationship("User", secondary=shared_calendar_members, backref="shared_calendars")

class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, default=lambda: {
        'default_timezone': 'UTC',
        'working_hours': {'start': '09:00', 'end': '18:00'},
        'weekends': [5, 6]  # Saturday, Sunday
    })
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="team", cascade="all, delete-orphan")

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default='member')  # owner, admin, member
    permissions = Column(JSON, default=lambda: {
        'create_tasks': True,
        'edit_tasks': True,
        'delete_tasks': False,
        'manage_members': False
    })
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="teams")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    color = Column(String(7), default="#4CAF50")
    status = Column(String(20), default='active')  # active, completed, archived
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    progress = Column(Float, default=0.0)  # 0-100
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    team = relationship("Team", back_populates="projects")
    user = relationship("User")

class TimeEntry(Base):
    __tablename__ = "time_entries"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer)  # seconds
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="time_entries")
    user = relationship("User")

class TaskAttachment(Base):
    __tablename__ = "task_attachments"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    file_url = Column(String(500))
    thumbnail_url = Column(String(500), nullable=True)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="attachments")
    user = relationship("User")

class UserAnalytics(Base):
    __tablename__ = "user_analytics"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Productivity metrics
    avg_completion_time = Column(Float, default=0.0)
    completion_rate = Column(Float, default=0.0)
    peak_productivity_hours = Column(JSON, default=lambda: {})
    
    # Task distribution
    tasks_by_category = Column(JSON, default=lambda: {})
    tasks_by_priority = Column(JSON, default=lambda: {})
    tasks_by_status = Column(JSON, default=lambda: {})
    
    # Time tracking
    total_time_tracked = Column(Integer, default=0)  # seconds
    avg_daily_time = Column(Float, default=0.0)
    
    # Calendar usage
    calendar_sync_count = Column(Integer, default=0)
    meeting_count = Column(Integer, default=0)
    
    # Collaboration
    collaborative_tasks_count = Column(Integer, default=0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="analytics")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(64), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    permissions = Column(JSON, default=lambda: ['read:tasks', 'create:tasks'])
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="api_keys")

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True)
    webhook_id = Column(String(100), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)