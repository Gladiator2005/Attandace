from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.attendance import get_attendance_records
from app.services.report_service import generate_excel_report, generate_pdf_report

router = APIRouter()

@router.get("/")
async def get_records(page: int = 1, per_page: int = 20, from_date: str = None, to_date: str = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = None if current_user.role in [UserRole.ADMIN, UserRole.FACULTY] else current_user.id
    skip = (page - 1) * per_page
    records = await get_attendance_records(db, user_id=user_id, from_date=from_date, to_date=to_date, skip=skip, limit=per_page)
    return {"records": [{"id": r.id, "user_id": r.user_id, "date": r.timestamp.strftime("%Y-%m-%d"), "time": r.timestamp.strftime("%H:%M:%S"), "entry_type": r.entry_type.value, "confidence_score": round(r.confidence_score, 1), "is_verified": r.is_verified, "is_late": r.is_late} for r in records], "page": page, "per_page": per_page}

@router.get("/export/{format}")
async def export_records(format: str, from_date: str = None, to_date: str = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = None if current_user.role in [UserRole.ADMIN, UserRole.FACULTY] else current_user.id
    records = await get_attendance_records(db, user_id=user_id, from_date=from_date, to_date=to_date, limit=1000)
    if format == "excel":
        output = generate_excel_report(records)
        if output:
            return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=attendance.xlsx"})
    elif format == "pdf":
        output = generate_pdf_report(records)
        if output:
            return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=attendance.pdf"})
    raise HTTPException(status_code=400, detail="Export failed")
