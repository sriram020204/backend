from fastapi import APIRouter, HTTPException, Depends
from models.registration_models import RegistrationRequest
from core.database import db
from routers.auth import get_current_user
from datetime import datetime
import traceback

router = APIRouter()
companies_collection = db["companies"]

@router.post("/register")
def register_company(payload: RegistrationRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Convert the payload to a dictionary and add user info
        profile_data = {
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "companyDetails": payload.companyDetails.dict(),
            "businessCapabilities": payload.businessCapabilities.dict(),
            "financialLegalInfo": payload.financialLegalInfo.dict(),
            "tenderExperience": payload.tenderExperience.dict(),
            "geographicDigitalReach": payload.geographicDigitalReach.dict(),
            "termsAndConditions": payload.termsAndConditions.dict(),
            "declarationsUploads": payload.declarationsUploads.dict(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # Check if company profile already exists for this user
        existing_profile = companies_collection.find_one({"user_id": current_user["id"]})
        
        if existing_profile:
            # Update existing profile
            profile_data["updated_at"] = datetime.utcnow()
            companies_collection.update_one(
                {"user_id": current_user["id"]},
                {"$set": profile_data}
            )
            return {
                "message": "Company profile updated successfully",
                "id": str(existing_profile["_id"]),
                "action": "updated"
            }
        else:
            # Create new profile
            result = companies_collection.insert_one(profile_data)
            return {
                "message": "Company profile registered successfully",
                "id": str(result.inserted_id),
                "action": "created"
            }

    except Exception as e:
        print(f"Registration error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.get("/profile")
def get_company_profile(current_user: dict = Depends(get_current_user)):
    try:
        profile = companies_collection.find_one({"user_id": current_user["id"]})
        if not profile:
            raise HTTPException(status_code=404, detail="Company profile not found")
        
        # Convert ObjectId to string
        profile["_id"] = str(profile["_id"])
        return profile
    except Exception as e:
        print(f"Profile fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")