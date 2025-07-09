#!/usr/bin/env python3
"""
Tender Matching Pipeline
Runs the AI-powered tender matching process for all users
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.database import db
from services.basic_filter import filter_tenders
from services.tender_matcher import compute_tender_match_score
from services.eligibility_extractor import extract_eligibility_text_from_url
from services.eligibility_parser import extract_eligibility_json_general
import traceback

def run_matching_for_user(user_id: str, threshold: float = 60.0) -> dict:
    """
    Run tender matching for a specific user
    
    Args:
        user_id: User ID to run matching for
        threshold: Minimum matching score threshold
        
    Returns:
        dict: Matching results
    """
    try:
        companies = db["companies"]
        tenders = db["filtered_tenders"]
        
        # Get user's company profile
        company = companies.find_one({"user_id": user_id})
        if not company:
            return {
                "success": False,
                "error": f"No company profile found for user {user_id}",
                "user_id": user_id
            }
        
        print(f"🏢 Processing user: {user_id} - {company.get('companyDetails', {}).get('companyName', 'Unknown')}")
        
        # Filter tenders based on company profile
        filtered_tenders = filter_tenders(company)
        print(f"📋 Found {len(filtered_tenders)} filtered tenders")
        
        if not filtered_tenders:
            return {
                "success": True,
                "user_id": user_id,
                "company_name": company.get('companyDetails', {}).get('companyName', 'Unknown'),
                "total_filtered": 0,
                "matches": [],
                "message": "No tenders match company profile"
            }
        
        matches = []
        processed = 0
        
        for tender in filtered_tenders:
            try:
                processed += 1
                print(f"  Processing tender {processed}/{len(filtered_tenders)}: {tender.get('title', 'Unknown')}")
                
                form_url = tender.get("form_url")
                if not form_url:
                    continue
                
                # Extract eligibility if not already done
                raw_eligibility = tender.get("raw_eligibility")
                if not raw_eligibility:
                    print(f"    Extracting eligibility from {form_url}")
                    raw_eligibility = extract_eligibility_text_from_url(form_url)
                    if raw_eligibility:
                        tenders.update_one(
                            {"_id": tender["_id"]},
                            {"$set": {"raw_eligibility": raw_eligibility, "last_updated": datetime.utcnow()}}
                        )
                
                # Parse structured eligibility if not already done
                structured_eligibility = tender.get("structured_eligibility")
                if not structured_eligibility and raw_eligibility:
                    print(f"    Parsing structured eligibility")
                    structured_eligibility = extract_eligibility_json_general(raw_eligibility)
                    if structured_eligibility:
                        tenders.update_one(
                            {"_id": tender["_id"]},
                            {"$set": {"structured_eligibility": structured_eligibility, "last_updated": datetime.utcnow()}}
                        )
                
                # Compute matching score
                if structured_eligibility:
                    result = compute_tender_match_score(structured_eligibility, company)
                    
                    if result["matching_score"] >= threshold:
                        match_data = {
                            "tender_id": str(tender["_id"]),
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
                        matches.append(match_data)
                        print(f"    ✅ Match found: {result['matching_score']:.1f}% score")
                    else:
                        print(f"    ❌ Below threshold: {result['matching_score']:.1f}% score")
                
            except Exception as tender_error:
                print(f"    ⚠️ Error processing tender: {str(tender_error)}")
                continue
        
        # Sort matches by score
        matches.sort(key=lambda x: x["matching_score"], reverse=True)
        
        return {
            "success": True,
            "user_id": user_id,
            "company_name": company.get('companyDetails', {}).get('companyName', 'Unknown'),
            "total_filtered": len(filtered_tenders),
            "total_matches": len(matches),
            "matches": matches,
            "threshold": threshold
        }
        
    except Exception as e:
        print(f"❌ Error processing user {user_id}: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }

def run_matching_for_all_users(threshold: float = 60.0) -> dict:
    """
    Run tender matching for all users with complete profiles
    
    Args:
        threshold: Minimum matching score threshold
        
    Returns:
        dict: Overall results
    """
    try:
        companies = db["companies"]
        
        # Get all companies with complete profiles
        all_companies = list(companies.find({}))
        print(f"🏢 Found {len(all_companies)} companies in database")
        
        results = {
            "total_companies": len(all_companies),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "user_results": [],
            "errors": []
        }
        
        for company in all_companies:
            user_id = company.get("user_id")
            if not user_id:
                continue
            
            print(f"\n{'='*60}")
            result = run_matching_for_user(user_id, threshold)
            
            results["processed"] += 1
            
            if result["success"]:
                results["successful"] += 1
                print(f"✅ Success: {result['total_matches']} matches found")
            else:
                results["failed"] += 1
                results["errors"].append(result)
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
            results["user_results"].append(result)
        
        return results
        
    except Exception as e:
        print(f"❌ Error in batch processing: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

def get_matching_statistics():
    """Display matching statistics"""
    try:
        companies = db["companies"]
        tenders = db["filtered_tenders"]
        
        total_companies = companies.count_documents({})
        total_tenders = tenders.count_documents({})
        
        # Count tenders with processed eligibility
        tenders_with_raw = tenders.count_documents({"raw_eligibility": {"$exists": True, "$ne": ""}})
        tenders_with_structured = tenders.count_documents({"structured_eligibility": {"$exists": True, "$ne": {}}})
        
        print("\n📊 Matching Pipeline Statistics:")
        print(f"  Total Companies: {total_companies}")
        print(f"  Total Tenders: {total_tenders}")
        print(f"  Tenders with Raw Eligibility: {tenders_with_raw}")
        print(f"  Tenders with Structured Eligibility: {tenders_with_structured}")
        print(f"  Processing Coverage: {(tenders_with_structured/total_tenders*100):.1f}%" if total_tenders > 0 else "  Processing Coverage: 0%")
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("🎯 Tender Matching Pipeline")
        print("\nUsage:")
        print("  python run_tender_matching.py <command> [args]")
        print("\nCommands:")
        print("  user <user_id> [threshold]  - Run matching for specific user")
        print("  all [threshold]             - Run matching for all users")
        print("  stats                       - Show matching statistics")
        print("\nExamples:")
        print("  python run_tender_matching.py user 12345 70.0")
        print("  python run_tender_matching.py all 60.0")
        print("  python run_tender_matching.py stats")
        return
    
    command = sys.argv[1].lower()
    
    if command == "user":
        if len(sys.argv) < 3:
            print("❌ Please provide user ID")
            print("Usage: python run_tender_matching.py user <user_id> [threshold]")
            return
        
        user_id = sys.argv[2]
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
        
        print(f"🎯 Running matching for user: {user_id} (threshold: {threshold}%)")
        result = run_matching_for_user(user_id, threshold)
        
        if result["success"]:
            print(f"\n✅ Matching completed successfully!")
            print(f"   Company: {result['company_name']}")
            print(f"   Filtered Tenders: {result['total_filtered']}")
            print(f"   Matches Found: {result['total_matches']}")
            
            if result["matches"]:
                print(f"\n🎯 Top Matches:")
                for i, match in enumerate(result["matches"][:5], 1):
                    print(f"   {i}. {match['title']} ({match['matching_score']:.1f}%)")
        else:
            print(f"\n❌ Matching failed: {result['error']}")
            sys.exit(1)
        
    elif command == "all":
        threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
        
        print(f"🎯 Running matching for all users (threshold: {threshold}%)")
        results = run_matching_for_all_users(threshold)
        
        print(f"\n📊 Batch Processing Results:")
        print(f"   Total Companies: {results['total_companies']}")
        print(f"   Processed: {results['processed']}")
        print(f"   Successful: {results['successful']}")
        print(f"   Failed: {results['failed']}")
        
        if results["errors"]:
            print(f"\n❌ Errors:")
            for error in results["errors"]:
                print(f"   - {error['user_id']}: {error['error']}")
        
        # Show summary of matches
        total_matches = sum(r.get('total_matches', 0) for r in results['user_results'] if r.get('success'))
        print(f"\n🎯 Total Matches Found: {total_matches}")
        
    elif command == "stats":
        get_matching_statistics()
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: user, all, stats")
        sys.exit(1)

if __name__ == "__main__":
    main()