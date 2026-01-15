import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class GoogleMeetIntegration:
    def __init__(self, credentials: Dict):
        self.credentials = Credentials.from_authorized_user_info(credentials)
        self.service = build('calendar', 'v3', credentials=self.credentials)
    
    async def create_meeting(self, summary: str, start_time: datetime,
                           end_time: datetime, attendees: list = None,
                           description: str = "", timezone: str = "UTC") -> Optional[Dict]:
        """Create a Google Meet meeting"""
        try:
            # Create event with Google Meet conference
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet_{int(datetime.now().timestamp())}",
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'reminders': {
                    'useDefault': True,
                }
            }
            
            if attendees:
                event['attendees'] = [
                    {'email': email} for email in attendees
                ]
            
            # Create event with conference
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            # Extract meeting details
            meet_details = created_event.get('conferenceData', {})
            
            return {
                'meeting_id': created_event.get('id'),
                'hangout_link': created_event.get('hangoutLink'),
                'conference_data': meet_details,
                'join_url': meet_details.get('entryPoints', [{}])[0].get('uri', ''),
                'event_data': created_event
            }
            
        except HttpError as e:
            logger.error(f"Google API error: {e}")
        except Exception as e:
            logger.error(f"Error creating Google Meet: {e}")
        
        return None
    
    async def generate_meet_link(self) -> Optional[str]:
        """Generate a standalone Google Meet link"""
        try:
            # Create a quick event to generate a Meet link
            event = {
                'summary': 'Quick Meeting',
                'start': {
                    'dateTime': datetime.now().isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': (datetime.now() + timedelta(hours=1)).isoformat(),
                    'timeZone': 'UTC',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"quick_meet_{int(datetime.now().timestamp())}",
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                }
            }
            
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            # Delete the event but keep the Meet link
            meet_link = created_event.get('hangoutLink')
            
            # Delete the temporary event
            self.service.events().delete(
                calendarId='primary',
                eventId=created_event['id']
            ).execute()
            
            return meet_link
            
        except Exception as e:
            logger.error(f"Error generating Meet link: {e}")
        
        return None