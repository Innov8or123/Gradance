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
    const progressText = document.getElementById('progress-text');
    const analyzeBtn = document.getElementById('analyze-btn');
    const newAnalysisBtn = document.getElementById('new-analysis-btn');
    const paperTitle = document.getElementById('paper-title');
    const timestamp = document.getElementById('timestamp');
    const totalQuestions = document.getElementById('total-questions');
    const paperStatus = document.getElementById('paper-status');
    const overallDifficulty = document.getElementById('overall-difficulty');
    const difficultyChart = document.getElementById('difficulty-chart').getContext('2d');
    // const bloomsChart = document.getElementById('blooms-chart').getContext('2d');
    const questionsTable = document.getElementById('questions-table');
    const assessmentDetails = document.getElementById('assessment-details');
    const difficultyFilter = document.getElementById('difficulty-filter');
    const bloomsFilter = document.getElementById('blooms-filter');
    const steps = document.querySelectorAll('.step');
    let timeRemaining = 20;
    let timer;

    // Chart instances
    let difficultyChartInstance = null;
    // let bloomsChartInstance = null;
    const bloom_levels = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'];
    const difficulty_map = {'Remember': 'level 1', 'Understand': 'level 2', 'Apply': 'level 3', 'Analyze': 'level 4'};

    // Drag and Drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        fileInput.files = e.dataTransfer.files;
        handleFileSelect();
    });

    // Browse Button
    browseBtn.addEventListener('click', () => fileInput.click());

    // File Input Change
    fileInput.addEventListener('change', handleFileSelect);

    function handleFileSelect() {
        const file = fileInput.files[0];
        if (file) {
            fileName.textContent = file.name;
            fileSize.textContent = `${(file.size / 1024).toFixed(2)} KB`;
            fileStatus.textContent = 'Ready';
            fileInfo.style.display = 'block';
            uploadArea.style.display = 'none';
            analyzeBtn.disabled = false;
        }
    }

    // Analyze Button
    analyzeBtn.addEventListener('click', () => {
        const file = fileInput.files[0];
        if (!file) return;

        // Transition to Processing Page
        landingPage.classList.remove('active');
        processingPage.classList.add('active');
        loadingOverlay.style.display = 'flex';

        // Simulate processing steps
        let stepIndex = 0;
        steps.forEach((step, index) => {
            setTimeout(() => {
                step.classList.add('active');
                if (index === steps.length - 1) {
                    clearInterval(timer);
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Analysis complete!';
                }
            }, index * 5000);
        });

        // Timer
        timer = setInterval(() => {
            timeRemaining--;
            document.getElementById('time-remaining').textContent = `${timeRemaining} seconds`;
            if (timeRemaining <= 0) clearInterval(timer);
        }, 1000);

        // Progress Simulation
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 5;
            progressFill.style.width = `${progress}%`;
            if (progress >= 100) clearInterval(progressInterval);
        }, 500);

        // Send to Backend
        const formData = new FormData();
        formData.append('file', file);

        fetch('/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                resetState();
            } else {
                // Transition to Results Page
                processingPage.classList.remove('active');
                resultsPage.classList.add('active');
                loadingOverlay.style.display = 'none';

                // Update Results
                paperTitle.textContent = `Analysis Results - ${file.name}`;
                timestamp.textContent = data.timestamp;
                totalQuestions.textContent = data.total_questions;
                paperStatus.textContent = 'Completed';
                paperStatus.classList.add('status--success');
                overallDifficulty.textContent = data.overall_difficulty;
                overallDifficulty.className = 'difficulty-badge ' + data.overall_difficulty.toLowerCase();

                // Charts
                if (difficultyChartInstance) difficultyChartInstance.destroy();
                // if (bloomsChartInstance) bloomsChartInstance.destroy();
                difficultyChartInstance = new Chart(difficultyChart, {
                    type: 'pie',
                    data: {
                        labels: ['level 1', 'level 2', 'level 3', 'level 4'],
                        datasets: [{
                            data: [
                                data.predictions.filter(p => ['Remember'].includes(p)).length / data.total_questions * 100,
                                data.predictions.filter(p => ['Understand'].includes(p)).length / data.total_questions * 100,
                                data.predictions.filter(p => ['Apply'].includes(p)).length / data.total_questions * 100,
                                data.predictions.filter(p => ['Analyze'].includes(p)).length / data.total_questions * 100
                            ],
                            backgroundColor: ['#10B981', '#F59E0B', '#EF4444', '#4F46E5']
                        }]
                    },
                    options: { 
                        responsive: true, 
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: { color: '#bfbdbd'}
                            },
                            title: {
                                display: true,
                                text: 'Bloom\'s Taxonomy Distribution',
                                color: '#bfbdbd'
                            }
                        }
                    }
                });


                //----------------------------
                // bloomsChartInstance = new Chart(bloomsChart, {
                //     type: 'pie',
                //     data: {
                //         labels: bloom_levels,
                //         datasets: [{
                //             data: bloom_levels.map(level => data.stats[level] || 0),
                //             backgroundColor: ['#10B981', '#F59E0B', '#FBBF24', '#EF4444', '#8B5CF6', '#6B7280']
                //         }]
                //     },
                //     options: {
                //         responsive: true,
                //         maintainAspectRatio: false,
                //         plugins: {
                //             legend: {
                //                 position: 'top',
                //                 labels: { color: '#bfbdbd' }
                //             },
                //             title: {
                //                 display: true,
                //                 text: 'Bloom\'s Taxonomy Distribution',
                //                 color: '#bfbdbd'
                //             }
                //         }
                //     }
                // });
                //-----------------------------------



                // Questions Table and Filtering
                const rows = data.questions.map((q, i) => `
                    <div class="questions-table-row" data-difficulty="${difficulty_map[data.predictions[i]]}" data-blooms="${data.predictions[i]}">
                        <div class="question-cell">${q}</div>
                        <div class="blooms-badge">${data.predictions[i]}</div>
                    </div>
                `);
                questionsTable.innerHTML = `
                    <div class="questions-table-header">
                        <div>Question</div>
                        <div>Bloom's Level</div>
                    </div>
                    ${rows.join('')}
                `;

                // Filter Logic
                function filterTable() {
                    // const diffFilter = difficultyFilter.value;
                    const bloomsFilterValue = bloomsFilter.value;
                    rows.forEach((row, i) => {
                        const rowElement = questionsTable.children[i + 1];
                        // const difficulty = rowElement.getAttribute('data-difficulty');
                        const blooms = rowElement.getAttribute('data-blooms');
                        // const matchDifficulty = diffFilter === 'all' || difficulty === diffFilter;
                        const matchBlooms = bloomsFilterValue === 'all' || blooms === bloomsFilterValue;
                        rowElement.style.display = matchBlooms ? 'grid' : 'none';
                    });
                }

                // difficultyFilter.addEventListener('change', filterTable);
                bloomsFilter.addEventListener('change', filterTable);
                filterTable(); // Initial filter

                // Assessment Report
                assessmentDetails.innerHTML = `
                    <div class="assessment-status assessment-status--success">
                        <span class="status-icon">✅</span> Analysis Successful
                    </div>
                    <div class="assessment-reasoning">
                        <h4>Reasoning</h4>
                        <p>The analysis distributed questions across Bloom's levels based on cognitive complexity, with ${data.overall_difficulty} as the dominant difficulty.</p>
                    </div>
                    <div class="recommendations">
                        <h4>Recommendations</h4>
                        <ul>
                            <li>Consider balancing ${data.overall_difficulty} questions with other levels for a well-rounded exam.</li>
                            <li>Add more ${bloom_levels[0]} or ${bloom_levels[1]} questions if foundational knowledge is needed.</li>
                        </ul>
                    </div>
                `;
            }
        })
        .catch(error => {
            showNotification('Error analyzing the filter.', 'error');
            resetState();
        });
    });

    // New Analysis Button
    newAnalysisBtn.addEventListener('click', () => {
        resetState();
        landingPage.classList.add('active');
        resultsPage.classList.remove('active');
        if (difficultyChartInstance) difficultyChartInstance.destroy();
        // if (bloomsChartInstance) bloomsChartInstance.destroy();
    });

    function resetState() {
        loadingOverlay.style.display = 'none';
        fileInfo.style.display = 'none';
        uploadArea.style.display = 'block';
        analyzeBtn.disabled = true;
        fileInput.value = '';
        fileName.textContent = 'No file selected';
        fileSize.textContent = '0 KB';
        fileStatus.textContent = 'Processing...';
        progressFill.style.width = '0%';
        progressText.textContent = 'Reading file...';
        clearInterval(timer);
        timeRemaining = 20;
        document.getElementById('time-remaining').textContent = `${timeRemaining} seconds`;
        steps.forEach(step => step.classList.remove('active'));
        // if (difficultyFilter) difficultyFilter.value = 'all';
        if (bloomsFilter) bloomsFilter.value = 'all';
    }

    function showNotification(message, type = 'info') {
        notification.textContent = message;
        notification.className = `notification notification--${type} show`;
        setTimeout(() => notification.classList.remove('show'), 5000);
    }
});