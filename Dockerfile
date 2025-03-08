# Use a base image with Python 
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (Tesseract & Poppler)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Copy the current directory contents into the container at /app
COPY . /app

# Install any Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "app.py"]
