import json
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from core.database import db
from services.blob_uploader import BlobUploader
import os

class TenderInserter:
    def __init__(self):
        self.tenders_collection = db.get_collection("filtered_tenders")
        self.blob_uploader = BlobUploader() if self._azure_configured() else None
        
    def _azure_configured(self) -> bool:
        """Check if Azure Blob Storage is configured"""
        return bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))

    def insert_tender(self, tender_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a single tender into the database
        
        Args:
            tender_data: Dictionary containing tender information
            
        Returns:
            Dict with insertion result
        """
        try:
            # Validate required fields
            if not self._validate_tender_data(tender_data):
                return {
                    "success": False,
                    "error": "Invalid tender data - missing required fields",
                    "tender_id": tender_data.get("reference_number", "unknown")
                }
            
            # Normalize and clean data
            normalized_data = self._normalize_tender_data(tender_data)
            
            # Add metadata
            normalized_data.update({
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
                "source": "manual_upload",
                "status": "active"
            })
            
            # Insert into database
            result = self.tenders_collection.insert_one(normalized_data)
            
            return {
                "success": True,
                "tender_id": str(result.inserted_id),
                "reference_number": normalized_data.get("reference_number"),
                "message": "Tender inserted successfully"
            }
            
        except DuplicateKeyError:
            return {
                "success": False,
                "error": "Tender with this form_url already exists",
                "tender_id": tender_data.get("reference_number", "unknown")
            }
        except Exception as e:
            print(f"Error inserting tender: {str(e)}")
            print(traceback.format_exc())
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
                "tender_id": tender_data.get("reference_number", "unknown")
            }

    def insert_multiple_tenders(self, tenders_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert multiple tenders into the database
        
        Args:
            tenders_data: List of tender dictionaries
            
        Returns:
            Dict with batch insertion results
        """
        results = {
            "total_processed": len(tenders_data),
            "successful_inserts": 0,
            "failed_inserts": 0,
            "errors": [],
            "inserted_ids": []
        }
        
        for tender_data in tenders_data:
            result = self.insert_tender(tender_data)
            
            if result["success"]:
                results["successful_inserts"] += 1
                results["inserted_ids"].append(result["tender_id"])
            else:
                results["failed_inserts"] += 1
                results["errors"].append({
                    "tender_id": result["tender_id"],
                    "error": result["error"]
                })
        
        return results

    def update_tender(self, tender_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing tender
        
        Args:
            tender_id: ID of the tender to update
            update_data: Data to update
            
        Returns:
            Dict with update result
        """
        try:
            from bson import ObjectId
            
            # Add update timestamp
            update_data["last_updated"] = datetime.utcnow()
            
            result = self.tenders_collection.update_one(
                {"_id": ObjectId(tender_id)},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                return {
                    "success": False,
                    "error": "Tender not found",
                    "tender_id": tender_id
                }
            
            return {
                "success": True,
                "tender_id": tender_id,
                "modified_count": result.modified_count,
                "message": "Tender updated successfully"
            }
            
        except Exception as e:
            print(f"Error updating tender {tender_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Update error: {str(e)}",
                "tender_id": tender_id
            }

    def delete_tender(self, tender_id: str) -> Dict[str, Any]:
        """
        Delete a tender from the database
        
        Args:
            tender_id: ID of the tender to delete
            
        Returns:
            Dict with deletion result
        """
        try:
            from bson import ObjectId
            
            result = self.tenders_collection.delete_one({"_id": ObjectId(tender_id)})
            
            if result.deleted_count == 0:
                return {
                    "success": False,
                    "error": "Tender not found",
                    "tender_id": tender_id
                }
            
            return {
                "success": True,
                "tender_id": tender_id,
                "message": "Tender deleted successfully"
            }
            
        except Exception as e:
            print(f"Error deleting tender {tender_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Deletion error: {str(e)}",
                "tender_id": tender_id
            }

    def _validate_tender_data(self, tender_data: Dict[str, Any]) -> bool:
        """
        Validate that tender data contains required fields
        
        Args:
            tender_data: Tender data to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ["form_url", "title"]
        
        for field in required_fields:
            if field not in tender_data or not tender_data[field]:
                print(f"Missing required field: {field}")
                return False
        
        return True

    def _normalize_tender_data(self, tender_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and clean tender data
        
        Args:
            tender_data: Raw tender data
            
        Returns:
            Dict: Normalized tender data
        """
        normalized = tender_data.copy()
        
        # Ensure business_category is a list
        if "business_category" in normalized:
            if isinstance(normalized["business_category"], str):
                normalized["business_category"] = [cat.strip() for cat in normalized["business_category"].split(",")]
            elif not isinstance(normalized["business_category"], list):
                normalized["business_category"] = []
        else:
            normalized["business_category"] = []
        
        # Ensure documents_required is a list
        if "documents_required" in normalized:
            if isinstance(normalized["documents_required"], str):
                normalized["documents_required"] = [doc.strip() for doc in normalized["documents_required"].split(",")]
            elif not isinstance(normalized["documents_required"], list):
                normalized["documents_required"] = []
        else:
            normalized["documents_required"] = []
        
        # Ensure certifications is a list
        if "certifications" in normalized:
            if isinstance(normalized["certifications"], str):
                normalized["certifications"] = [cert.strip() for cert in normalized["certifications"].split(",")]
            elif not isinstance(normalized["certifications"], list):
                normalized["certifications"] = []
        else:
            normalized["certifications"] = []
        
        # Normalize EMD structure
        if "emd" in normalized and isinstance(normalized["emd"], (str, int, float)):
            normalized["emd"] = {
                "amount": float(normalized["emd"]) if normalized["emd"] else 0,
                "exemption": []
            }
        elif "emd" not in normalized:
            normalized["emd"] = {"amount": 0, "exemption": []}
        
        # Normalize tender fee structure
        if "tender_fee" in normalized and isinstance(normalized["tender_fee"], (str, int, float)):
            normalized["tender_fee"] = {
                "amount": float(normalized["tender_fee"]) if normalized["tender_fee"] else 0,
                "exemption": []
            }
        elif "tender_fee" not in normalized:
            normalized["tender_fee"] = {"amount": 0, "exemption": []}
        
        # Normalize experience structure
        if "experience" in normalized and isinstance(normalized["experience"], (str, int)):
            normalized["experience"] = {
                "years": int(normalized["experience"]) if normalized["experience"] else 0,
                "sector": ""
            }
        elif "experience" not in normalized:
            normalized["experience"] = {"years": 0, "sector": ""}
        
        # Convert estimated_budget to float
        if "estimated_budget" in normalized:
            try:
                normalized["estimated_budget"] = float(normalized["estimated_budget"]) if normalized["estimated_budget"] else 0
            except (ValueError, TypeError):
                normalized["estimated_budget"] = 0
        else:
            normalized["estimated_budget"] = 0
        
        # Ensure string fields are strings
        string_fields = ["title", "reference_number", "institute", "location", "scope_of_work", "deadline", "eligibility_notes"]
        for field in string_fields:
            if field in normalized and normalized[field] is not None:
                normalized[field] = str(normalized[field])
            elif field not in normalized:
                normalized[field] = ""
        
        return normalized

    def get_tender_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tenders in the database
        
        Returns:
            Dict with tender statistics
        """
        try:
            total_tenders = self.tenders_collection.count_documents({})
            
            # Get tenders by status
            active_tenders = self.tenders_collection.count_documents({"status": "active"})
            
            # Get recent tenders (last 30 days)
            from datetime import timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_tenders = self.tenders_collection.count_documents({
                "created_at": {"$gte": thirty_days_ago}
            })
            
            return {
                "total_tenders": total_tenders,
                "active_tenders": active_tenders,
                "recent_tenders": recent_tenders,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Error getting tender stats: {str(e)}")
            return {
                "total_tenders": 0,
                "active_tenders": 0,
                "recent_tenders": 0,
                "error": str(e)
            }

    def search_tenders(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search tenders by text query
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching tenders
        """
        try:
            # Create text search query
            search_filter = {
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"reference_number": {"$regex": query, "$options": "i"}},
                    {"institute": {"$regex": query, "$options": "i"}},
                    {"scope_of_work": {"$regex": query, "$options": "i"}},
                    {"business_category": {"$regex": query, "$options": "i"}}
                ]
            }
            
            results = list(self.tenders_collection.find(search_filter).limit(limit))
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                result["_id"] = str(result["_id"])
            
            return results
            
        except Exception as e:
            print(f"Error searching tenders: {str(e)}")
            return []

# Convenience function for easy import
def get_tender_inserter():
    """Get a configured TenderInserter instance"""
    return TenderInserter()