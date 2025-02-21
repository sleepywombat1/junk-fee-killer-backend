from flask import Flask
from flask_cors import CORS  # Import CORS

app = Flask(__name__)

# Enable CORS for requests from your Vercel frontend
CORS(app, resources={r"/*": {"origins": "https://junk-fee-killer-frontend-3yphvpky9-marks-projects-42cdc383.vercel.app"}})

@app.route("/")
def home():
    return "Junk Fee Killer API is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
