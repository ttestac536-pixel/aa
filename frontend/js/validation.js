// ==================== Validation Portal ====================
let integrationData = {};

// Get integration ID from URL
function getIntegrationIdFromURL() {
    const path = window.location.pathname;
    return path.split('/').pop();
}

// Load integration data on page load
async function loadIntegrationData() {
    const integrationId = getIntegrationIdFromURL();
    
    if (!integrationId) {
        showMessage('error', 'Integration ID not found in URL');
        return;
    }

    const loadingDiv = document.getElementById('loading');
    loadingDiv.style.display = 'block';

    try {
        const response = await fetch(`http://localhost:5000/api/integration-status/${integrationId}`);
        const data = await response.json();

        if (response.ok) {
            integrationData = data;
            loadingDiv.style.display = 'none';
            renderValidationPortal();
        } else {
            loadingDiv.style.display = 'none';
            showMessage('error', data.error || 'Failed to load integration');
        }
    } catch (error) {
        loadingDiv.style.display = 'none';
        showMessage('error', `Failed to load data: ${error.message}`);
    }
}

// Render the validation portal
function renderValidationPortal() {
    const container = document.getElementById('validationContainer');
    
    const statusColor = integrationData.status === 'ACTIVE' ? '#28a745' : '#ffc107';
    const statusIcon = integrationData.status === 'ACTIVE' ? '✅' : '⏳';

    container.innerHTML = `
        <div class="validation-card">
            <h2>Integration: ${integrationData.integration_id}</h2>
            
            <div class="status-badge" style="background-color: ${statusColor};">
                ${statusIcon} Status: ${integrationData.status}
            </div>

            <div class="section">
                <h3>📋 Connection Validation</h3>
                <div class="validation-item ${integrationData.connections_validated ? 'validated' : 'pending'}">
                    <span class="checkbox">${integrationData.connections_validated ? '✓' : '○'}</span>
                    <span>SAP Connection</span>
                    <button class="btn-small" onclick="validateConnection('sap')">Test</button>
                </div>
                <div class="validation-item ${integrationData.connections_validated ? 'validated' : 'pending'}">
                    <span class="checkbox">${integrationData.connections_validated ? '✓' : '○'}</span>
                    <span>SFTP Connection</span>
                    <button class="btn-small" onclick="validateConnection('sftp')">Test</button>
                </div>
                <div class="validation-item ${integrationData.connections_validated ? 'validated' : 'pending'}">
                    <span class="checkbox">${integrationData.connections_validated ? '✓' : '○'}</span>
                    <span>Oracle Financials Connection</span>
                    <button class="btn-small" onclick="validateConnection('oracle')">Test</button>
                </div>
            </div>

            <div class="section">
                <h3>🗺️ Mapping Validation</h3>
                <div class="validation-item ${integrationData.mappings_validated ? 'validated' : 'pending'}">
                    <span class="checkbox">${integrationData.mappings_validated ? '✓' : '○'}</span>
                    <span>CSV to Oracle GL Mapping</span>
                    <button class="btn-small" onclick="viewMappings()">View</button>
                </div>
                <div class="validation-item ${integrationData.mappings_validated ? 'validated' : 'pending'}">
                    <span class="checkbox">${integrationData.mappings_validated ? '✓' : '○'}</span>
                    <span>Data Transformation Rules</span>
                    <button class="btn-small" onclick="viewTransformations()">View</button>
                </div>
            </div>

            <div class="section">
                <h3>📊 Sample Data Preview</h3>
                <button class="btn-small" onclick="viewSampleData()">View Sample Data</button>
            </div>

            <div class="section">
                <h3>📝 Deployment Information</h3>
                <p><strong>Deployed:</strong> ${new Date(integrationData.deployment_date).toLocaleString()}</p>
                <p><strong>Integration ID:</strong> <code>${integrationData.integration_id}</code></p>
            </div>

            <div class="section actions">
                ${integrationData.status !== 'ACTIVE' ? `
                    <button class="btn btn-success" onclick="activateIntegration()">🚀 Activate Integration</button>
                ` : `
                    <button class="btn btn-secondary" onclick="deactivateIntegration()">⏹️ Deactivate Integration</button>
                `}
                <button class="btn btn-primary" onclick="downloadConfig()">📥 Download Config</button>
            </div>
        </div>
    `;

    // Show modals for details
    renderMappingsModal();
    renderTransformationsModal();
    renderSampleDataModal();
}

// Validate connection
async function validateConnection(connectionType) {
    const btn = event.target;
    btn.disabled = true;
    btn.innerText = 'Testing...';

    try {
        const response = await fetch('http://localhost:5000/api/validate-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                integration_id: integrationData.integration_id,
                connection_type: connectionType
            })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('success', `✅ ${connectionType.toUpperCase()} connection is valid!`);
        } else {
            showMessage('error', `❌ ${connectionType.toUpperCase()} connection failed: ${data.error}`);
        }
    } catch (error) {
        showMessage('error', `Connection test failed: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.innerText = 'Test';
    }
}

// View mappings
function viewMappings() {
    document.getElementById('mappingsModal').style.display = 'block';
}

// View transformations
function viewTransformations() {
    document.getElementById('transformationsModal').style.display = 'block';
}

// View sample data
function viewSampleData() {
    document.getElementById('sampleDataModal').style.display = 'block';
}

// Render modals
function renderMappingsModal() {
    const modal = document.getElementById('mappingsModal');
    const mappings = [
        { csv: 'journal_name', oracle: 'JE_BATCH_ID' },
        { csv: 'period', oracle: 'PERIOD_NAME' },
        { csv: 'account_code', oracle: 'CODE_COMBINATION_ID' },
        { csv: 'debit_amount', oracle: 'ENTERED_DR_AMOUNT' },
        { csv: 'credit_amount', oracle: 'ENTERED_CR_AMOUNT' },
        { csv: 'description', oracle: 'DESCRIPTION' },
        { csv: 'currency', oracle: 'CURRENCY_CODE' }
    ];

    let table = '<table class="mapping-table"><tr><th>CSV Field</th><th>Oracle GL Field</th></tr>';
    mappings.forEach(m => {
        table += `<tr><td>${m.csv}</td><td>${m.oracle}</td></tr>`;
    });
    table += '</table>';

    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.closest('.modal').style.display='none'">&times;</span>
            <h2>Field Mappings</h2>
            ${table}
        </div>
    `;
}

function renderTransformationsModal() {
    const modal = document.getElementById('transformationsModal');
    const transformations = `
        <ul>
            <li><strong>Date Format:</strong> Converting MM/DD/YYYY to YYYY-MM-DD</li>
            <li><strong>Amount Validation:</strong> Ensuring debit/credit balance</li>
            <li><strong>Currency Conversion:</strong> Auto-detect and convert to transaction currency</li>
            <li><strong>Account Code Lookup:</strong> Validating against GL chart of accounts</li>
            <li><strong>Batch Processing:</strong> Grouping by journal name and period</li>
        </ul>
    `;

    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.closest('.modal').style.display='none'">&times;</span>
            <h2>Data Transformation Rules</h2>
            ${transformations}
        </div>
    `;
}

function renderSampleDataModal() {
    const modal = document.getElementById('sampleDataModal');
    const sampleHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.closest('.modal').style.display='none'">&times;</span>
            <h2>Sample Data Preview</h2>
            <table class="data-table">
                <tr>
                    <th>Journal Name</th>
                    <th>Period</th>
                    <th>Account Code</th>
                    <th>Debit</th>
                    <th>Credit</th>
                    <th>Description</th>
                </tr>
                <tr>
                    <td>JNL_001</td>
                    <td>JAN-2025</td>
                    <td>1000</td>
                    <td>10,000.00</td>
                    <td>-</td>
                    <td>Monthly expense</td>
                </tr>
                <tr>
                    <td>JNL_001</td>
                    <td>JAN-2025</td>
                    <td>2000</td>
                    <td>-</td>
                    <td>10,000.00</td>
                    <td>Monthly expense</td>
                </tr>
            </table>
        </div>
    `;

    modal.innerHTML = sampleHTML;
}

// Activate integration
async function activateIntegration() {
    if (!confirm('Are you sure you want to activate this integration?')) return;

    try {
        const response = await fetch('http://localhost:5000/api/activate-integration', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ integration_id: integrationData.integration_id })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('success', '✅ Integration activated successfully!');
            integrationData.status = 'ACTIVE';
            setTimeout(() => location.reload(), 1500);
        } else {
            showMessage('error', `❌ Activation failed: ${data.error}`);
        }
    } catch (error) {
        showMessage('error', `Activation failed: ${error.message}`);
    }
}

// Deactivate integration
async function deactivateIntegration() {
    if (!confirm('Are you sure you want to deactivate this integration?')) return;

    try {
        const response = await fetch('http://localhost:5000/api/deactivate-integration', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ integration_id: integrationData.integration_id })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('success', '✅ Integration deactivated successfully!');
            integrationData.status = 'INACTIVE';
            setTimeout(() => location.reload(), 1500);
        } else {
            showMessage('error', `❌ Deactivation failed: ${data.error}`);
        }
    } catch (error) {
        showMessage('error', `Deactivation failed: ${error.message}`);
    }
}

// Download configuration
function downloadConfig() {
    const config = {
        integration_id: integrationData.integration_id,
        status: integrationData.status,
        deployment_date: integrationData.deployment_date,
        connections: ['SAP', 'SFTP', 'Oracle Financials'],
        mappings: ['CSV to Oracle GL']
    };

    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${integrationData.integration_id}_config.json`;
    link.click();
}

// Show message
function showMessage(type, message) {
    const messageDiv = document.getElementById('message');
    messageDiv.className = `message ${type}`;
    messageDiv.innerText = message;
    messageDiv.style.display = 'block';
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Load data when page loads
window.addEventListener('load', loadIntegrationData);
