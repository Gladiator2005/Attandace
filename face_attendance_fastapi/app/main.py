import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings
from app.db.session import init_db, close_db, AsyncSessionLocal
from app.api.routes import auth, users, face, attendance, records, reports, admin, health
from app.api.routes import subjects as subjects_router
from app.api.routes import threshold as threshold_router
from app.api.routes import schedule as schedule_router
from app.api.routes import notifications as notifications_router
from app.api.routes import leave as leave_router
from app.api.routes import session as session_router
from app.api.routes import bulk_import as bulk_import_router
from app.api.routes import location as location_router
from app.api.routes import audit_route as audit_router
from app.api.routes import export as export_router
from app.api.routes import calendar as calendar_router
from app.api.routes import mentor as mentor_router
from app.api.routes.pages import router as pages_router
from app.middleware.rate_limit import RateLimitMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _create_default_admin()
    logger.info("Application started successfully")
    yield
    await close_db()
    logger.info("Application stopped")


async def _create_default_admin():
    from app.models.user import User, UserRole
    from app.utils.security import hash_password
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin@attendance.com"))
        if result.scalar_one_or_none() is None:
            admin_user = User(
                employee_id="ADMIN001",
                first_name="Admin",
                last_name="User",
                email="admin@attendance.com",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
                department="Administration",
                is_active=True,
            )
            db.add(admin_user)
            await db.commit()
            logger.info("Default admin user created: admin@attendance.com / admin123")


app = FastAPI(
    title="AntiGrav Access – College ERP",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(face.router, prefix="/api/face", tags=["face"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["attendance"])
app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(subjects_router.router, prefix="/api/subjects", tags=["subjects"])
app.include_router(threshold_router.router, prefix="/api/threshold", tags=["threshold"])
app.include_router(schedule_router.router, prefix="/api/schedule", tags=["schedule"])
app.include_router(notifications_router.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(leave_router.router, prefix="/api/leave", tags=["leave"])
app.include_router(session_router.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(bulk_import_router.router, prefix="/api/import", tags=["import"])
app.include_router(location_router.router, prefix="/api/location", tags=["location"])
app.include_router(audit_router.router, prefix="/api/audit", tags=["audit"])
app.include_router(export_router.router, prefix="/api/export", tags=["export"])
app.include_router(calendar_router.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(mentor_router.router, prefix="/api/mentor", tags=["mentor"])
app.include_router(health.router, tags=["health"])

# Page routes
app.include_router(pages_router)
