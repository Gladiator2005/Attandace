from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.crud.user import get_user_by_email, create_user
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token
from app.utils.security import verify_password, create_access_token, hash_password, get_current_user
from app.models.user import User, UserRole

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    token = create_access_token(data={"sub": user.email})
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax", max_age=10800)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await create_user(db, user_data)
    return UserResponse(id=user.id, employee_id=user.employee_id, first_name=user.first_name, last_name=user.last_name, email=user.email, phone=user.phone, department=user.department, role=user.role.value, is_active=user.is_active, has_face_data=user.has_face_data, created_at=user.created_at)

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}
