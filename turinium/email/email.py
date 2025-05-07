import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from turinium.logging import TLogging  # Turinium logging

class EmailSender:
    """
    A class to send emails using the SMTP protocol.
    Supports context management for SMTP connection handling.
    """

    def __init__(self, smtp_server: str, sender_email: str, password: str,
                 port: int = 587, debug_level: int = 0):
        """
        Initialize the EmailSender instance.

        :param smtp_server: The address of the SMTP server.
        :param sender_email: The sender's email address.
        :param password: The sender's email account password.
        :param port: The SMTP port (default: 587).
        :param debug_level: Debugging level for SMTP (default: 0, off).
        """
        self.smtp_server = smtp_server
        self.sender_email = sender_email
        self.password = password
        self.port = port
        self.debug_level = debug_level
        self.smtp_obj = None  # SMTP connection

        self.logger = TLogging("EmailSender", log_filename="email_logs", log_to=("console", "file"))

    def __enter__(self):
        """
        Establish SMTP connection and log in when used in a context manager.

        :return: Self, the EmailSender instance.
        """
        try:
            self.smtp_obj = smtplib.SMTP(self.smtp_server, self.port, timeout=10)
            self.smtp_obj.starttls()
            self.smtp_obj.login(self.sender_email, self.password)

            if self.debug_level:
                self.smtp_obj.set_debuglevel(self.debug_level)

            self.logger.info("Connected to SMTP server successfully.")
            return self

        except smtplib.SMTPException as e:
            self.logger.error(f"Failed to connect to SMTP server: {e}")
            raise RuntimeError(f"SMTP Connection Error: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the SMTP connection upon exiting the context.
        """
        if self.smtp_obj:
            self.smtp_obj.quit()
            self.logger.info("SMTP connection closed.")

    def _create_message(self, to_emails: List[str], subject: str, html_message: str,
                        text_message: Optional[str] = None, cc_emails: Optional[List[str]] = None,
                        attachments: Optional[List[str]] = None) -> MIMEMultipart:
        """
        Creates an email message with HTML, plaintext fallback, and optional attachments.

        :param to_emails: List of recipient emails.
        :param subject: Email subject.
        :param html_message: HTML content of the email.
        :param text_message: (Optional) Plain text alternative content.
        :param cc_emails: (Optional) List of CC recipient emails.
        :param attachments: (Optional) List of file paths to attach.
        :return: MIMEMultipart email message.
        """
        # Use 'mixed' to allow text, HTML, and attachments together
        msg = MIMEMultipart('mixed')
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject

        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)

        # BCC should not be added to headers

        # Build the 'alternative' part that includes both plain-text and HTML versions
        alt_part = MIMEMultipart('alternative')
        if text_message:
            alt_part.attach(MIMEText(text_message, 'plain'))
        alt_part.attach(MIMEText(html_message, 'html'))

        # Attach the text/HTML content to the main message
        msg.attach(alt_part)

        # Attach files if any
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as file:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(filepath)}"')
                    msg.attach(part)

        return msg

    def send_email(self, to_emails: List[str], subject: str, html_message: str,
                   text_message: Optional[str] = None, cc_emails: Optional[List[str]] = None,
                   bcc_emails: Optional[List[str]] = None, attachments: Optional[List[str]] = None) -> bool:
        """
        Sends an email with HTML and optional plain-text fallback, CC, BCC, and attachments.

        :param to_emails: List of recipient emails.
        :param subject: Email subject.
        :param html_message: HTML content of the email.
        :param text_message: (Optional) Plain-text version of the message.
        :param cc_emails: (Optional) List of CC recipient emails.
        :param bcc_emails: (Optional) List of BCC recipient emails.
        :param attachments: (Optional) List of file paths to attach.
        :return: True if email was sent successfully, False otherwise.
        """
        if not self.smtp_obj:
            self.logger.error("Attempted to send an email without an active SMTP connection.")
            raise RuntimeError("SMTP connection is not established.")

        to_emails = to_emails or []
        cc_emails = cc_emails or []
        bcc_emails = bcc_emails or []

        # Ensure at least one recipient
        all_recipients = to_emails + cc_emails + bcc_emails
        if not all_recipients:
            self.logger.warning("No recipients provided for email.")
            return False

        try:
            # Create email message
            msg = self._create_message(to_emails, subject, html_message, text_message, cc_emails, attachments)

            # Send the email
            self.smtp_obj.sendmail(self.sender_email, all_recipients, msg.as_string())
            self.logger.info(f"Email sent successfully to {', '.join(all_recipients)}")
            return True

        except smtplib.SMTPException as e:
            self.logger.error(f"Failed to send email: {e}")

        return False
