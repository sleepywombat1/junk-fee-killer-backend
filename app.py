from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import io
import pytesseract
import os
# Ensure Tesseract OCR is found
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  # Common path for Linux

from pdf2image import convert_from_bytes

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://junk-fee-killer-frontend-3yphvpky9-marks-projects-42cdc383.vercel.app"}})

# Define regex patterns for hidden fees
FEE_PATTERNS = [
    r'\b(service charge|convenience fee|processing fee|administrative fee)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(resort fee|activation fee|maintenance fee|overdraft fee)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(ATM fee|early termination fee|equipment rental fee|subscription fee)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(membership fee|renewal fee|compliance fee|government surcharge)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(data overage charge|line access fee|paper statement fee|booking fee)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(seat selection fee|baggage fee|cancellation fee|late payment fee)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(returned payment fee|minimum balance fee|wire transfer fee|foreign transaction fee)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(check image fee|card replacement fee|stop payment fee|check printing fee|account closure fee)[:\s]*\$?\d+(\.\d{2})?\b',
    r'\b(inactivity fee|transaction fee|annual fee|finance charge|interest charge|penalty fee)[:\s]*\$?\d+(\.\d{2})?\b'
]

def extract_text_from_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes)
    text = " "
    for image in images:
        text += pytesseract.image_to_string(image) + "\n"
    return text

def detect_fees(text):
    detected_fees = []
    for pattern in FEE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        detected_fees.extend(matches)
    return detected_fees

@app.route("/")
def home():
    return "Junk Fee Killer API is running!"

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        file_bytes = file.read()
        extracted_text = extract_text_from_pdf(file_bytes)
        detected_fees = detect_fees(extracted_text)

        return jsonify({"detected_fees": detected_fees, "message": "Fee detection complete"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
