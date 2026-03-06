import os
import sys
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, TESSERACT_PATH
from ocr.extractor import extract_text
from database.db_handler import save_form, get_all_forms

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ocr", methods=["POST"])
def run_ocr():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)
    fields = extract_text(filepath)
    return jsonify({"success": True, "fields": fields})

@app.route("/save", methods=["POST"])
def save():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
    result = save_form(data)
    if result:
        return jsonify({"success": True, "message": "Form saved successfully"})
    else:
        return jsonify({"error": "Failed to save form"}), 500

@app.route("/records", methods=["GET"])
def get_records():
    forms = get_all_forms()
    return jsonify({"success": True, "records": forms})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
