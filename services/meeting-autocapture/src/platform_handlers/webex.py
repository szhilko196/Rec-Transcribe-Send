"""
Webex Handler
Handler for Cisco Webex meetings
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class WebexHandler(BasePlatformHandler):
    """Handler for Webex platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to Webex meeting and join

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining Webex meeting: {meeting.meeting_link}")

            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)

            page.wait_for_timeout(3000)

            # Look for "Join from browser" option
            browser_join_selectors = [
                'button:has-text("Join from your browser")',
                'a:has-text("Join from your browser")',
                '.web-client-link'
            ]

            for selector in browser_join_selectors:
                try:
                    if page.query_selector(selector):
                        self.logger.info("Clicking 'Join from browser'")
                        page.click(selector, timeout=5000)
                        page.wait_for_timeout(2000)
                        break
                except:
                    continue

            # Enter name
            name_selectors = [
                'input[placeholder*="name"]',
                'input[placeholder*="Name"]',
                'input[aria-label*="name"]',
                'input[type="text"]'
            ]

            for selector in name_selectors:
                if page.query_selector(selector):
                    self.enter_name(page, meeting.sender_name, selector)
                    page.wait_for_timeout(1000)
                    break

            # Enter email if required
            email_selectors = [
                'input[placeholder*="email"]',
                'input[type="email"]'
            ]

            for selector in email_selectors:
                if page.query_selector(selector):
                    self.enter_name(page, meeting.sender_email, selector)
                    break

            # Click join button
            join_selectors = [
                'button:has-text("Join Meeting")',
                'button:has-text("Join")',
                'button[type="submit"]',
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

            # Wait for meeting to load
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined Webex meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join Webex meeting: {e}")
            return False
