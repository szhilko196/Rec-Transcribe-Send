"""
MRA Gazprombank Handler - Priority 1
Handler for mra.gazprombank.ru meeting platform
"""
from playwright.sync_api import Page
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_handlers.base_handler import BasePlatformHandler
from models import MeetingInvitation


class MRAGazprombankHandler(BasePlatformHandler):
    """Handler for mra.gazprombank.ru platform"""

    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to MRA Gazprombank meeting and join as guest

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        try:
            self.logger.info(f"Joining MRA Gazprombank meeting: {meeting.meeting_link}")

            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle', timeout=30000)
            self.logger.info(f"Navigated to URL: {page.url}")

            # Wait for page to stabilize
            page.wait_for_timeout(2000)

            # Take screenshot for debugging
            try:
                screenshot_path = f"data/meetings/mra_gpb_step1_{meeting.id[:8]}.png"
                page.screenshot(path=screenshot_path)
                self.logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                self.logger.warning(f"Could not save screenshot: {e}")

            # Check if we're already on the join screen (name remembered from previous session)
            # Try to find the join button with a short timeout
            self.logger.info("Checking if join button is already visible (name remembered)...")
            skip_name_entry = False
            try:
                join_button_test = page.wait_for_selector(
                    'button:has-text("Присоединиться к совещанию")',
                    state='visible',
                    timeout=3000
                )
                if join_button_test:
                    self.logger.info("✅ Join button already visible - name was remembered! Skipping to Step 3.")
                    skip_name_entry = True
            except Exception:
                self.logger.info("Join button not visible yet - proceeding with name entry flow")
                skip_name_entry = False

            # If join button is NOT visible, we need to enter the name first
            if not skip_name_entry:
                # Step 1: Enter name in the input field
                self.logger.info("Entering name (first visit)...")
                name_entered = False
                name_selectors = [
                    'input[type="text"]',  # Primary - generic text input
                    'input[placeholder*="имя"]',  # Backup - contains "имя" in placeholder
                    'input.form-control',  # Fallback - common CSS class
                    'input'  # Last resort - any input
                ]

                for selector in name_selectors:
                    try:
                        self.logger.info(f"Waiting for name input field: {selector}")
                        element = page.wait_for_selector(selector, state='visible', timeout=10000)
                        if element:
                            self.logger.info(f"Found name input field: {selector}")
                            # Clear field first, then fill with sender_email
                            element.fill('')
                            element.fill(meeting.sender_email)
                            self.logger.info(f"Entered name: {meeting.sender_email}")
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

                # Step 2: Click "Введите отображаемое имя" button
                button_clicked = False
                submit_name_selectors = [
                    'button:has-text("Введите отображаемое имя")',  # Primary - exact text match
                    'button:has-text("отображаемое имя")',  # Backup - partial text
                    'button[type="submit"]',  # Fallback - submit button
                    'button.btn-primary'  # Common CSS class
                ]

                for selector in submit_name_selectors:
                    try:
                        self.logger.info(f"Waiting for submit name button: {selector}")
                        element = page.wait_for_selector(selector, state='visible', timeout=10000)
                        if element:
                            self.logger.info(f"Found submit name button: {selector}")
                            element.click()
                            self.logger.info(f"Clicked submit name button")
                            button_clicked = True
                            break
                    except Exception as e:
                        self.logger.debug(f"Selector {selector} failed: {e}")
                        continue

                if not button_clicked:
                    self.logger.error("Could not find or click submit name button!")
                    return False

                # Wait for join meeting screen to load
                self.logger.info("Waiting for join meeting screen to load...")
                page.wait_for_timeout(3000)

            # Take screenshot of step 2
            try:
                screenshot_path = f"data/meetings/mra_gpb_step2_{meeting.id[:8]}.png"
                page.screenshot(path=screenshot_path)
                self.logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                self.logger.warning(f"Could not save screenshot: {e}")

            # Step 3: Click "Присоединиться к совещанию" (Join meeting) button
            # Wait longer for page to fully render
            page.wait_for_timeout(2000)

            join_clicked = False
            join_selectors = [
                'button:has-text("Присоединиться к совещанию")',  # Primary - exact text
                'button:has-text("Присоединиться")',  # Backup - partial text
                'button:has-text("совещанию")',  # Fallback - contains "meeting"
                'button.btn-success',  # Common green button class
                'button[type="button"]',  # Any button
            ]

            for selector in join_selectors:
                try:
                    self.logger.info(f"Waiting for join meeting button: {selector}")
                    element = page.wait_for_selector(selector, state='visible', timeout=15000)
                    if element:
                        self.logger.info(f"Found join meeting button: {selector}")

                        # Scroll to button to ensure it's in view
                        element.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)

                        # Click the button
                        element.click()
                        self.logger.info(f"Clicked join meeting button")
                        join_clicked = True
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not join_clicked:
                self.logger.error("Could not find or click join meeting button!")
                return False

            # Wait for meeting interface to load
            self.logger.info("Waiting for meeting interface to load...")
            page.wait_for_timeout(5000)

            # Take final screenshot
            try:
                screenshot_path = f"data/meetings/mra_gpb_joined_{meeting.id[:8]}.png"
                page.screenshot(path=screenshot_path)
                self.logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                self.logger.warning(f"Could not save screenshot: {e}")

            self.logger.info(f"Successfully joined MRA Gazprombank meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join MRA Gazprombank meeting: {e}", exc_info=True)
            return False
