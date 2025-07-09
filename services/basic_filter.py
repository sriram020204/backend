from pymongo import MongoClient
from sentence_transformers import SentenceTransformer, util
from datetime import datetime
from core.database import db  # assumes your db is initialized here

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Collection
filtered_tenders = db.get_collection("filtered_tenders")


def get_company_categories(company_profile: dict):
    """
    Dynamically extract company categories from capabilities and experience.
    """
    capability_keywords = []

    # Use correct key name
    caps = company_profile.get("businessCapabilities", {})
    for key in ["businessRoles", "industrySectors", "productServiceKeywords", "technicalCapabilities"]:
        val = caps.get(key)
        if val:
            capability_keywords.extend(val.split(","))
        else:
            print(f"⚠️ {key} is missing or empty.")

    # Use correct key name for tender experience
    tenders = company_profile.get("tenderExperience", {})
    if tenders.get("tenderTypesHandled"):
        capability_keywords.extend(tenders["tenderTypesHandled"].split(","))
    else:
        print("⚠️ No tenderTypesHandled provided.")

    # Normalize and deduplicate
    clean_categories = list({kw.strip().lower() for kw in capability_keywords if kw.strip()})
    
    if not clean_categories:
        print("🚫 No valid company categories found. Aborting filtering.")
    else:
        print("📌 Company Category Keywords:", clean_categories)
    
    return clean_categories


def is_category_similar(list1, list2, threshold=0.6):
    """
    Semantic similarity between categories using SentenceTransformer.
    """
    for a in list1:
        for b in list2:
            a_enc = model.encode(a, convert_to_tensor=True)
            b_enc = model.encode(b, convert_to_tensor=True)
            score = util.cos_sim(a_enc, b_enc).item()
            if score >= threshold:
                return True
    return False


def filter_tenders(company_profile: dict):
    """
    Main function to filter tenders based on company profile match.
    """
    company_categories = get_company_categories(company_profile)
    if not company_categories:
        print("🚫 No valid company categories found. Aborting filtering.\n")
        return []

    # Fetch tenders
    tenders = list(filtered_tenders.find())
    print(f"\n📦 Total Tenders Fetched from DB: {len(tenders)}\n")

    results = []
    for tender in tenders:
        title = tender.get("title", "Untitled Tender")
        print("➡️ Tender Title:", title)

        tender_categories = [cat.strip().lower() for cat in tender.get("business_category", []) if cat.strip()]
        print("   Tender Categories:", tender_categories)

        if is_category_similar(company_categories, tender_categories):
            print("   ✅ Category matched!\n")
            results.append(tender)
        else:
            print("   ❌ No match.\n")

    print(f"🧮 Tenders after filtering: {len(results)}\n")
    return results
