"""
Zoom Handler
Handler for Zoom meetings
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class ZoomHandler(BasePlatformHandler):
    """Handler for Zoom platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to Zoom meeting and join

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining Zoom meeting: {meeting.meeting_link}")

            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)

            page.wait_for_timeout(3000)

            # Look for "Join from Browser" link
            browser_join_selectors = [
                'a:has-text("Join from Your Browser")',
                'a:has-text("join from your browser")',
                '.join-from-browser'
            ]

            for selector in browser_join_selectors:
                try:
                    if page.query_selector(selector):
                        self.logger.info("Clicking 'Join from Browser'")
                        page.click(selector, timeout=5000)
                        page.wait_for_timeout(2000)
                        break
                except:
                    continue

            # Enter name
            name_selectors = [
                'input#inputname',
                'input[placeholder*="name"]',
                'input[type="text"]'
            ]

            for selector in name_selectors:
                if page.query_selector(selector):
                    self.enter_name(page, meeting.sender_name, selector)
                    break

            # Click join button
            join_selectors = [
                'button:has-text("Join")',
                'button#joinBtn',
                '.join-audio-by-voip__join-btn'
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

            # Handle audio/video permissions dialog
            try:
                # Look for "Join Audio" or "Join with Computer Audio"
                audio_selectors = [
                    'button:has-text("Join with Computer Audio")',
                    'button:has-text("Join Audio")',
                    '.join-audio-by-voip__join-btn'
                ]

                for selector in audio_selectors:
                    if page.query_selector(selector):
                        page.click(selector, timeout=5000)
                        break
            except:
                pass

            # Wait for meeting to load
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined Zoom meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join Zoom meeting: {e}")
            return False
