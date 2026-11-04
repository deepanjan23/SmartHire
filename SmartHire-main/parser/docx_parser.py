
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
import os


def extract_text_from_docx(file_path):
    """
    Extracts text from DOCX resumes, including paragraphs and tables.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.lower().endswith(".docx"):
        raise ValueError("Only .docx files are supported.")

    try:
        document = Document(file_path)
        extracted_text = []

        # Extract text from paragraphs
        for paragraph in document.paragraphs:
            content = paragraph.text.strip()

            if content:
                extracted_text.append(content)

        # Extract text from tables
        for table in document.tables:
            for row in table.rows:
                row_text = []

                for cell in row.cells:
                    cell_text = cell.text.strip()

                    if cell_text:
                        row_text.append(cell_text)

                if row_text:
                    extracted_text.append(" | ".join(row_text))

        # Combine extracted content
        final_text = "\n".join(extracted_text)

        return final_text

    except PackageNotFoundError:
        raise ValueError("Invalid or corrupted DOCX file.")

    except Exception as e:
        raise RuntimeError(f"Error extracting DOCX text: {e}")
