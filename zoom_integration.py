import jwt
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class ZoomIntegration:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.zoom.us/v2"
        self.access_token = None
        self.token_expiry = None
    
    async def get_access_token(self) -> str:
        """Get OAuth access token for Zoom"""
        if self.access_token and self.token_expiry and self.token_expiry > datetime.now():
            return self.access_token
        
        # Generate JWT token (for server-to-server apps)
        # Note: For production, use OAuth 2.0 with authorization code flow
        
        payload = {
            "iss": self.client_id,
            "exp": int(time.time()) + 3600
        }
        
        token = jwt.encode(payload, self.client_secret, algorithm="HS256")
        self.access_token = token
        self.token_expiry = datetime.now() + timedelta(hours=1)
        
        return token
    
    async def create_meeting(self, user_id: str, topic: str, start_time: datetime,
                           duration_minutes: int = 60, agenda: str = "",
                           timezone: str = "UTC", **kwargs) -> Optional[Dict]:
        """Create a Zoom meeting"""
        try:
            token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "topic": topic,
                "type": 2,  # Scheduled meeting
                "start_time": start_time.isoformat(),
                "duration": duration_minutes,
                "timezone": timezone,
                "agenda": agenda,
                "settings": {
                    "host_video": kwargs.get("host_video", True),
                    "participant_video": kwargs.get("participant_video", True),
                    "join_before_host": kwargs.get("join_before_host", False),
                    "mute_upon_entry": kwargs.get("mute_upon_entry", True),
                    "watermark": kwargs.get("watermark", False),
                    "use_pmi": kwargs.get("use_pmi", False),
                    "approval_type": kwargs.get("approval_type", 0),  # 0=automatically, 1=manually
                    "registration_type": kwargs.get("registration_type", 1),
                    "audio": kwargs.get("audio", "both"),
                    "auto_recording": kwargs.get("auto_recording", "none"),
                    "waiting_room": kwargs.get("waiting_room", True)
                }
            }
            
            response = requests.post(
                f"{self.base_url}/users/{user_id}/meetings",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 201:
                meeting_data = response.json()
                
                # Extract relevant information
                return {
                    "meeting_id": meeting_data.get("id"),
                    "join_url": meeting_data.get("join_url"),
                    "start_url": meeting_data.get("start_url"),
                    "password": meeting_data.get("password"),
                    "meeting_data": meeting_data
                }
            else:
                logger.error(f"Zoom API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error creating Zoom meeting: {e}")
        
        return None
    
    async def update_meeting(self, meeting_id: str, **kwargs) -> bool:
        """Update an existing Zoom meeting"""
        try:
            token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            data = {}
            
            if 'topic' in kwargs:
                data['topic'] = kwargs['topic']
            if 'start_time' in kwargs:
                data['start_time'] = kwargs['start_time'].isoformat()
            if 'duration' in kwargs:
                data['duration'] = kwargs['duration']
            if 'timezone' in kwargs:
                data['timezone'] = kwargs['timezone']
            if 'agenda' in kwargs:
                data['agenda'] = kwargs['agenda']
            
            if data:
                response = requests.patch(
                    f"{self.base_url}/meetings/{meeting_id}",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Error updating Zoom meeting: {e}")
        
        return False
    
    async def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a Zoom meeting"""
        try:
            token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            response = requests.delete(
                f"{self.base_url}/meetings/{meeting_id}",
                headers=headers,
                timeout=30
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Error deleting Zoom meeting: {e}")
        
        return False
    
    async def get_meeting_details(self, meeting_id: str) -> Optional[Dict]:
        """Get details of a Zoom meeting"""
        try:
            token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            response = requests.get(
                f"{self.base_url}/meetings/{meeting_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            logger.error(f"Error getting meeting details: {e}")
        
        return None
    
    async def add_registrant(self, meeting_id: str, email: str, first_name: str,
                           last_name: str = "") -> Optional[Dict]:
        """Add registrant to a meeting"""
        try:
            token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            }
            
            response = requests.post(
                f"{self.base_url}/meetings/{meeting_id}/registrants",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 201:
                return response.json()
                
        except Exception as e:
            logger.error(f"Error adding registrant: {e}")
        
        return None
    
    async def list_past_meetings(self, user_id: str, from_date: datetime = None,
                               to_date: datetime = None, page_size: int = 30) -> List[Dict]:
        """List past meetings"""
        try:
            token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            params = {
                "page_size": page_size
            }
            
            if from_date:
                params["from"] = from_date.strftime("%Y-%m-%d")
            if to_date:
                params["to"] = to_date.strftime("%Y-%m-%d")
            
            response = requests.get(
                f"{self.base_url}/users/{user_id}/meetings",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("meetings", [])
                
        except Exception as e:
            logger.error(f"Error listing meetings: {e}")
        
        return []