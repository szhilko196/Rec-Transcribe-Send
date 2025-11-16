"""
Telemost Yandex Handler
Handler for Yandex Telemost meetings
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class TelemostYandexHandler(BasePlatformHandler):
    """Handler for Telemost Yandex platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to Yandex Telemost meeting and join

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining Yandex Telemost meeting: {meeting.meeting_link}")

            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)

            page.wait_for_timeout(3000)

            # Click "Continue in browser" button if present
            continue_selectors = [
                'button:has-text("Продолжить в браузере")',
                'button:has-text("Continue in browser")',
                'a:has-text("Продолжить в браузере")',
                'a:has-text("Continue in browser")'
            ]

            for selector in continue_selectors:
                try:
                    if page.query_selector(selector):
                        self.logger.info(f"Clicking 'Continue in browser' button: {selector}")
                        page.click(selector, timeout=5000)
                        page.wait_for_timeout(3000)
                        break
                except:
                    continue

            # Yandex Telemost may require Yandex account login (handled by persistent profile)

            # Look for name/email input field (use sender_email as display name)
            name_selectors = [
                'input[placeholder*="имя"]',
                'input[placeholder*="Имя"]',
                'input[placeholder*="name"]',
                'input[name="name"]',
                'input[name="displayName"]',
                'input[type="text"]',
                'input.input',  # Generic input class
                'input'  # Last resort - any input
            ]

            name_entered = False
            for selector in name_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        # Use sender_email as the display name
                        self.logger.info(f"Entering sender_email into name field: {selector}")
                        self.enter_name(page, meeting.sender_email, selector)
                        page.wait_for_timeout(1000)
                        name_entered = True
                        break
                except:
                    continue

            if not name_entered:
                self.logger.warning("No visible name input field found, proceeding without entering name")

            # Click join/connect button
            join_selectors = [
                'button:has-text("Подключиться")',  # Connect button
                'button:has-text("Войти")',
                'button:has-text("Присоединиться")',
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

            self.logger.info(f"Successfully joined Yandex Telemost meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join Yandex Telemost meeting: {e}")
            return False
