from flask import Flask, render_template, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import PyPDF2
import re
import mammoth
import os

app = Flask(__name__)


device = torch.device('cpu')

tokenizer = AutoTokenizer.from_pretrained("cip29/bert-blooms-taxonomy-classifier")
model = AutoModelForSequenceClassification.from_pretrained("cip29/bert-blooms-taxonomy-classifier").to(device)

bloom_levels = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']

def predict_question(question):
    model.eval()
    encoding = tokenizer.encode_plus(
        question,
        add_special_tokens=True,
        max_length=128,
        return_token_type_ids=False,
        padding='max_length',
        truncation=True,
        return_attention_mask=True,
        return_tensors='pt'
    )
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        pred = torch.argmax(outputs.logits, dim=1).cpu().numpy()[0]
    
    return bloom_levels[pred]

def extract_questions(text):
    lines = re.split(r'\n', text.replace('\r', ''))
    questions = []
    currentQuestion = ''
    questionStart = r'^\s*(Q\s*?\d+|\d+\.|\d+\)|Question \d+|[a-z]\)|[A-Z]\.)\s*'
    ignoreKeywords = ['Note:', 'Subject:', 'Class', 'SEM:', 'Branch:', 'Duration:', 'Max.Marks:', 'All Questions', 'Figures', 'CO5',
                      'CO1', 'CO2', 'CO3', 'CO4', 'CO6', 'Internal','Attempt', 'First', 'Second', 'Signatures', 'Subject',
                      'Verified', 'L3', 'L2', 'CO', 'PI', 'Question', 'Blooms taxonomy']

    for line in lines:
        line = line.strip()
        if not line or any(line.startswith(keyword) for keyword in ignoreKeywords):
            continue

        if any(keyword in line for keyword in ignoreKeywords):
            if currentQuestion:
                questions.append(currentQuestion.strip())
            currentQuestion += ' '
            continue

        if re.match(questionStart, line):
            if currentQuestion:
                questions.append(currentQuestion.strip())
            currentQuestion = line
        else:
            currentQuestion += ' ' + line

    if currentQuestion:
        questions.append(currentQuestion.strip())

    questions = [q for q in questions if len(q.split()) > 3]

    return questions

#process different file types
def process_file(file):
    filename = file.filename
    if filename.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    elif filename.endswith(('.docx', '.doc')):
        result = mammoth.extract_raw_text(file)
        text = result.value
    elif filename.endswith('.txt'):
        text = file.read().decode('utf-8')
    else:
        raise ValueError("Unsupported file format")
    return extract_questions(text)

@app.route('/')
def home():
    return render_template('index.html')

# Route to handle file upload and prediction
@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not any(file.filename.endswith(ext) for ext in ['.pdf', '.docx', '.doc', '.txt']):
        return jsonify({'error': 'Please upload a PDF, DOCX, DOC, or TXT file'}), 400

    try:
        # Process file and extract questions
        questions = process_file(file)
        if not questions:
            return jsonify({'error': 'No questions found in the file'}), 400

        predictions = [predict_question(q) for q in questions]
        
        # Calculate statistics
        total_questions = len(questions)
        stats = {level: predictions.count(level) / total_questions * 100 for level in bloom_levels}
        stats['total_questions'] = total_questions

        difficulty_map = {'Remember': 'Easy', 'Understand': 'Easy', 'Apply': 'Moderate', 
                         'Analyze': 'Moderate', 'Evaluate': 'Hard', 'Create': 'Hard'}
        difficulties = [difficulty_map[p] for p in predictions]
        overall_difficulty = max(set(difficulties), key=difficulties.count) if difficulties else 'Unknown'

        return jsonify({
            'status': 'success',
            'stats': stats,
            'questions': questions,
            'predictions': predictions,
            'total_questions': total_questions,
            'overall_difficulty': overall_difficulty,
            'timestamp': 'Analysis completed at ' + os.popen('date').read().strip()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)