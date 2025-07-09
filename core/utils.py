from core.database import profiles
from bson import ObjectId

def save_or_update_profile(user_id: str, profile_data: dict):
    """Save or update complete company profile"""
    existing = profiles.find_one({"user_id": user_id})
    
    if existing:
        profiles.update_one(
            {"user_id": user_id},
            {"$set": profile_data}
        )
        return str(existing["_id"]), "updated"
    else:
        result = profiles.insert_one(profile_data)
        return str(result.inserted_id), "created"

def get_profile_by_user_id(user_id: str):
    """Get company profile by user ID"""
    return profiles.find_one({"user_id": user_id})

def mark_profile_submitted(user_id: str):
    """Mark profile as submitted"""
    profiles.update_one(
        {"user_id": user_id},
        {"$set": {"submitted": True}}
    )