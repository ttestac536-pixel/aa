const API_URL = 'http://localhost:5000/api';
let currentFileId = null;
let currentIntegrationId = null;

// ==================== Tab Navigation ====================
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
}

// ==================== CSV Upload ====================
const uploadArea = document.getElementById('uploadArea');
const csvFile = document.getElementById('csvFile');

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.background = '#f0e8ff';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.background = '#f9f7ff';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        csvFile.files = files;
        showFileName(files[0].name);
    }
});

// Click to select
uploadArea.addEventListener('click', () => {
    csvFile.click();
});

csvFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        showFileName(e.target.files[0].name);
    }
});

function showFileName(fileName) {
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = `<div class="status info">📄 Selected: <strong>${fileName}</strong></div>`;
}

async function uploadCSV() {
    if (!csvFile.files.length) {
        alert('Please select a CSV file');
        return;
    }

    const formData = new FormData();
    formData.append('file', csvFile.files[0]);

    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.innerHTML = '<div class="status info"><span class="loading"></span>Uploading...</div>';

    try {
        const response = await fetch(`${API_URL}/upload-csv`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            currentFileId = data.file_id;
            statusDiv.innerHTML = `<div class="status success">✅ ${data.message}</div>`;
            console.log('File ID:', currentFileId);
        } else {
            statusDiv.innerHTML = `<div class="status error">❌ ${data.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="status error">❌ Upload failed: ${error.message}</div>`;
    }
}

// ==================== Generate Integration ====================
async function generateIntegration() {
    if (!currentFileId) {
        alert('Please upload a CSV file first');
        return;
    }

    const statusDiv = document.getElementById('generateStatus');
    statusDiv.innerHTML = '<div class="status info"><span class="loading"></span>Generating integration...</div>';

    try {
        const response = await fetch(`${API_URL}/generate-integration`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ file_id: currentFileId })
        });

        const data = await response.json();

        if (response.ok) {
            currentIntegrationId = data.integration_id;
            statusDiv.innerHTML = `<div class="status success">✅ ${data.message}</div>`;
            console.log('Integration ID:', currentIntegrationId);
        } else {
            statusDiv.innerHTML = `<div class="status error">❌ ${data.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="status error">❌ Generation failed: ${error.message}</div>`;
    }
}

// ==================== Deploy Integration ====================
async function deployIntegration() {
    if (!currentIntegrationId) {
        alert('Please generate an integration first');
        return;
    }

    const statusDiv = document.getElementById('deployStatus');
    statusDiv.innerHTML = '<div class="status info"><span class="loading"></span>Deploying to OIC...</div>';

    try {
        const response = await fetch(`${API_URL}/deploy-integration`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ integration_id: currentIntegrationId })
        });

        const data = await response.json();

        if (response.ok) {
            statusDiv.innerHTML = `<div class="status success">✅ ${data.message}</div>`;
            
            // Show validation link
            const linkDiv = document.getElementById('validationLink');
            linkDiv.innerHTML = `
                <div class="validation-link">
                    <p><strong>🔗 Validation Link:</strong></p>
                    <a href="/validate/${currentIntegrationId}" target="_blank">
                        Click here to validate and activate the integration
                    </a>
                    <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                        Share this link with your team to review mappings and activate.
                    </p>
                </div>
            `;
        } else {
            statusDiv.innerHTML = `<div class="status error">❌ ${data.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="status error">❌ Deployment failed: ${error.message}</div>`;
    }
}

// Health check on page load
window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_URL}/health`);
        if (response.ok) {
            console.log('✅ Backend is connected');
        }
    } catch (error) {
        console.error('❌ Backend connection failed:', error);
    }
});