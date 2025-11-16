"""
Browser Joiner - Playwright automation for joining meetings
Phase 4 of Meeting Auto Capture - Using ffmpeg screen capture
"""
from playwright.sync_api import sync_playwright, BrowserContext, Playwright
import os
import logging
from typing import Optional
from datetime import datetime
import shutil
import subprocess

from models import MeetingInvitation


class BrowserJoiner:
    """Launch browser, join meetings, and record with ffmpeg screen capture"""

    def __init__(self, profiles_path: str, video_output_folder: str):
        """
        Initialize browser joiner

        Args:
            profiles_path: Path to browser profiles directory
            video_output_folder: Folder where videos will be saved
        """
        self.profiles_path = os.path.abspath(profiles_path)
        self.video_output_folder = os.path.abspath(video_output_folder)
        self.logger = logging.getLogger(__name__)

        # Ensure output folder exists
        os.makedirs(self.video_output_folder, exist_ok=True)

        # Store playwright instance
        self.playwright: Optional[Playwright] = None

        # Store ffmpeg processes and video file paths
        self.ffmpeg_processes = {}
        self.video_file_paths = {}

        # ffmpeg executable path
        self.ffmpeg_path = "C:/prj/Rec-Transcribe-Send/tools/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe"

    def join_meeting(self, meeting: MeetingInvitation) -> Optional[BrowserContext]:
        """
        Launch browser with persistent profile and Playwright video recording,
        join meeting, start recording, return context

        Args:
            meeting: MeetingInvitation object

        Returns:
            BrowserContext instance or None if failed
        """
        try:
            self.logger.info(f"Launching browser for meeting: {meeting.id}")

            # Get profile directory for this platform
            profile_name = self._get_profile_name(meeting.platform)
            profile_dir = os.path.join(self.profiles_path, profile_name)
            os.makedirs(profile_dir, exist_ok=True)

            self.logger.info(f"Using profile: {profile_dir}")

            # Start Playwright
            if not self.playwright:
                self.playwright = sync_playwright().start()

            # Launch persistent context WITHOUT Playwright video recording
            # We use ffmpeg to capture screen + audio externally
            context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,  # MUST be visible for meetings
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                    # Removed fake media stream flags - they show recording indicator on screen
                    # We don't need them since ffmpeg captures the screen externally
                ],
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True,
                ignore_default_args=['--enable-automation'],
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            self.logger.info("Browser context created")

            # Import platform handlers here to avoid circular imports
            from platform_handlers import get_handler

            # Get platform-specific handler
            handler = get_handler(meeting.platform)

            # Open new page and join meeting
            page = context.new_page()

            success = handler.join(page, meeting)

            if success:
                self.logger.info("Successfully joined meeting")

                # Wait a bit for meeting to fully load
                page.wait_for_timeout(5000)

                # Start ffmpeg screen recording
                video_path = self._start_ffmpeg_recording(meeting)
                if video_path:
                    self.logger.info(f"Started ffmpeg screen recording: {video_path}")
                else:
                    self.logger.warning("Failed to start ffmpeg recording")

                # Store context for later control
                return context
            else:
                self.logger.error("Failed to join meeting")
                context.close()
                return None

        except Exception as e:
            self.logger.error(f"Error joining meeting: {e}", exc_info=True)
            return None

    def stop_recording(self, context: BrowserContext, meeting: MeetingInvitation) -> Optional[str]:
        """
        Stop ffmpeg recording and close browser

        Args:
            context: BrowserContext instance
            meeting: MeetingInvitation object

        Returns:
            Path to the saved video file or None if failed
        """
        import time

        try:
            self.logger.info(f"Stopping recording for meeting: {meeting.id}")

            # Stop ffmpeg process
            ffmpeg_process = self.ffmpeg_processes.get(meeting.id)
            if ffmpeg_process:
                self.logger.info("Stopping ffmpeg recording...")

                # Send 'q' to ffmpeg to stop recording gracefully
                try:
                    ffmpeg_process.stdin.write(b'q')
                    ffmpeg_process.stdin.flush()
                except:
                    pass

                # Wait for ffmpeg to finish (max 10 seconds)
                try:
                    ffmpeg_process.wait(timeout=10)
                    self.logger.info("ffmpeg stopped gracefully")
                except subprocess.TimeoutExpired:
                    self.logger.warning("ffmpeg didn't stop gracefully, terminating...")
                    ffmpeg_process.terminate()
                    try:
                        ffmpeg_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        ffmpeg_process.kill()

                # Remove from tracking
                del self.ffmpeg_processes[meeting.id]
            else:
                self.logger.warning("No ffmpeg process found for this meeting")

            # Close browser
            self.logger.info("Closing browser context...")
            context.close()

            # Get video file path
            video_path = self.video_file_paths.get(meeting.id)
            if video_path and os.path.exists(video_path):
                self.logger.info(f"Video saved to: {video_path}")

                # Remove from tracking
                if meeting.id in self.video_file_paths:
                    del self.video_file_paths[meeting.id]

                return video_path
            else:
                self.logger.error(f"Video file not found: {video_path}")
                return None

        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}", exc_info=True)
            # Force close
            try:
                context.close()
            except:
                pass
            return None

    def _start_ffmpeg_recording(self, meeting: MeetingInvitation) -> Optional[str]:
        """
        Start ffmpeg screen recording with audio

        Args:
            meeting: MeetingInvitation object

        Returns:
            Path to video file being recorded, or None if failed
        """
        try:
            # Create filename with metadata
            # Format: {platform}_{timestamp}_mmmail({sender_email})_{meeting_id}.webm
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{meeting.platform}_{timestamp}_mmmail({meeting.sender_email})_{meeting.id}.webm"
            video_path = os.path.join(self.video_output_folder, filename)

            # ffmpeg command for screen capture with audio
            # WebM format (VP9 + Opus) - more robust than MP4 for recording
            # -f gdigrab: Screen capture on Windows
            # -framerate 15: Capture 15 frames per second (SD quality)
            # -i desktop: Capture entire desktop
            # -f dshow: DirectShow audio device
            # -i audio="...": Audio device name
            # -c:v libvpx-vp9: VP9 video codec (better compression than VP8)
            # -crf 33: Quality setting for VP9 (23=high, 33=SD, 45=low)
            # -b:v 0: Use CRF mode (ignore bitrate)
            # -c:a libopus: Opus audio codec (best quality)
            # -b:a 128k: High quality audio at 128 kbps
            ffmpeg_cmd = [
                self.ffmpeg_path,
                '-f', 'gdigrab',
                '-framerate', '15',
                '-i', 'desktop',
                '-f', 'dshow',
                '-i', 'audio=Набор микрофонов (Senary Audio)',
                '-c:v', 'libvpx-vp9',
                '-crf', '33',          # SD video quality
                '-b:v', '0',           # Use CRF mode
                '-c:a', 'libopus',
                '-b:a', '128k',        # High quality audio
                '-y',  # Overwrite output file
                video_path
            ]

            self.logger.info(f"Starting ffmpeg recording: {video_path}")
            self.logger.debug(f"ffmpeg command: {' '.join(ffmpeg_cmd)}")

            # Start ffmpeg process in background
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW  # Hide console window on Windows
            )

            # Store process and video path
            self.ffmpeg_processes[meeting.id] = process
            self.video_file_paths[meeting.id] = video_path

            self.logger.info(f"ffmpeg process started (PID: {process.pid})")
            return video_path

        except Exception as e:
            self.logger.error(f"Error starting ffmpeg recording: {e}", exc_info=True)
            return None

    def _get_profile_name(self, platform: str) -> str:
        """
        Convert platform name to profile directory name

        Args:
            platform: Platform name (e.g., 'gpb.video')

        Returns:
            Profile directory name (e.g., 'gpb_video')
        """
        if not platform:
            return 'default'

        # Replace special characters with underscores
        return platform.replace('.', '_').replace(':', '_').replace('/', '_')

    def cleanup(self):
        """Cleanup playwright instance"""
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
            self.playwright = None
