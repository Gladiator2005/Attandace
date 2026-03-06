from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    user = User(
        employee_id=user_data.employee_id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        phone=user_data.phone,
        department=user_data.department,
        program=user_data.program,
        major=user_data.major,
        specialization=user_data.specialization,
        section=user_data.section,
        semester=user_data.semester,
        role=UserRole(user_data.role),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_employee_id(db: AsyncSession, employee_id: str):
    result = await db.execute(select(User).where(User.employee_id == employee_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100, role: str = None, department: str = None):
    query = select(User)
    if role:
        query = query.where(User.role == UserRole(role))
    if department:
        query = query.where(User.department == department)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_students(db: AsyncSession):
    result = await db.execute(select(User).where(User.role == UserRole.STUDENT, User.is_active == True).order_by(User.employee_id))
    return result.scalars().all()


async def get_faculty(db: AsyncSession):
    result = await db.execute(select(User).where(User.role == UserRole.FACULTY, User.is_active == True).order_by(User.first_name))
    return result.scalars().all()


async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate):
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    for field, value in user_data.model_dump(exclude_unset=True).items():
        if field == "role":
            setattr(user, field, UserRole(value))
        else:
            setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def count_users(db: AsyncSession, role: UserRole = None):
    query = select(func.count(User.id)).where(User.is_active == True)
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    return result.scalar()
