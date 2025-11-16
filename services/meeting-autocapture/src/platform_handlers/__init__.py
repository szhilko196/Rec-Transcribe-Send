"""
Platform Handlers Package
Exports all platform-specific handlers and get_handler() function
"""
from .base_handler import BasePlatformHandler
from .gpb_video import GPBVideoHandler
from .psbank_meeting import PSBankMeetingHandler
from .zoom import ZoomHandler
from .webex import WebexHandler
from .google_meet import GoogleMeetHandler
from .telemost_yandex import TelemostYandexHandler


# Mapping of platform names to handler classes
HANDLERS = {
    'gpb.video': GPBVideoHandler,
    'meeting.psbank.ru': PSBankMeetingHandler,
    'zoom': ZoomHandler,
    'webex': WebexHandler,
    'google_meet': GoogleMeetHandler,
    'telemost.yandex': TelemostYandexHandler,
}


def get_handler(platform: str) -> BasePlatformHandler:
    """
    Get handler instance for platform

    Args:
        platform: Platform name (e.g., 'gpb.video', 'zoom')

    Returns:
        Platform handler instance

    Raises:
        ValueError: If no handler found for platform
    """
    handler_class = HANDLERS.get(platform)

    if handler_class:
        return handler_class()
    else:
        # Return default handler (GPBVideoHandler as fallback)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"No handler for platform: {platform}, using GPBVideoHandler as fallback")
        return GPBVideoHandler()


__all__ = [
    'BasePlatformHandler',
    'GPBVideoHandler',
    'PSBankMeetingHandler',
    'ZoomHandler',
    'WebexHandler',
    'GoogleMeetHandler',
    'TelemostYandexHandler',
    'get_handler'
]
