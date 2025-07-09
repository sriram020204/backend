import os
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from services.tender_inserter import TenderInserter
from services.blob_uploader import BlobUploader
from routers.auth import get_current_user
import traceback

router = APIRouter()

# Initialize services
tender_inserter = TenderInserter()
blob_uploader = None

# Initialize blob uploader if Azure is configured
try:
    blob_uploader = BlobUploader()
except Exception as e:
    print(f"Azure Blob Storage not configured: {e}")

@router.post("/upload-tender/")
async def upload_tender(
    tender_data: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a single tender with optional file attachment
    """
    try:
        # Parse tender data
        try:
            tender_dict = json.loads(tender_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in tender_data")
        
        # Handle file upload if provided
        file_url = None
        if file and blob_uploader:
            try:
                # Generate unique filename
                file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
                unique_filename = f"tender_{uuid.uuid4()}{file_extension}"
                
                # Read file content
                file_content = await file.read()
                
                # Upload to blob storage
                file_url = blob_uploader.upload_file(
                    file_content=file_content,
                    blob_name=unique_filename,
                    content_type=file.content_type
                )
                
                # Add file URL to tender data
                tender_dict["document_url"] = file_url
                tender_dict["original_filename"] = file.filename
                
            except Exception as e:
                print(f"File upload error: {str(e)}")
                # Continue without file if upload fails
                pass
        
        # Add uploader information
        tender_dict["uploaded_by"] = current_user["id"]
        tender_dict["uploader_email"] = current_user["email"]
        
        # Insert tender
        result = tender_inserter.insert_tender(tender_dict)
        
        if result["success"]:
            return JSONResponse(
                status_code=201,
                content={
                    "message": "Tender uploaded successfully",
                    "tender_id": result["tender_id"],
                    "reference_number": result.get("reference_number"),
                    "file_url": file_url
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload tender error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload-tenders-batch/")
async def upload_tenders_batch(
    tenders_data: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload multiple tenders with optional file attachments
    """
    try:
        # Parse tenders data
        try:
            tenders_list = json.loads(tenders_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in tenders_data")
        
        if not isinstance(tenders_list, list):
            raise HTTPException(status_code=400, detail="tenders_data must be a list")
        
        # Handle file uploads if provided
        file_urls = {}
        if files and blob_uploader:
            for i, file in enumerate(files):
                try:
                    # Generate unique filename
                    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
                    unique_filename = f"tender_batch_{uuid.uuid4()}{file_extension}"
                    
                    # Read file content
                    file_content = await file.read()
                    
                    # Upload to blob storage
                    file_url = blob_uploader.upload_file(
                        file_content=file_content,
                        blob_name=unique_filename,
                        content_type=file.content_type
                    )
                    
                    file_urls[i] = {
                        "url": file_url,
                        "original_filename": file.filename
                    }
                    
                except Exception as e:
                    print(f"File upload error for file {i}: {str(e)}")
                    continue
        
        # Add file URLs and uploader info to tender data
        for i, tender_dict in enumerate(tenders_list):
            if i in file_urls:
                tender_dict["document_url"] = file_urls[i]["url"]
                tender_dict["original_filename"] = file_urls[i]["original_filename"]
            
            tender_dict["uploaded_by"] = current_user["id"]
            tender_dict["uploader_email"] = current_user["email"]
        
        # Insert tenders
        result = tender_inserter.insert_multiple_tenders(tenders_list)
        
        return JSONResponse(
            status_code=201,
            content={
                "message": "Batch upload completed",
                "total_processed": result["total_processed"],
                "successful_inserts": result["successful_inserts"],
                "failed_inserts": result["failed_inserts"],
                "inserted_ids": result["inserted_ids"],
                "errors": result["errors"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Batch upload error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")

@router.put("/update-tender/{tender_id}")
async def update_tender(
    tender_id: str,
    tender_data: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing tender
    """
    try:
        # Parse tender data
        try:
            update_dict = json.loads(tender_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in tender_data")
        
        # Handle file upload if provided
        if file and blob_uploader:
            try:
                # Generate unique filename
                file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
                unique_filename = f"tender_update_{uuid.uuid4()}{file_extension}"
                
                # Read file content
                file_content = await file.read()
                
                # Upload to blob storage
                file_url = blob_uploader.upload_file(
                    file_content=file_content,
                    blob_name=unique_filename,
                    content_type=file.content_type
                )
                
                # Add file URL to update data
                update_dict["document_url"] = file_url
                update_dict["original_filename"] = file.filename
                
            except Exception as e:
                print(f"File upload error: {str(e)}")
                # Continue without file if upload fails
                pass
        
        # Add updater information
        update_dict["updated_by"] = current_user["id"]
        update_dict["updater_email"] = current_user["email"]
        
        # Update tender
        result = tender_inserter.update_tender(tender_id, update_dict)
        
        if result["success"]:
            return JSONResponse(
                content={
                    "message": "Tender updated successfully",
                    "tender_id": result["tender_id"],
                    "modified_count": result["modified_count"]
                }
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update tender error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.delete("/delete-tender/{tender_id}")
async def delete_tender(
    tender_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a tender
    """
    try:
        result = tender_inserter.delete_tender(tender_id)
        
        if result["success"]:
            return JSONResponse(
                content={
                    "message": "Tender deleted successfully",
                    "tender_id": result["tender_id"]
                }
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete tender error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.get("/tender-stats/")
async def get_tender_stats(current_user: dict = Depends(get_current_user)):
    """
    Get tender database statistics
    """
    try:
        stats = tender_inserter.get_tender_stats()
        return JSONResponse(content=stats)
        
    except Exception as e:
        print(f"Get stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/search-tenders/")
async def search_tenders(
    query: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """
    Search tenders by text query
    """
    try:
        if not query or len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
        
        results = tender_inserter.search_tenders(query.strip(), limit)
        
        return JSONResponse(
            content={
                "query": query,
                "total_results": len(results),
                "results": results
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/upload-file/")
async def upload_file_only(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a file to blob storage (without tender data)
    """
    try:
        if not blob_uploader:
            raise HTTPException(status_code=503, detail="File upload service not available")
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"upload_{uuid.uuid4()}{file_extension}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload to blob storage
        file_url = blob_uploader.upload_file(
            file_content=file_content,
            blob_name=unique_filename,
            content_type=file.content_type
        )
        
        return JSONResponse(
            status_code=201,
            content={
                "message": "File uploaded successfully",
                "file_url": file_url,
                "original_filename": file.filename,
                "blob_name": unique_filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.get("/list-files/")
async def list_uploaded_files(
    prefix: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List uploaded files in blob storage
    """
    try:
        if not blob_uploader:
            raise HTTPException(status_code=503, detail="File storage service not available")
        
        files = blob_uploader.list_blobs(prefix)
        
        return JSONResponse(
            content={
                "total_files": len(files),
                "files": files,
                "prefix": prefix
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.delete("/delete-file/{blob_name}")
async def delete_file(
    blob_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a file from blob storage
    """
    try:
        if not blob_uploader:
            raise HTTPException(status_code=503, detail="File storage service not available")
        
        success = blob_uploader.delete_blob(blob_name)
        
        if success:
            return JSONResponse(
                content={
                    "message": "File deleted successfully",
                    "blob_name": blob_name
                }
            )
        else:
            raise HTTPException(status_code=404, detail="File not found or could not be deleted")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete file error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File deletion failed: {str(e)}")