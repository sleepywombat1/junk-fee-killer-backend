# integration.py
"""
Connects all components of the Fee Detective system:
- FastAPI application (app.py)
- Document Processor (document_processor.py)
- Fee Detector (fee_detector.py)
- Secure File Handler (secure_file_handler.py)
"""

import logging
from fastapi import FastAPI, Depends, HTTPException
from secure_file_handler import SecureFileHandler
from document_processor import DocumentProcessor
from fee_detector import FeeDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
file_handler = SecureFileHandler(retention_minutes=60)  # 1 hour retention
document_processor = DocumentProcessor()
fee_detector = FeeDetector()

def process_document_pipeline(file_bytes, file_type, bill_type, provider=None):
    """
    Complete document processing pipeline from raw file to fee analysis.
    
    Args:
        file_bytes (bytes): Raw file content
        file_type (str): MIME type of the file
        bill_type (str): Type of bill (phone, utility, etc.)
        provider (str, optional): Service provider name
        
    Returns:
        dict: Complete analysis results
    """
    try:
        # Step 1: Store file securely and get references
        file_id, encryption_key, iv = file_handler.process_uploaded_file(file_bytes, file_type)
        
        # Step 2: Process document and extract text/data
        processed_doc = document_processor.process_document(file_bytes, file_type)
        
        # Step 3: Detect fees in the processed document
        analysis_result = fee_detector.detect_fees(processed_doc, bill_type)
        
        # Step 4: Enrich result with provider info if available
        if provider and not analysis_result.get('provider'):
            analysis_result['provider'] = provider
            
        # Step 5: Clean up temporary file immediately after processing
        file_handler.delete_file(file_id)
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in document processing pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

# Factory function to create FastAPI dependencies
def get_secure_file_handler():
    return file_handler

def get_document_processor():
    return document_processor

def get_fee_detector():
    return fee_detector
