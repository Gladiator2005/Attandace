from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.utils.security import get_current_user
from app.models.user import User, UserRole
from app.crud.user import get_user_by_id, get_users, update_user
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()

@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, employee_id=current_user.employee_id, first_name=current_user.first_name, last_name=current_user.last_name, email=current_user.email, phone=current_user.phone, department=current_user.department, role=current_user.role.value, is_active=current_user.is_active, has_face_data=current_user.has_face_data, created_at=current_user.created_at)

@router.get("/")
async def list_users(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role not in [UserRole.ADMIN, UserRole.FACULTY]:
        raise HTTPException(status_code=403, detail="Access denied")
    users = await get_users(db)
    return [{"id": u.id, "employee_id": u.employee_id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email, "role": u.role.value, "department": u.department, "is_active": u.is_active} for u in users]
