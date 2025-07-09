import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from services.template_parser import extract_schema_from_docx
from services.doc_generator import generate_docx_from_template
from services.field_mapper import map_fields_by_embedding
from routers.auth import get_current_user

router = APIRouter()

TEMPLATE_DIR = "backend/storage/templates"
OUTPUT_DIR = "backend/storage/output"

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@router.post("/upload-template/")
async def upload_template(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload and parse a document template"""
    file_ext = file.filename.split(".")[-1] if file.filename else ""
    if file_ext.lower() != "docx":
        raise HTTPException(status_code=400, detail="Only .docx files are allowed")

    template_id = str(uuid.uuid4())
    saved_path = os.path.join(TEMPLATE_DIR, f"{template_id}.docx")

    try:
        with open(saved_path, "wb") as f:
            content = await file.read()
            f.write(content)

        schema = extract_schema_from_docx(saved_path)
        if not schema:
            raise HTTPException(status_code=500, detail="Failed to parse schema from template")

        return {"templateId": template_id, "schema": schema}
    except Exception as e:
        # Clean up file if processing failed
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(status_code=500, detail=f"Template processing failed: {str(e)}")


@router.post("/auto-map-fields/")
async def auto_map_fields(
    templateId: str = Form(...),
    tenderId: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Automatically map template fields to tender data using AI"""
    try:
        from core.database import db
        
        # Get template schema
        template_path = os.path.join(TEMPLATE_DIR, f"{templateId}.docx")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Template not found")

        schema = extract_schema_from_docx(template_path)
        if not schema:
            raise HTTPException(status_code=500, detail="Failed to extract template schema")

        # Get tender data
        tender_data = db.tenders.find_one({"reference_number": tenderId})
        if not tender_data:
            # Return mock data for demo purposes
            tender_data = {
                'Tender ID': tenderId,
                'Company Name': 'Demo Company Ltd.',
                'Tender Title': 'Supply of Essential Services',
                'EMD Amount': '₹25,000',
                'Tender Date': '2024-01-15',
                'Submission Deadline': '2024-02-15',
                'Contact Person': 'John Doe',
                'Phone': '+91-9876543210',
                'Email': 'john.doe@democompany.com',
                'Address': '123 Business District, Mumbai, Maharashtra 400001',
                'Bank Name': 'State Bank of India',
                'Account Number': '1234567890',
                'IFSC Code': 'SBIN0001234',
                'Registration Number': 'REG/2024/001',
                'GST Number': '27ABCDE1234F1Z5',
                'PAN Number': 'ABCDE1234F',
                'Project Description': 'Supply and installation of essential IT services',
                'Contract Duration': '12 months',
                'Technical Specifications': 'As per tender document requirements',
                'Delivery Timeline': '30 days from award',
                'Warranty Period': '2 years comprehensive warranty',
                'Payment Terms': '30 days from delivery',
                'Bid Security': '₹25,000 or 2% of bid value',
                'Performance Guarantee': '10% of contract value',
                'Liquidated Damages': '0.5% per week of delay',
                'Completion Date': '2024-08-15',
                'Site Location': 'Mumbai, Maharashtra',
                'Tender Category': 'IT Services',
                'Minimum Turnover': '₹50,00,000',
                'Experience Required': '3 years in similar projects',
                'Certification Required': 'ISO 9001:2015',
                'Tender Opening Date': '2024-02-20',
                'Technical Bid Opening': '2024-02-20 11:00 AM',
                'Financial Bid Opening': '2024-02-25 11:00 AM',
                'Tender Validity': '90 days from opening',
                'Document Fee': '₹500',
                'Tender Issuing Authority': 'Municipal Corporation',
                'Tender Type': 'Open Tender',
                'Procurement Method': 'Two Bid System',
                'Currency': 'INR',
                'Tax Applicability': 'GST as applicable',
                'Evaluation Criteria': 'L1 (Lowest Price)',
                'Bid Submission Mode': 'Online through portal',
                'Clarification Deadline': '2024-02-10',
                'Amendment Notification': 'Will be published on portal',
                'Contact Email': 'procurement@municipal.gov.in',
                'Helpdesk Number': '+91-22-12345678',
                'Portal URL': 'https://etenders.municipal.gov.in',
                'Tender Document Size': '2.5 MB',
                'Language': 'English/Hindi',
                'Time Zone': 'IST (UTC +5:30)'
            }
        
        # Remove MongoDB's _id field if present
        if '_id' in tender_data:
            del tender_data['_id']
        
        # Get template fields
        template_fields = schema.get('fields', [])
        backend_fields = list(tender_data.keys())
        
        # Use field mapper to automatically map fields
        mapped_data = map_fields_by_embedding(
            gemini_fields=template_fields,
            backend_fields=backend_fields,
            backend_data=tender_data,
            threshold=0.5  # Adjust threshold as needed
        )
        
        # Categorize fields by mapping confidence
        auto_mapped = {}
        needs_review = {}
        unmapped = {}
        
        for field in template_fields:
            field_id = field['id']
            field_label = field.get('label', field_id)
            mapped_value = mapped_data.get(field_id, '')
            
            if mapped_value and mapped_value.strip():
                # Field was successfully mapped
                auto_mapped[field_id] = {
                    'label': field_label,
                    'value': mapped_value,
                    'type': field.get('type', 'string'),
                    'confidence': 'high'  # You could implement actual confidence scoring
                }
            else:
                # Field needs manual input
                unmapped[field_id] = {
                    'label': field_label,
                    'value': '',
                    'type': field.get('type', 'string'),
                    'required': field.get('required', False)
                }
        
        return {
            "templateId": templateId,
            "tenderId": tenderId,
            "autoMapped": auto_mapped,
            "needsReview": needs_review,
            "unmapped": unmapped,
            "mappingStats": {
                "totalFields": len(template_fields),
                "autoMapped": len(auto_mapped),
                "needsReview": len(needs_review),
                "unmapped": len(unmapped),
                "mappingRate": round((len(auto_mapped) / len(template_fields)) * 100, 1) if template_fields else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-mapping failed: {str(e)}")


@router.post("/generate-document/")
async def generate_document(
    templateId: str = Form(...),
    mappedData: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Generate a document from template and mapped data"""
    try:
        # Parse the mapped data
        import json
        mapped_data = json.loads(mappedData)
        
        template_path = os.path.join(TEMPLATE_DIR, f"{templateId}.docx")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Template not found")

        # Extract schema to get template string
        schema = extract_schema_from_docx(template_path)
        if not schema:
            raise HTTPException(status_code=500, detail="Failed to extract template schema")

        template_string = schema["templateString"]
        output_path = os.path.join(OUTPUT_DIR, f"{templateId}_final.docx")
        
        # Generate the document
        generate_docx_from_template(template_string, mapped_data, output_path)

        return FileResponse(
            output_path, 
            filename="Generated_Document.docx", 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in mappedData")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")


@router.get("/tender/{tender_id}")
async def get_tender_data(tender_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch tender data by Tender ID from MongoDB"""
    from core.database import db
    
    try:
        # Search in the tenders collection
        tender_data = db.tenders.find_one({"reference_number": tender_id})
        
        if not tender_data:
            # If not found, return mock data for demo purposes
            mock_data = {
                'Tender ID': tender_id,
                'Company Name': 'Demo Company Ltd.',
                'Tender Title': 'Supply of Essential Services',
                'EMD Amount': '₹25,000',
                'Tender Date': '2024-01-15',
                'Submission Deadline': '2024-02-15',
                'Contact Person': 'John Doe',
                'Phone': '+91-9876543210',
                'Email': 'john.doe@democompany.com',
                'Address': '123 Business District, Mumbai, Maharashtra 400001',
                'Bank Name': 'State Bank of India',
                'Account Number': '1234567890',
                'IFSC Code': 'SBIN0001234',
                'Registration Number': 'REG/2024/001',
                'GST Number': '27ABCDE1234F1Z5',
                'PAN Number': 'ABCDE1234F',
            }
            return mock_data
        
        # Remove MongoDB's _id field from response
        if '_id' in tender_data:
            del tender_data['_id']
        
        return tender_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tender data: {str(e)}")


@router.get("/tenders/")
async def list_tenders(limit: int = 10, skip: int = 0, current_user: dict = Depends(get_current_user)):
    """List all tenders with pagination"""
    from core.database import db
    
    try:
        # Get total count
        total = db.tenders.count_documents({})
        
        # Get paginated results
        tenders = list(db.tenders.find({}, {"_id": 0}).skip(skip).limit(limit))
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "tenders": tenders
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tenders: {str(e)}")


@router.get("/tender/{tender_id}/fields")
async def get_tender_fields(tender_id: str, current_user: dict = Depends(get_current_user)):
    """Get available fields for a specific tender"""
    from core.database import db
    
    try:
        tender_data = db.tenders.find_one({"reference_number": tender_id})
        
        if not tender_data:
            raise HTTPException(status_code=404, detail=f"Tender with ID '{tender_id}' not found")
        
        # Remove MongoDB's _id field
        if '_id' in tender_data:
            del tender_data['_id']
        
        # Return field names and sample values
        fields = {}
        for key, value in tender_data.items():
            fields[key] = {
                "type": type(value).__name__,
                "sample_value": str(value)[:100] if value else None  # Truncate long values
            }
        
        return {
            "tender_id": tender_id,
            "total_fields": len(fields),
            "fields": fields
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tender fields: {str(e)}")