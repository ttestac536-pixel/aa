function escapeHtml(s = '') {
  return String(s).replace(/[&<>"'`]/g, (m) => {
    return ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;', '`':'&#96;' })[m];
  });
}

function toggleTheme() {
  document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
}
if (localStorage.getItem('theme') === 'dark') document.documentElement.classList.add('dark');

// =====================
//  TEXTAREA AUTO-GROW
// =====================
const textarea = document.getElementById("chat-input");
if (textarea) {
  textarea.addEventListener("input", () => {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  });
}

function handleKeyPress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function triggerFileUpload() {
  document.getElementById('fileInput').click();
}

document.getElementById('fileInput')?.addEventListener('change', function(e) {
  const file = e.target.files[0];
  if (file) {
    document.getElementById('fileName').textContent = file.name;
    sessionStorage.setItem('filename', file.name);
    document.getElementById('fileSize').textContent = (file.size / 1024 / 1024).toFixed(1) + ' MB';
    document.getElementById('filePreview').classList.remove('hidden');
  }
});

function removeFile() {
  document.getElementById('filePreview').classList.add('hidden');
  document.getElementById('fileInput').value = '';
  sessionStorage.removeItem('filename');
}

// Textarea Auto-resize
function adjustTextareaHeight(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// =====================
//  FILE UPLOAD PREVIEW
// =====================
const fileInput = document.getElementById("fileInput");
if (fileInput) {
  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    const preview = document.getElementById("file-preview");
    if (file && preview) preview.textContent = `📎 ${file.name}`;
  });
}

// =====================
//  TOAST NOTIFICATION
// =====================
function showToast(message) {
  // Create toast element
  const toast = document.createElement('div');
  toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in';
  toast.textContent = message;
  document.body.appendChild(toast);
  
  // Remove after 3 seconds
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

// =====================
//  GENERATE IAR CODE
// =====================
async function generateIARCode(userInstructions) {
  try {
    const response = await fetch(`${state.backendUrl}/generate-iar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        instructions: userInstructions
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'IAR generation failed');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('IAR Generation Error:', error);
    throw error;
  }
}

// =====================
//  CHAT MESSAGE RENDER
// =====================
function renderMessage(role, content, markdown = true) {
  const chatContainer = document.getElementById("chatMessages");
  if (!chatContainer) return;

  const msgDiv = document.createElement("div");
  msgDiv.className = `message-stream max-w-4xl mx-auto mb-8`;
  
  if (role === 'user') {
    msgDiv.innerHTML = `
      <div class="flex items-start space-x-4 justify-end">
        <div class="flex-1 text-right">
          <div class="inline-block neuro-card bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-2xl px-6 py-4 max-w-2xl">
            <p class="leading-relaxed custom-wrap">${escapeHtml(content)}</p>
          </div>
          <div class="flex items-center justify-end mt-2 space-x-3">
            <span class="text-xs text-neutral-500">${state.username} • ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            <button onclick="copyMessage(this)" class="text-xs text-blue-600 hover:text-blue-700">Copy</button>
          </div>
        </div>
        <div class="w-10 h-10 neuro-card bg-neutral-200 rounded-full flex items-center justify-center">
          <span class="text-sm font-medium">You</span>
        </div>
      </div>
    `;
  } else {
    const formattedContent = markdown ? beautifyMessage(content) : escapeHtml(content);
    msgDiv.innerHTML = `
      <div class="flex items-start space-x-4">
        <div class="w-10 h-10 neuro-card bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
          <span class="text-white text-sm">🚀</span>
        </div>
        <div class="flex-1">
          <div class="neuro-card rounded-2xl px-6 py-4 max-w-2xl">
            ${formattedContent}
          </div>
          <div class="mt-2">
            <button onclick="copyMessage(this)" class="text-xs text-blue-600 hover:text-blue-700">Copy</button>
          </div>
        </div>
      </div>
    `;
  }

  chatContainer.appendChild(msgDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// =====================
//  TYPING INDICATOR
// =====================
function showTypingIndicator() {
  const chatContainer = document.getElementById("chatMessages");
  const typingDiv = document.createElement('div');
  typingDiv.id = 'typing-indicator';
  typingDiv.className = 'message-stream max-w-4xl mx-auto mb-8';
  typingDiv.innerHTML = `
    <div class="flex items-start space-x-4">
      <div class="w-10 h-10 neuro-card bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
        <span class="text-white text-sm">🚀</span>
      </div>
      <div class="flex-1">
        <div class="neuro-card rounded-2xl px-6 py-4">
          <div class="flex space-x-2">
            <div class="typing-dots w-2 h-2 bg-neutral-400 rounded-full"></div>
            <div class="typing-dots w-2 h-2 bg-neutral-400 rounded-full"></div>
            <div class="typing-dots w-2 h-2 bg-neutral-400 rounded-full"></div>
          </div>
        </div>
      </div>
    </div>
  `;
  chatContainer.appendChild(typingDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeTypingIndicator() {
  const typingDiv = document.getElementById('typing-indicator');
  if (typingDiv) typingDiv.remove();
}

// =====================
//  MAIN SEND MESSAGE
// =====================
let isSending = false;

async function sendMessage(customMessage = null) {
  const input = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');

  if (isSending) return;
  isSending = true;

  sendBtn.disabled = true;
  input.disabled = true;

  const message = customMessage || input.value.trim();
  
  if (!message) {
    isSending = false;
    sendBtn.disabled = false;
    input.disabled = false;
    return;
  }

  // Hide hero section
  const heroSection = document.getElementById('heroSection');
  if (heroSection) heroSection.style.display = 'none';

  const chatContainer = document.getElementById('chatMessages');
  
  // Add user message
  renderMessage('user', message, false);
  
  // Add to conversation history
  state.conversationHistory.push({
    role: 'user',
    content: message
  });

  input.value = '';
  adjustTextareaHeight(input);
  
  // Show typing indicator
  showTypingIndicator();

  try {
    // Call backend chat endpoint
    const response = await fetch(`${state.backendUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: state.session_id,
        message: message
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const assistantMessage = data.response;

    // Add to conversation history
    state.conversationHistory.push({
      role: 'assistant',
      content: assistantMessage
    });

    // Remove typing indicator
    removeTypingIndicator();

    // Add AI response
    renderMessage('assistant', assistantMessage, true);

    // Check if user wants to generate IAR
    if (assistantMessage.toLowerCase().includes('generate') || 
        assistantMessage.toLowerCase().includes('ready') ||
        message.toLowerCase().includes('generate iar')) {
      
      // Show option to generate
      const optionDiv = document.createElement('div');
      optionDiv.className = 'message-stream max-w-4xl mx-auto mb-8';
      optionDiv.innerHTML = `
        <div class="flex justify-start space-x-3">
          <button onclick="proceedWithIARGeneration()" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            🔧 Generate IAR Code
          </button>
          <button onclick="askMoreQuestions()" class="px-4 py-2 bg-gray-300 text-gray-800 rounded-lg hover:bg-gray-400 transition">
            Ask More
          </button>
        </div>
      `;
      chatContainer.appendChild(optionDiv);
    }

  } catch (err) {
    console.error("Chat error:", err);
    removeTypingIndicator();
    renderMessage('assistant', `❌ Error: ${err.message}`, false);
    showErrorModal(`Failed to get response: ${err.message}`);
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

// =====================
//  IAR GENERATION FLOW
// =====================
async function proceedWithIARGeneration() {
  showTypingIndicator();

  try {
    // Combine all user messages to create full instructions
    const userMessages = state.conversationHistory
      .filter(msg => msg.role === 'user')
      .map(msg => msg.content)
      .join('\n');

    const response = await generateIARCode(userMessages);

    removeTypingIndicator();

    if (response.success) {
      // Show generated IAR preview
      const previewDiv = document.createElement('div');
      previewDiv.className = 'message-stream max-w-4xl mx-auto mb-8';
      previewDiv.innerHTML = `
        <div class="flex items-start space-x-4">
          <div class="w-10 h-10 neuro-card bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center">
            <span class="text-white text-sm">✅</span>
          </div>
          <div class="flex-1">
            <div class="neuro-card rounded-2xl px-6 py-4 max-w-2xl">
              <p class="font-semibold mb-4">✨ IAR Code Generated Successfully!</p>
              <p class="text-sm text-gray-600 mb-4">
                Your integration code is ready. 
                <a href="${response.iar_filepath}" download class="text-blue-600 underline">Download IAR File</a>
              </p>
              <details class="mb-4">
                <summary class="cursor-pointer text-sm font-semibold text-blue-600 hover:text-blue-700">
                  View Code Preview
                </summary>
                <pre class="mt-2 bg-gray-900 text-green-400 p-3 rounded text-xs overflow-auto max-h-40">
${escapeHtml(response.iar_code.substring(0, 500))}...
                </pre>
              </details>
              <div class="flex gap-2">
                <button onclick="deployIARToOIC('${response.iar_filepath}', '${response.model}')" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition">
                  🚀 Deploy to OIC
                </button>
                <button onclick="refineIAR()" class="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition">
                  ✏️ Refine Code
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
      document.getElementById('chatMessages').appendChild(previewDiv);
      document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
    } else {
      throw new Error(response.error || 'Unknown error');
    }

  } catch (err) {
    removeTypingIndicator();
    console.error('IAR Generation failed:', err);
    renderMessage('assistant', `❌ IAR Generation Failed: ${err.message}`, false);
    showErrorModal(`Failed to generate IAR: ${err.message}`);
  }
}

async function deployIARToOIC(iarFilepath, model) {
  showTypingIndicator();

  try {
    // First, get available OIC instances
    const instanceResponse = await fetch(`${state.backendUrl}/oic-instances`);
    const instanceData = await instanceResponse.json();

    removeTypingIndicator();

    // Show instance selection dialog
    const instances = Object.entries(instanceData.instances || {});
    if (instances.length === 0) {
      throw new Error('No OIC instances configured');
    }

    // Create selection UI
    const selectionDiv = document.createElement('div');
    selectionDiv.className = 'message-stream max-w-4xl mx-auto mb-8';
    
    let optionsHTML = '<div class="flex flex-col gap-2">';
    instances.forEach(([name, url]) => {
      optionsHTML += `
        <button onclick="confirmDeploy('${iarFilepath}', '${name}')" 
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-left">
          ☁️ ${name} (${url})
        </button>
      `;
    });
    optionsHTML += '</div>';

    selectionDiv.innerHTML = `
      <div class="flex items-start space-x-4">
        <div class="w-10 h-10 neuro-card bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
          <span class="text-white text-sm">☁️</span>
        </div>
        <div class="flex-1">
          <div class="neuro-card rounded-2xl px-6 py-4">
            <p class="font-semibold mb-4">Select OIC Instance to Deploy:</p>
            ${optionsHTML}
          </div>
        </div>
      </div>
    `;

    document.getElementById('chatMessages').appendChild(selectionDiv);
    document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;

  } catch (err) {
    removeTypingIndicator();
    console.error('OIC deployment failed:', err);
    renderMessage('assistant', `❌ Deployment Error: ${err.message}`, false);
  }
}

async function confirmDeploy(iarFilepath, instanceName) {
  showTypingIndicator();

  try {
    const deployResponse = await fetch(`${state.backendUrl}/deploy-iar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        iar_filepath: iarFilepath,
        oic_instance: instanceName,
        integration_name: `Integration_${Date.now()}`
      })
    });

    if (!deployResponse.ok) {
      throw new Error('Deployment failed');
    }

    const deployData = await deployResponse.json();
    removeTypingIndicator();

    const successDiv = document.createElement('div');
    successDiv.className = 'message-stream max-w-4xl mx-auto mb-8';
    successDiv.innerHTML = `
      <div class="flex items-start space-x-4">
        <div class="w-10 h-10 neuro-card bg-gradient-to-r from-green-500 to-emerald-500 rounded-full flex items-center justify-center">
          <span class="text-white text-sm">🎉</span>
        </div>
        <div class="flex-1">
          <div class="neuro-card rounded-2xl px-6 py-4 max-w-2xl">
            <p class="font-semibold mb-2">✅ Deployment Successful!</p>
            <p class="text-sm mb-2">Instance: <strong>${instanceName}</strong></p>
            <p class="text-sm mb-4">Integration: <strong>${deployData.integration_name}</strong></p>
            <a href="${deployData.oic_url}" target="_blank" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 inline-block">
              🔗 Open OIC Console
            </a>
          </div>
        </div>
      </div>
    `;

    document.getElementById('chatMessages').appendChild(successDiv);
    document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
    
    showToast('✅ Integration deployed successfully!');

  } catch (err) {
    removeTypingIndicator();
    console.error('Deployment error:', err);
    renderMessage('assistant', `❌ Deployment Error: ${err.message}`, false);
    showErrorModal(`Failed to deploy: ${err.message}`);
  }
}

function askMoreQuestions() {
  sendMessage('What other information do you need?');
}

function refineIAR() {
  sendMessage('Can you refine the IAR code based on my requirements?');
}

// =====================
//  INIT ON LOAD
// =====================
document.getElementById("send-btn")?.addEventListener("click", sendMessage);
document.getElementById("messageInput")?.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});