import logging
import os
import re
import secrets
import uuid
import webbrowser

from datetime import timedelta
from pathlib import Path
from threading import Timer

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from flask_login import (
    login_user,
    login_required,
    logout_user,
    current_user
)

from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

# =====================================================
# IMPORT PROJECT MODULES
# =====================================================

from database import init_db
from extensions import db, login_manager
from models import User
from parser.pdf_parser import extract_text_from_pdf
from parser.docx_parser import extract_text_from_docx
from parser.text_cleaner import clean_text
from parser.resume_parser import parse_resume


# =====================================================
# FLASK APPLICATION CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
    static_url_path="/static"
)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Persistent secret key for local desktop sessions.
# For production deployments, provide a secure environment
# variable instead of sharing the key across installations.

DATA_DIR = Path.home() / ".smarthire"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SECRET_FILE = DATA_DIR / "secret.key"

if not SECRET_FILE.exists():
    SECRET_FILE.write_text(
        secrets.token_hex(32),
        encoding="utf-8"
    )

app.config["SECRET_KEY"] = os.environ.get(
    "SMARTHIRE_SECRET_KEY",
    SECRET_FILE.read_text(encoding="utf-8").strip()
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

UPLOAD_FOLDER = DATA_DIR / "resumes"
OUTPUT_FOLDER = DATA_DIR / "output"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =====================================================
# DATABASE CONFIGURATION
# =====================================================

init_db(app)


# =====================================================
# FLASK LOGIN CONFIGURATION
# =====================================================

login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = (
    "Please log in to analyze your resume."
)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def allowed_file(filename):
    """Check supported resume extensions."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def save_resume_output(
    filename,
    file_type,
    resume_data,
    cleaned_text
):
    """Save extracted candidate information."""

    output_filename = (
        f"resume_data_{uuid.uuid4().hex}.txt"
    )

    output_path = OUTPUT_FOLDER / output_filename

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as output:

        output.write("SMART HIRE - RESUME DATA\n")
        output.write("=" * 40 + "\n\n")

        output.write(
            f"Original filename: {filename}\n"
        )

        output.write(
            f"File type: {file_type}\n\n"
        )

        output.write("CANDIDATE INFORMATION\n")
        output.write("-" * 30 + "\n")

        for key, value in resume_data.items():
            output.write(f"{key}: {value}\n")

        output.write("\nCLEANED RESUME TEXT\n")
        output.write("-" * 30 + "\n")

        output.write(cleaned_text)

    return output_filename


def render_home_error(message, status_code=400):

    return render_template(
        "index.html",
        error=message
    ), status_code


# =====================================================
# LANDING PAGE
# =====================================================

@app.route("/", methods=["GET"])
def home():

    return render_template("frontpage.html")


# =====================================================
# REGISTRATION PAGE
# =====================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("upload_page"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not all([
            full_name,
            email,
            password,
            confirm_password
        ]):
            flash(
                "Please complete all registration fields.",
                "error"
            )
            return redirect(url_for("register"))

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Enter a valid email address.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "error"
            )
            return redirect(url_for("register"))

        password_rules = [
            (r"[A-Z]", "Password must contain an uppercase letter."),
            (r"[a-z]", "Password must contain a lowercase letter."),
            (r"[0-9]", "Password must contain a number."),
            (r"[^A-Za-z0-9\s]", "Password must contain a special character."),
        ]

        for pattern, message in password_rules:
            if not re.search(pattern, password):
                flash(message, "error")
                return redirect(url_for("register"))

        if re.search(r"\s", password):
            flash("Password must not contain spaces or whitespace.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        user = User(full_name=full_name, email=email)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                "An account with this email already exists.",
                "error"
            )

            return redirect(url_for("register"))

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("register.html")


# =====================================================
# LOGIN PAGE
# =====================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("upload_page"))

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        if not email or not password:
            flash(
                "Please enter your email and password.",
                "error"
            )
            return redirect(url_for("login"))

        user = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if user is None or not user.check_password(password):

            flash(
                "Invalid email or password.",
                "error"
            )

            return redirect(url_for("login"))

        login_user(user)

        session.permanent = True

        flash(
            f"Welcome to SmartHire, {user.full_name}!",
            "success"
        )

        # Redirect to resume analysis after login
        return redirect(url_for("upload_page"))

    return render_template("login.html")


# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()

    flash(
        "You have logged out successfully.",
        "success"
    )

    return redirect(url_for("login"))


# =====================================================
# RESUME UPLOAD AND ANALYSIS
# =====================================================

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_page():

    if request.method == "GET":
        return render_template("index.html")

    if "resume" not in request.files:

        return render_home_error(
            "Please select a resume to upload."
        )

    uploaded_file = request.files["resume"]

    if (
        not uploaded_file.filename
        or not uploaded_file.filename.strip()
    ):

        return render_home_error(
            "No file selected. Please choose a PDF or DOCX resume."
        )

    original_filename = secure_filename(
        uploaded_file.filename
    )

    if not original_filename:

        return render_home_error(
            "Invalid filename. Please rename your file and try again."
        )

    if not allowed_file(original_filename):

        return render_home_error(
            "Unsupported file format. Please upload a PDF or DOCX file."
        )

    extension = Path(
        original_filename
    ).suffix.lower()

    file_type = (
        "PDF" if extension == ".pdf" else "DOCX"
    )

    stored_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    file_path = UPLOAD_FOLDER / stored_filename

    try:

        # STEP 1: SAVE UPLOADED RESUME

        uploaded_file.save(str(file_path))

        if (
            not file_path.is_file()
            or file_path.stat().st_size == 0
        ):

            return render_home_error(
                "The uploaded file is empty. Please choose another file."
            )

        # STEP 2: EXTRACT RESUME TEXT

        if extension == ".pdf":

            extracted_text = extract_text_from_pdf(
                str(file_path)
            )

        else:

            extracted_text = extract_text_from_docx(
                str(file_path)
            )

        if (
            not isinstance(extracted_text, str)
            or not extracted_text.strip()
        ):

            return render_home_error(
                "No readable text was found. "
                "Please upload a text-based PDF or DOCX. "
                "Scanned PDFs may require OCR."
            )

        # STEP 3: EXTRACT CANDIDATE INFORMATION

        resume_data = parse_resume(extracted_text)

        if not isinstance(resume_data, dict):

            raise ValueError(
                "The resume parser did not return valid candidate data."
            )

        # STEP 4: CLEAN RESUME TEXT

        cleaned_text = clean_text(extracted_text)

        if not isinstance(cleaned_text, str):

            raise ValueError(
                "The text cleaner must return a string."
            )

        # STEP 5: SAVE PROCESSED RESULTS

        output_filename = save_resume_output(
            original_filename,
            file_type,
            resume_data,
            cleaned_text
        )

        logger.info(
            "Resume processed successfully: %s",
            original_filename
        )

        # STEP 6: DISPLAY RESULTS

        return render_template(
            "result.html",
            filename=original_filename,
            file_type=file_type,
            resume_data=resume_data,
            cleaned_text=cleaned_text,
            output_filename=output_filename
        )

    except Exception:

        logger.exception(
            "Resume processing failed for %s",
            original_filename
        )

        return render_home_error(
            "Resume processing failed. Please check the file and try again.",
            status_code=500
        )

    finally:
        # Remove temporary uploaded resume after processing
        file_path.unlink(missing_ok=True)


# =====================================================
# FILE SIZE ERROR HANDLER
# =====================================================

@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(error):

    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    return render_home_error(
        "File is too large. The maximum allowed size is 10 MB.",
        status_code=413
    )


# =====================================================
# APPLICATION ENTRY POINT
# =====================================================

if __name__ == "__main__":

    Timer(
        1.5,
        lambda: webbrowser.open(
            "http://127.0.0.1:5000/"
        )
    ).start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )
