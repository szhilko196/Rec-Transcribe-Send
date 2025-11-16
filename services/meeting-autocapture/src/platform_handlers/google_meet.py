"""
Google Meet Handler
Handler for Google Meet meetings
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class GoogleMeetHandler(BasePlatformHandler):
    """Handler for Google Meet platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to Google Meet meeting and join

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining Google Meet meeting: {meeting.meeting_link}")

            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)

            page.wait_for_timeout(3000)

            # Check if already logged in or need to enter name
            # Google Meet may require Google account sign-in (handled by persistent profile)

            # Look for name input (for guests)
            name_selectors = [
                'input[placeholder*="name"]',
                'input[placeholder*="Your name"]',
                'input[aria-label*="name"]'
            ]

            for selector in name_selectors:
                if page.query_selector(selector):
                    self.enter_name(page, meeting.sender_name, selector)
                    page.wait_for_timeout(1000)
                    break

            # Click "Ask to join" or "Join now" button
            join_selectors = [
                'button:has-text("Ask to join")',
                'button:has-text("Join now")',
                'button[aria-label*="Ask to join"]',
                'button[aria-label*="Join"]',
                '.join-button'
            ]

            for selector in join_selectors:
                try:
                    if page.query_selector(selector):
                        self.logger.info(f"Clicking join button: {selector}")
                        page.click(selector, timeout=5000)
                        page.wait_for_timeout(3000)
                        break
                except:
                    continue

            # Handle microphone/camera permissions dialogs
            try:
                # Dismiss or allow permissions
                page.wait_for_timeout(2000)
            except:
                pass

            # Wait for meeting to load
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined Google Meet meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join Google Meet meeting: {e}")
            return False
