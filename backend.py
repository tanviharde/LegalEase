import os
import shutil

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pdf_extractor import extract_text_from_document
from translator import (
    detect_language,
    english_to_marathi,
    marathi_to_english,
)
from classifier import classify_document, get_document_label
from analyser import run_ai_task


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI(
    title="LegalEase",
    description="AI-powered English-Marathi Legal Document Assistant",
    version="1.0.0",
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
async def home():
    return FileResponse(
        os.path.join(FRONTEND_DIR, "index.html")
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "LegalEase",
    }


# =========================================================
# UPLOAD + EXTRACTION
# =========================================================

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "No file selected.",
            },
        )

    allowed_extensions = {
        ".pdf",
        ".docx",
        ".jpg",
        ".jpeg",
        ".png",
    }

    original_filename = os.path.basename(
        file.filename
    )

    extension = os.path.splitext(
        original_filename
    )[1].lower()

    if extension not in allowed_extensions:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": (
                    "Unsupported file type. "
                    "Please upload PDF, DOCX, JPG, JPEG, or PNG."
                ),
            },
        )

    file_path = os.path.join(
        UPLOAD_DIR,
        original_filename,
    )

    try:

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

        extracted_text = extract_text_from_document(
            file_path
        )

        if not extracted_text.strip():
            raise ValueError(
                "No readable text could be extracted from the document."
            )

        detected_language = detect_language(
            extracted_text
        )

        document_type = classify_document(
            extracted_text
        )

        return {
            "success": True,
            "filename": original_filename,
            "file_type": extension,
            "text": extracted_text,
            "characters": len(extracted_text),
            "detected_language": detected_language,
            "document_type": document_type,
            "document_label": get_document_label(
                document_type
            ),
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
            },
        )


# =========================================================
# PROCESS TASK
# =========================================================

@app.post("/process")
async def process_document(payload: dict):

    text = payload.get(
        "text",
        "",
    ).strip()

    target_language = payload.get(
        "target_language",
        "",
    )

    task = payload.get(
        "task",
        "",
    )

    document_type = payload.get(
        "document_type",
        "unknown",
    )


    # -----------------------------------------------------
    # Validation
    # -----------------------------------------------------

    if not text:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "No document text was provided.",
            },
        )


    if target_language not in {
        "Marathi",
        "English",
    }:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": (
                    "Please select Marathi or English."
                ),
            },
        )


    allowed_tasks = {
        "translate",
        "summarize",
        "key_information",
        "simplify",
        "legal_analysis",
    }

    if task not in allowed_tasks:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Please select a valid task.",
            },
        )


    try:

        source_language = detect_language(
            text
        )


        # =================================================
        # TRANSLATE
        # =================================================

        if task == "translate":

            if (
                target_language == "Marathi"
                and "marathi" not in source_language.lower()
            ):

                result = english_to_marathi(
                    text
                )

            elif (
                target_language == "English"
                and "english" not in source_language.lower()
            ):

                result = marathi_to_english(
                    text
                )

            else:

                result = text


        # =================================================
        # ALL OTHER AI TASKS
        # =================================================

        else:

            result = run_ai_task(
                text=text,
                task=task,
                target_language=target_language,
                document_type=document_type,
            )


        return {
            "success": True,
            "task": task,
            "source_language": source_language,
            "target_language": target_language,
            "result": result,
        }


    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
            },
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
