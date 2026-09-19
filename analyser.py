import re
from datetime import datetime

from translator import (
    detect_language,
    english_to_marathi,
    marathi_to_english,
)


# =========================================================
# GENERAL HELPERS
# =========================================================

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_sentences(text: str):
    """
    Basic sentence splitting for English and Marathi.
    """
    text = clean_text(text)

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?।])\s+|\n+",
        text,
    )

    return [
        s.strip()
        for s in sentences
        if s.strip()
    ]


def translate_to_target(
    text: str,
    source_language: str,
    target_language: str,
) -> str:
    """
    Translate text only when the source and target differ.
    """

    if not text:
        return ""

    source = source_language.lower()
    target = target_language.lower()

    if "marathi" in source and "marathi" in target:
        return text

    if "english" in source and "english" in target:
        return text

    if "marathi" in source and "english" in target:
        return marathi_to_english(text)

    if "english" in source and "marathi" in target:
        return english_to_marathi(text)

    # Fallback: detect again
    detected = detect_language(text).lower()

    if "marathi" in detected and "english" in target:
        return marathi_to_english(text)

    if "english" in detected and "marathi" in target:
        return english_to_marathi(text)

    return text


def bullet_lines(items):
    return "\n".join(
        f"• {item}"
        for item in items
        if item
    )


# =========================================================
# EXTRACTIVE SUMMARY
# =========================================================

def sentence_score(sentence: str) -> int:
    lower = sentence.lower()

    score = 0

    for keyword, weight in [
        (k, v if isinstance(v, int) else 1)
        for k, v in (
            [
                ("agreement", 4),
                ("rent", 4),
                ("lease", 4),
                ("tenant", 3),
                ("landlord", 3),
                ("licensee", 3),
                ("licensor", 3),
                ("buyer", 3),
                ("seller", 3),
                ("purchaser", 3),
                ("plaintiff", 3),
                ("defendant", 3),
                ("court", 3),
                ("notice", 3),
                ("payment", 3),
                ("deposit", 3),
                ("obligation", 3),
                ("shall", 2),
                ("must", 2),
                ("termination", 3),
                ("property", 2),
                ("section", 2),
                ("करार", 4),
                ("भाडे", 4),
                ("भाडेकरू", 3),
                ("मालक", 3),
                ("परवानाधारक", 3),
                ("परवानादाता", 3),
                ("खरेदीदार", 3),
                ("विक्रेता", 3),
                ("न्यायालय", 3),
                ("नोटीस", 3),
                ("रक्कम", 2),
                ("ठेव", 3),
                ("अट", 2),
                ("जबाबदारी", 3),
                ("समाप्ती", 3),
                ("मालमत्ता", 2),
            ]
        )
    ]:
        if keyword in lower:
            score += weight

    # Dates
    if re.search(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        sentence,
    ):
        score += 3

    # Currency / money
    if re.search(
        r"(₹|rs\.?|रु\.?|रुपये)\s*[\d,]+",
        lower,
    ):
        score += 3

    # Legal section references
    if re.search(
        r"\bsection\s+\d+",
        lower,
    ) or re.search(
        r"\bकलम\s+\d+",
        lower,
    ):
        score += 3

    # Reasonable sentence length
    words = len(sentence.split())

    if 6 <= words <= 45:
        score += 1

    return score


def generate_summary(
    text: str,
    max_sentences: int = 8,
) -> str:

    sentences = split_sentences(text)

    if not sentences:
        return ""

    scored = []

    for index, sentence in enumerate(sentences):

        score = sentence_score(sentence)

        scored.append(
            (
                score,
                index,
                sentence,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    selected = scored[:max_sentences]

    # Restore document order
    selected.sort(
        key=lambda item: item[1]
    )

    return " ".join(
        sentence
        for _, _, sentence in selected
    )


# =========================================================
# KEY INFORMATION EXTRACTION
# =========================================================

def extract_dates(text: str):
    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+\d{4}\b",
        r"\b\d{1,2}\s+"
        r"(?:जानेवारी|फेब्रुवारी|मार्च|एप्रिल|मे|जून|जुलै|"
        r"ऑगस्ट|सप्टेंबर|ऑक्टोबर|नोव्हेंबर|डिसेंबर)"
        r"\s+\d{4}\b",
    ]

    results = []

    for pattern in patterns:
        results.extend(
            re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    return list(dict.fromkeys(results))


def extract_amounts(text: str):
    patterns = [
        r"(?:₹|Rs\.?|INR|रु\.?|रुपये)\s*[\d,]+(?:\.\d+)?",
        r"[\d,]+(?:\.\d+)?\s*(?:rupees|रुपये)",
    ]

    results = []

    for pattern in patterns:
        results.extend(
            re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    return list(dict.fromkeys(results))


def extract_emails(text: str):
    return list(
        dict.fromkeys(
            re.findall(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
                text,
            )
        )
    )


def extract_phone_numbers(text: str):
    return list(
        dict.fromkeys(
            re.findall(
                r"(?:\+91[\s-]?)?[6-9]\d{9}\b",
                text,
            )
        )
    )


def extract_parties(text: str):
    parties = []

    patterns = [
        r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:\.|,|\n)",
        r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:\s+hereinafter|\s+collectively)",
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in matches:

            if isinstance(match, tuple):

                for item in match:
                    item = clean_text(item)

                    if item and len(item) < 150:
                        parties.append(item)

    # Role-based names
    role_patterns = [
        r"(?:Landlord|Licensor|Seller|Buyer|Tenant|Licensee)"
        r"\s*[:\-]\s*([A-Z][A-Za-z .'-]{2,80})",
        r"(?:मालक|घरमालक|परवानादाता|विक्रेता|खरेदीदार|भाडेकरू|परवानाधारक)"
        r"\s*[:\-]\s*([^\n,]{2,80})",
    ]

    for pattern in role_patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for item in matches:

            item = clean_text(item)

            if item:
                parties.append(item)

    return list(dict.fromkeys(parties))


def extract_key_information(text: str):
    dates = extract_dates(text)
    amounts = extract_amounts(text)
    emails = extract_emails(text)
    phones = extract_phone_numbers(text)
    parties = extract_parties(text)

    obligations = []
    clauses = []

    sentences = split_sentences(text)

    obligation_keywords = [
        "shall",
        "must",
        "required",
        "obligation",
        "pay",
        "भरावे",
        "करणे आवश्यक",
        "करावे",
        "जबाबदारी",
    ]

    clause_keywords = [
        "termination",
        "notice",
        "deposit",
        "rent",
        "lease",
        "agreement",
        "section",
        "अट",
        "नोटीस",
        "ठेव",
        "भाडे",
        "करार",
        "समाप्ती",
    ]

    for sentence in sentences:

        lower = sentence.lower()

        if any(
            keyword.lower() in lower
            for keyword in obligation_keywords
        ):
            obligations.append(sentence)

        if any(
            keyword.lower() in lower
            for keyword in clause_keywords
        ):
            clauses.append(sentence)

    # Limit repeated text
    obligations = list(
        dict.fromkeys(obligations)
    )[:8]

    clauses = list(
        dict.fromkeys(clauses)
    )[:10]

    return {
        "parties": parties[:10],
        "dates": dates[:10],
        "amounts": amounts[:10],
        "emails": emails[:10],
        "phone_numbers": phones[:10],
        "obligations": obligations,
        "clauses": clauses,
    }


# =========================================================
# DOCUMENT SIMPLIFICATION
# =========================================================

ENGLISH_REPLACEMENTS = [
    (
        r"\bprior to\b",
        "before",
    ),
    (
        r"\bsubsequent to\b",
        "after",
    ),
    (
        r"\bin the event that\b",
        "if",
    ),
    (
        r"\bnotwithstanding the foregoing\b",
        "despite the above",
    ),
    (
        r"\bhereinafter referred to as\b",
        "called",
    ),
    (
        r"\bshall be entitled to\b",
        "can",
    ),
    (
        r"\bis required to\b",
        "must",
    ),
    (
        r"\bcommence\b",
        "start",
    ),
    (
        r"\bterminate\b",
        "end",
    ),
    (
        r"\bremuneration\b",
        "payment",
    ),
    (
        r"\breside\b",
        "live",
    ),
    (
        r"\bendeavour\b",
        "try",
    ),
]


MARATHI_REPLACEMENTS = [
    (
        "सदर",
        "",
    ),
    (
        "यापुढे",
        "पुढे",
    ),
    (
        "सदरहू",
        "",
    ),
    (
        "अनुषंगाने",
        "संबंधित",
    ),
    (
        "करावयाचे",
        "करायचे",
    ),
    (
        "आवश्यक आहे",
        "करावे लागेल",
    ),
]


def simplify_text(text: str) -> str:

    source_language = detect_language(
        text
    )

    result = text

    if "english" in source_language.lower():

        for pattern, replacement in ENGLISH_REPLACEMENTS:

            result = re.sub(
                pattern,
                replacement,
                result,
                flags=re.IGNORECASE,
            )

    elif "marathi" in source_language.lower():

        for old, new in MARATHI_REPLACEMENTS:

            result = result.replace(
                old,
                new,
            )

    result = re.sub(
        r"[ ]{2,}",
        " ",
        result,
    )

    result = re.sub(
        r"\n{3,}",
        "\n\n",
        result,
    )

    return result.strip()


# =========================================================
# LEGAL ANALYSIS
# =========================================================

def identify_urgency(
    text: str,
    dates,
):
    lower = text.lower()

    urgent_terms = [
        "hearing",
        "appear before",
        "within",
        "deadline",
        "last date",
        "termination",
        "notice",
        "summons",
        "arrest",
        "hearing date",
        "तातडी",
        "मुदत",
        "नोटीस",
        "समाप्ती",
        "अंतिम तारीख",
        "हजर",
    ]

    found = [
        term
        for term in urgent_terms
        if term.lower() in lower
    ]

    if found:
        return (
            "Potentially time-sensitive",
            found[:4],
        )

    if dates:
        return (
            "Contains important dates",
            dates[:4],
        )

    return (
        "No immediate deadline detected from the text",
        [],
    )


def build_legal_analysis(
    text: str,
    document_type: str,
):
    information = extract_key_information(
        text
    )

    summary = generate_summary(
        text,
        max_sentences=6,
    )

    urgency, urgency_evidence = identify_urgency(
        text,
        information["dates"],
    )

    return {
        "summary": summary,
        "parties": information["parties"],
        "dates": information["dates"],
        "amounts": information["amounts"],
        "obligations": information["obligations"],
        "clauses": information["clauses"],
        "urgency": urgency,
        "urgency_evidence": urgency_evidence,
        "document_type": document_type,
    }


# =========================================================
# OUTPUT FORMATTERS
# =========================================================

def format_key_information_output(
    information: dict,
    target_language: str,
):
    if target_language == "Marathi":

        labels = {
            "parties": "पक्षकार",
            "dates": "महत्त्वाच्या तारखा",
            "amounts": "महत्त्वाच्या रकमा",
            "emails": "ई-मेल",
            "phone_numbers": "फोन नंबर",
            "obligations": "मुख्य जबाबदाऱ्या",
            "clauses": "महत्त्वाच्या अटी / कलमे",
        }

    else:

        labels = {
            "parties": "Parties",
            "dates": "Important Dates",
            "amounts": "Important Amounts",
            "emails": "Email Addresses",
            "phone_numbers": "Phone Numbers",
            "obligations": "Key Obligations",
            "clauses": "Important Clauses",
        }

    blocks = []

    for key, label in labels.items():

        values = information.get(
            key,
            [],
        )

        if not values:
            continue

        if isinstance(values, list):

            body = bullet_lines(values)

        else:

            body = str(values)

        blocks.append(
            f"{label}\n{body}"
        )

    if not blocks:

        return (
            "No key information could be extracted."
            if target_language == "English"
            else
            "दस्तऐवजातून महत्त्वाची माहिती काढता आली नाही."
        )

    return "\n\n".join(blocks)


def format_legal_analysis_output(
    analysis: dict,
    target_language: str,
):
    if target_language == "Marathi":

        labels = {
            "document_type": "दस्तऐवजाचा प्रकार",
            "summary": "सोप्या भाषेतील सारांश",
            "parties": "पक्षकार",
            "dates": "महत्त्वाच्या तारखा",
            "amounts": "महत्त्वाच्या रकमा",
            "obligations": "मुख्य जबाबदाऱ्या",
            "clauses": "महत्त्वाच्या अटी / कलमे",
            "urgency": "तातडीची स्थिती",
        }

    else:

        labels = {
            "document_type": "Document Type",
            "summary": "Summary",
            "parties": "Parties",
            "dates": "Important Dates",
            "amounts": "Important Amounts",
            "obligations": "Key Obligations",
            "clauses": "Important Clauses",
            "urgency": "Urgency",
        }

    blocks = []


    document_type = analysis.get(
        "document_type",
        "unknown",
    )

    blocks.append(
        f"{labels['document_type']}\n{document_type}"
    )


    summary = analysis.get(
        "summary",
        "",
    )

    if summary:
        blocks.append(
            f"{labels['summary']}\n{summary}"
        )


    for key in [
        "parties",
        "dates",
        "amounts",
        "obligations",
        "clauses",
    ]:

        values = analysis.get(
            key,
            [],
        )

        if not values:
            continue

        blocks.append(
            f"{labels[key]}\n{bullet_lines(values)}"
        )


    blocks.append(
        f"{labels['urgency']}\n"
        f"{analysis.get('urgency', '')}"
    )


    note = (
        "टीप: हे दस्तऐवज समजून घेण्यासाठी तयार केलेले "
        "माहितीपर विश्लेषण आहे; हा कायदेशीर सल्ला नाही."
        if target_language == "Marathi"
        else
        "Note: This is informational document analysis "
        "and is not legal advice."
    )

    blocks.append(note)

    return "\n\n".join(blocks)


# =========================================================
# MAIN TASK FUNCTION
# =========================================================

def run_ai_task(
    text: str,
    task: str,
    target_language: str,
    document_type: str = "unknown",
) -> str:

    text = clean_text(text)

    if not text:
        raise ValueError(
            "No text available for analysis."
        )


    source_language = detect_language(
        text
    )


    # =====================================================
    # SUMMARY
    # =====================================================

    if task == "summarize":

        summary = generate_summary(
            text,
            max_sentences=8,
        )

        return translate_to_target(
            summary,
            source_language,
            target_language,
        )


    # =====================================================
    # KEY INFORMATION
    # =====================================================

    if task == "key_information":

        information = extract_key_information(
            text
        )

        output = format_key_information_output(
            information,
            source_language,
        )

        return translate_to_target(
            output,
            source_language,
            target_language,
        )


    # =====================================================
    # SIMPLIFY
    # =====================================================

    if task == "simplify":

        simplified = simplify_text(
            text
        )

        return translate_to_target(
            simplified,
            source_language,
            target_language,
        )


    # =====================================================
    # LEGAL ANALYSIS
    # =====================================================

    if task == "legal_analysis":

        analysis = build_legal_analysis(
            text,
            document_type,
        )

        output = format_legal_analysis_output(
            analysis,
            source_language,
        )

        return translate_to_target(
            output,
            source_language,
            target_language,
        )


    raise ValueError(
        f"Unsupported task: {task}"
    )


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

def analyse_document(
    text: str,
    document_type: str = "unknown",
):
    """
    Compatibility helper for the old LegalEase code.
    """

    return build_legal_analysis(
        text,
        document_type,
    )


def get_urgency_color(
    urgency: str,
):
    urgency_lower = urgency.lower()

    if "time-sensitive" in urgency_lower:
        return "#d97706"

    if "important" in urgency_lower:
        return "#2563eb"

    return "#16a34a"
