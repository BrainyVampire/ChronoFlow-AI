from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timedelta
import json

from .schemas import (
    TaskCreate, TaskUpdate, TaskResponse,
    CalendarSyncRequest, MeetingCreateRequest,
    AnalyticsRequest, ReportResponse,
    UserCreate, UserResponse
)
from database.crud import Database
from services.analytics_service import AnalyticsService
from services.report_generator import ReportGenerator
from .auth import verify_api_key, get_current_user

router = APIRouter()
security = HTTPBearer()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new task via API"""
    user = await verify_api_key(credentials.credentials, db)
    
    if 'create:tasks' not in user['permissions']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Create task
    created_task = await db.create_task(
        user_id=user['id'],
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority,
        category=task.category,
        tags=task.tags,
        estimated_duration=task.estimated_duration
    )
    
    return TaskResponse.from_orm(created_task)

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's tasks with filters"""
    user = await verify_api_key(credentials.credentials, db)
    
    filters = {}
    if status:
        filters['status'] = status
    if category:
        filters['category'] = category
    if priority:
        filters['priority'] = priority
    
    tasks = await db.get_user_tasks(
        user_id=user['id'],
        start_date=start_date,
        end_date=end_date,
        **filters
    )
    
    return [TaskResponse.from_orm(task) for task in tasks]

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a task"""
    user = await verify_api_key(credentials.credentials, db)
    
    # Check if user owns the task
    task = await db.get_task(task_id)
    if not task or task.user_id != user['id']:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if 'edit:tasks' not in user['permissions']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    updated_task = await db.update_task(task_id, **task_update.dict(exclude_unset=True))
    return TaskResponse.from_orm(updated_task)

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a task"""
    user = await verify_api_key(credentials.credentials, db)
    
    task = await db.get_task(task_id)
    if not task or task.user_id != user['id']:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if 'delete:tasks' not in user['permissions']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    await db.delete_task(task_id)
    return {"message": "Task deleted successfully"}

@router.post("/calendars/sync")
async def sync_calendar(
    sync_request: CalendarSyncRequest,
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Sync with external calendar"""
    user = await verify_api_key(credentials.credentials, db)
    
    # Implementation depends on calendar service
    # This would trigger sync with Google Calendar, Outlook, etc.
    
    return {"message": "Calendar sync initiated", "sync_id": "sync_123"}

@router.post("/meetings")
async def create_meeting(
    meeting_request: MeetingCreateRequest,
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a meeting with video conference"""
    user = await verify_api_key(credentials.credentials, db)
    
    # Choose meeting service based on request
    if meeting_request.service == "zoom":
        # Use Zoom integration
        pass
    elif meeting_request.service == "google_meet":
        # Use Google Meet integration
        pass
    elif meeting_request.service == "teams":
        # Use Teams integration
        pass
    
    return {"message": "Meeting created", "meeting_id": "meet_123"}

@router.get("/analytics")
async def get_analytics(
    period: str = Query("week"),
    metrics: List[str] = Query(["completion_rate", "time_tracked"]),
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get analytics data"""
    user = await verify_api_key(credentials.credentials, db)
    
    analytics_service = AnalyticsService(db.session)
    
    if period == "week":
        days_back = 7
    elif period == "month":
        days_back = 30
    elif period == "quarter":
        days_back = 90
    else:
        days_back = 7
    
    analytics_data = await analytics_service.calculate_user_productivity(
        user['id'], days_back
    )
    
    # Filter metrics if requested
    if metrics:
        filtered_data = {}
        for metric in metrics:
            if metric in analytics_data:
                filtered_data[metric] = analytics_data[metric]
        return filtered_data
    
    return analytics_data

@router.get("/reports/weekly")
async def get_weekly_report(
    format: str = Query("json"),
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Generate weekly report"""
    user = await verify_api_key(credentials.credentials, db)
    
    analytics_service = AnalyticsService(db.session)
    report_generator = ReportGenerator()
    
    analytics_data = await analytics_service.generate_weekly_report(user['id'])
    
    if format == "pdf":
        # Generate PDF report
        pdf_data = await report_generator.generate_productivity_report_pdf(
            analytics_data,
            {"name": user.get('name', 'User')}
        )
        
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=weekly_report.pdf"}
        )
    else:
        # Return JSON
        return analytics_data

@router.post("/webhooks/calendar")
async def handle_calendar_webhook(
    request: Request,
    db: Database = Depends()
):
    """Handle incoming calendar webhooks"""
    payload = await request.json()
    headers = dict(request.headers)
    
    # Verify webhook signature
    webhook_manager = WebhookManager(db.session)
    
    signature = headers.get('X-Goog-Signature') or headers.get('X-Outlook-Signature')
    
    if signature:
        body = await request.body()
        secret = config.WEBHOOK_SECRET
        
        if not await webhook_manager.verify_signature(body, signature, secret):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook based on source
    if 'X-Goog-Channel-ID' in headers:
        await webhook_manager.handle_google_calendar_webhook(payload, headers)
    elif 'X-Outlook-Channel-ID' in headers:
        await webhook_manager.handle_outlook_webhook(payload, headers)
    
    return {"status": "processed"}

@router.post("/ai/schedule")
async def ai_schedule_assistant(
    tasks: List[TaskCreate],
    constraints: Dict,
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """AI-powered scheduling assistant"""
    user = await verify_api_key(credentials.credentials, db)
    
    # Check if user has AI feature access
    if user['subscription_tier'] != 'premium':
        raise HTTPException(status_code=402, detail="AI features require premium subscription")
    
    ai_service = AIService(config.OPENAI_API_KEY)
    
    # Get busy slots from user's calendar
    busy_slots = await db.get_user_busy_slots(
        user['id'],
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7)
    )
    
    # Get AI scheduling suggestions
    suggestions = await ai_service.suggest_optimal_schedule(
        tasks,
        busy_slots,
        user.get('preferences', {})
    )
    
    return {"suggestions": suggestions}

@router.get("/collaborative/projects")
async def get_collaborative_projects(
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get collaborative projects"""
    user = await verify_api_key(credentials.credentials, db)
    
    projects = await db.get_user_projects(user['id'])
    
    return {"projects": projects}

@router.post("/collaborative/projects/{project_id}/tasks")
async def create_collaborative_task(
    project_id: int,
    task: TaskCreate,
    db: Database = Depends(),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create task in collaborative project"""
    user = await verify_api_key(credentials.credentials, db)
    
    # Check if user has access to project
    has_access = await db.check_project_access(user['id'], project_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="No access to project")
    
    # Create collaborative task
    task_data = task.dict()
    task_data['project_id'] = project_id
    
    created_task = await db.create_task(**task_data)
    
    # Notify project members
    await db.notify_project_members(
        project_id,
        f"New task created: {task.title}",
        user['id']
    )
    
    return TaskResponse.from_orm(created_task)