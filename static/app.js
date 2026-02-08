document.addEventListener('DOMContentLoaded', () => {
    const landingPage = document.getElementById('landing-page');
    const processingPage = document.getElementById('processing-page');
    const resultsPage = document.getElementById('results-page');
    const loadingOverlay = document.getElementById('loading-overlay');
    const notification = document.getElementById('notification');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const uploadArea = document.getElementById('upload-area');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const fileStatus = document.getElementById('file-status');
    const progressFill = document.getElementById('progress-fill');
    const analyzeBtn = document.getElementById('analyze-btn');
    const newAnalysisBtn = document.getElementById('new-analysis-btn');
    const paperTitle = document.getElementById('paper-title');
    const timestamp = document.getElementById('timestamp');
    const totalQuestions = document.getElementById('total-questions');
    const paperStatus = document.getElementById('paper-status');
    const overallDifficulty = document.getElementById('overall-difficulty');
    const questionsTable = document.getElementById('questions-table');
    const assessmentDetails = document.getElementById('assessment-details');
    const steps = document.querySelectorAll('.step');

    let timeRemaining = 20;
    let timer;

    // ---------------- FILE HANDLING ----------------
    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    uploadArea.addEventListener('dragover', e => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', e => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        fileInput.files = e.dataTransfer.files;
        handleFileSelect();
    });

    function handleFileSelect() {
        const file = fileInput.files[0];
        if (!file) return;

        fileName.textContent = file.name;
        fileSize.textContent = `${(file.size / 1024).toFixed(2)} KB`;
        fileStatus.textContent = 'Ready';
        fileInfo.style.display = 'block';
        uploadArea.style.display = 'none';
        analyzeBtn.disabled = false;
    }

    // ---------------- ANALYZE ----------------
    analyzeBtn.addEventListener('click', () => {
        const file = fileInput.files[0];
        if (!file) return;

        landingPage.classList.remove('active');
        processingPage.classList.add('active');
        loadingOverlay.style.display = 'flex';

        steps.forEach((step, index) => {
            setTimeout(() => step.classList.add('active'), index * 3000);
        });

        timer = setInterval(() => {
            timeRemaining--;
            document.getElementById('time-remaining').textContent = `${timeRemaining} seconds`;
            if (timeRemaining <= 0) clearInterval(timer);
        }, 1000);

        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 5;
            progressFill.style.width = `${progress}%`;
            if (progress >= 100) clearInterval(progressInterval);
        }, 500);

        const formData = new FormData();
        formData.append('file', file);

        fetch('/analyze', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                resetState();
                return;
            }

            processingPage.classList.remove('active');
            resultsPage.classList.add('active');
            loadingOverlay.style.display = 'none';

            paperTitle.textContent = `Analysis Results - ${file.name}`;
            timestamp.textContent = new Date().toLocaleTimeString();
            totalQuestions.textContent = data.total_questions;
            paperStatus.textContent = 'Completed';
            paperStatus.classList.add('status--success');

            overallDifficulty.textContent = data.overall_difficulty;
            overallDifficulty.className = 'difficulty-badge ' + data.overall_difficulty.replace(/\s+/g, '-').toLowerCase();

            // ---------------- QUESTIONS TABLE ----------------
            const rowsHTML = data.questions.map((q, i) => {
                const bloom = data.predictions[i];
                const co = data.co_mapping[i];
                
                return `
                    <div class="questions-table-row" data-blooms="${bloom}">
                        <div class="question-cell">${q}</div>
                        <div>
                            <span class="blooms-badge">${bloom}</span>
                        </div>
                        <div class="question-cell" style="font-style: italic; color: #888;">
                            ${co.co_name !== "Not Matched" ? co.co_name : 'General'}
                        </div>
                        <div>
                            <span class="co-badge" style="background: #1e1e2e; padding: 4px 8px; border-radius: 4px; border: 1px solid #333;">
                                ${co.co_code}
                            </span>
                        </div>
                    </div>
                `;
            }).join('');

            questionsTable.innerHTML = `
                <div class="questions-table-header">
                    <div>Question</div>
                    <div>Bloom's Level</div>
                    <div>Topic/Subject</div>
                    <div>CO</div>
                </div>
                ${rowsHTML}
            `;

            assessmentDetails.innerHTML = `
                <div class="assessment-status assessment-status--success">✅ Analysis Successful</div>
                <p>The dominant Bloom's level identified is <b>${data.overall_difficulty}</b>.</p>
            `;
        })
        .catch(err => {
            console.error(err);
            showNotification('Error analyzing the file.', 'error');
            resetState();
        });
    });

    // ---------------- RESET ----------------
    newAnalysisBtn.addEventListener('click', resetState);

    function resetState() {
        loadingOverlay.style.display = 'none';
        landingPage.classList.add('active');
        processingPage.classList.remove('active');
        resultsPage.classList.remove('active');
        fileInfo.style.display = 'none';
        uploadArea.style.display = 'block';
        analyzeBtn.disabled = true;
        fileInput.value = '';
        progressFill.style.width = '0%';
        clearInterval(timer);
        timeRemaining = 20;
        steps.forEach(step => step.classList.remove('active'));
    }

    function showNotification(msg, type = 'info') {
        notification.textContent = msg;
        notification.className = `notification notification--${type} show`;
        setTimeout(() => notification.classList.remove('show'), 4000);
    }
});