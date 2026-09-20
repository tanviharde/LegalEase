import os
import sys
import re
import torch

from transformers import AutoModelForSeq2SeqLM
from IndicTransToolkit.processor import IndicProcessor


# ============================================================
# DEVICE
# ============================================================

if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")

print(f"Translation device: {DEVICE}")


# ============================================================
# LOCAL INDIC TRANS CODE
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CUSTOM_CODE_DIR = os.path.join(BASE_DIR, "custom_code")

if CUSTOM_CODE_DIR not in sys.path:
    sys.path.insert(0, CUSTOM_CODE_DIR)

from tokenization_indictrans import IndicTransTokenizer


# ============================================================
# MODEL PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MR_EN_MODEL = os.path.join(BASE_DIR, "models")

EN_MR_MODEL = os.path.join(
    BASE_DIR,
    "models",
    "legalese_en_mr"
)


# ============================================================
# MODEL CACHE
# ============================================================

_models = {}
_tokenizers = {}


# ============================================================
# LOAD MODEL
# ============================================================

def load_translation_model(model_dir):

    if model_dir in _models:
        return _models[model_dir], _tokenizers[model_dir]

    print(f"\nLoading translation model:")
    print(model_dir)

    src_vocab = os.path.join(model_dir, "dict.SRC.json")
    tgt_vocab = os.path.join(model_dir, "dict.TGT.json")
    src_spm = os.path.join(model_dir, "model.SRC")
    tgt_spm = os.path.join(model_dir, "model.TGT")

    for file in [src_vocab, tgt_vocab, src_spm, tgt_spm]:
        if not os.path.exists(file):
            raise FileNotFoundError(
                f"Required tokenizer file not found:\n{file}"
            )

    print("Loading local tokenizer files...")

    tokenizer = IndicTransTokenizer(
        src_vocab_fp=src_vocab,
        tgt_vocab_fp=tgt_vocab,
        src_spm_fp=src_spm,
        tgt_spm_fp=tgt_spm,
    )

    print("Tokenizer loaded successfully.")

    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_dir,
        trust_remote_code=True,
        local_files_only=True,
    )

    model = model.to(DEVICE)
    model.eval()

    print("Fine-tuned LegalEase model loaded successfully.")

    _models[model_dir] = model
    _tokenizers[model_dir] = tokenizer

    return model, tokenizer


# ============================================================
# SINGLE CHUNK TRANSLATION
# ============================================================

def translate_chunk(
    text,
    src_lang,
    tgt_lang,
    model_dir,
):

    if not text or not text.strip():
        return ""

    model, tokenizer = load_translation_model(model_dir)

    processor = IndicProcessor(inference=True)

    batch = processor.preprocess_batch(
        [text],
        src_lang=src_lang,
        tgt_lang=tgt_lang,
    )

    inputs = tokenizer(
        batch,
        padding="longest",
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(DEVICE)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        generated_tokens = model.generate(
            **inputs,
            use_cache=True,
            min_length=0,
            max_length=256,
            num_beams=5,
            num_return_sequences=1,
        )

    generated_tokens = generated_tokens.cpu().tolist()

    translations = tokenizer.batch_decode(
        generated_tokens,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )

    # IndicTrans2 may return language tags in the decoded output.
    # Remove the source/target tags before post-processing.
    for i, translation in enumerate(translations):
        translation = re.sub(
            r"^(?:eng_Latn|mar_Deva)\s+(?:eng_Latn|mar_Deva)\s*",
            "",
            translation.strip(),
        )
        translations[i] = translation

    translations = processor.postprocess_batch(
        translations,
        lang=tgt_lang,
    )

    return translations[0]


# ============================================================
# SPLIT DOCUMENT
# ============================================================

def split_text(text, max_chars=900):

    text = text.strip()

    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    chunks = []
    current = ""

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if len(current) + len(paragraph) + 2 <= max_chars:

            current += (
                "\n\n" if current else ""
            ) + paragraph

            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= max_chars:

            current = paragraph

            continue

        sentences = re.split(
            r"(?<=[.!?।])\s+",
            paragraph
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            if len(current) + len(sentence) + 1 <= max_chars:

                current += (
                    " " if current else ""
                ) + sentence

            else:

                if current:
                    chunks.append(current)

                if len(sentence) > max_chars:

                    for i in range(
                        0,
                        len(sentence),
                        max_chars
                    ):

                        chunks.append(
                            sentence[
                                i:i + max_chars
                            ]
                        )

                    current = ""

                else:

                    current = sentence

    if current:
        chunks.append(current)

    return chunks


# ============================================================
# FULL DOCUMENT TRANSLATION
# ============================================================

def translate_document(
    text,
    src_lang,
    tgt_lang,
    model_dir,
):

    if not text or not text.strip():
        return ""

    chunks = split_text(text)

    print(
        f"\nTranslating document: "
        f"{len(chunks)} chunk(s)"
    )

    translated_chunks = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        print(
            f"Translating chunk "
            f"{index}/{len(chunks)}..."
        )

        translated = translate_chunk(
            text=chunk,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            model_dir=model_dir,
        )

        translated_chunks.append(
            translated
        )

    return "\n\n".join(
        translated_chunks
    )


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_language(text):

    if not text or not text.strip():
        return "English"

    devanagari_count = sum(
        1
        for char in text
        if "\u0900" <= char <= "\u097F"
    )

    latin_count = sum(
        1
        for char in text
        if "a" <= char.lower() <= "z"
    )

    if devanagari_count > latin_count:
        return "Marathi"

    return "English"


# ============================================================
# ENGLISH → MARATHI
# ============================================================

def english_to_marathi(text):

    return translate_document(
        text=text,
        src_lang="eng_Latn",
        tgt_lang="mar_Deva",
        model_dir=EN_MR_MODEL,
    )


# ============================================================
# MARATHI → ENGLISH
# ============================================================

def marathi_to_english(text):

    return translate_document(
        text=text,
        src_lang="mar_Deva",
        tgt_lang="eng_Latn",
        model_dir=MR_EN_MODEL,
    )
