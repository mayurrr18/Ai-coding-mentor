// Global variables
let currentStudentId = null;
let currentUsername = null;
let currentSessionId = null;
let currentChallenge = null;
let mistakeTypesChart = null;
let progressChart = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
    setupEventListeners();
});

// Check if user is authenticated
async function checkAuthentication() {
    try {
        const response = await fetch('/api/check-auth');
        const data = await response.json();
        
        if (data.authenticated) {
            // User is logged in
            currentStudentId = data.student_id;
            currentUsername = data.username;
            localStorage.setItem('studentId', data.student_id);
            localStorage.setItem('username', data.username);
            
            await loadStudentData();
            await loadDashboard();
        } else {
            // User is not logged in, redirect to login
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Authentication error:', error);
        window.location.href = '/';
    }
}

// Load student data
async function loadStudentData() {
    try {
        const response = await fetch(`/api/profile/${currentStudentId}`);
        const profile = await response.json();
        
        if (!profile.error) {
            // Display username instead of student ID
            const displayName = currentUsername || profile.username || `Student ${profile.student_id}`;
            document.getElementById('studentName').textContent = displayName;
            document.getElementById('welcomeName').textContent = displayName.split(' ')[0]; // Use first name for welcome
            
            const skillLevel = profile.skill_level?.python || 'beginner';
            document.getElementById('studentLevel').textContent = skillLevel.charAt(0).toUpperCase() + skillLevel.slice(1);
        }
    } catch (error) {
        console.error('Error loading student data:', error);
    }
}

// Load dashboard
async function loadDashboard() {
    // Preload a challenge in the background
    preloadChallenge();
    
    await loadStats();
    await loadRecommendations();
    await loadWeakConcepts();
}

// Preload challenge in the background for faster loading
async function preloadChallenge() {
    try {
        if (!currentStudentId || currentChallenge) return; // Already loaded
        
        console.log('Preloading challenge in background...');
        const response = await fetch(`/api/challenge/${currentStudentId}`);
        
        if (response.ok) {
            const challenge = await response.json();
            if (challenge.id && !challenge.error) {
                currentChallenge = challenge;
                currentSessionId = challenge.session_id;
                console.log('Challenge preloaded successfully');
            }
        }
    } catch (error) {
        console.log('Background challenge preload failed (non-critical):', error.message);
        // This is non-critical, so we don't show an error to the user
    }
}

// Load statistics with progress tracking
async function loadStats() {
    try {
        const response = await fetch(`/api/stats/${currentStudentId}`);
        const stats = await response.json();
        
        if (!stats.error) {
            // Calculate progress metrics
            const completed = stats.total_challenges_completed || 0;
            const total = 27; // Total challenges in system
            const progress = Math.round((completed / total) * 100);
            const masteryPercent = Math.round((stats.average_mastery || 0) * 100);
            const speed = stats.learning_speed || 0;
            const mistakes = stats.total_mistakes || 0;
            const accuracy = completed > 0 ? Math.round((1 - (mistakes / (completed + mistakes))) * 100) : 0;
            
            // Update stat cards with progress indicators
            const challengesCard = document.getElementById('challengesCompleted');
            challengesCard.innerHTML = `
                <h3 class="stat-value">${completed}</h3>
                <p class="stat-label">Challenges Completed</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <p class="progress-text">${progress}% Complete</p>
            `;
            
            const masteryCard = document.getElementById('masteryLevel');
            masteryCard.innerHTML = `
                <h3 class="stat-value">${masteryPercent}%</h3>
                <p class="stat-label">Overall Mastery</p>
                <div class="mastery-indicator">
                    ${getMasteryBadge(masteryPercent)}
                </div>
            `;
            
            const speedCard = document.getElementById('learningSpeed');
            speedCard.innerHTML = `
                <h3 class="stat-value">${speed > 0 ? Math.round(speed) + 's' : '—'}</h3>
                <p class="stat-label">Avg Solution Time</p>
            `;
            
            const mistakesCard = document.getElementById('mistakesCount');
            mistakesCard.innerHTML = `
                <h3 class="stat-value">${mistakes}</h3>
                <p class="stat-label">Mistakes Made</p>
                <div class="accuracy-badge">Accuracy: ${accuracy}%</div>
            `;
            
            // Store stats for use in learning path and stats pages
            window.currentStats = stats;
            
            return stats;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Helper function to get mastery badge
function getMasteryBadge(percent) {
    if (percent >= 80) return '<span class="badge-excellent">🏆 Excellent</span>';
    if (percent >= 60) return '<span class="badge-good">👍 Good Progress</span>';
    if (percent >= 40) return '<span class="badge-improving">📈 Improving</span>';
    return '<span class="badge-learning">🌱 Keep Learning</span>';
}

// Load recommendations
async function loadRecommendations() {
    try {
        const response = await fetch(`/api/learning-path/${currentStudentId}`);
        const data = await response.json();
        
        const recommendationsList = document.getElementById('recommendationsList');
        
        if (!data.error && data.recommendations && data.recommendations.length > 0) {
            recommendationsList.innerHTML = data.recommendations.map(rec => 
                `<div class="recommendation-item">
                    <i class="fas fa-check-circle"></i>
                    ${rec}
                </div>`
            ).join('');
        } else {
            recommendationsList.innerHTML = '<div class="recommendation-item"><i class="fas fa-lightbulb"></i> Complete more challenges to get personalized recommendations!</div>';
        }
    } catch (error) {
        console.error('Error loading recommendations:', error);
        document.getElementById('recommendationsList').innerHTML = '<div class="recommendation-item">Unable to load recommendations</div>';
    }
}

// Load weak concepts
async function loadWeakConcepts() {
    try {
        const response = await fetch(`/api/profile/${currentStudentId}`);
        const profile = await response.json();
        
        const conceptsList = document.getElementById('weakConceptsList');
        
        if (!profile.error && profile.weakest_concepts && profile.weakest_concepts.length > 0) {
            const concepts = profile.weakest_concepts.slice(0, 5); // Show top 5
            conceptsList.innerHTML = concepts.map((concept, index) => 
                `<div class="concept-item">
                    <span class="concept-badge">${index + 1}</span>
                    <span class="concept-name">📚 ${concept.replace('_', ' ').charAt(0).toUpperCase() + concept.replace('_', ' ').slice(1)}</span>
                    <span class="concept-hint">Focus on mastering this concept</span>
                </div>`
            ).join('');
        } else {
            conceptsList.innerHTML = '<div class="concept-item"><span class="concept-badge">✓</span><span class="concept-name">Keep practicing! You\'re doing great!</span> 🚀</div>';
        }
    } catch (error) {
        console.error('Error loading concepts:', error);
        document.getElementById('weakConceptsList').innerHTML = '<div class="concept-item">Unable to load weak concepts</div>';
    }
}

// Load challenge with enhanced error handling
async function loadChallenge() {
    try {
        // Show loading state
        showChallengeLoading(true);
        console.log(`Loading challenge for student ${currentStudentId}...`);
        
        if (!currentStudentId) {
            throw new Error('Student ID not available. Please login again.');
        }
        
        const response = await fetch(`/api/challenge/${currentStudentId}`);
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.warn('Unauthorized access - redirecting to login');
                window.location.href = '/';
                return;
            }
            throw new Error(`Server error: HTTP ${response.status}`);
        }
        
        const challenge = await response.json();
        
        if (challenge.error) {
            console.error('Challenge error:', challenge.error);
            throw new Error(`Challenge API error: ${challenge.error}`);
        }
        
        if (!challenge.id) {
            throw new Error('Invalid challenge data received');
        }
        
        currentChallenge = challenge;
        currentSessionId = challenge.session_id;
        console.log(`Challenge loaded: ${challenge.title} (ID: ${challenge.id})`);
        
        // Update all challenge display elements
        updateChallengeDisplay(challenge);
        
        // Switch to challenge tab and hide loading
        switchTab('challenge');
        showChallengeLoading(false);
        console.log('Challenge display updated successfully');
    } catch (error) {
        console.error('Error loading challenge:', error);
        showChallengeLoading(false);
        showNotification(`Failed to load challenge: ${error.message}`, 'error');
    }
}

// Helper function to show/hide loading state
function showChallengeLoading(isLoading) {
    const challengeContainer = document.querySelector('.challenge-container');
    if (!challengeContainer) return;
    
    if (isLoading) {
        challengeContainer.style.opacity = '0.6';
        challengeContainer.style.pointerEvents = 'none';
    } else {
        challengeContainer.style.opacity = '1';
        challengeContainer.style.pointerEvents = 'auto';
    }
}

// Helper function to update challenge display
function updateChallengeDisplay(challenge) {
    try {
        // Update basic info
        const titleEl = document.getElementById('challengeTitle');
        const diffEl = document.getElementById('challengeDifficulty');
        const conceptEl = document.getElementById('challengeConcept');
        const descEl = document.getElementById('challengeDescription');
        const noteEl = document.getElementById('personalizedNoteText');
        
        if (titleEl) titleEl.textContent = challenge.title || 'Untitled';
        if (diffEl) diffEl.textContent = (challenge.difficulty || 'beginner').toUpperCase();
        if (conceptEl) conceptEl.textContent = (challenge.concept || 'coding').toUpperCase();
        if (descEl) descEl.textContent = challenge.description || 'No description provided';
        if (noteEl) noteEl.textContent = challenge.personalized_note || '';
        
        // Update examples
        const examplesList = document.getElementById('examplesList');
        if (examplesList) {
            if (challenge.examples && challenge.examples.length > 0) {
                examplesList.innerHTML = challenge.examples.map(ex => 
                    `<div class="example-item">
                        <strong>Input:</strong> <code>${escapeHtml(ex.input)}</code><br>
                        <strong>Output:</strong> <code>${escapeHtml(ex.output)}</code>
                    </div>`
                ).join('');
            } else {
                examplesList.innerHTML = '<div class="example-item">No examples provided</div>';
            }
        }
        
        // Update hints
        const hintsList = document.getElementById('hintsList');
        if (hintsList) {
            if (challenge.hints && challenge.hints.length > 0) {
                hintsList.innerHTML = challenge.hints.map(hint => 
                    `<li>${hint}</li>`
                ).join('');
            } else {
                hintsList.innerHTML = '<li>No hints available - try to solve it!</li>';
            }
        }
        
        // Update code editor
        const codeEditor = document.getElementById('codeEditor');
        if (codeEditor) {
            codeEditor.value = challenge.starter_code || '# Write your code here';
        }
        
        // Clear output and suggestions
        const outputArea = document.getElementById('outputArea');
        if (outputArea) outputArea.textContent = '';
        
        const suggestionsList = document.getElementById('suggestionsList');
        if (suggestionsList) suggestionsList.innerHTML = '';
        
        console.log('Challenge display updated');
    } catch (error) {
        console.error('Error updating challenge display:', error);
    }
}

// Helper function to show notifications
function showNotification(message, type = 'info') {
    // Create notification element if it doesn't exist
    let notifContainer = document.getElementById('notificationContainer');
    if (!notifContainer) {
        notifContainer = document.createElement('div');
        notifContainer.id = 'notificationContainer';
        notifContainer.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;max-width:400px;';
        document.body.appendChild(notifContainer);
    }
    
    const notif = document.createElement('div');
    notif.style.cssText = `
        padding:15px 20px;
        margin-bottom:10px;
        border-radius:8px;
        font-size:14px;
        animation:slideIn 0.3s ease-out;
        ${type === 'error' ? 'background:#fee;color:#c33;border:1px solid #fcc;' : 
          type === 'success' ? 'background:#efe;color:#363;border:1px solid #cfc;' : 
          'background:#eef;color:#33c;border:1px solid #ccf;'}
    `;
    notif.textContent = message;
    notifContainer.appendChild(notif);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notif.style.opacity = '0';
        setTimeout(() => notif.remove(), 300);
    }, 5000);
}

// Load a new different challenge with enhanced error handling
async function loadNewChallenge() {
    try {
        // Show loading state
        showChallengeLoading(true);
        console.log(`Loading new challenge for student ${currentStudentId}...`);
        
        if (!currentStudentId) {
            throw new Error('Student ID not available. Please login again.');
        }
        
        const response = await fetch(`/api/new-challenge/${currentStudentId}`);
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.warn('Unauthorized access - redirecting to login');
                window.location.href = '/';
                return;
            }
            throw new Error(`Server error: HTTP ${response.status}`);
        }
        
        const challenge = await response.json();
        
        if (challenge.error) {
            console.error('Challenge error:', challenge.error);
            throw new Error(`Challenge API error: ${challenge.error}`);
        }
        
        if (!challenge.id) {
            throw new Error('Invalid challenge data received');
        }
        
        currentChallenge = challenge;
        currentSessionId = challenge.session_id;
        console.log(`New challenge loaded: ${challenge.title} (ID: ${challenge.id})`);
        
        // Update all challenge display elements
        updateChallengeDisplay(challenge);
        
        // Switch to challenge tab and hide loading
        switchTab('challenge');
        showChallengeLoading(false);
        showNotification(`New challenge loaded: ${challenge.title}`, 'success');
        console.log('New challenge display updated successfully');
    } catch (error) {
        console.error('Error loading new challenge:', error);
        showChallengeLoading(false);
        showNotification(`Failed to load new challenge: ${error.message}`, 'error');
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
    try {
        const response = await fetch(`/api/learning-path/${currentStudentId}`);
        
        if (!response.ok) {
            throw new Error('Failed to load learning path');
        }
        
        const data = await response.json();
        const container = document.getElementById('learningPathContent');
        
        if (data.error) {
            container.innerHTML = '<p class="empty-state">📚 Complete some challenges to generate your personalized learning path!</p>';
            return;
        }
        
        let html = '<div class="learning-path-container">';
        
        // Learning path timeline
        if (data.learning_path && data.learning_path.length > 0) {
            html += '<div class="path-section">';
            html += '<h3><i class="fas fa-map"></i> Your Learning Journey</h3>';
            html += '<div class="timeline">';
            
            data.learning_path.forEach((concept, index) => {
                const conceptName = concept.replace('_', ' ').charAt(0).toUpperCase() + concept.replace('_', ' ').slice(1);
                html += `
                    <div class="timeline-node" data-step="${index + 1}">
                        <div class="node-number">${index + 1}</div>
                        <div class="node-label">${conceptName}</div>
                    </div>
                `;
            });
            
            html += '</div></div>';
        }
        
        // Practice plan with detailed recommendations
        if (data.practice_plan && data.practice_plan.length > 0) {
            html += '<div class="path-section"><h3><i class="fas fa-clipboard-list"></i> Your Practice Plan</h3>';
            html += '<div class="practice-cards">';
            
            data.practice_plan.forEach((plan, index) => {
                const masteryPercent = Math.round(plan.current_mastery * 100);
                const masteryColor = masteryPercent < 30 ? '#ff6b6b' : masteryPercent < 70 ? '#ffd93d' : '#6bcf7f';
                
                html += `
                    <div class="practice-card">
                        <div class="card-header">
                            <h4><span class="step-num">${index + 1}</span> ${plan.concept.replace('_', ' ').toUpperCase()}</h4>
                            <span class="mastery-percentage" style="color: ${masteryColor};">${masteryPercent}% 🎯</span>
                        </div>
                        
                        <div class="mastery-bar">
                            <div class="mastery-fill" style="width: ${masteryPercent}%; background-color: ${masteryColor};"></div>
                        </div>
                        
                        <div class="practice-suggestions">
                            <ul>
                                ${plan.suggested_practices.map(p => `<li><i class="fas fa-arrow-right"></i> ${p}</li>`).join('')}
                            </ul>
                        </div>
                        
                        <div class="time-estimate">
                            <i class="fas fa-hourglass-half"></i> Est. ${plan.estimated_time_hours}h
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div>';
        }
        
        // Recommendations
        if (data.recommendations && data.recommendations.length > 0) {
            html += '<div class="path-section"><h3><i class="fas fa-star"></i> Recommendations</h3>';
            html += '<div class="recommendations-list">';
            
            data.recommendations.forEach(rec => {
                html += `<div class="recommendation-card"><i class="fas fa-check-circle"></i> ${rec}</div>`;
            });
            
            html += '</div></div>';
        }
        
        // Next goals
        if (data.next_learning_goals && data.next_learning_goals.length > 0) {
            html += '<div class="path-section"><h3><i class="fas fa-bullseye"></i> Next Learning Goals</h3>';
            html += '<ul class="goals-list">';
            
            data.next_learning_goals.forEach(goal => {
                html += `<li><i class="fas fa-target"></i> ${goal}</li>`;
            });
            
            html += '</ul></div>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading learning path:', error);
        document.getElementById('learningPathContent').innerHTML = 
            '<p class="empty-state">Unable to load learning path. Please try again.</p>';
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
    const tabElement = document.getElementById(`${tabName}-tab`);
    if (tabElement) {
        tabElement.classList.add('active');
    } else {
        console.warn(`Tab element not found: ${tabName}-tab`);
        return;
    }
    
    // Load tab-specific data
    switch(tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'challenge':
            // If challenge is preloaded, display it immediately
            if (currentChallenge) {
                updateChallengeDisplay(currentChallenge);
                console.log('Displaying preloaded challenge');
            } else {
                // Otherwise load it
                loadChallenge();
            }
            break;
        case 'terminal':
            loadFreeCodeTerminal();
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
    
    // Run code button (challenges)
    document.getElementById('runCodeBtn').addEventListener('click', runCode);
    
    // New challenge button
    const newChallengeBtn = document.getElementById('newChallengeBtn');
    if (newChallengeBtn) {
        newChallengeBtn.addEventListener('click', loadNewChallenge);
    }
    
    // Free code editor buttons
    const runTerminalButton = document.getElementById('runTerminalCodeBtn');
    if (runTerminalButton) {
        runTerminalButton.addEventListener('click', runFreeCode);
    }
    
    const clearCodeBtn = document.getElementById('clearCodeBtn');
    if (clearCodeBtn) {
        clearCodeBtn.addEventListener('click', () => {
            document.getElementById('terminalCodeEditor').value = '';
        });
    }
    
    const clearOutputBtn = document.getElementById('clearOutputBtn');
    if (clearOutputBtn) {
        clearOutputBtn.addEventListener('click', () => {
            document.getElementById('terminalOutput').textContent = '';
        });
    }
    
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

// Load Free Code Terminal
async function loadFreeCodeTerminal
() {
    const response = await fetch(`/api/free-practice/${currentStudentId}`);
    const data = await response.json();
    
    if (!data.error) {
        // Initialize free code editor with starter code
        document.getElementById('terminalCodeEditor').value = data.starter_code || '# Write your Python code here\nprint("Hello, World!")';
        
        // Clear output
        document.getElementById('terminalOutput').textContent = '';
    }
}

// Run Free Code
async function runFreeCode() {
    const code = document.getElementById('terminalCodeEditor').value;
    const outputArea = document.getElementById('terminalOutput');
    
    if (!code.trim()) {
        outputArea.textContent = 'Error: Please write some code first!';
        return;
    }
    
    outputArea.textContent = 'Running...\n';
    
    try {
        const response = await fetch('/api/execute-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: code,
                language: 'python'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            outputArea.textContent = result.output || '(No output)';
        } else {
            outputArea.textContent = `Error:\n${result.error}`;
        }
    } catch (error) {
        outputArea.textContent = `Execution failed: ${error.message}`;
    }
}

// Export for debugging
window.app = {
    loadChallenge,
    loadLearningPath,
    loadMistakesHistory,
    loadStatistics,
    loadFreeCodeTerminal,
    runFreeCode
};