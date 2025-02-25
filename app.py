from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS

app = Flask(__name__)

# Enable CORS for requests from your Vercel frontend
CORS(app, resources={r"/*": {"origins": "https://junk-fee-killer-frontend-3yphvpky9-marks-projects-42cdc383.vercel.app"}})

@app.route("/")
def home():
    return "Junk Fee Killer API is running!"

# Upload route (Fix for 404 issue)
@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Process the file (store, analyze, etc.)
    return jsonify({"message": "File successfully uploaded"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
