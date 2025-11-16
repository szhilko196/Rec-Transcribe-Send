"""
PSBank Meeting Handler - Priority 2
Handler for meeting.psbank.ru platform
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class PSBankMeetingHandler(BasePlatformHandler):
    """Handler for meeting.psbank.ru platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to PSBank meeting and join

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining PSBank meeting: {meeting.meeting_link}")

            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)

            # Wait for page to load
            page.wait_for_timeout(3000)

            # Check if password is required
            password_input = page.query_selector('input[type="password"]')
            if password_input and meeting.password:
                self.logger.info("Entering meeting password")
                self.enter_password(page, meeting.password, 'input[type="password"]')

                # Click submit/enter button
                submit_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Enter")',
                    'button:has-text("Войти")',
                    '.submit-button'
                ]

                for selector in submit_selectors:
                    try:
                        if page.query_selector(selector):
                            page.click(selector, timeout=3000)
                            break
                    except:
                        continue

                page.wait_for_timeout(2000)

            # Look for name input
            name_selectors = [
                'input[placeholder*="name"]',
                'input[placeholder*="имя"]',
                'input[name="displayName"]',
                'input[name="name"]',
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
                '.join-button'
            ]

            for selector in join_selectors:
                try:
                    if page.query_selector(selector):
                        self.logger.info(f"Found join button: {selector}")
                        page.click(selector, timeout=5000)
                        break
                except:
                    continue

            # Wait for meeting interface
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined PSBank meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join PSBank meeting: {e}")
            return False
