import logging
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class WebhookManager:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.active_webhooks = {}
    
    async def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        digest = hmac.new(
            secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={digest}", signature)
    
    async def handle_google_calendar_webhook(self, payload: Dict, headers: Dict):
        """Handle Google Calendar webhook notifications"""
        try:
            # Verify it's a valid Google Calendar notification
            if headers.get('X-Goog-Resource-State') == 'sync':
                logger.info("Initial sync notification")
                return
            
            # Extract calendar ID and user ID from channel ID
            channel_id = headers.get('X-Goog-Channel-ID', '')
            resource_id = headers.get('X-Goog-Resource-ID', '')
            
            # Parse notification
            resource_state = headers.get('X-Goog-Resource-State')
            resource_uri = headers.get('X-Goog-Resource-URI', '')
            
            if resource_state in ['exists', 'not_exists']:
                # Handle calendar changes
                await self.sync_calendar_changes(channel_id, resource_uri)
            
            logger.info(f"Processed Google Calendar webhook: {resource_state}")
            
        except Exception as e:
            logger.error(f"Error handling Google webhook: {e}")
    
    async def sync_calendar_changes(self, channel_id: str, resource_uri: str):
        """Sync calendar changes with our database"""
        # Find calendar by webhook ID
        from database.crud import get_calendar_by_webhook_id
        calendar = await get_calendar_by_webhook_id(self.db_session, channel_id)
        
        if not calendar:
            logger.warning(f"Calendar not found for webhook: {channel_id}")
            return
        
        # Get updated events from Google Calendar
        creds = Credentials.from_authorized_user_info({
            'access_token': calendar.access_token,
            'refresh_token': calendar.refresh_token
        })
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Get events changed since last sync
        last_sync = calendar.updated_at or datetime.utcnow() - timedelta(hours=1)
        
        events_result = service.events().list(
            calendarId=calendar.calendar_id,
            timeMin=last_sync.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Sync events to tasks
        for event in events:
            await self.sync_event_to_task(calendar, event)
    
    async def sync_event_to_task(self, calendar, event: Dict):
        """Sync Google Calendar event to task"""
        from database.crud import get_or_create_task_from_event
        
        await get_or_create_task_from_event(
            self.db_session,
            calendar.user_id,
            event,
            calendar.id
        )
    
    async def create_google_calendar_watch(self, credentials: Dict, calendar_id: str, 
                                          user_id: int, webhook_url: str) -> Optional[str]:
        """Create watch subscription for Google Calendar"""
        try:
            creds = Credentials.from_authorized_user_info(credentials)
            service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
            
            # Generate unique channel ID
            channel_id = f"channel_{user_id}_{calendar_id}_{int(datetime.utcnow().timestamp())}"
            
            # Create watch request
            watch_request = {
                'id': channel_id,
                'type': 'web_hook',
                'address': webhook_url,
                'token': f"user_{user_id}",
                'expiration': int((datetime.utcnow() + timedelta(days=7)).timestamp() * 1000)
            }
            
            # Execute watch request
            result = service.events().watch(
                calendarId=calendar_id,
                body=watch_request
            ).execute()
            
            # Store webhook info
            webhook_info = {
                'resource_id': result.get('resourceId'),
                'resource_uri': result.get('resourceUri'),
                'expiration': result.get('expiration')
            }
            
            self.active_webhooks[channel_id] = webhook_info
            
            return channel_id
            
        except Exception as e:
            logger.error(f"Error creating Google Calendar watch: {e}")
            return None
    
    async def renew_webhook_subscription(self, channel_id: str, credentials: Dict):
        """Renew expiring webhook subscription"""
        try:
            # Google Calendar webhooks expire after 7 days
            # This method should be called periodically to renew them
            creds = Credentials.from_authorized_user_info(credentials)
            service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
            
            # Stop existing channel
            service.channels().stop(body={
                'id': channel_id,
                'resourceId': self.active_webhooks[channel_id]['resource_id']
            }).execute()
            
            # Create new watch
            # ... implementation similar to create_google_calendar_watch
            
        except Exception as e:
            logger.error(f"Error renewing webhook: {e}")
    
    async def handle_outlook_webhook(self, payload: Dict, validation_token: Optional[str] = None):
        """Handle Outlook calendar webhook"""
        if validation_token:
            # This is a subscription validation request
            return validation_token
        
        # Process actual notification
        for notification in payload.get('value', []):
            resource = notification.get('resource')
            change_type = notification.get('changeType')
            
            if resource and 'events' in resource:
                # Handle event changes
                await self.sync_outlook_event(resource, change_type)
    
    async def sync_outlook_event(self, resource: str, change_type: str):
        """Sync Outlook event changes"""
        # Implement Outlook event syncing
        pass