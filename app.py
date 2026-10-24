import json
import os
import re

import joblib
import numpy as np
from flask import Flask, jsonify, render_template, request
from sentence_transformers import SentenceTransformer

from nlp_utils import (
    clean_for_model,
    extract_questions,
    read_uploaded_file,
    strip_leading_marker,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIFIER_PATH = os.path.join(BASE_DIR, "model", "bloom_multilingual.joblib")  # made by train_multilingual.py
JSON_PATH = os.path.join(BASE_DIR, "data", "co_mapping.json")

# CO / subject matching thresholds (cosine similarity, 0..1). Tune these on real papers:
# raise them if unrelated questions get matched, lower them if too many show "Not Matched".
MIN_SUBJECT_SCORE = 0.30
MIN_CO_SCORE = 0.30
KEYWORD_BOOST = 0.20  # extra score when an exact (English) keyword appears in the question

app = Flask(__name__)

# ---------------------------------------------------------------- load models
bundle = joblib.load(CLASSIFIER_PATH)
clf = bundle["clf"]
embedder = SentenceTransformer(bundle["embed_model"])  # downloads once from Hugging Face, then cached

with open(JSON_PATH, encoding="utf-8") as f:
    config = json.load(f)


def embed(texts):
    """L2-normalised embeddings, so a dot product == cosine similarity."""
    return embedder.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)


# ---------------------------------------------------------------- CO index
def build_index(cfg):
    """Pre-embed every subject keyword and every CO name/keyword once at startup."""
    index = {}
    for subject, sdata in cfg.get("subjects", {}).items():
        kws = [k for k in sdata.get("keywords", []) if str(k).strip()]
        cos = {}
        for co_key, co in cfg.get("co_mappings", {}).get(subject, {}).items():
            texts = [t for t in [co.get("name", "")] + co.get("keywords", []) if str(t).strip()]
            if texts:
                cos[co_key] = {"name": co.get("name", ""), "texts": texts, "emb": embed(texts)}
        index[subject] = {"texts": kws, "emb": embed(kws) if kws else None, "cos": cos}
    return index


INDEX = build_index(config)


def keyword_hit(kw, text):
    kw = str(kw).lower().strip()
    if not kw:
        return False
    if kw.isascii():  # whole-word match so "tree" doesn't fire on "street"
        return re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", text) is not None
    return kw in text


def score(q_emb, q_text, emb, texts):
    if emb is None or len(texts) == 0:
        return 0.0
    best = float(np.max(emb @ q_emb))
    if any(keyword_hit(t, q_text) for t in texts):
        best += KEYWORD_BOOST
    return best


def match_co(q_emb, q_text):
    """Pick the best subject, then the best CO inside it. Never raises."""
    best_subject, best_score = None, 0.0
    for subject, s in INDEX.items():
        sc = score(q_emb, q_text, s["emb"], s["texts"])
        if sc > best_score:
            best_subject, best_score = subject, sc
    if best_subject is None or best_score < MIN_SUBJECT_SCORE:
        return "CO-NA", "Not Matched"

    best_co, best_co_score, best_co_name = None, 0.0, ""
    for co_key, co in INDEX[best_subject]["cos"].items():
        sc = score(q_emb, q_text, co["emb"], co["texts"])
        if sc > best_co_score:
            best_co, best_co_score, best_co_name = co_key, sc, co["name"]
    if best_co is None or best_co_score < MIN_CO_SCORE:
        return "CO-NA", "Not Matched"
    return best_co, best_co_name


def analyze_questions(questions):
    """Returns [(bloom_level, co_id, co_name), ...] – works for English, Hindi and Marathi."""
    if not questions:
        return []
    cleaned = [clean_for_model(strip_leading_marker(q)) for q in questions]
    embs = embed(cleaned)
    blooms = clf.predict(embs)
    results = []
    for q_text, q_emb, bloom in zip(cleaned, embs, blooms):
        co_id, co_name = match_co(q_emb, q_text)
        results.append((str(bloom), co_id, co_name))
    return results


# ---------------------------------------------------------------- routes
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        text = read_uploaded_file(file)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        app.logger.exception("Could not read uploaded file")
        return jsonify({"error": "Could not read this file. Try a different PDF/DOCX/TXT."}), 400

    questions = extract_questions(text)
    results = analyze_questions(questions)
    predictions = [r[0] for r in results]
    co_mapping = [{"co_code": r[1], "co_name": r[2]} for r in results]

    dominant_bloom = max(set(predictions), key=predictions.count) if predictions else "Remember"
    return jsonify({
        "status": "success",
        "questions": questions,
        "predictions": predictions,
        "co_mapping": co_mapping,
        "total_questions": len(questions),
        "overall_difficulty": dominant_bloom,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)