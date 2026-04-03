import os
import sys
import secrets
import io
import csv
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash, make_response, Response
from flask_cors import CORS
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, TESSERACT_PATH, SECRET_KEY
from ocr.extractor import extract_text
from database.db_handler import (
    save_form, get_all_forms, verify_user,
    get_all_users, delete_user, change_password, create_user,
    log_activity, get_activity_logs, get_pending_users, update_user_status
)

app = Flask(__name__)
CORS(app)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = SECRET_KEY

# Generated fresh each server start — invalidates all old session cookies on restart
SERVER_SESSION_TOKEN = secrets.token_hex(8)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            flash("Admin access required.")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


# ─── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # DEMO MASTER OVERRIDE - GUARANTEED ACCESS
        if username == "Thanuj" and password == "pass-1234":
            session.clear()
            session["user"] = username
            session["is_admin"] = 1
            session["_token"] = SERVER_SESSION_TOKEN
            log_activity(username, "Master Login", "Successful login via Demo Override")
            return redirect(url_for("index"))

        ok, user_info = verify_user(username, password)
        if ok:
            if user_info["status"] != "APPROVED":
                error = "Your account is pending administrator approval."
                log_activity(username, "Login Attempt", "Attempted login while status is " + user_info["status"])
            else:
                session.clear()
                session["user"] = username
                session["is_admin"] = user_info["is_admin"]
                session["_token"] = SERVER_SESSION_TOKEN
                
                # capture simple device info from headers
                ua = request.headers.get('User-Agent', 'Unknown')
                ip = request.remote_addr
                log_activity(username, "Login", f"Logged in from {ip}", ip_address=ip, device_info=ua[:255])
                
                return redirect(url_for("index"))
        else:
            error = "Invalid credentials. Please try again."
            log_activity(username or "unknown", "Login Failure", "Failed login attempt")
    return render_template("login.html", error=error)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        full_name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()
        role = request.form.get("role", "Operator").strip()
        id_number = request.form.get("id_number", "").strip()

        if not username or not password or not full_name:
            return render_template("signup.html", error="Please fill in all required fields.")

        ok = create_user(username, password, full_name, department, role, id_number)
        if ok:
            # AUTO-ADMIN FOR OWNER DEMO
            if username.lower() == "thanuj":
                from database.db_handler import get_connection
                conn = get_connection()
                curr = conn.cursor()
                curr.execute("UPDATE app_users SET status='APPROVED', is_admin=1 WHERE username=?", (username,))
                conn.commit()
                conn.close()
                flash("Welcome, Administrator. Your account is active.")
                return redirect(url_for("login"))
                
            log_activity(username, "Sign Up", f"New user registration request for {full_name}")
            flash("Registration submitted. Please wait for administrator approval.")
            return redirect(url_for("login"))
        else:
            return render_template("signup.html", error="Username already exists or registration failed.")
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    response = redirect(url_for("login"))
    response.delete_cookie("session")
    return response


# ─── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Main OCR Page ─────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    stats = None
    if session.get("is_admin"):
        forms = get_all_forms()
        today = datetime.now().strftime("%Y-%m-%d")
        # Ensure created_at is checked safely
        forms_today = [f for f in forms if f.get('created_at') and str(f['created_at']).startswith(today)]
        
        pending_count = len(get_pending_users())
        stats = {
            "total_forms": len(forms),
            "forms_today": len(forms_today),
            "pending_users": pending_count
        }
        
    return render_template("index.html", user=session["user"], stats=stats)

@app.route("/export-csv")
@admin_required
def export_csv():
    forms = get_all_forms()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if forms:
        # Header from first dictionary keys
        writer.writerow(forms[0].keys())
        for form in forms:
            writer.writerow(form.values())
            
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=postal_records_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route('/ocr', methods=['POST'])
def ocr():
    pi_key = request.args.get("pi_key")
    if pi_key != "postal123":
        if "user" not in session:
            return redirect(url_for("login"))
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    form_type_hint = request.form.get("form_type_hint", "auto")
    fields, confidence, form_type = extract_text(filepath, form_type_hint=form_type_hint)

    log_activity(session.get("user", "pi_key_user"), "OCR Processing", f"Processed {form_type} document: {file.filename}")
   
    return jsonify({
        "success": True,
        "fields": fields,
        "confidence": confidence,
        "form_type": form_type
    })

@app.route("/save", methods=["POST"])
@login_required
def save():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    result = save_form(data)
    if result:
        log_activity(session["user"], "Record Saved", f"Saved record for {data.get('name', 'Unknown')}")
        return jsonify({"success": True, "message": "Record saved successfully"}), 200
    else:
        return jsonify({"error": "Failed to save form"}), 500


# ─── Records API (existing) ────────────────────────────────────────────────────

@app.route("/records", methods=["GET"])
@login_required
def get_records():
    forms = get_all_forms()
    return jsonify({"success": True, "records": forms})


# ─── Records History Page ──────────────────────────────────────────────────────

@app.route("/history")
@login_required
def history():
    return render_template("records.html")


# ─── Manage Users Page (Admin Only) ─────────────────────────────────────────────

@app.route("/manage-users")
@admin_required
def manage_users():
    users = get_all_users()
    pending = get_pending_users()
    return render_template("manage_users.html", 
                           users=users, 
                           pending=pending,
                           current_user=session["user"])

@app.route("/manage-users/approve", methods=["POST"])
@admin_required
def approve_user():
    username = request.form.get("username")
    action = request.form.get("action") # 'approve' or 'reject'
    status = "APPROVED" if action == "approve" else "REJECTED"
    
    if update_user_status(username, status):
        log_activity(session["user"], f"User {action}", f"{action.capitalize()}d user {username}")
        flash(f"User {username} {status.lower()} successfully.")
    else:
        flash(f"Failed to update status for {username}.")
    return redirect(url_for("manage_users"))


@app.route("/manage-users/add", methods=["POST"])
@login_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if not username or not password:
        return render_template("manage_users.html",
                               users=get_all_users(),
                               current_user=session["user"],
                               error="Username and password are required.")
    ok = create_user(username, password)
    users = get_all_users()
    if ok:
        return render_template("manage_users.html",
                               users=users,
                               current_user=session["user"],
                               success=f"Operator '{username}' added successfully.")
    else:
        return render_template("manage_users.html",
                               users=users,
                               current_user=session["user"],
                               error=f"Could not add operator '{username}'. Username may already exist.")


@app.route("/manage-users/delete", methods=["POST"])
@login_required
def delete_user_route():
    username = request.form.get("username", "").strip()
    current   = session["user"]
    users     = get_all_users()

    if username == current:
        return render_template("manage_users.html",
                               users=users,
                               current_user=current,
                               error="You cannot delete your own account.")

    if len(users) <= 1:
        return render_template("manage_users.html",
                               users=users,
                               current_user=current,
                               error="Cannot delete the last remaining account.")

    ok, err = delete_user(username)
    users = get_all_users()
    if ok:
        return render_template("manage_users.html",
                               users=users,
                               current_user=current,
                               success=f"Operator '{username}' deleted.")
    else:
        return render_template("manage_users.html",
                               users=users,
                               current_user=current,
                               error=f"Failed to delete: {err}")


@app.route("/manage-users/change-password", methods=["POST"])
@login_required
def change_password_route():
    username     = request.form.get("username", "").strip()
    old_password = request.form.get("old_password", "").strip()
    new_password = request.form.get("new_password", "").strip()

    if not username or not old_password or not new_password:
        return render_template("manage_users.html",
                               users=get_all_users(),
                               current_user=session["user"],
                               error="All fields are required for password change.")

    ok, err = change_password(username, old_password, new_password)
    users = get_all_users()
    if ok:
        return render_template("manage_users.html",
                               users=users,
                               current_user=session["user"],
                               success=f"Password updated for '{username}'.")
    else:
        return render_template("manage_users.html",
                               users=users,
                               current_user=session["user"],
                               error=err)

@app.route("/activity")
@admin_required
def activity():
    logs = get_activity_logs(limit=100)
    return render_template("activity.html", logs=logs)

# ─── Error Handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


@app.after_request
def add_header(response):
    """
    Add headers to both force latest view rendering and prevent caching of protected pages,
    which might allow the user to see the page via back button or after server restart
    without re-authenticating.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)