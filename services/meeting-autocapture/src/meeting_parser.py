"""
Meeting Parser - Parse email content and extract meeting details
Phase 2 of Meeting Auto Capture
"""
from icalendar import Calendar
import re
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging
from email.utils import parseaddr

from models import MeetingInvitation, MeetingPattern


class MeetingParser:
    """Parse email content and extract meeting details to JSON"""

    def __init__(self, patterns_file: str):
        """
        Initialize meeting parser

        Args:
            patterns_file: Path to meeting_patterns.json file
        """
        self.logger = logging.getLogger(__name__)
        self.patterns = self._load_patterns(patterns_file)

    def _load_patterns(self, patterns_file: str) -> List[MeetingPattern]:
        """Load meeting patterns from JSON file"""
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            patterns = [MeetingPattern(**p) for p in data['patterns']]
            # Sort by priority
            patterns.sort(key=lambda x: x.priority)

            self.logger.info(f"Loaded {len(patterns)} meeting patterns")
            return patterns

        except Exception as e:
            self.logger.error(f"Failed to load patterns file: {e}")
            return []

    def parse_email_to_meeting(self, email_data: Dict) -> Optional[MeetingInvitation]:
        """
        Main parsing function - convert email to MeetingInvitation

        Args:
            email_data: Email data from email_monitor

        Returns:
            MeetingInvitation object or None if not a meeting invitation
        """
        try:
            headers = email_data.get('headers', {})
            html_body = email_data.get('html_body', '')
            text_body = email_data.get('text_body', '')
            calendar_attachments = email_data.get('calendar_attachments', [])

            # Extract sender info
            sender_name, sender_email = parseaddr(headers.get('from', ''))
            if not sender_name:
                sender_name = sender_email.split('@')[0]

            # Parse calendar attachment if present
            calendar_data = None
            if calendar_attachments:
                calendar_data = self.parse_ics_attachment(calendar_attachments[0]['content'])

            # Extract meeting URL from email body
            search_text = text_body or html_body or ''
            meeting_url, platform = self.extract_meeting_url(search_text)

            # If no meeting URL found in body, check calendar location
            if not meeting_url and calendar_data and calendar_data.get('location'):
                meeting_url, platform = self.extract_meeting_url(calendar_data['location'])

            # If still no meeting URL, this might not be a meeting invitation
            if not meeting_url:
                self.logger.debug(f"No meeting URL found in email: {headers.get('subject')}")
                return None

            # Extract meeting password
            password = self.extract_password(search_text)

            # Get start/end time from calendar or estimate
            if calendar_data:
                start_time = calendar_data.get('start')
                end_time = calendar_data.get('end')
                subject = calendar_data.get('summary') or headers.get('subject', 'No Subject')
            else:
                # Try to parse from subject or use current time (fallback)
                start_time = datetime.utcnow()
                end_time = None
                subject = headers.get('subject', 'No Subject')

            # Calculate duration
            if end_time and start_time:
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
            else:
                # Default to 60 minutes
                duration_minutes = 60
                end_time = start_time + timedelta(minutes=60)

            # Extract participants (basic implementation)
            participants = []
            to_header = headers.get('to', '')
            if to_header:
                # Parse email addresses from To field
                for addr in to_header.split(','):
                    name, email = parseaddr(addr.strip())
                    if email:
                        participants.append(email)

            # Create MeetingInvitation object
            meeting = MeetingInvitation(
                platform=platform,
                meeting_link=meeting_url,
                subject=subject,
                sender_email=sender_email,
                sender_name=sender_name,
                participants=participants,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                password=password,
                status='pending',
                # IMPORTANT: Save full email body for later stages
                email_body_html=html_body,
                email_body_text=text_body,
                email_raw_headers=headers,
                email_attachments=[a['filename'] for a in email_data.get('attachments', [])]
            )

            self.logger.info(f"Parsed meeting: {subject} ({platform}) at {start_time}")
            return meeting

        except Exception as e:
            self.logger.error(f"Error parsing email to meeting: {e}", exc_info=True)
            return None

    def parse_ics_attachment(self, ics_content: bytes) -> Dict:
        """
        Extract start, end, duration from .ics calendar file

        Args:
            ics_content: .ics file content as bytes

        Returns:
            Dictionary with calendar data
        """
        try:
            # Handle both bytes and string
            if isinstance(ics_content, bytes):
                ics_content = ics_content.decode('utf-8')

            cal = Calendar.from_ical(ics_content)

            for component in cal.walk():
                if component.name == "VEVENT":
                    start = component.get('dtstart')
                    end = component.get('dtend')
                    summary = component.get('summary')
                    location = component.get('location')

                    # Convert to datetime if needed
                    start_dt = start.dt if start else None
                    end_dt = end.dt if end else None

                    # Handle date-only (convert to datetime)
                    if start_dt and not isinstance(start_dt, datetime):
                        start_dt = datetime.combine(start_dt, datetime.min.time())
                    if end_dt and not isinstance(end_dt, datetime):
                        end_dt = datetime.combine(end_dt, datetime.max.time())

                    return {
                        'start': start_dt,
                        'end': end_dt,
                        'summary': str(summary) if summary else None,
                        'location': str(location) if location else None
                    }

            return {}

        except Exception as e:
            self.logger.error(f"Error parsing .ics attachment: {e}")
            return {}

    def extract_meeting_url(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Find meeting URL and detect platform

        Args:
            text: Text to search (email body or location)

        Returns:
            Tuple of (meeting_url, platform_name) or (None, None)
        """
        if not text:
            return None, None

        # Try each pattern (already sorted by priority)
        for pattern in self.patterns:
            match = re.search(pattern.regex, text, re.IGNORECASE)
            if match:
                url = match.group(0)
                # Ensure URL has protocol
                if not url.startswith('http'):
                    url = 'https://' + url
                return url, pattern.name

        return None, None

    def extract_password(self, text: str) -> Optional[str]:
        """
        Extract meeting password from email body

        Args:
            text: Email body text

        Returns:
            Password string or None
        """
        if not text:
            return None

        # Common password patterns
        patterns = [
            r'[Pp]assword:\s*(\w+)',
            r'[Пп]ароль:\s*(\w+)',
            r'[Cc]ode:\s*(\w+)',
            r'[Кк]од:\s*(\w+)',
            r'Meeting [Pp]assword:\s*(\w+)',
            r'Passcode:\s*(\w+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                password = match.group(1)
                self.logger.debug(f"Found meeting password: {password}")
                return password

        return None

    def _sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """
        Sanitize text for use in filename

        Args:
            text: Text to sanitize
            max_length: Maximum length of sanitized text

        Returns:
            Sanitized text safe for filesystem
        """
        import re
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', text)
        # Replace spaces and dots with hyphens
        sanitized = sanitized.replace(' ', '-').replace('.', '-')
        # Remove multiple consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Trim and limit length
        sanitized = sanitized.strip('-')[:max_length]
        return sanitized or 'unnamed'

    def _generate_filename(self, meeting: MeetingInvitation) -> str:
        """
        Generate human-readable filename for meeting JSON
        Format: YYYYMMDD_HHMM_platform_subject_id.json

        Args:
            meeting: MeetingInvitation object

        Returns:
            Filename string
        """
        # Format start time as YYYYMMDD_HHMM
        time_str = meeting.start_time.strftime('%Y%m%d_%H%M')

        # Sanitize platform name
        platform = self._sanitize_filename(meeting.platform or 'unknown', 20)

        # Sanitize subject
        subject = self._sanitize_filename(meeting.subject, 40)

        # Get first 8 chars of ID for uniqueness
        id_short = meeting.id[:8]

        # Combine: time_platform_subject_id.json
        filename = f"{time_str}_{platform}_{subject}_{id_short}.json"

        return filename

    def save_meeting_json(self, meeting: MeetingInvitation, folder: str = 'data/meetings/pending'):
        """
        Save meeting to JSON file in specified folder

        Args:
            meeting: MeetingInvitation object
            folder: Target folder (default: pending)
        """
        try:
            # Ensure folder exists
            os.makedirs(folder, exist_ok=True)

            # Generate human-readable filename
            filename = self._generate_filename(meeting)
            filepath = os.path.join(folder, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                # Convert to dict and handle datetime serialization
                data = meeting.model_dump()
                # Convert datetime to ISO format
                for key, value in data.items():
                    if isinstance(value, datetime):
                        data[key] = value.isoformat()

                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved meeting JSON: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Error saving meeting JSON: {e}")
            raise
