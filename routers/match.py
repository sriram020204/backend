from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from core.database import db
from services.basic_filter import filter_tenders
from services.eligibility_extractor import extract_eligibility_text_from_url
from services.eligibility_parser import extract_eligibility_json_general
from services.tender_matcher import compute_tender_match_score
from services.summarizer import PDFSummaryService
from routers.auth import get_current_user
from datetime import datetime
from tempfile import NamedTemporaryFile
import traceback
import requests
import os
from urllib.parse import urlparse
router = APIRouter()

companies = db["companies"]
tenders = db["filtered_tenders"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")

def serialize_tender(tender):
    """Convert ObjectId to string for JSON serialization"""
    if "_id" in tender:
        tender["_id"] = str(tender["_id"])
    return tender

@router.get("/tenders/summary")
def get_tenders_summary(current_user: dict = Depends(get_current_user)):
    """Get total and filtered tender counts"""
    try:
        company = companies.find_one({"user_id": current_user["id"]})
        print("📄 Loaded company profile:", company)

        if not company:
            raise HTTPException(status_code=404, detail="Company profile not found. Please complete your profile first.")

        total_tenders = tenders.count_documents({})
        filtered = filter_tenders(company)
        serialized_filtered = [serialize_tender(t) for t in filtered]

        return {
            "total_tenders": total_tenders,
            "filtered_tenders": len(serialized_filtered),
            "filtered_list": serialized_filtered
        }
    except Exception as e:
        print(f"Summary error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get tender summary: {str(e)}")

@router.post("/tenders/match")
def match_tenders(current_user: dict = Depends(get_current_user)):
    """Run tender matching pipeline"""
    try:
        company = companies.find_one({"user_id": current_user["id"]})
        if not company:
            raise HTTPException(status_code=404, detail="Company profile not found. Please complete your profile first.")

        filtered_tenders_list = filter_tenders(company)

        if not filtered_tenders_list:
            return {
                "message": "No tenders match your company profile",
                "matches": []
            }

        threshold = 60.0
        results = []

        for tender in filtered_tenders_list:
            form_url = tender.get("form_url")
            if not form_url:
                continue

            try:
                raw_eligibility = tender.get("raw_eligibility")
                if not raw_eligibility:
                    raw_eligibility = extract_eligibility_text_from_url(form_url)
                    if raw_eligibility:
                        tenders.update_one(
                            {"_id": tender["_id"]},
                            {"$set": {"raw_eligibility": raw_eligibility, "last_updated": datetime.utcnow()}}
                        )

                structured_eligibility = tender.get("structured_eligibility")
                if not structured_eligibility:
                    structured_eligibility = extract_eligibility_json_general(raw_eligibility)
                    
                    if structured_eligibility:
                        tenders.update_one(
                            {"_id": tender["_id"]},
                            {"$set": {"structured_eligibility": structured_eligibility, "last_updated": datetime.utcnow()}}
                        )

                result = compute_tender_match_score(structured_eligibility, company)

                if result["matching_score"] >= threshold:
                    match_data = {
                        "_id": str(tender["_id"]),
                        "title": tender.get("title"),
                        "reference_number": tender.get("reference_number"),
                        "location": tender.get("location"),
                        "business_category": tender.get("business_category", []),
                        "deadline": tender.get("deadline"),
                        "form_url": form_url,
                        "matching_score": result["matching_score"],
                        "field_scores": result["field_scores"],
                        "eligible": result["eligible"],
                        "missing_fields": result["missing_fields"],
                        "emd": tender.get("emd"),
                        "estimated_budget": tender.get("estimated_budget")
                    }
                    results.append(match_data)

            except Exception as tender_error:
                print(f"Error processing tender {tender.get('title')}: {str(tender_error)}")
                continue

        results.sort(key=lambda x: x["matching_score"], reverse=True)

        return {
            "message": f"Found {len(results)} matching tenders",
            "matches": results
        }

    except Exception as e:
        print(f"Matching error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to match tenders: {str(e)}")

@router.get("/tenders/{tender_id}/summarize")
def summarize_tender(tender_id: str, current_user: dict = Depends(get_current_user)):
    """Generate Gemini AI summary for a specific tender PDF"""
    try:
        tender = tenders.find_one({"_id": ObjectId(tender_id)})
        if not tender:
            raise HTTPException(status_code=404, detail="Tender not found")

        form_url = tender.get("form_url")
        print(f"📄 Summarizing tender {tender_id} from URL: {form_url}")
        

        parsed_url = urlparse(form_url)
        if not parsed_url.path.endswith(".pdf"):
           raise HTTPException(status_code=400, detail="Tender does not contain a valid PDF for summarization.")


        # Download the PDF to a temporary file
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            response = requests.get(form_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to download tender PDF.")
            tmp_file.write(response.content)
            tmp_pdf_path = tmp_file.name

        # Summarize using Gemini
        service = PDFSummaryService(api_key=GEMINI_API_KEY)
        summary_text = service.summarize_pdf(tmp_pdf_path)

        # Clean up
        os.remove(tmp_pdf_path)

        return {
            "tender_id": tender_id,
            "summary": summary_text.strip()
        }

    except Exception as e:
        print(f"Summarization error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to summarize tender: {str(e)}")
