import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger(__name__)


def _send_email_sync(to: str, subject_line: str, body: str) -> bool:
    """Synchronous SMTP send — always called via asyncio.to_thread."""
    smtp_host = settings.smtp_host or None
    smtp_user  = settings.smtp_user or None
    smtp_pass  = settings.smtp_password or None
    from_email = settings.from_email or "noreply@antigrav-access.edu"

    if not smtp_host or not smtp_user:
        logger.info(f"📧 EMAIL (console): To={to}, Subject='{subject_line}'")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject_line
        msg["From"] = from_email
        msg["To"] = to
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP(smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to, msg.as_string())
        logger.info(f"Email sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


async def send_absent_email(student_email: str, student_name: str,
                             subject_name: str, subject_code: str, att_date: str):
    """Non-blocking absent email — runs SMTP in a thread pool to avoid blocking the event loop."""
    subject_line = f"Attendance Alert: Absent in {subject_code} – {subject_name}"
    body = f"""
    <html><body style="font-family:Inter,Arial,sans-serif;background:#f0f4f8;padding:20px;">
    <div style="max-width:500px;margin:auto;background:white;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <div style="text-align:center;margin-bottom:20px;">
            <div style="width:48px;height:48px;background:#ef4444;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;color:white;font-size:24px;">✗</div>
        </div>
        <h2 style="color:#1e293b;text-align:center;margin-bottom:4px;">Attendance Alert</h2>
        <p style="color:#64748b;text-align:center;margin-bottom:24px;">You have been marked absent.</p>
        <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px;">Student</td><td style="text-align:right;font-weight:600;color:#1e293b;">{student_name}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px;">Subject</td><td style="text-align:right;font-weight:600;color:#1e293b;">{subject_code} – {subject_name}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px;">Date</td><td style="text-align:right;font-weight:600;color:#1e293b;">{att_date}</td></tr>
            <tr><td style="padding:8px 0;color:#64748b;font-size:14px;">Status</td><td style="text-align:right;font-weight:700;color:#ef4444;">ABSENT</td></tr>
        </table>
        <p style="color:#64748b;font-size:13px;margin-top:20px;text-align:center;">
            If you believe this is an error, please contact your faculty or admin.
        </p>
    </div></body></html>
    """
    return await asyncio.to_thread(_send_email_sync, student_email, subject_line, body)
