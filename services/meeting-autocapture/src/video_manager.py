"""
Video Manager - Track video file creation and link to meetings
Phase 7 of Meeting Auto Capture
"""
import os
import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from models import MeetingInvitation


class VideoFileHandler(FileSystemEventHandler):
    """File system event handler for video files"""

    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        """Called when a file is created"""
        if not event.is_directory and event.src_path.endswith('.webm'):
            self.callback(event.src_path)


class VideoManager:
    """Track video file creation and link to meetings"""

    def __init__(self, output_folder: str):
        """
        Initialize video manager

        Args:
            output_folder: Folder where extension saves videos
        """
        self.output_folder = output_folder
        self.logger = logging.getLogger(__name__)
        self.pending_meetings: Dict[str, MeetingInvitation] = {}  # meeting_id -> meeting

    def register_meeting(self, meeting: MeetingInvitation):
        """
        Register meeting to watch for its video file

        Args:
            meeting: MeetingInvitation object
        """
        self.pending_meetings[meeting.id] = meeting
        self.logger.info(f"Registered meeting for video monitoring: {meeting.id}")

    def monitor_for_video(self, meeting_id: str, timeout: int = 300) -> Optional[str]:
        """
        Monitor output folder for video file matching meeting_id

        Args:
            meeting_id: Meeting ID to look for
            timeout: Timeout in seconds

        Returns:
            Path to video file or None if timeout
        """
        start_time = time.time()

        self.logger.info(f"Monitoring for video file: {meeting_id} (timeout: {timeout}s)")

        while time.time() - start_time < timeout:
            if not os.path.exists(self.output_folder):
                time.sleep(5)
                continue

            files = os.listdir(self.output_folder)
            for file in files:
                # Check if filename contains meeting ID
                if meeting_id in file and file.endswith('.webm'):
                    video_path = os.path.join(self.output_folder, file)
                    self.logger.info(f"Found video file: {video_path}")
                    return video_path

            time.sleep(5)  # Check every 5 seconds

        self.logger.warning(f"Video file not found for meeting {meeting_id} after {timeout}s")
        return None

    def check_for_video(self, meeting_id: str) -> Optional[str]:
        """
        Check once if video file exists for meeting

        Args:
            meeting_id: Meeting ID to look for

        Returns:
            Path to video file or None
        """
        if not os.path.exists(self.output_folder):
            return None

        try:
            files = os.listdir(self.output_folder)
            for file in files:
                # Check if filename contains meeting ID
                if meeting_id in file and file.endswith('.webm'):
                    video_path = os.path.join(self.output_folder, file)
                    self.logger.info(f"Found video file: {video_path}")
                    return video_path
        except Exception as e:
            self.logger.error(f"Error checking for video: {e}")

        return None

    def update_meeting_with_video(self, meeting_id: str, video_path: str):
        """
        Update meeting JSON with video file path

        Args:
            meeting_id: Meeting ID
            video_path: Path to video file
        """
        # Try to find meeting in completed folder
        meeting_json = f"data/meetings/completed/{meeting_id}.json"

        if not os.path.exists(meeting_json):
            # Try in_progress folder
            meeting_json = f"data/meetings/in_progress/{meeting_id}.json"

        if not os.path.exists(meeting_json):
            self.logger.warning(f"Meeting JSON not found for {meeting_id}")
            return

        try:
            # Load existing meeting data
            with open(meeting_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Update with video path
            data['video_file_path'] = video_path
            data['processed_at'] = datetime.utcnow().isoformat()

            # Save updated data
            with open(meeting_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Updated meeting {meeting_id} with video path: {video_path}")

            # Remove from pending meetings
            if meeting_id in self.pending_meetings:
                del self.pending_meetings[meeting_id]

        except Exception as e:
            self.logger.error(f"Error updating meeting JSON: {e}")

    def start_watching(self):
        """
        Start file system watcher for video output folder
        (Optional - for real-time monitoring)
        """
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder, exist_ok=True)

        event_handler = VideoFileHandler(self._on_video_created)
        observer = Observer()
        observer.schedule(event_handler, self.output_folder, recursive=False)
        observer.start()

        self.logger.info(f"Started watching folder: {self.output_folder}")
        return observer

    def _on_video_created(self, video_path: str):
        """
        Callback when video file is created

        Args:
            video_path: Path to created video file
        """
        self.logger.info(f"Video file created: {video_path}")

        # Check if this video matches any pending meetings
        filename = os.path.basename(video_path)

        for meeting_id, meeting in list(self.pending_meetings.items()):
            if meeting_id in filename:
                self.logger.info(f"Matched video to meeting: {meeting_id}")
                self.update_meeting_with_video(meeting_id, video_path)
                break
