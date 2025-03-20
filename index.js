const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const morgan = require('morgan');
const path = require('path');
const multer = require('multer');
const fs = require('fs');
const axios = require('axios');
const FormData = require('form-data');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

// Initializes express app
const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(morgan('dev'));

// Ensure uploads directory exists
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: function(req, file, cb) {
    cb(null, uploadsDir);
  },
  filename: function(req, file, cb) {
    cb(null, uuidv4() + path.extname(file.originalname));
  }
});
const upload = multer({ storage: storage });

// Serve static files from the uploads directory
app.use('/uploads', express.static(uploadsDir));

// Routes
app.post('/api/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // Here we would typically process the file
    // For example, using OCR or other analysis tools

    return res.status(200).json({
      message: 'File uploaded successfully',
      filename: req.file.filename,
      path: `/uploads/${req.file.filename}`
    });
  } catch (error) {
    console.error('Error uploading file:', error);
    return res.status(500).json({ error: 'Error uploading file' });
  }
});

app.post('/api/analyze', async (req, res) => {
  try {
    const { filePath, fileType } = req.body;

    if (!filePath) {
      return res.status(400).json({ error: 'No file path provided' });
    }

    // This would be where you analyze the document for junk fees
    // For now, return a mock response
    const mockResponse = {
      fees: [
        {
          name: 'Administrative Fee',
          amount: 24.99,
          description: 'Monthly fee for account maintenance',
          isJunk: true,
          reason: 'This fee is unnecessary and can be waived'
        },
        {
          name: 'Service Charge',
          amount: 15.00,
          description: 'Charge for customer service',
          isJunk: true,
          reason: 'This service should be included in your basic plan'
        }
      ],
      totalFees: 39.99,
      junkFeesTotal: 39.99,
      document: {
        type: fileType || 'unknown',
        path: filePath
      }
    };

    return res.status(200).json(mockResponse);
  } catch (error) {
    console.error('Error analyzing file:', error);
    return res.status(500).json({ error: 'Error analyzing file' });
  }
});

// Basic route for testing
app.get('/', (req, res) => {
  res.json({ message: 'Welcome to the Junk Fee Killer API' });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});