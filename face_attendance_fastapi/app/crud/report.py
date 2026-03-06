from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date
from app.models.attendance_report import AttendanceReport, AttendanceStatus

async def get_or_create_report(db: AsyncSession, user_id: int, report_date: date):
    result = await db.execute(select(AttendanceReport).where(and_(AttendanceReport.user_id == user_id, AttendanceReport.date == report_date)))
    report = result.scalar_one_or_none()
    if not report:
        report = AttendanceReport(user_id=user_id, date=report_date, status=AttendanceStatus.ABSENT)
        db.add(report)
        await db.commit()
        await db.refresh(report)
    return report

async def get_monthly_reports(db: AsyncSession, user_id: int, year: int, month: int):
    from datetime import date as d
    start = d(year, month, 1)
    end = d(year, month + 1, 1) if month < 12 else d(year + 1, 1, 1)
    result = await db.execute(select(AttendanceReport).where(and_(AttendanceReport.user_id == user_id, AttendanceReport.date >= start, AttendanceReport.date < end)))
    return result.scalars().all()
