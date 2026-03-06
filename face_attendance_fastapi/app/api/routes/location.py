import math
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.utils.security import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter()


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    """Calculate great-circle distance in km between two GPS points."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lng2 - lng1)
    a = math.sin(dφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class LocationPayload(BaseModel):
    latitude: float
    longitude: float


@router.get("/campus")
async def get_campus_location(current_user: User = Depends(get_current_user)):
    """Return campus coordinates so the frontend can request and verify student GPS."""
    return {
        "lat": settings.campus_lat,
        "lng": settings.campus_lng,
        "radius_km": settings.campus_radius_km,
        "enabled": settings.campus_lat != 0.0,
    }


@router.post("/verify")
async def verify_location(
    payload: LocationPayload,
    current_user: User = Depends(get_current_user),
):
    """Verify if a student's GPS coordinates are within campus radius."""
    if settings.campus_lat == 0.0:
        return {"valid": True, "distance_km": 0.0, "message": "Location check disabled"}

    dist = haversine_km(payload.latitude, payload.longitude,
                        settings.campus_lat, settings.campus_lng)
    valid = dist <= settings.campus_radius_km
    return {
        "valid": valid,
        "distance_km": round(dist, 3),
        "radius_km": settings.campus_radius_km,
        "message": "On campus ✅" if valid else f"Too far from campus ({dist:.2f} km away) 🚫",
    }
