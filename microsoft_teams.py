import msal
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class MicrosoftTeamsIntegration:
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        self.graph_url = "https://graph.microsoft.com/v1.0"
        self.access_token = None
    
    async def get_access_token(self) -> Optional[str]:
        """Get access token using client credentials"""
        try:
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_for_client(scopes=self.scope)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                return self.access_token
            else:
                logger.error(f"Token acquisition failed: {result.get('error_description')}")
                
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
        
        return None
    
    async def create_online_meeting(self, subject: str, start_time: datetime,
                                  end_time: datetime, participants: list = None,
                                  **kwargs) -> Optional[Dict]:
        """Create a Teams online meeting"""
        try:
            token = await self.get_access_token()
            if not token:
                return None
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "subject": subject,
                "startDateTime": start_time.isoformat(),
                "endDateTime": end_time.isoformat(),
                "participants": {
                    "attendees": participants or []
                }
            }
            
            # Add optional parameters
            if kwargs.get('allow_attendee_to_enable_camera'):
                data['allowAttendeeToEnableCamera'] = kwargs['allow_attendee_to_enable_camera']
            if kwargs.get('allow_attendee_to_enable_mic'):
                data['allowAttendeeToEnableMic'] = kwargs['allow_attendee_to_enable_mic']
            if kwargs.get('allowed_presenters'):
                data['allowedPresenters'] = kwargs['allowed_presenters']
            
            response = requests.post(
                f"{self.graph_url}/me/onlineMeetings",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 201:
                meeting_data = response.json()
                
                return {
                    "meeting_id": meeting_data.get("id"),
                    "join_url": meeting_data.get("joinWebUrl"),
                    "join_information": meeting_data.get("joinInformation"),
                    "participants": meeting_data.get("participants"),
                    "meeting_data": meeting_data
                }
            else:
                logger.error(f"Graph API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error creating Teams meeting: {e}")
        
        return None
    
    async def send_meeting_invite(self, event_id: str, recipients: List[str],
                                message: str = "") -> bool:
        """Send meeting invite via Teams"""
        try:
            token = await self.get_access_token()
            if not token:
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "message": {
                    "subject": "Meeting Invitation",
                    "body": {
                        "contentType": "HTML",
                        "content": message or "You're invited to a meeting!"
                    },
                    "toRecipients": [
                        {"emailAddress": {"address": email}}
                        for email in recipients
                    ]
                }
            }
            
            response = requests.post(
                f"{self.graph_url}/me/sendMail",
                headers=headers,
                json=data,
                timeout=30
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Error sending meeting invite: {e}")
        
        return False