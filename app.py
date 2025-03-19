# app.py - Main FastAPI application
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import shutil
from tempfile import NamedTemporaryFile
import asyncio
import logging
from datetime import datetime, timedelta
import secrets
import hashlib
import base64
from cryptography.fernet import Fernet
import json

from document_processor import DocumentProcessor
from fee_detector import FeeDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fee Detective API",
    description="API for detecting hidden fees in bills and statements",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Generate an encryption key for temporary data
# We'll store this in memory only and regenerate on restart
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# In-memory storage for temporary processing results
# We'll use this instead of a database to avoid storing sensitive data
# Results will be purged regularly
temp_results = {}

# Request and response models
class AnalysisRequest(BaseModel):
    bill_type: str
    provider: Optional[str] = None

class FileUploadResponse(BaseModel):
    upload_id: str
    expires_at: str

class DetectedFee(BaseModel):
    description: str
    amount: float
    is_questionable: bool
    reason: Optional[str] = None

class AnalysisResult(BaseModel):
    detected_fees: List[DetectedFee]
    potential_savings: float
    summary: dict
    provider: Optional[str] = None
    bill_type: str

# Background task to clean up expired results
async def cleanup_expired_results():
    while True:
        current_time = datetime.now()
        expired_keys = []
        
        for key, value in temp_results.items():
            if value['expires_at'] < current_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del temp_results[key]
            logger.info(f"Cleaned up expired result: {key}")
        
        # Run cleanup every 15 minutes
        await asyncio.sleep(900)

@app.on_event("startup")
async def startup_event():
    # Start background task for cleanup
    asyncio.create_task(cleanup_expired_results())

# Utility function to encrypt data
def encrypt_data(data):
    """Encrypt data using the app's encryption key"""
    json_data = json.dumps(data)
    encrypted = cipher_suite.encrypt(json_data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

# Utility function to decrypt data
def decrypt_data(encrypted_data):
    """Decrypt data using the app's encryption key"""
    try:
        decoded = base64.urlsafe_b64decode(encrypted_data)
        decrypted = cipher_suite.decrypt(decoded)
        return json.loads(decrypted)
    except Exception as e:
        logger.error(f"Error decrypting data: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid or expired data")

# Endpoints
@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    bill_type: str = Form(...),
    provider: Optional[str] = Form(None)
):
    """
    Upload a bill file (PDF or image) for analysis
    """
    try:
        # Validate file type
        content_type = file.content_type
        if content_type not in ["application/pdf", "image/jpeg", "image/png"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {content_type}. Please upload a PDF, JPEG, or PNG."
            )
        
        # Read file content
        file_content = await file.read()
        
        # Process the document
        doc_processor = DocumentProcessor()
        processed_doc = doc_processor.process_document(file_content, content_type)
        
        # Get initial structured data
        structured_data = processed_doc.get('structured_data', {})
        
        # If provider wasn't specified, try to get it from the document
        if not provider and structured_data.get('service_provider'):
            provider = structured_data.get('service_provider')
        
        # Store processed data temporarily
        upload_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)
        
        # Store encrypted data
        temp_results[upload_id] = {
            'processed_doc': encrypt_data(processed_doc),
            'bill_type': bill_type,
            'provider': provider,
            'expires_at': expires_at
        }
        
        return {
            "upload_id": upload_id,
            "expires_at": expires_at.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/api/analyze/{upload_id}", response_model=AnalysisResult)
async def analyze_document(upload_id: str, request: AnalysisRequest):
    """
    Analyze a previously uploaded document for fees
    """
    if upload_id not in temp_results:
        raise HTTPException(status_code=404, detail="Upload not found or expired")
    
    try:
        # Get stored data
        stored_data = temp_results[upload_id]
        
        # Check expiration
        if stored_data['expires_at'] < datetime.now():
            del temp_results[upload_id]
            raise HTTPException(status_code=404, detail="Upload expired")
        
        # Decrypt the processed document
        processed_doc = decrypt_data(stored_data['processed_doc'])
        
        # Use provided bill type and provider from request if available
        bill_type = request.bill_type or stored_data['bill_type']
        provider = request.provider or stored_data['provider']
        
        # Initialize the fee detector
        fee_detector = FeeDetector()
        
        # Detect fees
        result = fee_detector.detect_fees(processed_doc, bill_type)
        
        # Update the provider if it was determined from the document
        if not result['provider'] and provider:
            result['provider'] = provider
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing document: {str(e)}")

@app.get("/api/health")
async def health_check():
    """
    Simple health check endpoint
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Additional API endpoints can be added as needed
