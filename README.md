# Gradence – Question Paper Analyser

Gradence is a Flask web application that analyses a question paper automatically. You upload a paper (PDF, DOCX or TXT); it extracts the individual questions, predicts the **Bloom's Taxonomy level** of each question, maps each question to a **subject and Course Outcome (CO)**, and shows the results on a dashboard.

## Features

- Upload a question paper in **PDF**, **DOCX** or **TXT** format
- Automatic extraction of questions (handles `Q1`, `a)`, `b)`, `OR A)` style numbering and removes header lines)
- Bloom's level prediction (BT1–BT6) with a TF-IDF + neural network model
- Subject and CO mapping using syllabus keywords
- Dashboard with the number of questions, a per-question table and the dominant Bloom's level of the paper

## Bloom's levels

| Label | Level      |
| ----- | ---------- |
| BT1   | Remember   |
| BT2   | Understand |
| BT3   | Apply      |
| BT4   | Analyze    |
| BT5   | Evaluate   |
| BT6   | Create     |

## How it works

1. The uploaded file is read (PyPDF2 for PDF, mammoth for DOCX, plain read for TXT).
2. Questions are split out with regular-expression rules and header/instruction lines are dropped.
3. Each question is lower-cased, stripped of punctuation and converted to TF-IDF features (2,000 features, 1–3 word n-grams).
4. A feed-forward neural network (Dense 128 → Dense 64 → softmax, with batch normalisation, dropout and L2 regularisation) predicts the Bloom's level.
5. The CO mapper counts syllabus keywords from `data/co_mapping.json` found in the question, picks the best subject and then the best CO.

## Model performance

Trained on 14,847 labelled questions (80:20 stratified split). On the 2,970 test questions:

| Metric            | Value  |
| ----------------- | ------ |
| Accuracy          | 86.33% |
| Weighted F1-score | 86.42% |
| Macro F1-score    | 88.33% |

The most common mistakes are between Remember (BT1) and Understand (BT2).

## Project structure

```
Gradance/
├── app.py                      # Flask application and analysis logic
├── updateCo.py                 # builds data/co_mapping.json from a syllabus Excel sheet
├── data/
│   ├── blooms_taxonomy_dataset.csv   # labelled training questions
│   └── co_mapping.json               # subjects, COs and keywords
├── model/
│   ├── model.ipynb             # training notebook
│   ├── bloom_model.h5          # trained neural network
│   ├── vectorizer.pkl          # fitted TF-IDF vectoriser
│   └── label_encoder.pkl       # label encoder
├── static/                     # app.js, style.css
└── templates/index.html        # web interface
```

## Setup

Requires Python 3.12.

```bash
git clone https://github.com/Innov8or123/Gradance.git
cd Gradance
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install flask tensorflow pandas numpy scikit-learn PyPDF2 mammoth
```

## Run

```bash
python app.py
```

Open http://127.0.0.1:5000, upload a question paper and click **Analyze**.

## Adding or updating a subject's COs

`updateCo.py` reads a syllabus `.xls` sheet whose CO headings look like `1.0 Topic name`, and writes the CO names and keywords into `data/co_mapping.json`.

1. Open `updateCo.py` and set `EXCEL_FILE` to your syllabus file and the `subject_name` argument to your subject.
2. Run `python updateCo.py`.

## Retraining the model

Open `model/model.ipynb`, run all cells and the notebook saves `bloom_model.h5`, `vectorizer.pkl` and `label_encoder.pkl` in `model/`.

## Limitations

- English only
- Scanned (image-only) PDFs are not supported
- CO mapping is keyword based, so questions without the configured keywords show "Not Matched"
- Marks of questions are not analysed
- `.doc` files are not supported; save them as `.docx`

## Authors

- Vishruth Shetty
- Shlok Yadav
- Devika Nair
- Sanika Desai
