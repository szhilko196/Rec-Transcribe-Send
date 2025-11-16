"""
Email Monitor - IMAP email monitoring for meeting invitations
Phase 1 of Meeting Auto Capture
"""
import imapclient
import email
from email import policy
from email.parser import BytesParser
import logging
import time
import threading
from typing import List, Dict, Optional, Callable
import os


class EmailMonitor:
    """Monitor IMAP folder for new meeting invitations"""

    def __init__(self, config: dict, on_email_callback: Optional[Callable] = None):
        """
        Initialize email monitor

        Args:
            config: Dictionary with IMAP configuration
                - host: IMAP server host
                - port: IMAP server port
                - username: Email username
                - password: Email password
                - folder: Folder to monitor
                - check_interval: Seconds between checks
            on_email_callback: Function to call when new email detected
        """
        self.host = config['host']
        self.port = config['port']
        self.username = config['username']
        self.password = config['password']
        self.folder = config['folder']
        self.check_interval = config['check_interval']
        self.on_email_callback = on_email_callback

        self.logger = logging.getLogger(__name__)
        self.client: Optional[imapclient.IMAPClient] = None
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def connect(self) -> imapclient.IMAPClient:
        """
        Establish IMAP connection

        Returns:
            IMAPClient instance

        Raises:
            Exception: If connection fails
        """
        try:
            self.logger.info(f"Connecting to IMAP server {self.host}:{self.port}")
            client = imapclient.IMAPClient(self.host, port=self.port, ssl=True)
            client.login(self.username, self.password)

            # Select folder
            client.select_folder(self.folder)
            self.logger.info(f"Connected to IMAP and selected folder: {self.folder}")

            return client

        except Exception as e:
            self.logger.error(f"Failed to connect to IMAP: {e}")
            raise

    def fetch_new_emails(self) -> List[Dict]:
        """
        Fetch UNSEEN emails from folder

        Returns:
            List of email data dictionaries
        """
        try:
            if not self.client:
                self.client = self.connect()

            # Search for UNSEEN (unread) messages only
            messages = self.client.search(['UNSEEN'])

            if not messages:
                return []

            self.logger.info(f"Found {len(messages)} new email(s)")

            emails = []
            for msg_id in messages:
                try:
                    # Fetch email data
                    fetch_data = self.client.fetch([msg_id], ['RFC822'])
                    email_data = fetch_data[msg_id][b'RFC822']

                    # Parse email
                    parsed_email = self.parse_email(email_data)
                    parsed_email['imap_id'] = msg_id
                    emails.append(parsed_email)

                    # Mark as seen after processing
                    self.client.add_flags([msg_id], [imapclient.SEEN])
                    self.logger.debug(f"Processed email ID {msg_id} and marked as seen")

                except Exception as e:
                    self.logger.error(f"Error processing email ID {msg_id}: {e}")
                    continue

            return emails

        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
            # Try to reconnect on next iteration
            self.client = None
            return []

    def parse_email(self, email_data: bytes) -> Dict:
        """
        Parse email to extract body, headers, attachments

        Args:
            email_data: Raw email bytes

        Returns:
            Dictionary with email components
        """
        # Parse email with modern policy
        parser = BytesParser(policy=policy.default)
        email_msg = parser.parsebytes(email_data)

        # Extract headers
        headers = {
            'subject': str(email_msg.get('Subject', '')),
            'from': str(email_msg.get('From', '')),
            'to': str(email_msg.get('To', '')),
            'date': str(email_msg.get('Date', '')),
            'message_id': str(email_msg.get('Message-ID', ''))
        }

        # Extract body parts
        html_body = None
        text_body = None

        # Get HTML body
        html_part = email_msg.get_body(preferencelist=('html',))
        if html_part:
            html_body = html_part.get_content()

        # Get plain text body
        text_part = email_msg.get_body(preferencelist=('plain',))
        if text_part:
            text_body = text_part.get_content()

        # Extract attachments and calendar parts
        attachments = []
        calendar_attachments = []

        # Walk through ALL parts of the email (including inline calendar)
        for part in email_msg.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()

            # Skip multipart containers
            if part.is_multipart():
                continue

            # Extract calendar parts (text/calendar)
            if content_type == 'text/calendar':
                try:
                    calendar_attachments.append({
                        'filename': filename or 'calendar.ics',
                        'content': part.get_content()
                    })
                    self.logger.debug(f"Found calendar part: {content_type}")
                except Exception as e:
                    self.logger.error(f"Error extracting calendar: {e}")

            # Extract regular attachments
            if filename:
                try:
                    attachments.append({
                        'filename': filename,
                        'content_type': content_type,
                        'size': len(part.get_content())
                    })
                except Exception as e:
                    self.logger.error(f"Error extracting attachment {filename}: {e}")

        result = {
            'headers': headers,
            'html_body': html_body,
            'text_body': text_body,
            'attachments': attachments,
            'calendar_attachments': calendar_attachments
        }

        self.logger.debug(f"Parsed email: {headers['subject']}")
        return result

    def extract_calendar_attachment(self, email_data: Dict) -> Optional[bytes]:
        """
        Extract .ics attachment if present

        Args:
            email_data: Parsed email dictionary

        Returns:
            .ics file content as bytes, or None
        """
        if email_data.get('calendar_attachments'):
            return email_data['calendar_attachments'][0]['content']
        return None

    def monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        self.logger.info("Email monitoring loop started")

        while self.running:
            try:
                # Fetch new emails
                new_emails = self.fetch_new_emails()

                # Process each email
                for email_data in new_emails:
                    if self.on_email_callback:
                        try:
                            self.on_email_callback(email_data)
                        except Exception as e:
                            self.logger.error(f"Error in email callback: {e}")

                # Sleep until next check
                time.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

        self.logger.info("Email monitoring loop stopped")

    def start(self):
        """Start monitoring in background thread"""
        if self.running:
            self.logger.warning("Email monitor already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Email monitor started")

    def stop(self):
        """Stop monitoring"""
        if not self.running:
            return

        self.logger.info("Stopping email monitor...")
        self.running = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        if self.client:
            try:
                self.client.logout()
            except:
                pass

        self.logger.info("Email monitor stopped")

    def is_connected(self) -> bool:
        """Check if connected to IMAP server"""
        return self.client is not None
