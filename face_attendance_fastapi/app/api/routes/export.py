import io
from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.crud.subject_attendance import get_all_students_threshold
from fastapi import HTTPException

router = APIRouter()


def _build_pdf(subject_name: str, subject_code: str, threshold: float,
               rows: list, month: int, year: int) -> bytes:
    """Generate PDF attendance report using reportlab."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=16, spaceAfter=6)
    sub_style  = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)

    story = []
    month_name = date(year, month, 1).strftime("%B %Y") if month else str(year)
    story.append(Paragraph(f"Attendance Report – {subject_code}: {subject_name}", title_style))
    story.append(Paragraph(f"Period: {month_name} | Minimum Threshold: {threshold}%", sub_style))
    story.append(Spacer(1, 0.4*cm))

    # Table header
    headers = ["#", "Enrollment No.", "Student Name", "Department",
               "Classes Attended", "Classes Conducted", "Percentage", "Status"]
    table_data = [headers]

    for i, r in enumerate(rows, 1):
        pct = r.get("percentage", 0.0)
        status = "✅ Above" if pct >= threshold else "⚠️ Below"
        table_data.append([
            str(i),
            r.get("enrollment_no", ""),
            r.get("student_name", ""),
            r.get("department", "") or "-",
            str(r.get("classes_attended", 0)),
            str(r.get("classes_conducted", 0)),
            f"{pct:.1f}%",
            status,
        ])

    col_widths = [1*cm, 3.5*cm, 5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3*cm, 3.5*cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ROWHEIGHT", (0, 0), (-1, -1), 0.7*cm),
    ]))
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


@router.get("/pdf")
async def export_pdf(
    subject_id: int = Query(...),
    month: int = Query(0, ge=0, le=12),
    year: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download attendance report as PDF for a subject."""
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Not allowed")

    sub_result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = sub_result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    rows = await get_all_students_threshold(db, subject_id)
    threshold = subject.attendance_threshold or 75.0
    yr = year or date.today().year

    pdf_bytes = _build_pdf(subject.name, subject.code, threshold, rows, month, yr)
    filename = f"{subject.code}_attendance_{yr}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
