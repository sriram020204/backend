# models/match_models.py
from pydantic import BaseModel
from typing import List, Optional, Dict

class MatchRequest(BaseModel):
    company_profile: dict
    score_threshold: Optional[float] = 70.0

class MatchResult(BaseModel):
    form_url: str
    title: str
    reference_number: str
    location: str
    business_category: List[str]
    deadline: str
    matching_score: float
    eligible: bool
    field_scores: Dict[str, float]
    missing_fields: Dict[str, str]
