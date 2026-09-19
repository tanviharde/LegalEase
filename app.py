import os
import html
import gradio as gr

from pdf_extractor import extract_text_from_pdf
from classifier import classify_document, get_document_label
from analyser import analyse_document, get_urgency_color
from translator import (
    detect_language,
    english_to_marathi,
    marathi_to_english,
)


# ============================================================
# SETTINGS
# ============================================================

APP_TITLE = "LegalEase — Legal Document Assistant"

URGENCY_EMOJI = {
    "HIGH": "🔴",
    "MEDIUM": "🟠",
    "LOW": "🟢",
}


# ============================================================
# HELPERS
# ============================================================

def safe_text(text):
    if text is None:
        return ""

    return str(text).replace(
        "\x00",
        ""
    )


def is_text_usable(text):
    if not text:
        return False

    stripped = text.strip()

    if len(stripped) < 100:
        return False

    alpha_count = sum(
        char.isalpha()
        for char in stripped
    )

    ratio = alpha_count / max(
        1,
        len(stripped)
    )

    return ratio >= 0.15


def escape(value):
    return html.escape(
        safe_text(value)
    )


def list_to_html(items, empty_message="Not specified"):
    if not items:
        return f"<p class='muted'>{empty_message}</p>"

    result = "<ul>"

    for item in items:
        if isinstance(item, dict):
            role = escape(item.get("role", ""))
            name = escape(item.get("name", ""))

            if name:
                result += (
                    f"<li><strong>{role}</strong>: "
                    f"{name}</li>"
                )
            else:
                result += (
                    f"<li><strong>{role}</strong></li>"
                )
        else:
            result += (
                f"<li>{escape(item)}</li>"
            )

    result += "</ul>"

    return result


def dates_to_html(dates):

    if not dates:
        return (
            "<p class='muted'>"
            "No important dates identified."
            "</p>"
        )

    cards = ""

    for item in dates:

        label = escape(
            item.get(
                "label",
                "Date"
            )
        )

        date = escape(
            item.get(
                "date",
                ""
            )
        )

        importance = escape(
            item.get(
                "importance",
                ""
            )
        )

        cards += f"""
        <div class="date-card">
            <div class="date-label">{label}</div>
            <div class="date-value">{date}</div>
            <div class="date-info">{importance}</div>
        </div>
        """

    return cards


# ============================================================
# ANALYSIS HTML
# ============================================================

def format_analysis_html(
    analysis,
    doc_label,
    detected_language
):

    if not isinstance(analysis, dict):
        return """
        <div class="error-card">
            Analysis could not be displayed.
        </div>
        """

    if "error" in analysis:
        return f"""
        <div class="error-card">
            <h3>Analysis Error</h3>
            <p>{escape(analysis.get("error"))}</p>
        </div>
        """

    document_type = escape(
        analysis.get(
            "document_type",
            doc_label
        )
    )

    summary = escape(
        analysis.get(
            "simple_summary",
            "No summary available."
        )
    )

    urgency = safe_text(
        analysis.get(
            "urgency_level",
            "MEDIUM"
        )
    ).upper()

    urgency_reason = escape(
        analysis.get(
            "urgency_reason",
            ""
        )
    )

    urgency_color = get_urgency_color(
        urgency
    )

    emoji = URGENCY_EMOJI.get(
        urgency,
        "🟠"
    )

    parties = analysis.get(
        "parties_involved",
        []
    )

    dates = analysis.get(
        "critical_dates",
        []
    )

    conditions = analysis.get(
        "key_conditions",
        []
    )

    rights = analysis.get(
        "your_rights",
        []
    )

    consequences = escape(
        analysis.get(
            "what_happens_if_ignored",
            "No specific consequence identified."
        )
    )

    next_steps = analysis.get(
        "next_steps",
        []
    )

    return f"""
    <div class="results">

        <div class="document-header">
            <div>
                <div class="eyebrow">
                    DOCUMENT ANALYSIS
                </div>

                <h2>{document_type}</h2>

                <p class="detected">
                    Detected language:
                    <strong>{escape(detected_language)}</strong>
                </p>
            </div>

            <div
                class="urgency"
                style="border-color:{urgency_color};"
            >
                <div class="urgency-label">
                    URGENCY
                </div>

                <div
                    class="urgency-value"
                    style="color:{urgency_color};"
                >
                    {emoji} {escape(urgency)}
                </div>

                <div class="urgency-reason">
                    {urgency_reason}
                </div>
            </div>
        </div>


        <!-- SUMMARY -->

        <div class="section-card">
            <div class="section-title">
                <span class="section-icon">🧠</span>
                Simple Summary
            </div>

            <p class="summary-text">
                {summary}
            </p>
        </div>


        <!-- PARTIES -->

        <div class="section-card">
            <div class="section-title">
                <span class="section-icon">👥</span>
                Parties Involved
            </div>

            {list_to_html(parties)}
        </div>


        <!-- DATES -->

        <div class="section-card">
            <div class="section-title">
                <span class="section-icon">📅</span>
                Important Dates
            </div>

            <div class="date-grid">
                {dates_to_html(dates)}
            </div>
        </div>


        <!-- CONDITIONS -->

        <div class="section-card">
            <div class="section-title">
                <span class="section-icon">📌</span>
                Key Conditions
            </div>

            {list_to_html(conditions)}
        </div>


        <!-- CONSEQUENCES -->

        <div class="section-card warning-card">
            <div class="section-title">
                <span class="section-icon">⚠️</span>
                What Happens If You Ignore It?
            </div>

            <p>
                {consequences}
            </p>
        </div>


        <!-- RIGHTS -->

        <div class="section-card">
            <div class="section-title">
                <span class="section-icon">⚖️</span>
                Your Rights
            </div>

            {list_to_html(rights)}
        </div>


        <!-- NEXT STEPS -->

        <div class="section-card">
            <div class="section-title">
                <span class="section-icon">✅</span>
                Suggested Next Steps
            </div>

            {list_to_html(next_steps)}
        </div>

        <div class="disclaimer">
            <strong>Important:</strong>
            LegalEase provides an AI-generated explanation
            for educational and informational purposes.
            It is not a substitute for advice from a
            qualified legal professional.
        </div>

    </div>
    """


# ============================================================
# TRANSLATION
# ============================================================

def translate_full_document(
    text,
    detected_language,
    target_language
):

    if not text.strip():
        return ""

    if target_language == "Marathi":

        if detected_language == "Marathi":
            return text

        return english_to_marathi(text)

    if target_language == "English":

        if detected_language == "English":
            return text

        return marathi_to_english(text)

    return text


# ============================================================
# MAIN PROCESSING
# ============================================================

def process_document(
    pdf_file,
    target_language
):

    if pdf_file is None:

        return (
            "<div class='error-card'>"
            "Please upload a PDF document."
            "</div>",
            "",
            "",
            "",
        )

    try:

        text = extract_text_from_pdf(
            pdf_file
        )

        text = safe_text(text)

    except Exception as e:

        return (
            f"""
            <div class="error-card">
                <h3>Could not read the PDF</h3>
                <p>{escape(str(e))}</p>
            </div>
            """,
            "",
            "",
            "",
        )

    if not is_text_usable(text):

        return (
            """
            <div class="error-card">
                <h3>Unreadable PDF</h3>
                <p>
                    The PDF does not contain enough readable
                    text. It may be a scanned/image-only PDF.
                </p>
            </div>
            """,
            "",
            "",
            "",
        )

    # --------------------------------------------------------
    # LANGUAGE DETECTION
    # --------------------------------------------------------

    detected_language = detect_language(
        text
    )

    # --------------------------------------------------------
    # DOCUMENT CLASSIFICATION
    # --------------------------------------------------------

    doc_type = classify_document(
        text
    )

    doc_label = get_document_label(
        doc_type
    )

    # --------------------------------------------------------
    # TRANSLATION
    # --------------------------------------------------------

    try:

        translated_document = (
            translate_full_document(
                text,
                detected_language,
                target_language
            )
        )

    except Exception as e:

        return (
            f"""
            <div class="error-card">
                <h3>Translation failed</h3>
                <p>{escape(str(e))}</p>
            </div>
            """,
            "",
            detected_language,
            doc_label,
        )

    # --------------------------------------------------------
    # AI ANALYSIS
    # --------------------------------------------------------

    try:

        analysis = analyse_document(
            text,
            doc_type,
            doc_label
        )

    except Exception as e:

        return (
            f"""
            <div class="error-card">
                <h3>AI analysis failed</h3>
                <p>{escape(str(e))}</p>
            </div>
            """,
            translated_document,
            detected_language,
            doc_label,
        )

    # --------------------------------------------------------
    # TRANSLATE ANALYSIS TO MARATHI WHEN REQUESTED
    # --------------------------------------------------------

    if target_language == "Marathi":

        try:

            summary = analysis.get(
                "simple_summary",
                ""
            )

            if (
                detected_language == "English"
                and summary
            ):

                analysis["simple_summary"] = (
                    english_to_marathi(
                        summary
                    )
                )

            conditions = analysis.get(
                "key_conditions",
                []
            )

            if (
                detected_language == "English"
                and conditions
            ):

                analysis["key_conditions"] = [
                    english_to_marathi(
                        item
                    )
                    for item in conditions
                ]

            consequences = analysis.get(
                "what_happens_if_ignored",
                ""
            )

            if (
                detected_language == "English"
                and consequences
            ):

                analysis[
                    "what_happens_if_ignored"
                ] = english_to_marathi(
                    consequences
                )

            rights = analysis.get(
                "your_rights",
                []
            )

            if (
                detected_language == "English"
                and rights
            ):

                analysis["your_rights"] = [
                    english_to_marathi(
                        item
                    )
                    for item in rights
                ]

            next_steps = analysis.get(
                "next_steps",
                []
            )

            if (
                detected_language == "English"
                and next_steps
            ):

                analysis["next_steps"] = [
                    english_to_marathi(
                        item
                    )
                    for item in next_steps
                ]

            urgency_reason = analysis.get(
                "urgency_reason",
                ""
            )

            if (
                detected_language == "English"
                and urgency_reason
            ):

                analysis[
                    "urgency_reason"
                ] = english_to_marathi(
                    urgency_reason
                )

        except Exception:
            # Keep original English analysis if
            # optional analysis translation fails.
            pass

    # --------------------------------------------------------
    # FORMAT RESULT
    # --------------------------------------------------------

    html_output = format_analysis_html(
        analysis,
        doc_label,
        detected_language
    )

    status = (
        f"✓ Document processed successfully  |  "
        f"{doc_label}  |  "
        f"{detected_language} → {target_language}"
    )

    return (
        html_output,
        translated_document,
        detected_language,
        status,
    )


# ============================================================
# CSS
# ============================================================

CSS = """
* {
    box-sizing: border-box;
}

body {
    background: #f5f7fb !important;
}

.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
}

#hero {
    text-align: center;
    padding: 35px 20px 20px;
}

#hero h1 {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 5px;
    color: #172033;
}

#hero p {
    font-size: 17px;
    color: #697386;
}

.upload-box {
    border: 2px dashed #c9d1df !important;
    border-radius: 16px !important;
    background: white !important;
}

.action-row {
    margin-top: 12px;
}

#process-btn {
    border-radius: 10px !important;
    font-weight: 700 !important;
}

.section-card {
    background: white;
    border: 1px solid #e3e7ee;
    border-radius: 14px;
    padding: 22px;
    margin: 14px 0;
}

.section-title {
    font-size: 19px;
    font-weight: 750;
    color: #172033;
    margin-bottom: 14px;
}

.section-icon {
    margin-right: 7px;
}

.summary-text {
    font-size: 17px;
    line-height: 1.75;
    color: #374151;
}

.section-card ul {
    margin-top: 5px;
    padding-left: 24px;
}

.section-card li {
    margin-bottom: 9px;
    line-height: 1.6;
    color: #374151;
}

.document-header {
    display: flex;
    justify-content: space-between;
    gap: 25px;
    background: white;
    border: 1px solid #e3e7ee;
    border-radius: 14px;
    padding: 25px;
    margin-bottom: 14px;
}

.document-header h2 {
    margin: 4px 0;
    color: #172033;
}

.eyebrow {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.2px;
    color: #718096;
}

.detected {
    color: #718096;
}

.urgency {
    min-width: 190px;
    padding: 15px;
    border: 2px solid;
    border-radius: 12px;
}

.urgency-label {
    font-size: 11px;
    font-weight: 800;
    color: #718096;
}

.urgency-value {
    font-size: 20px;
    font-weight: 800;
    margin-top: 3px;
}

.urgency-reason {
    margin-top: 8px;
    font-size: 13px;
    color: #667085;
    line-height: 1.4;
}

.date-grid {
    display: grid;
    grid-template-columns: repeat(
        auto-fit,
        minmax(210px, 1fr)
    );
    gap: 12px;
}

.date-card {
    background: #f8fafc;
    border: 1px solid #e4e8ef;
    border-radius: 10px;
    padding: 15px;
}

.date-label {
    font-size: 13px;
    font-weight: 700;
    color: #667085;
}

.date-value {
    font-size: 18px;
    font-weight: 800;
    margin-top: 4px;
    color: #172033;
}

.date-info {
    margin-top: 7px;
    font-size: 13px;
    color: #667085;
    line-height: 1.4;
}

.warning-card {
    border-left: 5px solid #f59e0b;
}

.disclaimer {
    margin-top: 18px;
    padding: 16px;
    border-radius: 10px;
    background: #fff8e8;
    color: #6b5a28;
    font-size: 13px;
    line-height: 1.6;
}

.error-card {
    background: #fff1f1;
    border: 1px solid #f1b8b8;
    border-radius: 12px;
    padding: 20px;
    color: #8b1e1e;
    margin: 10px 0;
}

.muted {
    color: #8a94a6;
    font-style: italic;
}

.translation-box textarea {
    font-size: 16px !important;
    line-height: 1.7 !important;
}

footer {
    text-align: center;
    color: #8a94a6;
    padding: 25px;
}

@media (max-width: 700px) {

    .document-header {
        flex-direction: column;
    }

    .urgency {
        min-width: auto;
    }

    #hero h1 {
        font-size: 32px;
    }
}
"""


# ============================================================
# GRADIO APP
# ============================================================

with gr.Blocks(
    title=APP_TITLE,
    css=CSS
) as app:

    # --------------------------------------------------------
    # HERO
    # --------------------------------------------------------

    gr.HTML(
        """
        <div id="hero">
            <h1>LegalEase</h1>
            <p>
                Understand legal documents in simple language.
                Translate, summarize and identify important information.
            </p>
        </div>
        """
    )

    # --------------------------------------------------------
    # UPLOAD SECTION
    # --------------------------------------------------------

    with gr.Row():

        with gr.Column(scale=2):

            pdf_input = gr.File(
                label="Upload Legal Document",
                file_types=[".pdf"],
                type="filepath",
                elem_classes=["upload-box"]
            )

        with gr.Column(scale=1):

            target_language = gr.Dropdown(
                choices=[
                    "Marathi",
                    "English"
                ],
                value="Marathi",
                label="Translate Document To"
            )

            process_button = gr.Button(
                "Process Document",
                variant="primary",
                elem_id="process-btn"
            )

    status_text = gr.Markdown(
        "Upload a PDF to begin."
    )

    # --------------------------------------------------------
    # DOCUMENT INFORMATION
    # --------------------------------------------------------

    detected_language = gr.Textbox(
        label="Detected Source Language",
        interactive=False
    )

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    analysis_output = gr.HTML(
        label="Legal Analysis"
    )

    # --------------------------------------------------------
    # FULL TRANSLATION
    # --------------------------------------------------------

    gr.Markdown(
        "## 📄 Full Translated Document"
    )

    translated_document = gr.Textbox(
        label="Complete Translation",
        lines=25,
        show_copy_button=True,
        interactive=False,
        elem_classes=["translation-box"]
    )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    gr.HTML(
        """
        <footer>
            LegalEase · AI-assisted legal document understanding
        </footer>
        """
    )

    # --------------------------------------------------------
    # EVENT
    # --------------------------------------------------------

    process_button.click(
        fn=process_document,
        inputs=[
            pdf_input,
            target_language
        ],
        outputs=[
            analysis_output,
            translated_document,
            detected_language,
            status_text,
        ]
    )


# ============================================================
# LAUNCH
# ============================================================

if __name__ == "__main__":

    app.launch(
        share=False,
        show_api=False
    )
