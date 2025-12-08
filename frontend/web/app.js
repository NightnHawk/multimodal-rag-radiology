// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const queryButton = document.getElementById('queryButton');
const regenerateButton = document.getElementById('regenerateButton');
const statusBar = document.getElementById('statusBar');
const statusText = document.getElementById('statusText');
const resultsSection = document.getElementById('resultsSection');
const generatedDescription = document.getElementById('generatedDescription');
const retrievedDocuments = document.getElementById('retrievedDocuments');
const qualityIndicator = document.getElementById('qualityIndicator');
const qualityBadge = document.getElementById('qualityBadge');
const qualityScore = document.getElementById('qualityScore');
const useRetrievedImages = document.getElementById('useRetrievedImages');

let currentQueryId = null;
let currentFile = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAPIHealth();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // File input
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // Query button
    queryButton.addEventListener('click', handleQuery);
    
    // Regenerate button
    regenerateButton.addEventListener('click', handleRegenerate);
}

// Check API health
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            updateStatus('API connected', 'success');
        } else {
            updateStatus('API connection failed', 'error');
        }
    } catch (error) {
        updateStatus('API not available. Make sure the backend is running.', 'error');
    }
}

// Handle file selection
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        currentFile = file;
        updateStatus(`Selected: ${file.name}`, 'success');
        queryButton.disabled = false;
    }
}

// Drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const file = e.dataTransfer.files[0];
    if (file) {
        fileInput.files = e.dataTransfer.files;
        currentFile = file;
        updateStatus(`Selected: ${file.name}`, 'success');
        queryButton.disabled = false;
    }
}

// Handle query
async function handleQuery() {
    if (!currentFile) {
        alert('Please select a file first');
        return;
    }
    
    updateStatus('Processing image...', 'processing');
    queryButton.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('use_retrieved_images', useRetrievedImages.checked);
        
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }
        
        const result = await response.json();
        currentQueryId = result.query_id;
        
        displayResults(result);
        updateStatus('Analysis complete', 'success');
        
    } catch (error) {
        updateStatus(`Error: ${error.message}`, 'error');
        alert(`Error: ${error.message}`);
    } finally {
        queryButton.disabled = false;
    }
}

// Handle regenerate
async function handleRegenerate() {
    if (!currentQueryId) {
        alert('No query to regenerate');
        return;
    }
    
    updateStatus('Regenerating answer...', 'processing');
    regenerateButton.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('query_id', currentQueryId);
        if (currentFile) {
            formData.append('file', currentFile);
        }
        formData.append('use_same_retrieval', 'false');
        
        const response = await fetch(`${API_BASE_URL}/query/regenerate`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Regeneration failed');
        }
        
        const result = await response.json();
        currentQueryId = result.query_id;
        
        displayResults(result);
        updateStatus('Regeneration complete', 'success');
        
    } catch (error) {
        updateStatus(`Error: ${error.message}`, 'error');
        alert(`Error: ${error.message}`);
    } finally {
        regenerateButton.disabled = false;
    }
}

// Display results
function displayResults(result) {
    resultsSection.style.display = 'block';
    
    // Display generated description
    generatedDescription.textContent = result.generated_description || 'No description generated';
    
    // Display quality indicator
    if (result.quality_score !== null) {
        const score = (result.quality_score * 100).toFixed(1);
        qualityScore.textContent = `Quality Score: ${score}%`;
        
        if (result.quality_approved) {
            qualityBadge.textContent = 'APPROVED';
            qualityBadge.className = 'quality-badge approved';
        } else {
            qualityBadge.textContent = 'NEEDS REVIEW';
            qualityBadge.className = 'quality-badge rejected';
        }
        qualityIndicator.style.display = 'flex';
    } else {
        qualityIndicator.style.display = 'none';
    }
    
    // Display retrieved documents
    if (result.retrieved_documents && result.retrieved_documents.length > 0) {
        retrievedDocuments.innerHTML = result.retrieved_documents.map((doc, index) => `
            <div class="retrieved-doc">
                <h4>Reference Case ${index + 1}</h4>
                <div class="score">Similarity Score: ${doc.score.toFixed(4)}</div>
                <div class="desc">
                    <strong>Short Description:</strong> ${doc.short_description || 'N/A'}<br>
                    <strong>Full Description:</strong> ${doc.full_description || 'N/A'}
                </div>
            </div>
        `).join('');
    } else {
        retrievedDocuments.innerHTML = '<p>No similar documents found.</p>';
    }
    
    // Show regenerate button if quality is low
    if (!result.quality_approved) {
        regenerateButton.style.display = 'inline-block';
    }
}

// Update status
function updateStatus(message, type = '') {
    statusText.textContent = message;
    statusBar.className = `status-bar ${type}`;
}

