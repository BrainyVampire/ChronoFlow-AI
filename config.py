import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    ADMIN_IDS: list = list(map(int, os.getenv("ADMIN_IDS", "").split(',')))
    
    # Database
    DB_URL: str = os.getenv("DB_URL", "postgresql+asyncpg://user:pass@localhost/scheduler_bot")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Google APIs
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/callback")
    
    # Microsoft APIs
    MICROSOFT_CLIENT_ID: str = os.getenv("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: str = os.getenv("MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT_ID: str = os.getenv("MICROSOFT_TENANT_ID")
    
    # Zoom API
    ZOOM_CLIENT_ID: str = os.getenv("ZOOM_CLIENT_ID")
    ZOOM_CLIENT_SECRET: str = os.getenv("ZOOM_CLIENT_SECRET")
    
    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # Webhooks
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "https://yourdomain.com/webhook")
    
    # Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Scheduler
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY")
    
    # Limits
    MAX_TASKS_FREE: int = 50
    MAX_CALENDARS_FREE: int = 1
    MAX_COLLABORATORS_FREE: int = 3
    REMINDER_INTERVALS_FREE: list = [5, 15, 30]
    
    # Premium features
    PREMIUM_FEATURES: dict = {
        'ai_assistant': True,
        'advanced_analytics': True,
        'unlimited_calendars': True,
        'team_collaboration': True,
        'custom_templates': True,
        'api_access': True,
        'priority_support': True
    }

config = Config()