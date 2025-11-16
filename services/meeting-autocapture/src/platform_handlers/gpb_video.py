"""
GPB Video Handler - Priority 1
Handler for gpb.video meeting platform
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class GPBVideoHandler(BasePlatformHandler):
    """Handler for gpb.video platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to GPB Video meeting and join

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining GPB Video meeting: {meeting.meeting_link}")

            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)

            # Wait for page to load
            page.wait_for_timeout(3000)

            # Look for name input field (adjust selectors based on actual page)
            # Common patterns for name inputs
            name_selectors = [
                'input[name="name"]',
                'input[placeholder*="имя"]',
                'input[placeholder*="name"]',
                'input[type="text"]'
            ]

            for selector in name_selectors:
                if page.query_selector(selector):
                    self.enter_name(page, meeting.sender_name, selector)
                    break

            # Look for join button
            join_selectors = [
                'button:has-text("Join")',
                'button:has-text("Войти")',
                'button:has-text("Присоединиться")',
                'button[type="submit"]',
                '.join-button',
                '#join-button'
            ]

            for selector in join_selectors:
                try:
                    if page.query_selector(selector):
                        self.logger.info(f"Found join button: {selector}")
                        page.click(selector, timeout=5000)
                        break
                except:
                    continue

            # Wait for meeting interface to load
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined GPB Video meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join GPB Video meeting: {e}")
            return False
