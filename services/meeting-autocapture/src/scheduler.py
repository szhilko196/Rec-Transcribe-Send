"""
Scheduler - Schedule and trigger meeting joins
Phase 3 of Meeting Auto Capture
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
import os
import json
import shutil
import logging
from typing import Dict, Optional

from models import MeetingInvitation


class MeetingScheduler:
    """Schedule meeting joins and recording stops"""

    def __init__(self, browser_joiner, video_manager):
        """
        Initialize scheduler

        Args:
            browser_joiner: BrowserJoiner instance
            video_manager: VideoManager instance
        """
        self.scheduler = BackgroundScheduler()
        self.browser_joiner = browser_joiner
        self.video_manager = video_manager
        self.active_sessions: Dict[str, any] = {}  # meeting_id -> browser context
        self.logger = logging.getLogger(__name__)

        # Configuration from environment (will be set by main.py)
        self.pre_join_minutes = 2
        self.post_buffer_minutes = 5

    def start(self):
        """Start scheduler and load pending meetings"""
        self.logger.info("Starting meeting scheduler...")

        # Load existing pending meetings
        self.load_pending_meetings()

        # Start background scheduler with minute-level checking
        self.scheduler.add_job(
            self.check_meetings,
            'interval',
            minutes=1,
            id='meeting_checker',
            replace_existing=True
        )

        self.scheduler.start()
        self.logger.info("Scheduler started successfully")

    def load_pending_meetings(self):
        """Load all pending meeting JSONs and schedule them"""
        pending_dir = "data/meetings/pending"

        if not os.path.exists(pending_dir):
            self.logger.info("No pending meetings directory found")
            return

        json_files = [f for f in os.listdir(pending_dir) if f.endswith('.json')]
        self.logger.info(f"Loading {len(json_files)} pending meetings")

        for filename in json_files:
            try:
                filepath = os.path.join(pending_dir, filename)
                meeting = self._load_meeting_from_file(filepath)

                if meeting:
                    self.logger.info(f"Loaded pending meeting: {meeting.subject} at {meeting.start_time}")

            except Exception as e:
                self.logger.error(f"Error loading meeting {filename}: {e}")

    def check_meetings(self):
        """
        Check if any meetings need to join (runs every minute)
        """
        now = datetime.now().astimezone()  # Get current time in local timezone
        pending_dir = "data/meetings/pending"

        self.logger.debug(f"Checking meetings at {now}")

        if not os.path.exists(pending_dir):
            self.logger.warning(f"Pending directory does not exist: {pending_dir}")
            return

        for filename in os.listdir(pending_dir):
            if not filename.endswith('.json'):
                continue

            try:
                filepath = os.path.join(pending_dir, filename)
                meeting = self._load_meeting_from_file(filepath)

                if not meeting:
                    self.logger.warning(f"Could not load meeting from {filename}")
                    continue

                if meeting.status != 'pending':
                    self.logger.debug(f"Skipping meeting {meeting.subject} - status is {meeting.status}")
                    continue

                # Calculate join time (N minutes before start)
                join_time = meeting.start_time - timedelta(minutes=self.pre_join_minutes)

                self.logger.debug(f"Meeting {meeting.subject}: now={now}, join_time={join_time}, start_time={meeting.start_time}")

                # Check if it's time to join
                if now >= join_time:
                    self.logger.info(f"Time to join meeting: {meeting.subject}")
                    self.trigger_join(meeting)
                else:
                    self.logger.debug(f"Not yet time to join {meeting.subject} (need to wait {(join_time - now).total_seconds():.0f} seconds)")

            except Exception as e:
                self.logger.error(f"Error checking meeting {filename}: {e}", exc_info=True)

    def trigger_join(self, meeting: MeetingInvitation):
        """
        Start browser session and join meeting

        Args:
            meeting: MeetingInvitation object
        """
        try:
            self.logger.info(f"Triggering join for meeting: {meeting.id}")

            # Update status to in_progress
            meeting.status = 'in_progress'
            self._move_meeting_json(meeting, 'pending', 'in_progress')

            # Register meeting with video manager
            self.video_manager.register_meeting(meeting)

            # Start browser session and join meeting
            context = self.browser_joiner.join_meeting(meeting)

            if context:
                # Store session
                self.active_sessions[meeting.id] = context

                # Schedule stop recording
                if meeting.end_time:
                    stop_time = meeting.end_time + timedelta(minutes=self.post_buffer_minutes)

                    self.scheduler.add_job(
                        self.trigger_stop,
                        'date',
                        run_date=stop_time,
                        args=[meeting.id],
                        id=f'stop_{meeting.id}',
                        replace_existing=True
                    )

                    self.logger.info(f"Scheduled stop for {meeting.id} at {stop_time}")

                self.logger.info(f"Successfully joined meeting: {meeting.id}")
            else:
                raise Exception("Browser session not created")

        except Exception as e:
            self.logger.error(f"Failed to join meeting {meeting.id}: {e}")

            # Update meeting status to failed
            meeting.status = 'failed'
            meeting.error_message = str(e)
            self._move_meeting_json(meeting, 'in_progress', 'completed')

    def trigger_stop(self, meeting_id: str):
        """
        Stop recording and close browser

        Args:
            meeting_id: Meeting ID
        """
        try:
            self.logger.info(f"Triggering stop for meeting: {meeting_id}")

            # Load meeting first
            meeting = self._load_meeting(meeting_id, 'in_progress')
            if not meeting:
                self.logger.error(f"Meeting {meeting_id} not found in in_progress")
                return

            if meeting_id in self.active_sessions:
                context = self.active_sessions[meeting_id]

                # Stop recording (now returns video file path)
                video_path = self.browser_joiner.stop_recording(context, meeting)

                # Update meeting with video path
                if video_path:
                    meeting.video_file_path = video_path
                    self.logger.info(f"Video saved: {video_path}")

                # Remove from active sessions
                del self.active_sessions[meeting_id]

            # Update status
            meeting.status = 'completed'
            meeting.processed_at = datetime.now(timezone.utc)
            self._move_meeting_json(meeting, 'in_progress', 'completed')

            self.logger.info(f"Meeting {meeting_id} completed successfully")

        except Exception as e:
            self.logger.error(f"Error stopping meeting {meeting_id}: {e}")

    def _find_meeting_file(self, meeting_id: str, status: str) -> Optional[str]:
        """
        Find meeting JSON file by ID in the given status folder
        Supports both old (just ID) and new (human-readable) filename formats

        Args:
            meeting_id: Meeting ID (full or short 8-char version)
            status: Folder name (pending/in_progress/completed)

        Returns:
            Full filepath if found, None otherwise
        """
        folder = f"data/meetings/{status}"
        if not os.path.exists(folder):
            return None

        # Get short ID (first 8 chars) for matching new format
        id_short = meeting_id[:8]

        for filename in os.listdir(folder):
            if not filename.endswith('.json'):
                continue

            # Check if filename contains the ID (full or short)
            if meeting_id in filename or id_short in filename:
                return os.path.join(folder, filename)

        return None

    def _load_meeting(self, meeting_id: str, status: str) -> Optional[MeetingInvitation]:
        """Load meeting from JSON file"""
        filepath = self._find_meeting_file(meeting_id, status)
        if not filepath:
            self.logger.warning(f"Meeting file not found for ID: {meeting_id} in {status}")
            return None
        return self._load_meeting_from_file(filepath)

    def _load_meeting_from_file(self, filepath: str) -> Optional[MeetingInvitation]:
        """Load meeting from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert ISO datetime strings back to datetime objects
            for key in ['start_time', 'end_time', 'created_at', 'processed_at']:
                if key in data and data[key]:
                    data[key] = datetime.fromisoformat(data[key])

            return MeetingInvitation(**data)

        except Exception as e:
            self.logger.error(f"Error loading meeting from {filepath}: {e}")
            return None

    def _generate_filename(self, meeting: MeetingInvitation) -> str:
        """
        Generate human-readable filename for meeting JSON
        Format: YYYYMMDD_HHMM_platform_subject_id.json
        """
        import re

        def sanitize(text: str, max_len: int = 50) -> str:
            """Sanitize text for filename"""
            text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', text)
            text = text.replace(' ', '-').replace('.', '-')
            text = re.sub(r'-+', '-', text).strip('-')[:max_len]
            return text or 'unnamed'

        time_str = meeting.start_time.strftime('%Y%m%d_%H%M')
        platform = sanitize(meeting.platform or 'unknown', 20)
        subject = sanitize(meeting.subject, 40)
        id_short = meeting.id[:8]

        return f"{time_str}_{platform}_{subject}_{id_short}.json"

    def _move_meeting_json(self, meeting: MeetingInvitation, from_status: str, to_status: str):
        """
        Move meeting JSON between folders and update it

        Args:
            meeting: MeetingInvitation object
            from_status: Source folder (pending/in_progress/completed)
            to_status: Destination folder
        """
        try:
            # Find source file (supports old and new formats)
            src = self._find_meeting_file(meeting.id, from_status)
            if not src:
                self.logger.warning(f"Source file not found for meeting {meeting.id} in {from_status}")
                # Create new file in destination anyway
                src = None

            # Generate destination filename
            dst_filename = self._generate_filename(meeting)
            dst = f"data/meetings/{to_status}/{dst_filename}"

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)

            # Save updated meeting to destination
            with open(dst, 'w', encoding='utf-8') as f:
                data = meeting.model_dump()
                # Convert datetime to ISO format
                for key, value in data.items():
                    if isinstance(value, datetime):
                        data[key] = value.isoformat()

                json.dump(data, f, indent=2, ensure_ascii=False)

            # Remove source file if it exists and is different from destination
            if src and os.path.exists(src) and src != dst:
                os.remove(src)

            self.logger.debug(f"Moved meeting {meeting.id} from {from_status} to {to_status}")

        except Exception as e:
            self.logger.error(f"Error moving meeting JSON: {e}")

    def stop(self):
        """Stop scheduler"""
        self.logger.info("Stopping scheduler...")

        # Stop all active sessions
        for meeting_id, context in list(self.active_sessions.items()):
            try:
                # Load meeting to pass to stop_recording
                meeting = self._load_meeting(meeting_id, 'in_progress')
                if meeting:
                    self.browser_joiner.stop_recording(context, meeting)
            except:
                pass

        self.scheduler.shutdown()
        self.logger.info("Scheduler stopped")

    def set_timing_config(self, pre_join_minutes: int, post_buffer_minutes: int):
        """
        Set timing configuration

        Args:
            pre_join_minutes: Minutes before meeting start to join
            post_buffer_minutes: Minutes after meeting end to keep recording
        """
        self.pre_join_minutes = pre_join_minutes
        self.post_buffer_minutes = post_buffer_minutes
        self.logger.info(f"Timing config: join {pre_join_minutes}min before, stop {post_buffer_minutes}min after")
