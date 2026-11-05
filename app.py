import logging
import uuid
import webbrowser
from threading import Timer
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from parser.pdf_parser import extract_text_from_pdf
from parser.docx_parser import extract_text_from_docx
from parser.text_cleaner import clean_text
from parser.resume_parser import parse_resume


# =====================================================
# FLASK APPLICATION CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
    static_url_path="/static"
)

# 10 MB maximum request size
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  
app.config["TEMPLATES_AUTO_RELOAD"] = True

UPLOAD_FOLDER = BASE_DIR / "resumes"
OUTPUT_FOLDER = BASE_DIR / "output"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def allowed_file(filename):
    """Return True when the file has a supported extension."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def save_resume_output(filename, file_type, resume_data, cleaned_text):
    """Save extracted candidate information and cleaned text."""

    output_filename = f"resume_data_{uuid.uuid4().hex}.txt"
    output_path = OUTPUT_FOLDER / output_filename

    with output_path.open("w", encoding="utf-8") as output:
        output.write("SMART HIRE - RESUME DATA\n")
        output.write("=" * 40 + "\n\n")

        output.write(f"Original filename: {filename}\n")
        output.write(f"File type: {file_type}\n\n")

        output.write("CANDIDATE INFORMATION\n")
        output.write("-" * 30 + "\n")

        for key, value in resume_data.items():
            output.write(f"{key}: {value}\n")

        output.write("\nCLEANED RESUME TEXT\n")
        output.write("-" * 30 + "\n")
        output.write(cleaned_text)

    return output_filename


def render_home_error(message, status_code=400):
    """Render the upload page with a user-friendly error."""
    return render_template("index.html", error=message), status_code


# =====================================================
# HOME PAGE
# =====================================================

@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return "Login form submitted. Authentication is not configured yet."

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        return "Registration form submitted. Registration is not configured yet."

    return render_template("register.html")
# =====================================================
# UPLOAD AND PROCESS RESUME
# =====================================================

@app.route("/upload", methods=["POST"])
def upload_resume():

    if "resume" not in request.files:
        return render_home_error(
            "Please select a resume to upload."
        )

    uploaded_file = request.files["resume"]

    if not uploaded_file.filename or not uploaded_file.filename.strip():
        return render_home_error(
            "No file selected. Please choose a PDF or DOCX resume."
        )

    original_filename = secure_filename(uploaded_file.filename)

    if not original_filename:
        return render_home_error(
            "Invalid filename. Please rename your file and try again."
        )

    if not allowed_file(original_filename):
        return render_home_error(
            "Unsupported file format. Please upload a PDF or DOCX file."
        )

    extension = Path(original_filename).suffix.lower()
    file_type = "PDF" if extension == ".pdf" else "DOCX"

    # Unique filename prevents accidental overwriting.
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_FOLDER / stored_filename

    try:
        # 1. Save uploaded resume.
        uploaded_file.save(str(file_path))

        if not file_path.is_file() or file_path.stat().st_size == 0:
            file_path.unlink(missing_ok=True)
            return render_home_error(
                "The uploaded file is empty. Please choose another file."
            )

        # 2. Extract original resume text.
        if extension == ".pdf":
            extracted_text = extract_text_from_pdf(str(file_path))
        else:
            extracted_text = extract_text_from_docx(str(file_path))

        if not isinstance(extracted_text, str) or not extracted_text.strip():
            return render_home_error(
                "No readable text was found. Please upload a text-based "
                "PDF or DOCX. Scanned PDFs may require OCR."
            )

        # 3. Extract candidate information from original text.
        resume_data = parse_resume(extracted_text)

        if not isinstance(resume_data, dict):
            raise ValueError(
                "The resume parser did not return valid candidate data."
            )

        # 4. Clean text for NLP and resume matching.
        cleaned_text = clean_text(extracted_text)

        if not isinstance(cleaned_text, str):
            raise ValueError(
                "The text cleaner must return a string."
            )

        # 5. Save the processed results.
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

        # 6. Display the results page.
        return render_template(
            "result.html",
            filename=original_filename,
            file_type=file_type,
            resume_data=resume_data,
            cleaned_text=cleaned_text,
            output_filename=output_filename
        )

    except (ValueError, RuntimeError) as exc:
        logger.exception(
        "Resume processing failed for %s",
        original_filename
        )

        return render_home_error(
        f"Resume processing failed: {exc}"
        )

        return render_home_error(
            "The resume could not be processed. Please check the file "
            "and try again."
        )

    except Exception:
        logger.exception(
            "Unexpected error processing resume: %s",
            original_filename
        )

        return render_home_error(
            "An unexpected error occurred. Please try another resume "
            "or check the application terminal for details.",
            status_code=500
        )


# =====================================================
# FILE SIZE ERROR HANDLER
# =====================================================

@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(error):
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
        lambda: webbrowser.open("http://127.0.0.1:5000/login")
    ).start()

    app.run(debug=True, use_reloader=False)