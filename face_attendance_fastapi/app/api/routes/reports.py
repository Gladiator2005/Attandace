from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User
from app.crud.report import get_monthly_reports

router = APIRouter()

@router.get("/monthly")
async def monthly_report(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    now = datetime.now()
    reports = await get_monthly_reports(db, current_user.id, now.year, now.month)
    present = sum(1 for r in reports if r.status.value in ["Present", "Late"])
    late = sum(1 for r in reports if r.status.value == "Late")
    absent = sum(1 for r in reports if r.status.value == "Absent")
    return {"total_present": present, "total_late": late, "total_absent": absent, "month": now.month, "year": now.year}
