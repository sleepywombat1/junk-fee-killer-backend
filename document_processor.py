import os
import pytesseract
from PIL import Image
import pdf2image
import io
import numpy as np
import cv2
from tempfile import NamedTemporaryFile

class DocumentProcessor:
    """
    Handles the extraction of text from various document formats like PDF and images.
    Focuses on temporary processing without permanent storage.
    """
    
    def __init__(self, config=None):
        """
        Initialize the document processor with optional configuration.
        
        Args:
            config (dict, optional): Configuration options for the processor.
        """
        self.config = config or {}
        # Set default OCR language to English
        self.lang = self.config.get('lang', 'eng')
        # Configure Tesseract path if provided
        if 'tesseract_path' in self.config:
            pytesseract.pytesseract.tesseract_cmd = self.config['tesseract_path']
    
    def process_document(self, file_bytes, file_type):
        """
        Process a document from bytes and extract text.
        
        Args:
            file_bytes (bytes): The raw file bytes.
            file_type (str): The MIME type of the file.
            
        Returns:
            dict: Extracted text and document structure.
        """
        if file_type == 'application/pdf':
            return self._process_pdf(file_bytes)
        elif file_type in ['image/jpeg', 'image/png']:
            return self._process_image(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _process_pdf(self, pdf_bytes):
        """
        Extract text from a PDF file.
        
        Args:
            pdf_bytes (bytes): Raw PDF file bytes.
            
        Returns:
            dict: Extracted text and metadata.
        """
        # Convert PDF to images
        with NamedTemporaryFile(suffix='.pdf', delete=True) as temp_pdf:
            temp_pdf.write(pdf_bytes)
            temp_pdf.flush()
            
            try:
                # Convert PDF pages to images
                images = pdf2image.convert_from_path(temp_pdf.name)
                full_text = ""
                page_texts = []
                
                # Process each page
                for i, image in enumerate(images):
                    # Convert PIL image to OpenCV format
                    open_cv_image = np.array(image) 
                    open_cv_image = open_cv_image[:, :, ::-1].copy() 
                    
                    # Enhance image for better OCR
                    enhanced_image = self._enhance_image(open_cv_image)
                    
                    # Extract text from the enhanced image
                    page_text = pytesseract.image_to_string(enhanced_image, lang=self.lang)
                    full_text += page_text + "\n\n"
                    page_texts.append(page_text)
                
                return {
                    'full_text': full_text,
                    'page_count': len(images),
                    'page_texts': page_texts,
                    'structured_data': self._extract_structured_data(full_text)
                }
            except Exception as e:
                raise Exception(f"Error processing PDF: {str(e)}")
    
    def _process_image(self, image_bytes):
        """
        Extract text from an image file.
        
        Args:
            image_bytes (bytes): Raw image file bytes.
            
        Returns:
            dict: Extracted text and metadata.
        """
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert PIL image to OpenCV format
            open_cv_image = np.array(image)
            if open_cv_image.shape[2] == 3:  # Color image
                open_cv_image = open_cv_image[:, :, ::-1].copy()  # RGB to BGR
            
            # Enhance image for better OCR
            enhanced_image = self._enhance_image(open_cv_image)
            
            # Extract text
            text = pytesseract.image_to_string(enhanced_image, lang=self.lang)
            
            return {
                'full_text': text,
                'page_count': 1,
                'page_texts': [text],
                'structured_data': self._extract_structured_data(text)
            }
        except Exception as e:
            raise Exception(f"Error processing image: {str(e)}")
    
    def _enhance_image(self, image):
        """
        Enhance image for better OCR results.
        
        Args:
            image (numpy.ndarray): The input image.
            
        Returns:
            numpy.ndarray: The enhanced image.
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Apply thresholding to get black and white image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply noise reduction
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        return denoised
    
    def _extract_structured_data(self, text):
        """
        Extract structured data from text like dates, amounts, etc.
        
        Args:
            text (str): The extracted text.
            
        Returns:
            dict: Structured data extracted from the text.
        """
        # Implement basic structured data extraction
        # This is a simplified implementation - would need to be expanded
        structured_data = {
            'total_amount': self._extract_total_amount(text),
            'line_items': self._extract_line_items(text),
            'service_provider': self._extract_service_provider(text),
            'bill_date': self._extract_bill_date(text),
            'customer_details': self._extract_customer_details(text)
        }
        
        return structured_data
    
    def _extract_total_amount(self, text):
        """Extract the total amount from the bill text."""
        # This is a placeholder implementation
        # Real implementation would use regex patterns and context
        import re
        
        # Look for patterns like "Total: $123.45" or "Amount Due: $123.45"
        patterns = [
            r"Total[\s:]*\$?([0-9,]+\.[0-9]{2})",
            r"Amount Due[\s:]*\$?([0-9,]+\.[0-9]{2})",
            r"Balance[\s:]*\$?([0-9,]+\.[0-9]{2})"
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                # Remove commas and convert to float
                amount_str = matches.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    pass
        
        return None
    
    def _extract_line_items(self, text):
        """Extract line items (charges) from the bill text."""
        # This is a placeholder - real implementation would be more complex
        # Would need to identify patterns specific to the bill format
        import re
        
        line_items = []
        
        # Simple pattern to match descriptions followed by amounts
        pattern = r"([\w\s\-]+)[\s:]*\$?([0-9,]+\.[0-9]{2})"
        
        matches = re.finditer(pattern, text)
        for match in matches:
            description = match.group(1).strip()
            amount_str = match.group(2).replace(',', '')
            
            # Filter out inappropriate matches
            if len(description) > 3 and len(description) < 100:
                try:
                    amount = float(amount_str)
                    line_items.append({
                        'description': description,
                        'amount': amount
                    })
                except ValueError:
                    pass
        
        return line_items
    
    def _extract_service_provider(self, text):
        """Extract the service provider name from the bill."""
        # Placeholder implementation
        # Would need to be trained on specific bill formats
        import re
        
        # Common service provider patterns
        patterns = [
            r"(AT&T|Verizon|T-Mobile|Sprint|Comcast|Xfinity|Spectrum|Cox|CenturyLink|Frontier|Optimum|Dish|DirectTV)",
            r"(PG&E|Southern California Edison|Duke Energy|Florida Power & Light)",
            r"(Water Authority|Gas Company)"
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                return matches.group(1)
        
        return None
    
    def _extract_bill_date(self, text):
        """Extract the bill date from the text."""
        # Placeholder implementation
        import re
        from datetime import datetime
        
        # Search for common date patterns
        date_patterns = [
            r"Bill Date:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
            r"Date:?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
            r"(\d{1,2}/\d{1,2}/\d{2,4})"
        ]
        
        for pattern in date_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                date_str = matches.group(1)
                try:
                    # Try to parse the date
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date_str, "%m/%d/%y")
                        return date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
        
        return None
    
    def _extract_customer_details(self, text):
        """Extract customer information from the bill."""
        # Placeholder implementation
        import re
        
        # Look for account number patterns
        account_match = re.search(r"Account\s*(?:Number|#)?\s*:?\s*([A-Z0-9\-]+)", text, re.IGNORECASE)
        account_number = account_match.group(1) if account_match else None
        
        # Look for names (this is a simplistic approach)
        name_match = re.search(r"Name\s*:?\s*([A-Za-z\s]+)", text, re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else None
        
        return {
            'account_number': account_number,
            'name': name
        }
