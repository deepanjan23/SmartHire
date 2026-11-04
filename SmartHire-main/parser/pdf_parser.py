
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
import os


def extract_text_from_pdf(file_path):
    """
    Extract text from PDF resumes for the SmartHire NLP pipeline.

    Features:
    - File existence validation
    - PDF extension validation
    - Text extraction from multiple pages
    - Empty page handling
    - Corrupted PDF handling
    - Clean text output
    """

    # Check whether file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    # Validate file extension
    if not file_path.lower().endswith(".pdf"):
        raise ValueError("Invalid file format. Please upload a PDF.")

    try:
        reader = PdfReader(file_path)

        # Check for encrypted PDF
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("The PDF is password protected.")

        extracted_pages = []

        # Extract text from every page
        for page_number, page in enumerate(reader.pages, start=1):

            page_text = page.extract_text()

            if page_text and page_text.strip():
                extracted_pages.append(page_text.strip())

        # Combine extracted text
        final_text = "\n".join(extracted_pages)

        # Check whether text was extracted
        if not final_text.strip():
            raise ValueError(
                "No readable text found. The PDF may be scanned or image-based."
            )

        return final_text

    except PdfReadError:
        raise ValueError("The PDF file is corrupted or unreadable.")

    except ValueError:
        raise

    except Exception as e:
        raise RuntimeError(f"Error extracting PDF text: {e}")
