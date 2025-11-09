"""
Quick SMTP connectivity test
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def test_smtp():
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT'))
    smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from_email = os.getenv('SMTP_FROM_EMAIL')
    smtp_from_name = os.getenv('SMTP_FROM_NAME', 'Meeting Transcriber')

    print(f"Testing SMTP connection...")
    print(f"  Server: {smtp_server}:{smtp_port}")
    print(f"  SSL: {smtp_use_ssl}, TLS: {smtp_use_tls}")
    print(f"  From: {smtp_from_name} <{smtp_from_email}>")

    # Create a test email
    msg = MIMEMultipart()
    msg['Subject'] = 'Test email from Meeting Transcriber'
    msg['From'] = f"{smtp_from_name} <{smtp_from_email}>"
    msg['To'] = smtp_from_email  # Send to ourselves
    msg.attach(MIMEText("This is a test email from Meeting Transcriber SMTP configuration.", 'plain', 'utf-8'))

    try:
        if smtp_use_ssl:
            print("\nConnecting with SSL...")
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                print("[OK] Connected with SSL")
                print("Logging in...")
                server.login(smtp_username, smtp_password)
                print("[OK] Logged in")
                print("Sending message...")
                server.send_message(msg)
                print("[OK] Email sent successfully!")
        else:
            print("\nConnecting with TLS...")
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                print("[OK] Connected")
                if smtp_use_tls:
                    print("Starting TLS...")
                    server.starttls()
                    print("[OK] TLS started")
                print("Logging in...")
                server.login(smtp_username, smtp_password)
                print("[OK] Logged in")
                print("Sending message...")
                server.send_message(msg)
                print("[OK] Email sent successfully!")

        return True

    except Exception as e:
        print(f"[ERROR] SMTP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_smtp()
