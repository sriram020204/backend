from fastapi import APIRouter
from core.database import db
from bson import json_util

router = APIRouter()

@router.get("/companies")
def list_companies():
    companies = db["companies"].find({}, {"_id": 1, "name": 1})
    return json_util.dumps(list(companies))
