from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS

app = Flask(__name__)

# Enable CORS for debugging (allowing all origins for now)
CORS(app, resources={r"/*": {"origins": "*"}})  # Temporarily open for debugging

@app.route("/")
def home():
    return "Junk Fee Killer API is running!"

# Upload route with logging for debugging
@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        response = jsonify({"error": "No file part"})
        print("Response:", response.get_json())  # Log response
        return response, 400

    file = request.files['file']

    if file.filename == '':
        response = jsonify({"error": "No selected file"})
        print("Response:", response.get_json())  # Log response
        return response, 400

    # Successfully received file
    response = jsonify({"message": "File successfully uploaded"})
    print("Response:", response.get_json())  # Log response
    return response, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
