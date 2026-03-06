from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.face_data import FaceData

async def create_face_data(db: AsyncSession, user_id: int, encoding: str, image_path: str = None, face_quality: float = 0.0):
    face = FaceData(user_id=user_id, encoding=encoding, image_path=image_path, face_quality=face_quality, is_verified=True)
    db.add(face)
    await db.commit()
    await db.refresh(face)
    return face

async def get_face_data_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(FaceData).where(FaceData.user_id == user_id))
    return result.scalars().all()

async def get_all_face_data(db: AsyncSession):
    result = await db.execute(select(FaceData))
    return result.scalars().all()
