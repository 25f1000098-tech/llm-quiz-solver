# app.py
import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Get the secret from the environment variable
STUDENT_SECRET = os.getenv("MY_SECRET_STRING")

# Import the SolverEngine
from solver import SolverEngine

@app.route("/", methods=["POST"])
def quiz_handler():
    # 1. Check for valid JSON payload
    try:
        payload = request.get_json()
        email = payload.get("email")
        secret = payload.get("secret")
        url = payload.get("url")
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # 2. Check for missing fields
    if not all([email, secret, url]):
        return jsonify({"error": "Missing 'email', 'secret', or 'url' in payload"}), 400

    # 3. Verify the secret string
    if secret != STUDENT_SECRET:
        return jsonify({"error": "Invalid secret string"}), 403

    # --- Verification Successful: Start the Quiz Solver ---
    try:
        # Initialize the solver instance
        solver = SolverEngine(email, secret)
        # Start the solving process in the background. 
        # For evaluation, we need to return HTTP 200 quickly.
        # In a real production environment, this would be delegated to a background task
        # to avoid request timeouts. For a simplified local setup, we call it directly:
        solver.solve_quiz(url) 

        # Respond immediately to acknowledge receipt and processing start
        return jsonify({
            "status": "Task accepted",
            "message": f"Automated quiz solution for URL: {url} is starting."
        }), 200

    except Exception as e:
        print(f"Error during solver setup: {e}")
        return jsonify({"error": "Internal server error during task processing"}), 500

if __name__ == "__main__":
    # Use this for local testing
    app.run(debug=True, port=8080)