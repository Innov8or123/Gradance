# Gradence – Question Paper Analyser (multilingual-support branch)

This branch extends Gradence so that it can analyse question papers written in **English, Hindi and Marathi**. As before, you upload a paper (PDF, DOCX or TXT); it extracts the questions, predicts the **Bloom's Taxonomy level** of each one and maps it to a **subject and Course Outcome (CO)**.

For the original English-only version, see the `main` branch.

## What is different from `main`

| Area | `main` | `multilingual-support` |
|---|---|---|
| Text cleaning | `re` with `\w` (removes Devanagari vowel signs) | `regex` library; keeps Devanagari letters and marks, normalises digits (१२३ → 123) |
| Question splitting | English markers only | Also handles `प्र. १`, `प्रश्न 1`, `अ) ब) क)`, `अथवा` / `किंवा`, and `।` |
| PDF reading | PyPDF2 | PyMuPDF, with optional OCR fallback for scanned pages |
| Bloom's classifier | TF-IDF + Keras neural network | Multilingual sentence embeddings + logistic regression |
| CO mapping | substring keyword match | embedding similarity plus whole-word keyword boost; English keywords work for Hindi and Marathi questions |
| Dependencies | TensorFlow, PyPDF2 | sentence-transformers, PyMuPDF, regex, joblib (TensorFlow and PyPDF2 not needed) |

## Project structure

```
Gradance/
├── app.py                       # Flask app (multilingual version)
├── nlp_utils.py                 # cleaning, question splitting, file reading
├── train_multilingual.py        # trains the classifier and saves it
├── requirements.txt
├── updateCo.py
├── data/
│   ├── blooms_taxonomy_dataset.csv
│   ├── co_mapping.json
│   ├── augmented_hi_mr.csv      # optional: extra Hindi/Marathi training rows
│   └── test_hi_mr.csv           # optional: hand-labelled Hindi/Marathi test rows
├── model/
│   └── bloom_multilingual.joblib    # created by train_multilingual.py
├── test_papers/                 # sample Hindi, Marathi and mixed papers
├── static/
└── templates/index.html
```

## Setup

Requires Python 3.12.

```bash
git clone https://github.com/Innov8or123/Gradance.git
cd Gradance
git checkout multilingual-support
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Optional: OCR for scanned PDFs

Install the Tesseract program with the Hindi and Marathi language packs:

```bash
brew install tesseract tesseract-lang                       # macOS
sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar   # Ubuntu
```

## Train the classifier (required once)

The app loads `model/bloom_multilingual.joblib`, which does not exist until you train it:

```bash
python train_multilingual.py
```

- The first run downloads the embedding model `paraphrase-multilingual-MiniLM-L12-v2` (about 470 MB) from Hugging Face; later runs use the cached copy.
- It prints the English test accuracy and per-class scores.
- If `data/test_hi_mr.csv` exists, it also prints Hindi/Marathi scores. Add 100–200 hand-labelled rows (columns `Questions,Category`) to measure these. Without that file, accuracy for Hindi and Marathi is **not measured**.
- To add training data, put translated rows in `data/augmented_hi_mr.csv` (same columns).

## Run

```bash
python app.py
```

Open http://127.0.0.1:5000 and upload a paper. Samples to try are in `test_papers/`:

- `test_paper_hindi.txt`
- `test_paper_marathi.txt`
- `test_paper_mixed.txt` (English, Hindi and Marathi together)

## Tuning

In `app.py`:

- `MIN_SUBJECT_SCORE` and `MIN_CO_SCORE` (default 0.30): raise them if unrelated questions get matched, lower them if too many show "Not Matched".
- `KEYWORD_BOOST` (default 0.20): extra score when an exact English keyword appears in the question.

In `nlp_utils.py`, `EMBED_MODEL_NAME` selects the embedding model (for example `LaBSE` or `multilingual-e5-base`). Retrain after changing it.

## Limitations

- Hindi and Marathi accuracy depends on cross-language transfer from the English training data until you add labelled Hindi/Marathi data.
- PDFs created with legacy fonts (for example Kruti Dev) extract as unreadable text; use Unicode fonts or OCR.
- CO mapping needs the syllabus keywords in `co_mapping.json`; questions far from those topics show "Not Matched".
- Scanned PDFs need the optional OCR setup.
- `.doc` files are not supported; save them as `.docx`.
- Marks of questions are not analysed.

## Authors

- Vishruth Shetty
- Shlok Yadav

Subject In-charge: Prof. Ujwala Ravale · HOD: Prof. Aparna Bannore
