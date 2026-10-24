"""Train the multilingual Bloom's-taxonomy classifier.

Run from the project root:   python train_multilingual.py

Reads   data/blooms_taxonomy_dataset.csv                (English, required)
Optional data/augmented_hi_mr.csv                       (Hindi/Marathi training rows: Questions,Category)
Optional data/test_hi_mr.csv                            (hand-labelled Hindi/Marathi TEST rows: Questions,Category)
Writes  model/bloom_multilingual.joblib
"""
import os

import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from nlp_utils import EMBED_MODEL_NAME, clean_for_model

BASE = os.path.dirname(os.path.abspath(__file__))
EN_CSV = os.path.join(BASE, "data", "blooms_taxonomy_dataset.csv")
AUG_CSV = os.path.join(BASE, "data", "augmented_hi_mr.csv")
TEST_CSV = os.path.join(BASE, "data", "test_hi_mr.csv")
OUT = os.path.join(BASE, "model", "bloom_multilingual.joblib")


def read_csv(path):
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
    df = df.dropna(subset=["Questions", "Category"])
    df["Questions"] = df["Questions"].astype(str).map(clean_for_model)
    return df[df["Questions"].str.len() > 0]


print("Loading embedding model:", EMBED_MODEL_NAME)
embedder = SentenceTransformer(EMBED_MODEL_NAME)


def embed(texts):
    return embedder.encode(list(texts), batch_size=64, normalize_embeddings=True, show_progress_bar=True)


def make_clf():
    return LogisticRegression(C=10, max_iter=3000, class_weight="balanced")


en = read_csv(EN_CSV)
print("English rows:", len(en))
print(en["Category"].value_counts().to_string())

X_tr, X_te, y_tr, y_te = train_test_split(
    en["Questions"], en["Category"], test_size=0.2, stratify=en["Category"], random_state=42
)

extra = read_csv(AUG_CSV) if os.path.exists(AUG_CSV) else None
if extra is not None:
    print("Adding Hindi/Marathi training rows:", len(extra))
    X_tr = pd.concat([X_tr, extra["Questions"]])
    y_tr = pd.concat([y_tr, extra["Category"]])

# 1) honest evaluation on held-out data
clf = make_clf().fit(embed(X_tr), y_tr)
print("\n=== English held-out test ===")
print(classification_report(y_te, clf.predict(embed(X_te)), digits=3))

if os.path.exists(TEST_CSV):
    hm = read_csv(TEST_CSV)
    print("=== Hindi/Marathi hand-labelled test (%d rows) ===" % len(hm))
    print(classification_report(hm["Category"], clf.predict(embed(hm["Questions"])), digits=3))
else:
    print("No data/test_hi_mr.csv found – Hindi/Marathi accuracy is NOT measured. "
          "Add ~100-200 hand-labelled rows (Questions,Category) to measure it.")

# 2) final model: refit on everything we have
all_X = [en["Questions"]] + ([extra["Questions"]] if extra is not None else [])
all_y = [en["Category"]] + ([extra["Category"]] if extra is not None else [])
final = make_clf().fit(embed(pd.concat(all_X)), pd.concat(all_y))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
joblib.dump({"clf": final, "embed_model": EMBED_MODEL_NAME}, OUT)
print("Saved", OUT)