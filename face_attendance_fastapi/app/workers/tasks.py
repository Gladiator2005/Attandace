import logging
from datetime import date
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models import User, AttendanceReport, AttendanceStatus, AuditLog, AuditAction

logger = logging.getLogger(__name__)

async def generate_daily_reports():
    today = date.today()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.is_active == True))
        users = result.scalars().all()
        for user in users:
            report_result = await db.execute(select(AttendanceReport).where(AttendanceReport.user_id == user.id, AttendanceReport.date == today))
            if report_result.scalar_one_or_none() is None:
                report = AttendanceReport(user_id=user.id, date=today, status=AttendanceStatus.ABSENT, total_hours=0)
                db.add(report)
        audit = AuditLog(action=AuditAction.REPORT_GENERATED, description=f"Daily reports for {today}")
        db.add(audit)
        await db.commit()
        logger.info(f"Daily reports generated for {today}")
