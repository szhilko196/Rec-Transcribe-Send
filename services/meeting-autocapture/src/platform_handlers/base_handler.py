"""
Base Platform Handler - Abstract base class for platform-specific join logic
Phase 5 of Meeting Auto Capture
"""
from abc import ABC, abstractmethod
from playwright.sync_api import Page
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import MeetingInvitation


class BasePlatformHandler(ABC):
    """Abstract base class for platform-specific handlers"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to meeting and join.

        Args:
            page: Playwright Page object
            meeting: MeetingInvitation object

        Returns:
            True on success, False on failure
        """
        pass

    def enter_name(self, page: Page, name: str, selector: str) -> bool:
        """
        Helper: Enter participant name

        Args:
            page: Playwright Page object
            name: Name to enter
            selector: CSS selector for name input

        Returns:
            True on success, False on failure
        """
        try:
            page.fill(selector, name)
            self.logger.debug(f"Entered name: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to enter name: {e}")
            return False

    def enter_password(self, page: Page, password: str, selector: str) -> bool:
        """
        Helper: Enter meeting password

        Args:
            page: Playwright Page object
            password: Password to enter
            selector: CSS selector for password input

        Returns:
            True on success, False on failure
        """
        try:
            page.fill(selector, password)
            self.logger.debug(f"Entered password")
            return True
        except Exception as e:
            self.logger.error(f"Failed to enter password: {e}")
            return False

    def click_join_button(self, page: Page, selector: str) -> bool:
        """
        Helper: Click join button

        Args:
            page: Playwright Page object
            selector: CSS selector for join button

        Returns:
            True on success, False on failure
        """
        try:
            page.click(selector)
            self.logger.debug(f"Clicked join button")
            return True
        except Exception as e:
            self.logger.error(f"Failed to click join: {e}")
            return False

    def wait_for_element(self, page: Page, selector: str, timeout: int = 10000) -> bool:
        """
        Helper: Wait for element to appear

        Args:
            page: Playwright Page object
            selector: CSS selector
            timeout: Timeout in milliseconds

        Returns:
            True if element appeared, False otherwise
        """
        try:
            page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.warning(f"Element not found: {selector}")
            return False
