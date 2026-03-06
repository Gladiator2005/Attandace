from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.utils.security import get_current_user, hash_password
from app.models.user import User, UserRole
from app.crud.user import get_user_by_email, get_user_by_employee_id, create_user
from app.schemas.user import UserCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def _get_optional_user(request: Request, db: AsyncSession) -> Optional[User]:
    try:
        return await get_current_user(request, token=None, db=db)
    except Exception:
        return None


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    user = await _get_optional_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": current_user})


@router.get("/mark-attendance", response_class=HTMLResponse)
async def mark_attendance_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("mark_attendance.html", {"request": request, "user": current_user})


@router.get("/add-face", response_class=HTMLResponse)
async def add_face_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("add_face.html", {"request": request, "user": current_user})


@router.get("/records", response_class=HTMLResponse)
async def records_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("records.html", {"request": request, "user": current_user})


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.STUDENT:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("admin.html", {"request": request, "user": current_user})


@router.get("/subjects", response_class=HTMLResponse)
async def subjects_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("subjects.html", {"request": request, "user": current_user})


@router.get("/mark-subject-attendance", response_class=HTMLResponse)
async def mark_subject_attendance_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.STUDENT:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("mark_subject_attendance.html", {"request": request, "user": current_user})


@router.get("/threshold", response_class=HTMLResponse)
async def threshold_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("threshold.html", {"request": request, "user": current_user})


@router.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("schedule.html", {"request": request, "user": current_user})


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("notifications.html", {"request": request, "user": current_user})


@router.get("/face-attendance", response_class=HTMLResponse)
async def face_attendance_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("face_attendance.html", {"request": request, "user": current_user})


@router.get("/disputes", response_class=HTMLResponse)
async def disputes_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.STUDENT:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("disputes.html", {"request": request, "user": current_user})


@router.get("/leave", response_class=HTMLResponse)
async def leave_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("leave.html", {"request": request, "user": current_user})


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("calendar.html", {"request": request, "user": current_user})


@router.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("audit.html", {"request": request, "user": current_user})


@router.get("/add-user", response_class=HTMLResponse)
async def add_user_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("add_user.html", {"request": request, "user": current_user})


@router.post("/add-user", response_class=HTMLResponse)
async def add_user_submit(
    request: Request,
    employee_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("Student"),
    phone: str = Form(""),
    department: str = Form(""),
    program: str = Form(""),
    major: str = Form(""),
    specialization: str = Form(""),
    section: str = Form(""),
    semester: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        return RedirectResponse(url="/dashboard")

    error = None
    success = None

    if len(password) < 6:
        error = "Password must be at least 6 characters."
    elif await get_user_by_email(db, email):
        error = f"Email '{email}' is already registered."
    elif await get_user_by_employee_id(db, employee_id):
        error = f"ID '{employee_id}' already exists."
    else:
        try:
            sem = int(semester) if semester else None
            user_data = UserCreate(
                employee_id=employee_id, first_name=first_name, last_name=last_name,
                email=email, password=password, role=role,
                phone=phone or None, department=department or None,
                program=program or None, major=major or None,
                specialization=specialization or None, section=section or None,
                semester=sem,
            )
            new_user = await create_user(db, user_data)
            success = f"User '{new_user.full_name}' ({new_user.employee_id}) created as {new_user.role.value}."
        except Exception as e:
            error = f"Failed: {str(e)}"

    return templates.TemplateResponse("add_user.html", {
        "request": request, "user": current_user, "error": error, "success": success,
    })
