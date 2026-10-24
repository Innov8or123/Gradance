"""Shared text helpers for Gradance (English / Hindi / Marathi).

Used by both app.py and train_multilingual.py so training and inference
clean text in exactly the same way.
"""
import io
import re
import unicodedata

import regex  # pip install regex  (needed: Python's built-in `re` \w drops Devanagari vowel signs)

# Multilingual sentence-embedding model (supports English, Hindi, Marathi).
# Alternatives: "sentence-transformers/LaBSE" (heavier), "intfloat/multilingual-e5-base".
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


# --------------------------------------------------------------------------
# Cleaning
# --------------------------------------------------------------------------
def normalize_text(text):
    """NFC-normalise, turn Devanagari digits into ASCII digits, drop invisible junk."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_DEVANAGARI_DIGITS)
    # zero-width space / BOM / soft hyphen are noise; ZWJ/ZWNJ are kept (they matter in Devanagari)
    for ch in ("​", "﻿", "­"):
        text = text.replace(ch, "")
    return text


# Keep letters, combining marks (Devanagari vowel signs!), numbers, whitespace, ZWJ/ZWNJ.
_PUNCT = regex.compile(r"[^\p{L}\p{M}\p{N}\s‌‍]")

# "Q1.", "Q.1", "प्र. 1", "प्रश्न 1:", "a)", "(b)", "अ)", "OR", "किंवा", "अथवा" at the start of a question
_LEAD_MARKER = regex.compile(
    r"^\s*(?:(?:OR|किंवा|अथवा)\s+)?"
    r"(?:(?:Q|प्र(?:श्न)?)\.?\s*\d+\s*[\.:\)]?\s*)?"
    r"(?:\(?\s*(?:[a-g]|[अबकडखगघ])\s*\)\s*)?",
    regex.IGNORECASE,
)


def strip_leading_marker(text):
    """Remove numbering like 'Q1. a)' so it doesn't pollute the model input."""
    return _LEAD_MARKER.sub("", text, count=1).strip()


def clean_for_model(text):
    """Lowercase + strip punctuation WITHOUT destroying Devanagari vowel signs."""
    text = normalize_text(text).lower()
    text = _PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Question splitting
# --------------------------------------------------------------------------
_SEP = "|||"
_IGNORE_SUBSTR = [
    "Class / SEM:", "Subject:", "Max. Marks:", "Duration:", "Note:",
    "Figures to the right", "Internal Assessment",
]
# Header labels in Hindi / Marathi (always followed by a colon)
_IGNORE_DEV = regex.compile(
    r"(?:विषय|कक्षा|वर्ग|सत्र|पूर्णांक|कमाल गुण|एकूण गुण|गुण|वेळ|समय|अवधि|दिनांक|तारीख|सूचना|निर्देश|टीप|टिप)\s*[:：]"
)
# "Solve any two questions" style instructions (only dropped when the chunk is short)
_INSTR_DEV = regex.compile(r"प्रश्न\S*\s+(?:के\s+)?(?:उत्तर|सोडवा|हल)")


def extract_questions(text):
    if not text:
        return []
    text = normalize_text(text).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # 1) question numbers: Q1 / Q.1 / प्र.1 / प्रश्न 1
    text = re.sub(r"(?<!\w)((?:Q|प्र(?:श्न)?)\.?\s*\d+[\.:]?)", _SEP + r"\1", text)
    # 2) sub-questions: a) (b) A) B) अ) ब) क) ...  (not f(a) -> lookbehind excludes word chars and '(')
    text = re.sub(r"(?<![\w(])(\(\s*(?:[a-gA-B]|[अबकडखगघ])\s*\)|(?:[a-gA-B]|[अबकडखगघ])\s*\))", _SEP + r"\1", text)
    # 3) a new sentence after '?' or the Devanagari danda '।' / '॥'
    #    (original only handled '?' followed by an UPPERCASE letter; Devanagari has no case)
    text = re.sub(r"([?।॥]\s+)(?=[A-Zऀ-ॿ])", r"\1" + _SEP, text)

    final_questions = []
    for chunk in text.split(_SEP):
        q = chunk.strip()
        # trailing "OR" / "किंवा" / "अथवा" belongs to the separator, not the question
        q = re.sub(r"(?:\s+(?:OR|किंवा|अथवा))+\s*$", "", q).strip()

        if not q or len(q) < 10:
            continue
        if not regex.search(r"\p{L}", q):  # e.g. "[10]" or "(5 marks)"-only chunks
            continue
        if any(k in q for k in _IGNORE_SUBSTR) or _IGNORE_DEV.search(q):
            continue
        short = len(q.split()) < 15
        if short and (any(p in q.lower() for p in ("attempt any", "solve any")) or _INSTR_DEV.search(q)):
            continue
        final_questions.append(q)
    return final_questions


# --------------------------------------------------------------------------
# File reading
# --------------------------------------------------------------------------
def _ocr_page(page):
    """OCR one PDF page (scanned papers). Needs: pip install pytesseract pillow
    plus the Tesseract binary with the 'hin' and 'mar' language packs. Returns '' if unavailable."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for lang in ("hin+mar+eng", "eng"):
        try:
            return pytesseract.image_to_string(img, lang=lang)
        except Exception:
            continue
    return ""


def _read_pdf(data):
    try:
        import pymupdf  # PyMuPDF – much better Devanagari extraction than PyPDF2
    except ImportError:  # older PyMuPDF versions
        import fitz as pymupdf

    pages = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text") or ""
            if len(text.strip()) < 20:  # looks like a scanned page -> try OCR
                text = _ocr_page(page) or text
            pages.append(text)
    return "\n".join(pages)


def _read_docx(data):
    import mammoth

    return mammoth.extract_raw_text(io.BytesIO(data)).value


def _decode_text(data):
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def read_uploaded_file(file):
    """`file` is a werkzeug FileStorage. Returns plain text."""
    name = (file.filename or "").lower()
    data = file.read()
    if name.endswith(".pdf"):
        return _read_pdf(data)
    if name.endswith(".docx"):
        return _read_docx(data)
    if name.endswith(".doc"):
        raise ValueError("Old .doc files are not supported. Please re-save the file as .docx or PDF.")
    return _decode_text(data)