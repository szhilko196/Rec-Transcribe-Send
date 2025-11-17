"""
JVC Inspider Handler - Priority 2
Handler for jvc.inspider.ru meeting platform
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class JVCInspiderHandler(BasePlatformHandler):
    """Handler for jvc.inspider.ru platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to JVC Inspider meeting and join as guest

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining JVC Inspider meeting: {meeting.meeting_link}")

            # Navigate to meeting (will redirect to inspider.ru/sso/auth/)
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)
            self.logger.info(f"Navigated to URL: {page.url}")

            # Wait for redirect to SSO page and page to stabilize
            page.wait_for_timeout(2000)

            # Take screenshot for debugging
            try:
                screenshot_path = f"data/meetings/jvc_sso_page_{meeting.id[:8]}.png"
                page.screenshot(path=screenshot_path)
                self.logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                self.logger.warning(f"Could not save screenshot: {e}")

            # Wait for and fill guest name input field
            # The page shows: <input placeholder="Имя Фамилия"> in the guest section
            name_entered = False
            name_selectors = [
                'input[placeholder="Имя Фамилия"]',  # Primary - matches screenshot
                'input[name="guest"]',  # Backup
                'input.input[type="text"]'  # Fallback
            ]

            for selector in name_selectors:
                try:
                    self.logger.info(f"Waiting for name input field: {selector}")
                    element = page.wait_for_selector(selector, state='visible', timeout=10000)
                    if element:
                        self.logger.info(f"Found name input field: {selector}")
                        # Clear field first, then fill
                        element.fill('')
                        element.fill(meeting.sender_email)
                        self.logger.info(f"Entered guest name: {meeting.sender_email}")
                        name_entered = True
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not name_entered:
                self.logger.error("Could not find name input field!")
                return False

            # Wait a bit after entering name
            page.wait_for_timeout(1000)

            # Click "Войти как гость" (Enter as Guest) button
            # The button is in the lower section of the SSO page
            button_clicked = False
            join_selectors = [
                'button:has-text("Войти как гость")',  # Primary - matches screenshot exactly
                'button.is-warning:has-text("гость")',  # Backup with partial text
                'button[type="submit"]:has-text("Войти")'  # Fallback
            ]

            for selector in join_selectors:
                try:
                    self.logger.info(f"Waiting for join button: {selector}")
                    element = page.wait_for_selector(selector, state='visible', timeout=10000)
                    if element:
                        self.logger.info(f"Found join button: {selector}")
                        element.click()
                        self.logger.info(f"Clicked join button")
                        button_clicked = True
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not button_clicked:
                self.logger.error("Could not find or click join button!")
                return False

            # Wait for meeting interface to load
            self.logger.info("Waiting for meeting interface to load...")
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined JVC Inspider meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join JVC Inspider meeting: {e}", exc_info=True)
            return False
