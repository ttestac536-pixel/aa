// ===============================
// COMMON JS (Unified Session + State Management)
// ===============================

// Backend URL for OIC integration
const baseurl = "http://80.225.238.179:5003";
const BACKEND_URL = "http://localhost:5000/api"; // Your Python Flask backend
const SELECTED_TEMPLATE_KEY = 1;

const state = {
  envLoaded: true,
  baseUrl: baseurl,
  backendUrl: BACKEND_URL,
  userIdHeader: '',
  limit: 10,
  offset: 0,
  searchParam: '',
  total: null,
  items: [],
  editingId: null,
  syncId: '',
  session_id: '',
  username:'',
  currentHash:'',
  initialMessageSent: false,
  request_id: '',
  userId:'',
  selectedTemplateId: null,
  conversationHistory: [], // Chat history for LLM context
  headers: {
    "Content-Type": "application/json",
    "X-OUScribe-Agent-Session-ID": "",
    "X-OUScribe-Agent-Request-ID": "",
    "X-OUScribe-Agent-User-ID": "",
    "X-OUScribe-Agent-User-Name": "",
    "X-OUScribe-Agent-Template-ID":null
  },
};

// ===============================
// COMMON JS (Unified Session + State Management)
// ===============================

// ===============================
// HASH PARSING + SESSION SETUP
// ===============================

function parseBase64Hash() {
  debugger
  
  const hashValue = window.location.hash.substring(1);
  
  // const decodedHash = atob(hashValue);
  // const parsedData = JSON.parse(decodedHash);
  // if (!parsedData) return null;
  try {
    const decoded = atob(hashValue);
    try {
      return JSON.parse(decoded);
    } catch {
      return { session_id: decoded };
    }
  } catch (e) {
    console.error("Invalid hash/base64:", e);
    return null;
  }
}

function initializeSessionFromHash() {
  
  const data = parseBase64Hash();
  if (data) {
    Object.entries(data).forEach(([key, val]) => sessionStorage.setItem(key, val));
  }
  
    sessionStorage.setItem('logged',true);
  

  if (data?.defaultValue) {
    state.defaultValue = data.defaultValue; // store default value for later use
  } else {
      state.defaultValue = "FDD"; // fallback if none
  }

  const session_id =  data?.sessionId || sessionStorage.getItem("session_id") || generateUUIDFallback();
  const userId = data?.userId || sessionStorage.getItem("userId") ||  "guest@domain.com";
  const userName = data?.username || sessionStorage.getItem("username") || "guest";
  // sessionStorage.setItem("session_id", session_id);
  // sessionStorage.setItem("userId", userId);
  // sessionStorage.setItem("username",userName);
  state.session_id = session_id;
  state.userIdHeader = userId;
  state.userId = userId;
  state.username = userName;
  document.querySelector('#userid').innerHTML =state.username;
  updateHeaders();
  updateUserDisplay(userId);
  updateSessionDisplay(session_id);

  console.log("✅ Session initialized:", { session_id, userId });

  ensureHashReflectsCurrentSession();
}

function ensureHashReflectsCurrentSession() {
  const payload = { session_id: state.session_id, userId: state.userIdHeader,username:state.username };
  const encoded = btoa(JSON.stringify(payload));
  if (window.location.hash.substring(1) !== encoded) {
    history.replaceState(null, "", `${window.location.pathname}#${encoded}`);
  }
}


// --- TEMPLATE DROPDOWN INIT ---



function updateHeaders() {
  state.headers["X-OUScribe-Agent-Session-ID"] = state.session_id || "session__1";
  state.headers["X-OUScribe-Agent-Request-ID"] = generateRequestId() || "request__1";
  state.headers["X-OUScribe-Agent-User-ID"] = state.userIdHeader || "guest@email.com";
  state.headers["X-OUScribe-Agent-User-Name"] = state.username || "Guest";
}

function updateUserDisplay(email) {
  const namePart = email?.split("@")[0] || "Guest";
  const cleanName = namePart.split(/[._]/)[0];
  const formattedName = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);

  const userIdEl = document.getElementById("user-id");
  const userEmailEl = document.getElementById("userEmail");
  const userNameEl = document.getElementById("userName");

  if (userIdEl) userIdEl.innerText = formattedName;
  if (userEmailEl) {
    userEmailEl.textContent = email;
    userEmailEl.title = email;
  }
  if (userNameEl) {
    userNameEl.textContent = formattedName;
    userNameEl.title = formattedName;
  }
  // state.username = formattedName;
  const userBlockEl = document.getElementById("username");
  if(userBlockEl)
  {
    userBlockEl.innerHTML = formattedName.charAt(0)
  }
  const userNameSignEl = document.getElementById("user");
  if(userNameSignEl){
  userNameSignEl.textContent = "Welcome, "+state.username;
  }
  
  
}

function updateSessionDisplay(sessionId) {
  document.querySelectorAll(".sessionId, #sessionid").forEach(el => {
    el.textContent = sessionId;
    el.title = sessionId;
  });
}

document.querySelector('#adminLink')?.addEventListener('click', () => {
  state.initialMessageSent = true;
  navigateTo('admin.html');
});

document.querySelector('#chatLink')?.addEventListener('click', () => {
  state.initialMessageSent = true;
  navigateTo('chat.html');
});

// ===============================
// ID + REQUEST UTILITIES
// ===============================

function generateRequestId() {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substr(2, 5);
  return timestamp + random;
}

function generateUUIDFallback() {
  const template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx";
  return template.replace(/[xy]/g, c => {
    const r = crypto.getRandomValues(new Uint8Array(1))[0] & 15;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function generateSecureUUID() {
  return generateUUIDFallback();
}

// ===============================
// NEW CHAT SESSION (Keeps userId)
// ===============================

function startNewChat() {
  const newSession = generateSecureUUID();
  state.session_id = newSession;
  sessionStorage.setItem("session_id", newSession);
  updateHeaders();
  updateSessionDisplay(newSession);
  
  

  const payload = { session_id: newSession, userId: state.userIdHeader };
  const encoded = btoa(JSON.stringify(payload));
  window.location.hash = encoded;
  window.location.pathname = "/ou-scribe/chat.html";
  window.open("chat.html#" + encoded, "_self");
  boolValue = sessionStorage.getItem("logged");
   location.reload();
   navigateTo('chat.html');
  if (state.defaultValue && boolValue) {
      sendMessage(state.defaultValue);
  }
  else {
   
  }
}

// ===============================
// PAGE NAVIGATION HELPERS (Preserve Hash)
// ===============================

function navigateTo(page) {
  const currentHash = window.location.hash;
  window.location.href = `${page}${currentHash}`;
  state.currentHash = window.location.href;
  sessionStorage.setItem('hashvalue',currentHash)
}

// ===============================
// STATE MANAGEMENT
// ===============================

function loadState() {
  ;
  state.currentHash = sessionStorage.getItem('hashValue');
  const saved = sessionStorage.getItem("appState");
  
  if (saved) {
    try {
      Object.assign(state, JSON.parse(saved));
      console.log("✅ State loaded:", state);
    } catch {
      console.warn("⚠️ Failed to parse state.");
    }
  } else {
    state.session_id = generateUUIDFallback();
    saveState();
  }
  state.selectedTemplateId = sessionStorage.getItem('SELECTED_TEMPLATE_KEY');
  document.querySelector('#userid').innerHTML =sessionStorage.getItem('username') || saved.username;
}

function saveState() {
  sessionStorage.setItem("appState", JSON.stringify(state));
}

function clearState() {
  sessionStorage.removeItem("appState");
  console.log("🧹 Local state cleared");
}

// ===============================
// UI UTILITIES
// ===============================

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  });
  children.forEach(c => node.appendChild(c));
  return node;
}

// ===============================
// SIDEBAR
// ===============================

const sidebarDrawer = document.getElementById("sidebarDrawer");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const sidebarOpenBtn = document.getElementById("sidebarOpenBtn");
const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");

if (sidebarOpenBtn && sidebarDrawer) {
  sidebarOpenBtn.onclick = () => {
    sidebarDrawer.classList.remove("-translate-x-full");
    sidebarDrawer.classList.add("translate-x-0");
    sidebarOverlay.classList.remove("opacity-0", "pointer-events-none");
    sidebarOverlay.classList.add("opacity-100");
    sidebarOverlay.style.pointerEvents = "auto";
  };
}

function closeSidebar() {
  if (!sidebarDrawer || !sidebarOverlay) return;
  sidebarDrawer.classList.add("-translate-x-full");
  sidebarDrawer.classList.remove("translate-x-0");
  sidebarOverlay.classList.remove("opacity-100");
  sidebarOverlay.classList.add("opacity-0", "pointer-events-none");
  sidebarOverlay.style.pointerEvents = "none";
}

if (sidebarCloseBtn) sidebarCloseBtn.onclick = closeSidebar;
if (sidebarOverlay) sidebarOverlay.onclick = closeSidebar;

// ===============================
// MODALS + LOADER
// ===============================


function createErrorModal() {
  if (document.getElementById('errorModal')) return;

  const modal = el('div', {
    id: 'errorModal',
    class: 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999] hidden'
  }, [
    el('div', { class: 'bg-white dark:bg-neutral-900 p-6 rounded-xl shadow-lg max-w-md w-full' }, [
      el('h2', { class: 'text-xl font-bold text-red-600 mb-4', html: 'Error' }),
      el('p', { id: 'errorModalMessage', class: 'text-red-700 dark:text-red-400 mb-6 whitespace-pre-wrap', html: '' }),
      el('button', {
        id: 'errorModalClose',
        class: 'neuro-button bg-red-600 text-white rounded-lg px-4 py-2 hover:bg-red-700',
        html: 'Close'
      })
    ])
  ]);

  document.body.appendChild(modal);

  modal.querySelector('#errorModalClose').addEventListener('click', () => {
    modal.classList.add('hidden');
  });
}




function beautifyMessage(message) {
  if (!message) return '';

  // 1️⃣ Normalize line breaks
  message = message.replace(/\\n/g, '\n').replace(/\r\n|\r/g, '\n');

  // 2️⃣ Add spacing before headers/lists
  message = message
    .replace(/([^\n])\n(#+ )/g, '$1\n\n$2')
    .replace(/([^\n])\n(- )/g, '$1\n\n$2')
    .replace(/\n{3,}/g, '\n\n');

  // 3️⃣ Preserve code blocks
  const codeBlockPattern = /```([\s\S]*?)```/g;
  const codeBlocks = [];
  message = message.replace(codeBlockPattern, (_, codeContent) => {
    codeBlocks.push(codeContent);
    return `[[CODEBLOCK_${codeBlocks.length - 1}]]`;
  });

  // 4️⃣ Convert tables first
  const tablePattern = /((\|.+\|)\n(\|[-:\s|]+\|)\n((\|.*\|(?:\n)?)+))/g;
  message = message.replace(tablePattern, (_, tableMarkdown) => {
    try {
      return '\n\n' + convertMarkdownTableToHtml(tableMarkdown.trim(), '') + '\n\n';
    } catch (err) {
      console.warn('Table conversion failed:', err);
      return tableMarkdown;
    }
  });

  // 5️⃣ Parse remaining Markdown
  let html = marked.parse(message, { breaks: true, gfm: true });

  // 6️⃣ Style lists
  html = html
    .replace(/<ul>/g, '<ul class="list-disc ml-6 mb-4">')
    .replace(/<ol>/g, '<ol class="list-decimal ml-6 mb-4">')
    .replace(/<li>/g, '<li class="mb-2">');

  // 7️⃣ Style existing emp_option anchor tags
  html = html.replace(
    /<a\s+([^>]*class=["']emp_option["'][^>]*)>/gi,
    (match, attrs) =>
      `<a ${attrs} class="emp_option text-blue-400 font-medium underline underline-offset-2 decoration-blue-500 hover:text-blue-800 hover:decoration-blue-800 transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-400">`
  );




  // 8️⃣ Handle .docx/.pdf URLs that are NOT already inside <a>
  const docPattern = /(https?:\/\/[^\s"'<>\]]+?\.(?:docx|pdf))/i;
  const docMatch = html.match(docPattern);
  let downloadHtml = '';

  if (docMatch) {
    const url = docMatch[0];
    const filename = url.split('/').pop();

    downloadHtml = `
      <div class="mt-4 " style="display:flex;align-items:center;gap:0.25rem;">
        <a href="${url}" target="_blank" download
          class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg shadow-sm hover:bg-indigo-700 transition">
          <i class="fa-solid fa-download"></i> Generated Document
        </a>
      </div>
    `;

    // 🧹 Remove <a> tag wrapping that URL (if any) OR the raw URL itself
    const anchorPattern = new RegExp(
      `<a[^>]*>\\s*${url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*<\\/a>`,
      'gi'
    );
    html = html.replace(anchorPattern, ''); // remove <a>…</a> entirely
    html = html.replace(docPattern, ''); // just in case it appears bare
  }


  // 9️⃣ Restore code blocks
  codeBlocks.forEach((content, i) => {
    const escapedContent = escapeHtml(content);
    html = html.replace(
      `[[CODEBLOCK_${i}]]`,
      `<pre class="bg-gray-100 dark:bg-gray-900 rounded-xl p-4 overflow-x-auto"><code>${escapedContent}</code></pre>`
    );
  });

  //  🔟 Append download button at the end if present
  if (downloadHtml) {
    html += downloadHtml;
  }

  return html;
}



function copyMessage(button) {
  // 1️⃣ Find the closest .message-stream and get text content
  const container = button.closest('.message-stream');
  if (!container) return console.warn('No message container found.');

  const el = container.querySelector('p, div');
  if (!el) return console.warn('No text element found inside message.');

  const messageText = el.innerText.trim();
  if (!messageText) return console.warn('Message is empty.');

  // 2️⃣ Try modern Clipboard API first
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(messageText)
      .then(() => {
        showToast('✅ Copied!');
      })
      .catch(err => {
        console.error('Clipboard API failed:', err);
        fallbackCopy(messageText);
      });
  } else {
    // 3️⃣ Fallback for unsupported browsers / non-secure contexts
    fallbackCopy(messageText);
  }

  // 4️⃣ Local fallback using textarea + execCommand
  function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed'; // Avoid scroll jump
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      console.log('✅ Copied!');
    } catch (err) {
      console.error('Fallback copy failed:', err);
    }
    document.body.removeChild(textarea);
  }
}



function convertMarkdownTableToHtml(markdown,nonTableParts) {
    const lines = markdown.trim().split('\n');

    if (lines.length < 2) return markdown;

    const headers = lines[0].split('|').map(h => h.trim()).filter(Boolean);
    const rows = lines.slice(2).map(row =>
        row.split('|').map(cell => cell.trim()).filter(Boolean)
    ).filter(r => r.length && r.length === headers.length);

    let filteredHeaders = headers;
    let filteredRows = rows;

    // 🟣 Case: single row — remove keys with null/empty
    if (rows.length === 1) {
        const keepIndices = rows[0]
            .map((val, i) => val?.toLowerCase?.() !== 'null' && val !== '' ? i : null)
            .filter(i => i !== null);

        filteredHeaders = keepIndices.map(i => headers[i]);
        filteredRows = [keepIndices.map(i => rows[0][i])];
    }


const columnTypes = filteredHeaders.map((header, colIdx) => {
  const headerLower = header.toLowerCase();
  const values = filteredRows.map(row => (row[colIdx] ?? '').toString().trim());

  const headerHints = {
    percent: /%|percent/i,
    number: /amount|total|price|cost|qty|quantity|number/i,
    date: /date|time/i,
  };

  const headerTypeHint = Object.entries(headerHints)
    .find(([, regex]) => regex.test(headerLower))?.[0];

  const isDateLike = v =>
    /^(\d{4}-\d{2}-\d{2}|[0-3]?\d-[A-Za-z]{3}-\d{4}|[A-Za-z]+ \d{1,2}, \d{4}(,)?( \d{1,2}:\d{2}(:\d{2})?\s?(am|pm)?)?|[A-Za-z]+ \d{1,2}, \d{4}( at \d{1,2}:\d{2}(:\d{2})?\s?(am|pm)?)?)(z|[+-]\d{2}:?\d{2})?$/i.test(v);

  const isNumericOnly = v => /^(\p{Sc})?\s?\d[\d,]*(\.\d+)?$/u.test(v.replace(/,/g, ''));
  const isPercentLike = v => /^\d+(\.\d+)?\s?%$/.test(v);

  let numCount = 0, percentCount = 0, dateCount = 0, nonNumberCount = 0;

  values.forEach(v => {
    if (v === '' || v.toLowerCase() === 'null') return;

    if (isPercentLike(v)) percentCount++;
    else if (isNumericOnly(v)) numCount++;
    else if (isDateLike(v)) dateCount++;
    else nonNumberCount++;
  });

  const total = values.filter(v => v !== '' && v.toLowerCase() !== 'null').length;

  // Decision rules
  if (percentCount === total || headerTypeHint === 'percent') return 'percent';
  if (dateCount === total || headerTypeHint === 'date') return 'date';

  // 🟢 FIX HERE: Only return 'number' if ALL are numbers
  if (nonNumberCount === 0 && (numCount === total || headerTypeHint === 'number')) return 'number';

  return 'text';
});




function getAlignClassForType(type) {
    
    switch (type) {
        case 'number':
        case 'percent':
            return 'text-right';
        case 'date':
            return 'text-right';
        default:
            return 'text-left';
    }
}

    let html = `
<div class="w-full max-w-[40vw] scroll-hover-container overflow-auto max-h-[300px] my-4 rounded-xl border border-gray-200 shadow-sm bg-white">
  <div class="custom-scrollbar min-w-full p-2">
    <table class="min-w-full table-auto text-sm text-left text-gray-100 bg-white rounded-xl">
      <thead class="bg-gray-100/95 backdrop-blur sticky top-0 z-10 text-xs uppercase text-gray-900 sticky top-0 z-10 shadow-sm font-bold">
        <tr class="hover:bg-gray-50 transition-colors">
            ${filteredHeaders.map((h, i) =>
            `<th style="width:max-content;white-space:nowrap;" class="px-4 py-2 border-b border-gray-200 font-bold ${getAlignClassForType(columnTypes[i])}">${h}</th>`
            ).join('')}
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-100">
        ${filteredRows.map(row => {
            const cols = row.map((cell, i) => {
                // const { content, alignClass } = detectAndFormatCellContent(cell, columnTypes[i]);
                const { content } = detectAndFormatCellContent(cell, columnTypes[i]);  // remove alignClass from here
                let safeContent = escapeHtml(content);
                safeContent = marked.parseInline(safeContent);
                const alignClass = getAlignClassForType(columnTypes[i]); // use consistent alignment
                return `<td class="px-4 py-2 border-b border-gray-100 ${alignClass}">
                <div style="white-space:nowrap;" class="text-gray-800 max-w-[300px] line-clamp-2 overflow-hidden text-ellipsis whitespace-normal ${alignClass}" title="${String(content).replace(/"/g, '&quot;')}">
                    ${safeContent}
                </div>
                </td>`;

            }).join('');
            return `<tr class="hover:bg-gray-50 transition-colors">${cols}</tr>`;
        }).join('')}
      </tbody>
    </table>
  </div>
</div>`;
let expandHtml = `
  <div class="flex justify-start">
    <div class="flex justify-start mb-2">
  <button
    onclick='openMarkdownTableInNewTab(${JSON.stringify(filteredHeaders)}, ${JSON.stringify(filteredRows)},${JSON.stringify(nonTableParts)})'
    class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-indigo-600 bg-white border border-indigo-300 rounded-lg shadow-sm hover:bg-indigo-50 hover:text-indigo-700 transition"
    title="Expand table in new tab"
  >
    <i class="fa-solid fa-up-right-and-down-left-from-center text-xs"></i>
    Expand
  </button>
</div>

  </div>
`;


    return html;
}

function detectAndFormatCellContent(value, columnType = 'auto') {
    const trimmed = value?.toString().trim() || '';
    const lower = trimmed.toLowerCase();
    

    const isDateLike = /^(\d{4}-\d{2}-\d{2}|[0-3]?\d-[A-Za-z]{3}-\d{4})([T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?)?([Zz]|[+-]\d{2}:?\d{2})?$/;


    const numberPattern = /^(\p{Sc})?\s?\d{1,3}(,\d{3})*(\.\d+)?$|^\d+(\.\d+)?$/u;
    const percentagePattern = /^\d+(\.\d+)?\s?%$/;

    // Force align by column type
    if (['number', 'percent', 'date'].includes(columnType)) {
        let formatted = trimmed;

        if (columnType === 'date' && isDateLike.test(trimmed)) {
            const parsedDate = new Date(trimmed);
            if (!isNaN(parsedDate)) {
                const dd = String(parsedDate.getDate()).padStart(2, '0');
                const mm = String(parsedDate.getMonth() + 1).padStart(2, '0');
                const yyyy = parsedDate.getFullYear();

                const hasTime = /[tT\s]\d{1,2}:\d{2}/.test(lower);
                formatted = `${dd}-${mm}-${yyyy}`;
                if (hasTime) {
                    const hh = String(parsedDate.getHours()).padStart(2, '0');
                    const min = String(parsedDate.getMinutes()).padStart(2, '0');
                    formatted += ` ${hh}:${min}`;
                }
            }
        }

        return {
            content: formatted,
            alignClass: 'text-right',
        };
    }

    // Auto-detect fallback
    if (percentagePattern.test(trimmed)) return { content: trimmed, alignClass: 'text-right' };
    if (numberPattern.test(trimmed.replace(/,/g, ''))) return { content: trimmed, alignClass: 'text-right' };

    if (isDateLike.test(trimmed)) {
        const parsedDate = new Date(trimmed);
        if (!isNaN(parsedDate)) {
            const dd = String(parsedDate.getDate()).padStart(2, '0');
            const mm = String(parsedDate.getMonth() + 1).padStart(2, '0');
            const yyyy = parsedDate.getFullYear();

            const hasTime = /[tT\s]\d{1,2}:\d{2}/.test(lower);
            let formatted = `${dd}-${mm}-${yyyy}`;
            if (hasTime) {
                const hh = String(parsedDate.getHours()).padStart(2, '0');
                const min = String(parsedDate.getMinutes()).padStart(2, '0');
                formatted += ` ${hh}:${min}`;
            }
            return {
                content: formatted,
                alignClass: 'text-right',
            };
        }
    }

    return {
        content: trimmed,
        alignClass: 'text-left',
    };
}

function showErrorModal(message) {
  createErrorModal();
  const modal = document.getElementById("errorModal");
  const messageEl = document.getElementById("errorModalMessage");
  if (messageEl) messageEl.textContent = message || "An unknown error occurred.";
  modal.classList.remove("hidden");
}

function closeErrorModal() {
  const modal = document.getElementById("errorModal");
  if (modal) modal.classList.add("hidden");
}

function showSuccessModal(message) {
  createSuccessModal();
  const modal = document.getElementById("successModal");
  const messageEl = document.getElementById("successModalMessage");
  if (messageEl) messageEl.textContent = message || "Operation completed successfully.";
  modal.classList.remove("hidden");
}

function closeSuccessModal() {
  const modal = document.getElementById("successModal");
  if (modal) modal.classList.add("hidden");
}

function showSyncLoader(duration = 2000) {
  const loader = document.getElementById("syncLoader");
  loader.classList.remove("hidden");
  setTimeout(() => loader.classList.add("hidden"), duration);
}

async function initTemplateDropdown() {
  
  const savedTemplateId = sessionStorage.getItem('SELECTED_TEMPLATE_KEY');

state.selectedTemplateId = savedTemplateId;

  sessionStorage.setItem('initialCall', 'true');

  try {
    const dropdown = document.getElementById("instanceEnvDropdown");
    if (!dropdown) return;

    const url = `${state.baseUrl}/templates?limit=100&offset=0`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Failed: ${resp.status}`);

    const data = await resp.json();

    // ✅ Correct API shape handling
    const templates = data?.data || [];

    // --- Build option data ---
    const options = templates.map(tpl => ({
      value: String(tpl.id),
      text: `Template ID: ${tpl.id}`
    }));

    // --- TomSelect already exists → update it ---
    if (dropdown.tomselect) {
      const ts = dropdown.tomselect;
      ts.clearOptions();
      ts.addOptions(options);
      ts.refreshOptions(false);

    } 
    else {
      // --- Init only ONCE ---
      new TomSelect(dropdown, {
        create: false,
        options,
        valueField: 'value',
        labelField: 'text',
        searchField: 'text',
        sortField: { field: "text", direction: "asc" },
        placeholder: "Search or select template...",
        onChange(value) {
          
          const selected = value || null;

  state.selectedTemplateId = selected;
  //selectedTemplate = selected;

  sessionStorage.setItem('SELECTED_TEMPLATE_KEY', selected);

  if (window.cachedTemplates) {
    renderGrid(window.cachedTemplates);
  }
  startNewChat()
        }
      });
    }
    if (dropdown.tomselect && state.selectedTemplateId) {
  dropdown.tomselect.setValue(state.selectedTemplateId, true);
}

  } catch (err) {
    console.error("Template dropdown init failed:", err);
    showErrorModal("Failed to load templates");
  }
}


// ===============================
// SYNC DATA (uses dynamic headers)
// ===============================

async function syncData() {
  showSyncLoader();
  const url = `${state.baseUrl}/sync-data`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-OUScribe-Agent-User-ID": state.userIdHeader || "guest@email.com"
      },
      body: JSON.stringify({ instance_identifier: state.syncId })
    });

    if (!response.ok) throw new Error(await response.text() || "Sync failed");

    const data = await response.json();
    console.log("✅ Sync successful:", data);
    await apiGetInstances?.();
    showSuccessModal("Sync Successful");
  } catch (error) {
    console.error("❌ Sync error:", error);
    showErrorModal(`Sync failed: ${error}`);
  }
}

// ===============================
// IMAGE MODAL
// ===============================

function openImageModal(src) {
  const modal = document.getElementById("imageModal");
  const modalImg = document.getElementById("modalImage");
  if (!modal || !modalImg) return;
  modalImg.src = src;
  modal.classList.remove("hidden");
}

function closeImageModal() {
  const modal = document.getElementById("imageModal");
  if (modal) {
    modal.classList.add("hidden");
    document.getElementById("modalImage").src = "";
  }
}

// ===============================
// INIT
// ===============================

window.addEventListener("load", () => {
  boolValue = sessionStorage.getItem("logged");
  initTemplateDropdown();
  if(!boolValue){
    initializeSessionFromHash();
    if (state.defaultValue) {
    const message = state.defaultValue;
    sendMessage(message);
    state.initialMessageSent = true;
  }
  }
  else {
     const data = parseBase64Hash();
     const session_id =  data?.session_id || sessionStorage.getItem("session_id") || generateUUIDFallback();
      const userId = data?.userId || sessionStorage.getItem("userId") ||  "guest@domain.com";
      const username = data?.username || sessionStorage.getItem('username') || "User";
      state.defaultValue = data?.defaultValue;
      // sessionStorage.setItem("session_id", session_id);
      // sessionStorage.setItem("userId", userId);
      // sessionStorage.setItem("username",username);
      state.session_id = session_id;
      state.userIdHeader = userId;
      state.userId = userId;
      state.username = username;
      state.selectedTemplateId = data.templateid;
      updateHeaders();
      updateUserDisplay(userId);
      updateSessionDisplay(session_id);
      if (state.defaultValue) {
    const message = state.defaultValue;
    sendMessage(message);
    state.initialMessageSent = true;
  }
  if(state.selectedTemplateId){
    dropdown.tomselect.setValue(state.selectedTemplateId, true);
  }
  }
  document.querySelector('#userid').innerHTML =sessionStorage.getItem('username');
  loadState();
  
});
