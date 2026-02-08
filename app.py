from flask import Flask, render_template, request, jsonify
import os
import json
import pandas as pd
import tensorflow as tf
import pickle
import PyPDF2
import re
import mammoth
import numpy as np

app = Flask(__name__)

# --- Load Models ---
MODEL_PATH = "model/bloom_model.h5"
VECTORIZER_PATH = "model/vectorizer.pkl"
LABEL_ENCODER_PATH = "model/label_encoder.pkl"
JSON_PATH = "data/co_mapping.json"

model = tf.keras.models.load_model(MODEL_PATH)
with open(VECTORIZER_PATH, 'rb') as f:
    vectorizer = pickle.load(f)
with open(LABEL_ENCODER_PATH, 'rb') as f:
    label_encoder = pickle.load(f)
with open(JSON_PATH, "r") as f:
    config = json.load(f)

def get_best_match(clean_q, items):
    if not items: return "N/A", 0
    matches = []
    for key, data in items.items():
        score = sum(kw.lower() in clean_q for kw in data.get('keywords', []))
        matches.append((key, score, data.get('name', '')))
    best_match = max(matches, key=lambda x: x[1], default=("N/A", 0, ""))
    return best_match if best_match[1] > 0 else ("CO-NA", 0, "Not Matched")

def get_notebook_analysis(question_text):
    clean_q = re.sub(r'[^\w\s]', '', question_text.lower())
    tfidf_q = vectorizer.transform([clean_q]).toarray()
    bloom_level = label_encoder.inverse_transform([np.argmax(model.predict(tfidf_q, verbose=0))])[0]
    subject_id, _ , _ = get_best_match(clean_q, config.get('subjects', {}))
    co_id, _, co_name = get_best_match(clean_q, config.get('co_mappings', {}).get(subject_id, {}))
    return bloom_level, co_id, co_name

# --- FIXED EXTRACTION LOGIC ---
def extract_questions(text):
    if not text: return []
    # Normalize whitespace
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    
    sep = "|||"
    # 1. Split on Main markers (Q.1, Q2)
    text = re.sub(r'(\bQ\.?\s*\d+[\.:]?)', sep + r'\1', text)
    # 2. Split on sub-markers a) to g) (prevents i, ii merge)
    text = re.sub(r'(\b[a-g]\s*\))', sep + r'\1', text)
    # 3. Split on A) and B) - including "OR A)" and "OR B)"
    text = re.sub(r'(\bOR\s+[AB]\s*\)|\b[AB]\s*\))', sep + r'\1', text)
    # 4. Split on start words "In" or "Any" if they follow punctuation
    text = re.sub(r'([\.?!]\s+)(In|Any)\b', r'\1' + sep + r'\2', text)
    # 5. Split after '?' if the next part is capitalized
    text = re.sub(r'(\?\s+)(?=[A-Z])', r'\1' + sep, text)

    chunks = text.split(sep)
    final_questions = []
    ignore = ["Class / SEM:", "Subject:", "Max. Marks:", "Duration:", "Note:", "Figures to the right", "Internal Assessment"]

    for chunk in chunks:
        q = chunk.strip()
        if not q or len(q) < 10 or any(k in q for k in ignore):
            continue
        # Check instructions: keep only if long
        if any(p in q.lower() for p in ["attempt any", "solve any"]) and len(q.split()) < 15:
            continue
        final_questions.append(q)
    return final_questions

@app.route('/')
def home(): return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files['file']
    if file.filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        text = " ".join(page.extract_text() or "" for page in reader.pages)
    elif file.filename.endswith((".docx", ".doc")):
        text = mammoth.extract_raw_text(file).value
    else:
        text = file.read().decode("utf-8")

    questions = extract_questions(text)
    predictions, co_mapping = [], []
    for q in questions:
        bloom, co_id, co_name = get_notebook_analysis(q)
        predictions.append(bloom)
        co_mapping.append({"co_code": co_id, "co_name": co_name})

    dominant_bloom = max(set(predictions), key=predictions.count) if predictions else "Remember"
    return jsonify({
        "status": "success",
        "questions": questions,
        "predictions": predictions,
        "co_mapping": co_mapping,
        "total_questions": len(questions),
        "overall_difficulty": dominant_bloom
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)