"""
Meeting Auto Capture - Main Entry Point
Standalone Python service for automated meeting capture
"""
import os
import sys
import logging
import time
from dotenv import load_dotenv
from pathlib import Path

# Import our modules
from email_monitor import EmailMonitor
from meeting_parser import MeetingParser
from scheduler import MeetingScheduler
from browser_joiner import BrowserJoiner
from video_manager import VideoManager


def setup_logging():
    """Configure logging with colorlog"""
    log_level = os.getenv('MAC_LOG_LEVEL', 'INFO').upper()

    # Create logs directory
    os.makedirs('logs', exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/autocapture.log'),
            logging.StreamHandler()
        ]
    )

    # Reduce noise from playwright
    logging.getLogger('playwright').setLevel(logging.WARNING)


def validate_environment():
    """
    Validate required environment variables

    Returns:
        Tuple of (valid, missing_vars)
    """
    required_vars = [
        'MAC_IMAP_HOST',
        'MAC_IMAP_USER',
        'MAC_IMAP_PASSWORD'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    return len(missing) == 0, missing


def on_email_received(email_data: dict, parser: MeetingParser):
    """
    Callback when new email is received

    Args:
        email_data: Email data from email monitor
        parser: MeetingParser instance
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"New email received: {email_data['headers']['subject']}")

        # Parse email to meeting
        meeting = parser.parse_email_to_meeting(email_data)

        if meeting:
            # Save to pending folder
            parser.save_meeting_json(meeting, 'data/meetings/pending')
            logger.info(f"Saved meeting: {meeting.subject} scheduled for {meeting.start_time}")
        else:
            logger.debug("Email was not a meeting invitation")

    except Exception as e:
        logger.error(f"Error processing email: {e}", exc_info=True)


def main():
    """Main entry point for standalone execution"""

    # Load environment variables from .env file
    # Look for .env in config/ or current directory
    env_paths = [
        Path('config/.env'),
        Path('.env'),
        Path('../config/.env')
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("="*60)
    logger.info("Meeting Auto Capture - Starting...")
    logger.info("="*60)

    # Validate environment
    valid, missing = validate_environment()
    if not valid:
        logger.error(f"Missing required environment variables: {missing}")
        logger.error("Please create a .env file from config/.env.example")
        sys.exit(1)

    logger.info("Environment variables validated")

    # Create data directories
    os.makedirs('data/meetings/pending', exist_ok=True)
    os.makedirs('data/meetings/in_progress', exist_ok=True)
    os.makedirs('data/meetings/completed', exist_ok=True)
    os.makedirs('data/browser_profiles', exist_ok=True)

    try:
        # Initialize components
        logger.info("Initializing components...")

        # Video Manager
        video_output_folder = os.getenv('MAC_VIDEO_OUTPUT_FOLDER', '../../data/input')
        video_manager = VideoManager(output_folder=video_output_folder)
        logger.info(f"[OK] Video Manager initialized (output: {video_output_folder})")

        # Browser Joiner - Uses ffmpeg for screen + audio capture (WebM format)
        profiles_path = os.getenv('MAC_BROWSER_PROFILES_PATH', './data/browser_profiles')

        browser_joiner = BrowserJoiner(
            profiles_path=profiles_path,
            video_output_folder=video_output_folder
        )
        logger.info(f"[OK] Browser Joiner initialized (ffmpeg screen capture, WebM format)")
        logger.info(f"  Profiles: {profiles_path}")
        logger.info(f"  Video output: {video_output_folder}")

        # Scheduler
        scheduler = MeetingScheduler(
            browser_joiner=browser_joiner,
            video_manager=video_manager
        )

        # Set timing configuration
        pre_join_minutes = int(os.getenv('MAC_PRE_MEETING_JOIN_MINUTES', 2))
        post_buffer_minutes = int(os.getenv('MAC_POST_MEETING_BUFFER_MINUTES', 5))
        scheduler.set_timing_config(pre_join_minutes, post_buffer_minutes)

        logger.info(f"[OK] Scheduler initialized")

        # Meeting Parser
        patterns_file = 'config/meeting_patterns.json'
        if not os.path.exists(patterns_file):
            # Try relative path
            patterns_file = '../config/meeting_patterns.json'

        parser = MeetingParser(patterns_file=patterns_file)
        logger.info(f"[OK] Meeting Parser initialized")

        # Email Monitor Configuration
        email_config = {
            'host': os.getenv('MAC_IMAP_HOST'),
            'port': int(os.getenv('MAC_IMAP_PORT', 993)),
            'username': os.getenv('MAC_IMAP_USER'),
            'password': os.getenv('MAC_IMAP_PASSWORD'),
            'folder': os.getenv('MAC_IMAP_FOLDER', 'INBOX'),
            'check_interval': int(os.getenv('MAC_IMAP_CHECK_INTERVAL', 60))
        }

        # Email Monitor with callback
        email_monitor = EmailMonitor(
            config=email_config,
            on_email_callback=lambda email_data: on_email_received(email_data, parser)
        )
        logger.info(f"[OK] Email Monitor initialized")
        logger.info(f"  Server: {email_config['host']}:{email_config['port']}")
        logger.info(f"  User: {email_config['username']}")
        logger.info(f"  Folder: {email_config['folder']}")

        # Start services
        logger.info("="*60)
        logger.info("Starting services...")
        logger.info("="*60)

        # Start scheduler (loads pending meetings)
        scheduler.start()
        logger.info("[OK] Scheduler started")

        # Start email monitoring
        email_monitor.start()
        logger.info("[OK] Email monitor started")

        logger.info("="*60)
        logger.info("Meeting Auto Capture is running!")
        logger.info("="*60)
        logger.info("Services:")
        logger.info(f"  • Email monitoring: {email_config['folder']} (every {email_config['check_interval']}s)")
        logger.info(f"  • Meeting scheduling: Check every minute")
        logger.info(f"  • Auto-join: {pre_join_minutes} min before meeting")
        logger.info(f"  • Auto-stop: {post_buffer_minutes} min after meeting")
        logger.info("="*60)
        logger.info("Press Ctrl+C to stop")
        logger.info("="*60)

        # Keep running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n" + "="*60)
        logger.info("Shutting down gracefully...")
        logger.info("="*60)

        # Stop services
        try:
            email_monitor.stop()
            logger.info("[OK] Email monitor stopped")
        except:
            pass

        try:
            scheduler.stop()
            logger.info("[OK] Scheduler stopped")
        except:
            pass

        try:
            browser_joiner.cleanup()
            logger.info("[OK] Browser joiner cleaned up")
        except:
            pass

        logger.info("="*60)
        logger.info("Stopped successfully")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
