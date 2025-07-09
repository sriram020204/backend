#!/usr/bin/env python3
"""
Manual Tender Upload Pipeline
Allows manual upload of tender data to the database
"""

import json
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.tender_inserter import TenderInserter
from services.blob_uploader import BlobUploader
import traceback

def upload_tender_from_json(json_file_path: str) -> bool:
    """
    Upload tender data from a JSON file
    
    Args:
        json_file_path: Path to the JSON file containing tender data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize services
        tender_inserter = TenderInserter()
        
        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Handle both single tender and multiple tenders
        if isinstance(data, list):
            print(f"📦 Processing {len(data)} tenders from {json_file_path}")
            result = tender_inserter.insert_multiple_tenders(data)
            
            print(f"✅ Successfully inserted: {result['successful_inserts']}")
            print(f"❌ Failed inserts: {result['failed_inserts']}")
            
            if result['errors']:
                print("\n🚨 Errors:")
                for error in result['errors']:
                    print(f"  - {error['tender_id']}: {error['error']}")
            
            return result['failed_inserts'] == 0
            
        else:
            print(f"📄 Processing single tender from {json_file_path}")
            result = tender_inserter.insert_tender(data)
            
            if result['success']:
                print(f"✅ Successfully inserted tender: {result['tender_id']}")
                return True
            else:
                print(f"❌ Failed to insert tender: {result['error']}")
                return False
                
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in file {json_file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error processing {json_file_path}: {e}")
        print(traceback.format_exc())
        return False

def upload_sample_tenders():
    """Upload sample tender data for testing"""
    sample_tenders = [
        {
            "form_url": "https://example.com/tender1.pdf",
            "title": "Supply of Office Equipment",
            "reference_number": "TENDER001",
            "institute": "Government Office",
            "location": "New Delhi",
            "business_category": ["Office Supplies", "Equipment"],
            "scope_of_work": "Supply of computers, printers, and office furniture",
            "estimated_budget": 500000,
            "deadline": "2024-03-15",
            "emd": {"amount": 10000, "exemption": []},
            "tender_fee": {"amount": 500, "exemption": []},
            "documents_required": ["PAN Card", "GST Certificate", "Experience Certificate"],
            "experience": {"years": 2, "sector": "Office Equipment"},
            "certifications": ["ISO 9001"],
            "eligibility_notes": "Minimum 2 years experience required"
        },
        {
            "form_url": "https://example.com/tender2.pdf",
            "title": "Construction of School Building",
            "reference_number": "TENDER002",
            "institute": "Education Department",
            "location": "Mumbai",
            "business_category": ["Construction", "Infrastructure"],
            "scope_of_work": "Construction of 3-story school building with modern facilities",
            "estimated_budget": 5000000,
            "deadline": "2024-04-20",
            "emd": {"amount": 100000, "exemption": ["MSME"]},
            "tender_fee": {"amount": 2000, "exemption": []},
            "documents_required": ["Contractor License", "PAN Card", "GST Certificate"],
            "experience": {"years": 5, "sector": "Construction"},
            "certifications": ["PWD Registration"],
            "eligibility_notes": "Minimum 5 years construction experience required"
        },
        {
            "form_url": "https://example.com/tender3.pdf",
            "title": "IT Services and Maintenance",
            "reference_number": "TENDER003",
            "institute": "IT Department",
            "location": "Bangalore",
            "business_category": ["IT Services", "Technology"],
            "scope_of_work": "Annual maintenance contract for IT infrastructure",
            "estimated_budget": 1200000,
            "deadline": "2024-03-30",
            "emd": {"amount": 24000, "exemption": ["Startups"]},
            "tender_fee": {"amount": 1000, "exemption": []},
            "documents_required": ["Company Registration", "IT Certification", "Experience Certificate"],
            "experience": {"years": 3, "sector": "IT Services"},
            "certifications": ["ISO 27001", "CMMI Level 3"],
            "eligibility_notes": "Minimum 3 years IT services experience required"
        }
    ]
    
    try:
        tender_inserter = TenderInserter()
        print("📦 Uploading sample tenders...")
        
        result = tender_inserter.insert_multiple_tenders(sample_tenders)
        
        print(f"✅ Successfully inserted: {result['successful_inserts']}")
        print(f"❌ Failed inserts: {result['failed_inserts']}")
        
        if result['errors']:
            print("\n🚨 Errors:")
            for error in result['errors']:
                print(f"  - {error['tender_id']}: {error['error']}")
        
        return result['failed_inserts'] == 0
        
    except Exception as e:
        print(f"❌ Error uploading sample tenders: {e}")
        print(traceback.format_exc())
        return False

def get_tender_statistics():
    """Display current tender database statistics"""
    try:
        tender_inserter = TenderInserter()
        stats = tender_inserter.get_tender_stats()
        
        print("\n📊 Tender Database Statistics:")
        print(f"  Total Tenders: {stats['total_tenders']}")
        print(f"  Active Tenders: {stats['active_tenders']}")
        print(f"  Recent Tenders (30 days): {stats['recent_tenders']}")
        print(f"  Last Updated: {stats['last_updated']}")
        
        if 'error' in stats:
            print(f"  ⚠️ Error: {stats['error']}")
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("📋 Tender Upload Pipeline")
        print("\nUsage:")
        print("  python manual_tender_upload.py <command> [args]")
        print("\nCommands:")
        print("  upload <json_file>  - Upload tenders from JSON file")
        print("  sample             - Upload sample tenders for testing")
        print("  stats              - Show database statistics")
        print("\nExamples:")
        print("  python manual_tender_upload.py upload tenders.json")
        print("  python manual_tender_upload.py sample")
        print("  python manual_tender_upload.py stats")
        return
    
    command = sys.argv[1].lower()
    
    if command == "upload":
        if len(sys.argv) < 3:
            print("❌ Please provide JSON file path")
            print("Usage: python manual_tender_upload.py upload <json_file>")
            return
        
        json_file = sys.argv[2]
        success = upload_tender_from_json(json_file)
        sys.exit(0 if success else 1)
        
    elif command == "sample":
        success = upload_sample_tenders()
        get_tender_statistics()
        sys.exit(0 if success else 1)
        
    elif command == "stats":
        get_tender_statistics()
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: upload, sample, stats")
        sys.exit(1)

if __name__ == "__main__":
    main()