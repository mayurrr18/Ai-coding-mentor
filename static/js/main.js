// Global variables
let currentStudentId = null;
let currentSessionId = null;
let currentChallenge = null;
let mistakeTypesChart = null;
let progressChart = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeStudent();
    setupEventListeners();
});

// Initialize or load student
async function initializeStudent() {
    // Check if student exists in localStorage
    let studentId = localStorage.getItem('studentId');
    
    if (!studentId) {
        // Register new student
        studentId = await registerStudent();
    }
    
    currentStudentId = studentId;
    await loadStudentData();
    await loadDashboard();
}

// Register new student
async function registerStudent() {
    const languages = ['python', 'javascript'];
    
    const response = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            languages: languages
        })
    });
    
    const data = await response.json();
    
    if (data.success) {
        localStorage.setItem('studentId', data.student_id);
        return data.student_id;
    }
    
    return null;
}

// Load student data
async function loadStudentData() {
    const response = await fetch(`/api/profile/${currentStudentId}`);
    const profile = await response.json();
    
    if (!profile.error) {
        document.getElementById('studentName').textContent = `Student ${profile.student_id}`;
        const skillLevel = profile.skill_level?.python || 'beginner';
        document.getElementById('studentLevel').textContent = skillLevel.charAt(0).toUpperCase() + skillLevel.slice(1);
        document.getElementById('welcomeName').textContent = `Student ${profile.student_id}`;
    }
}

// Load dashboard
async function loadDashboard() {
    await loadStats();
    await loadRecommendations();
    await loadWeakConcepts();
}

// Load statistics
async function loadStats() {
    const response = await fetch(`/api/stats/${currentStudentId}`);
    const stats = await response.json();
    
    if (!stats.error) {
        document.getElementById('challengesCompleted').textContent = stats.total_challenges_completed || 0;
        document.getElementById('masteryLevel').textContent = `${Math.round((stats.average_mastery || 0) * 100)}%`;
        document.getElementById('learningSpeed').textContent = `${Math.round(stats.learning_speed || 0)}s`;
        document.getElementById('mistakesCount').textContent = stats.total_mistakes || 0;
    }
}

// Load recommendations
async function loadRecommendations() {
    const response = await fetch(`/api/learning-path/${currentStudentId}`);
    const data = await response.json();
    
    const recommendationsList = document.getElementById('recommendationsList');
    
    if (!data.error && data.recommendations) {
        recommendationsList.innerHTML = data.recommendations.map(rec => 
            `<div class="recommendation-item">${rec}</div>`
        ).join('');
    } else {
        recommendationsList.innerHTML = '<div class="recommendation-item">Complete more challenges to get personalized recommendations!</div>';
    }
}

// Load weak concepts
async function loadWeakConcepts() {
    const response = await fetch(`/api/profile/${currentStudentId}`);
    const profile = await response.json();
    
    const conceptsList = document.getElementById('weakConceptsList');
    
    if (!profile.error && profile.weakest_concepts && profile.weakest_concepts.length > 0) {
        conceptsList.innerHTML = profile.weakest_concepts.map(concept => 
            `<div class="concept-item">🎯 ${concept.replace('_', ' ').toUpperCase()} - Focus on mastering this concept</div>`
        ).join('');
    } else {
        conceptsList.innerHTML = '<div class="concept-item">Keep practicing! You\'re doing great! 🚀</div>';
    }
}

// Load challenge
async function loadChallenge() {
    const response = await fetch(`/api/challenge/${currentStudentId}`);
    const challenge = await response.json();
    
    if (!challenge.error) {
        currentChallenge = challenge;
        currentSessionId = challenge.session_id;
        
        document.getElementById('challengeTitle').textContent = challenge.title;
        document.getElementById('challengeDifficulty').textContent = challenge.difficulty.toUpperCase();
        document.getElementById('challengeConcept').textContent = challenge.concept.toUpperCase();
        document.getElementById('challengeDescription').textContent = challenge.description;
        document.getElementById('personalizedNoteText').textContent = challenge.personalized_note || '';
        
        // Load examples
        const examplesList = document.getElementById('examplesList');
        if (challenge.examples) {
            examplesList.innerHTML = challenge.examples.map(ex => 
                `<div class="example-item">
                    <strong>Input:</strong> ${ex.input}<br>
                    <strong>Output:</strong> ${ex.output}
                </div>`
            ).join('');
        }
        
        // Load hints
        const hintsList = document.getElementById('hintsList');
        if (challenge.hints) {
            hintsList.innerHTML = challenge.hints.map(hint => 
                `<li>${hint}</li>`
            ).join('');
        }
        
        // Load starter code
        document.getElementById('codeEditor').value = challenge.starter_code || '# Write your code here';
        
        // Switch to challenge tab
        switchTab('challenge');
    } else {
        alert('Error loading challenge: ' + challenge.error);
    }
}

// Run code
async function runCode() {
    const code = document.getElementById('codeEditor').value;
    const language = document.getElementById('languageSelect').value;
    
    // Simple code execution simulation (in production, use a secure sandbox)
    const outputArea = document.getElementById('outputArea');
    outputArea.textContent = 'Running code...\n';
    
    try {
        // Simulate code execution (in reality, send to backend for safe execution)
        const result = simulateCodeExecution(code, language, currentChallenge);
        
        if (result.error) {
            outputArea.textContent = `Error:\n${result.error}`;
            
            // Get debugging suggestions
            const debugResponse = await fetch('/api/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    code: code,
                    error: result.error,
                    is_correct: false
                })
            });
            
            const debugData = await debugResponse.json();
            
            // Display debugging suggestions
            const suggestionsList = document.getElementById('suggestionsList');
            if (debugData.debugging_suggestions && debugData.debugging_suggestions.suggestions) {
                suggestionsList.innerHTML = debugData.debugging_suggestions.suggestions.map(s => 
                    `<div class="suggestion-item">${s.message}</div>`
                ).join('');
            }
            
            // Record mistake
            await fetch('/api/mistake', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: currentStudentId,
                    language: language,
                    mistake_type: detectMistakeType(result.error),
                    code_snippet: code,
                    error_message: result.error,
                    concept: currentChallenge.concept,
                    severity: 3
                })
            });
        } else {
            outputArea.textContent = `Output:\n${result.output}`;
            
            // Check if output matches expected
            const isCorrect = checkIfCorrect(result.output, currentChallenge);
            
            // Submit correct code
            await fetch('/api/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    code: code,
                    error: null,
                    is_correct: isCorrect
                })
            });
            
            if (isCorrect) {
                outputArea.textContent += '\n\n✅ Correct! Great job!';
                document.getElementById('suggestionsList').innerHTML = '<div class="suggestion-item">🎉 Solution accepted! Moving to next challenge...</div>';
                setTimeout(() => {
                    loadChallenge();
                }, 2000);
            } else {
                outputArea.textContent += '\n\n❌ Not quite right. Check your output against the examples!';
            }
        }
    } catch (error) {
        outputArea.textContent = `Error: ${error.message}`;
    }
}

// Simulate code execution (simplified for demo)
function simulateCodeExecution(code, language, challenge) {
    // This is a simplified simulation. In production, use a secure code execution service
    try {
        // For demo purposes, check common patterns
        if (code.includes('return') && challenge.id === 'hello_world') {
            if (code.includes('Hello, World!')) {
                return { output: 'Hello, World!' };
            }
        }
        
        if (challenge.id === 'array_sum') {
            if (code.includes('sum') && code.includes('return')) {
                return { output: '6' };
            }
        }
        
        // If we can't simulate, return a generic message
        return { output: 'Code executed successfully!\n\nTip: Use the examples to test your code.' };
    } catch (e) {
        return { error: e.message };
    }
}

// Check if output is correct
function checkIfCorrect(output, challenge) {
    // Simplified check - in production, compare with expected outputs
    if (challenge.id === 'hello_world' && output.includes('Hello, World!')) {
        return true;
    }
    if (challenge.id === 'array_sum' && output.includes('6')) {
        return true;
    }
    return false;
}

// Detect mistake type from error message
function detectMistakeType(error) {
    if (error.includes('IndexError') || error.includes('out of range')) return 'off_by_one';
    if (error.includes('TypeError')) return 'type_error';
    if (error.includes('SyntaxError')) return 'syntax_error';
    if (error.includes('NameError')) return 'variable_scope';
    return 'logic_error';
}

// Load learning path
async function loadLearningPath() {
    const response = await fetch(`/api/learning-path/${currentStudentId}`);
    const data = await response.json();
    
    const container = document.getElementById('learningPathContent');
    
    if (!data.error) {
        let html = '<div class="learning-path-container">';
        
        // Learning path
        if (data.learning_path && data.learning_path.length > 0) {
            html += '<div class="path-timeline"><h3>Your Learning Journey</h3><div class="timeline">';
            data.learning_path.forEach((concept, index) => {
                html += `
                    <div class="timeline-node">
                        <div class="node-marker">${index + 1}</div>
                        <div class="node-content">
                            <h4>${concept.toUpperCase()}</h4>
                            <p>Master this concept to progress</p>
                        </div>
                    </div>
                `;
            });
            html += '</div></div>';
        }
        
        // Practice plan
        if (data.practice_plan && data.practice_plan.length > 0) {
            html += '<div class="practice-plan"><h3>Recommended Practice Plan</h3>';
            data.practice_plan.forEach(plan => {
                html += `
                    <div class="plan-card">
                        <h4>${plan.concept.toUpperCase()}</h4>
                        <div class="mastery-bar">
                            <div class="mastery-fill" style="width: ${plan.current_mastery * 100}%"></div>
                        </div>
                        <p>Mastery: ${Math.round(plan.current_mastery * 100)}%</p>
                        <ul>
                            ${plan.suggested_practices.map(p => `<li>${p}</li>`).join('')}
                        </ul>
                        <p class="time-estimate">⏱️ Estimated time: ${plan.estimated_time_hours} hours</p>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        // Goals
        if (data.next_learning_goals && data.next_learning_goals.length > 0) {
            html += '<div class="learning-goals"><h3>Next Goals</h3><ul>';
            data.next_learning_goals.forEach(goal => {
                html += `<li>${goal}</li>`;
            });
            html += '</ul></div>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    } else {
        container.innerHTML = '<p>Complete some challenges to generate your learning path!</p>';
    }
}

// Load mistakes history
async function loadMistakesHistory() {
    const response = await fetch(`/api/mistakes/${currentStudentId}`);
    const data = await response.json();
    
    const container = document.getElementById('mistakesList');
    const searchTerm = document.getElementById('searchMistakes')?.value.toLowerCase() || '';
    const filterType = document.getElementById('filterMistakeType')?.value || 'all';
    
    if (data.mistakes && data.mistakes.length > 0) {
        let filteredMistakes = data.mistakes;
        
        // Apply filters
        if (searchTerm) {
            filteredMistakes = filteredMistakes.filter(m => 
                m.error_message?.toLowerCase().includes(searchTerm) ||
                m.code_snippet?.toLowerCase().includes(searchTerm)
            );
        }
        
        if (filterType !== 'all') {
            filteredMistakes = filteredMistakes.filter(m => m.mistake_type === filterType);
        }
        
        if (filteredMistakes.length > 0) {
            container.innerHTML = filteredMistakes.map(mistake => `
                <div class="mistake-card">
                    <div class="mistake-header">
                        <span class="mistake-type ${getMistakeClass(mistake.mistake_type)}">
                            ${mistake.mistake_type.replace('_', ' ').toUpperCase()}
                        </span>
                        <span class="mistake-date">${new Date(mistake.timestamp).toLocaleDateString()}</span>
                    </div>
                    <div class="mistake-concept">Concept: ${mistake.concept || 'General'}</div>
                    <div class="mistake-code">
                        <strong>Your code:</strong><br>
                        <pre>${escapeHtml(mistake.code_snippet)}</pre>
                    </div>
                    <div class="mistake-fix">
                        <strong>💡 How to fix:</strong><br>
                        <pre>${escapeHtml(mistake.corrected_code)}</pre>
                    </div>
                    <div class="mistake-error">
                        <strong>Error:</strong> ${escapeHtml(mistake.error_message)}
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p>No mistakes match your filters.</p>';
        }
    } else {
        container.innerHTML = '<p>No mistakes recorded yet. Keep practicing and learning from errors!</p>';
    }
}

// Get CSS class for mistake type
function getMistakeClass(type) {
    if (type.includes('syntax')) return 'syntax';
    if (type.includes('logic')) return 'logic';
    if (type.includes('off_by_one')) return 'off_by_one';
    return 'logic';
}

// Load statistics page
async function loadStatistics() {
    const response = await fetch(`/api/stats/${currentStudentId}`);
    const stats = await response.json();
    
    if (!stats.error) {
        // Update detailed stats
        const detailedStats = document.getElementById('detailedStats');
        detailedStats.innerHTML = `
            <h3>Detailed Analysis</h3>
            <div class="stats-details-grid">
                <div class="stat-detail">
                    <strong>Total Challenges Completed:</strong> ${stats.total_challenges_completed}
                </div>
                <div class="stat-detail">
                    <strong>Total Mistakes:</strong> ${stats.total_mistakes}
                </div>
                <div class="stat-detail">
                    <strong>Average Mastery:</strong> ${Math.round(stats.average_mastery * 100)}%
                </div>
                <div class="stat-detail">
                    <strong>Learning Speed:</strong> ${Math.round(stats.learning_speed)} seconds per challenge
                </div>
            </div>
        `;
        
        // Create mistake types chart
        if (stats.mistake_types && Object.keys(stats.mistake_types).length > 0) {
            const ctx = document.getElementById('mistakeTypesChart').getContext('2d');
            if (mistakeTypesChart) mistakeTypesChart.destroy();
            mistakeTypesChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: Object.keys(stats.mistake_types).map(t => t.replace('_', ' ')),
                    datasets: [{
                        data: Object.values(stats.mistake_types),
                        backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' },
                        title: { display: true, text: 'Mistakes by Type' }
                    }
                }
            });
        }
        
        // Create progress chart (simulated)
        const progressCtx = document.getElementById('progressChart').getContext('2d');
        if (progressChart) progressChart.destroy();
        progressChart = new Chart(progressCtx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Mastery Progress',
                    data: [20, 35, 55, stats.average_mastery * 100],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Learning Progress' }
                }
            }
        });
    }
}

// Switch tabs
function switchTab(tabName) {
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.tab === tabName) {
            item.classList.add('active');
        }
    });
    
    // Update active tab content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Load tab-specific data
    switch(tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'challenge':
            if (!currentChallenge) loadChallenge();
            break;
        case 'learning-path':
            loadLearningPath();
            break;
        case 'mistakes':
            loadMistakesHistory();
            break;
        case 'stats':
            loadStatistics();
            break;
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Setup event listeners
function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(item.dataset.tab);
        });
    });
    
    // New challenge button
    document.getElementById('newChallengeBtn').addEventListener('click', () => {
        loadChallenge();
    });
    
    // Run code button
    document.getElementById('runCodeBtn').addEventListener('click', runCode);
    
    // Mistake filters
    const searchInput = document.getElementById('searchMistakes');
    const filterSelect = document.getElementById('filterMistakeType');
    
    if (searchInput) {
        searchInput.addEventListener('input', loadMistakesHistory);
    }
    if (filterSelect) {
        filterSelect.addEventListener('change', loadMistakesHistory);
    }
}

// Load initial data
async function loadInitialData() {
    await loadDashboard();
}

// Export for debugging
window.app = {
    loadChallenge,
    loadLearningPath,
    loadMistakesHistory,
    loadStatistics
};