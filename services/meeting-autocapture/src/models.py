"""
Data models for Meeting Auto Capture service
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid


class MeetingInvitation(BaseModel):
    """Model for meeting invitation data"""

    # Meeting identification
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: Optional[str] = None  # gpb.video, zoom, etc.
    meeting_link: Optional[str] = None

    # Meeting details
    subject: str
    sender_email: str
    sender_name: str
    participants: List[str] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    password: Optional[str] = None

    # Status tracking
    status: str = "pending"  # pending, in_progress, completed, failed

    # Full email body for later stages (USER REQUIREMENT)
    email_body_html: Optional[str] = None
    email_body_text: Optional[str] = None
    email_raw_headers: Dict[str, str] = {}
    email_attachments: List[str] = []  # Attachment filenames

    # Processing metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    video_file_path: Optional[str] = None
    error_message: Optional[str] = None
    browser_session_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MeetingPattern(BaseModel):
    """Model for meeting platform pattern configuration"""

    name: str
    regex: str
    priority: Optional[int] = 999
    requires_auth: bool = False
    requires_password: bool = False
    profile_name: str
