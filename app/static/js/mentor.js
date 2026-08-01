/* CyberMentor Chat JS — YC-032.1.1 */
(function(){
'use strict';

/* ── State ── */
let isOpen = false;
let isLoading = false;
let aiOnline = false;
let history = [];
const STORE_KEY = 'cybermentor_history';
const SUGGESTED = [
    'Explain SQL Injection',
    'Help with my current lab',
    'Recommend my next lesson',
    'Explain this Nmap output',
    'What should I study next?',
    'Review my answer',
];

/* ── DOM refs (set after inject) ── */
let panel, overlay, fab, msgArea, input, sendBtn, clearBtn,
    statusDot, modelLabel, ctxBar, promptsWrap;

/* ── Init ── */
function init(){
    if(!document.querySelector('[data-mentor-user]')) return;
    injectHTML();
    bindRefs();
    bindEvents();
    loadHistory();
    checkHealth();
    if(history.length === 0) showWelcome();
}

/* ── Inject component HTML ── */
function injectHTML(){
    const user = document.querySelector('[data-mentor-user]');
    const username = user ? user.dataset.mentorUser : '';
    const lab = user ? (user.dataset.mentorLab || '') : '';
    const level = user ? (user.dataset.mentorLevel || '1') : '1';
    const xp = user ? (user.dataset.mentorXp || '0') : '0';

    // Fab button
    const fabEl = document.createElement('button');
    fabEl.className = 'mentor-fab mentor-fab--pulse';
    fabEl.setAttribute('aria-label','Open CyberMentor');
    fabEl.setAttribute('title','CyberMentor');
    fabEl.innerHTML = '🤖';
    document.body.appendChild(fabEl);

    // Overlay
    const ov = document.createElement('div');
    ov.className = 'mentor-overlay';
    document.body.appendChild(ov);

    // Panel
    const p = document.createElement('div');
    p.className = 'mentor-panel';
    p.setAttribute('role','dialog');
    p.setAttribute('aria-label','CyberMentor Chat');
    p.innerHTML = `
    <div class="mentor-header">
        <span class="mentor-header__icon">🤖</span>
        <span class="mentor-header__title">CyberMentor</span>
        <div class="mentor-header__meta">
            <span class="mentor-header__status" data-mentor-status></span>
            <span data-mentor-model>—</span>
        </div>
        <button class="mentor-header__close" aria-label="Close" data-mentor-close>✕</button>
    </div>
    <div class="mentor-ctx" data-mentor-ctx>
        ${lab ? `<span class="mentor-ctx__item"><span class="mentor-ctx__label">Lab:</span> ${esc(lab)}</span>` : ''}
        <span class="mentor-ctx__item"><span class="mentor-ctx__label">Level:</span> ${esc(level)}</span>
        <span class="mentor-ctx__item"><span class="mentor-ctx__label">XP:</span> ${esc(xp)}</span>
    </div>
    <div class="mentor-messages" data-mentor-messages></div>
    <div class="mentor-prompts" data-mentor-prompts></div>
    <div class="mentor-input">
        <textarea class="mentor-input__field" data-mentor-input
            placeholder="Ask CyberMentor anything..." rows="1"
            aria-label="Message"></textarea>
        <button class="mentor-input__clear" data-mentor-clear
            title="Clear conversation">⟲</button>
        <button class="mentor-input__send" data-mentor-send
            aria-label="Send" disabled>▶</button>
    </div>`;
    document.body.appendChild(p);
}

function bindRefs(){
    fab = document.querySelector('.mentor-fab');
    overlay = document.querySelector('.mentor-overlay');
    panel = document.querySelector('.mentor-panel');
    msgArea = panel.querySelector('[data-mentor-messages]');
    input = panel.querySelector('[data-mentor-input]');
    sendBtn = panel.querySelector('[data-mentor-send]');
    clearBtn = panel.querySelector('[data-mentor-clear]');
    statusDot = panel.querySelector('[data-mentor-status]');
    modelLabel = panel.querySelector('[data-mentor-model]');
    promptsWrap = panel.querySelector('[data-mentor-prompts]');
}

function bindEvents(){
    fab.addEventListener('click', toggle);
    overlay.addEventListener('click', close);
    panel.querySelector('[data-mentor-close]').addEventListener('click', close);
    sendBtn.addEventListener('click', send);
    clearBtn.addEventListener('click', clearChat);
    input.addEventListener('input', onInput);
    input.addEventListener('keydown', function(e){
        if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
    });
    document.addEventListener('keydown', function(e){
        if(e.key==='Escape' && isOpen) close();
    });
    renderPrompts();
}

/* ── Panel toggle ── */
function toggle(){ isOpen ? close() : open(); }
function open(){
    isOpen = true;
    panel.classList.add('mentor-panel--open');
    overlay.classList.add('mentor-overlay--open');
    fab.classList.remove('mentor-fab--pulse');
    input.focus();
    scrollBottom();
}
function close(){
    isOpen = false;
    panel.classList.remove('mentor-panel--open');
    overlay.classList.remove('mentor-overlay--open');
}

/* ── Send message ── */
function send(){
    const text = input.value.trim();
    if(!text || isLoading) return;
    addMessage('user', text);
    input.value = '';
    input.style.height = 'auto';
    sendBtn.disabled = true;
    hidePrompts();
    showTyping();
    isLoading = true;

    const lab = document.querySelector('[data-mentor-user]');
    const labSlug = lab ? (lab.dataset.mentorLab || '') : '';

    fetch('/api/ai/chat', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({message: text, current_lab: labSlug})
    })
    .then(function(r){ return r.json(); })
    .then(function(data){
        hideTyping();
        isLoading = false;
        if(data.error){
            addError(data.error);
        } else {
            addMessage('assistant', data.content || 'No response.');
        }
    })
    .catch(function(err){
        hideTyping();
        isLoading = false;
        addError('Network error — check your connection.');
    });
}

/* ── Messages ── */
function addMessage(role, content){
    const cls = role === 'user' ? 'mentor-msg--user' : 'mentor-msg--ai';
    const div = document.createElement('div');
    div.className = 'mentor-msg ' + cls;
    if(role === 'user'){
        div.textContent = content;
    } else {
        div.innerHTML = renderMarkdown(content);
        div.querySelectorAll('.mentor-code__copy').forEach(function(btn){
            btn.addEventListener('click', function(){
                const code = btn.closest('.mentor-code').querySelector('code');
                navigator.clipboard.writeText(code.textContent).then(function(){
                    btn.textContent = 'Copied!';
                    setTimeout(function(){ btn.textContent = 'Copy'; }, 1500);
                });
            });
        });
    }
    msgArea.appendChild(div);
    history.push({role: role, content: content});
    saveHistory();
    scrollBottom();
}

function addError(msg){
    const div = document.createElement('div');
    div.className = 'mentor-error';
    div.textContent = msg;
    msgArea.appendChild(div);
    scrollBottom();
}

function showWelcome(){
    const user = document.querySelector('[data-mentor-user]');
    const username = user ? user.dataset.mentorUser : 'there';
    const div = document.createElement('div');
    div.className = 'mentor-welcome';
    div.innerHTML = `
        <div class="mentor-welcome__icon">🤖</div>
        <div class="mentor-welcome__title">Hello, ${esc(username)} 👋</div>
        <div class="mentor-welcome__sub">I'm CyberMentor, your cybersecurity learning assistant.</div>
        <ul class="mentor-welcome__list">
            <li>I know your current level and XP</li>
            <li>I know your completed labs</li>
            <li>I can help with your current lesson</li>
            <li>Ask me anything about cybersecurity</li>
        </ul>`;
    msgArea.appendChild(div);
}

function showTyping(){
    const div = document.createElement('div');
    div.className = 'mentor-typing';
    div.setAttribute('data-mentor-typing','');
    div.innerHTML = `CyberMentor is thinking
        <span class="mentor-typing__dots">
            <span class="mentor-typing__dot"></span>
            <span class="mentor-typing__dot"></span>
            <span class="mentor-typing__dot"></span>
        </span>`;
    msgArea.appendChild(div);
    scrollBottom();
}
function hideTyping(){
    const t = msgArea.querySelector('[data-mentor-typing]');
    if(t) t.remove();
}

/* ── Suggested prompts ── */
function renderPrompts(){
    if(!promptsWrap) return;
    promptsWrap.innerHTML = '';
    SUGGESTED.forEach(function(text){
        const btn = document.createElement('button');
        btn.className = 'mentor-prompts__btn';
        btn.textContent = text;
        btn.addEventListener('click', function(){
            input.value = text;
            input.focus();
            sendBtn.disabled = false;
        });
        promptsWrap.appendChild(btn);
    });
}
function hidePrompts(){
    if(promptsWrap) promptsWrap.style.display = 'none';
}

/* ── Input auto-resize ── */
function onInput(){
    sendBtn.disabled = !input.value.trim();
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}

/* ── Scroll ── */
function scrollBottom(){
    requestAnimationFrame(function(){
        msgArea.scrollTop = msgArea.scrollHeight;
    });
}

/* ── Health check ── */
function checkHealth(){
    fetch('/api/ai/health')
    .then(function(r){ return r.json(); })
    .then(function(data){
        aiOnline = data.status === 'ok';
        if(statusDot){
            statusDot.className = 'mentor-header__status' +
                (aiOnline ? '' : ' mentor-header__status--offline');
        }
        if(modelLabel) modelLabel.textContent = data.model || 'AI';
    })
    .catch(function(){
        aiOnline = false;
        if(statusDot) statusDot.classList.add('mentor-header__status--offline');
    });
}

/* ── Session persistence ── */
function saveHistory(){
    try{ sessionStorage.setItem(STORE_KEY, JSON.stringify(history.slice(-40))); }
    catch(e){}
}
function loadHistory(){
    try{
        const saved = sessionStorage.getItem(STORE_KEY);
        if(!saved) return;
        history = JSON.parse(saved);
        history.forEach(function(m){
            const cls = m.role === 'user' ? 'mentor-msg--user' : 'mentor-msg--ai';
            const div = document.createElement('div');
            div.className = 'mentor-msg ' + cls;
            if(m.role === 'user'){
                div.textContent = m.content;
            } else {
                div.innerHTML = renderMarkdown(m.content);
            }
            msgArea.appendChild(div);
        });
        if(history.length > 0) hidePrompts();
        scrollBottom();
    }catch(e){}
}

function clearChat(){
    history = [];
    sessionStorage.removeItem(STORE_KEY);
    msgArea.innerHTML = '';
    showWelcome();
    if(promptsWrap){ promptsWrap.style.display = ''; renderPrompts(); }
}

/* ── Markdown renderer (lightweight) ── */
function renderMarkdown(text){
    if(!text) return '';
    // Fenced code blocks
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, function(_, lang, code){
        lang = lang || 'text';
        return '<div class="mentor-code">' +
            '<div class="mentor-code__header"><span>' + esc(lang) + '</span>' +
            '<button class="mentor-code__copy">Copy</button></div>' +
            '<pre><code>' + esc(code.trim()) + '</code></pre></div>';
    });
    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic
    text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Links
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // Unordered lists
    text = text.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    // Ordered lists
    text = text.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    // Headers
    text = text.replace(/^### (.+)$/gm, '<strong>$1</strong>');
    text = text.replace(/^## (.+)$/gm, '<strong>$1</strong>');
    // Paragraphs
    text = text.replace(/\n\n/g, '</p><p>');
    text = '<p>' + text + '</p>';
    text = text.replace(/<p>\s*<\/p>/g, '');
    // Cyber formatting
    text = applyCyberTokens(text);
    return text;
}

function applyCyberTokens(html){
    // IPs
    html = html.replace(/\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/g,
        '<span class="cyber-ip">$1</span>');
    // Ports
    html = html.replace(/\b(port\s+)(\d{2,5})\b/gi,
        '$1<span class="cyber-port">$2</span>');
    // CVEs
    html = html.replace(/\b(CVE-\d{4}-\d{4,})\b/g,
        '<span class="cyber-cve">$1</span>');
    // Hashes (40+ hex chars)
    html = html.replace(/\b([a-f0-9]{40,})\b/gi,
        '<span class="cyber-hash">$1</span>');
    // File paths
    html = html.replace(/((?:\/[\w.-]+){2,}|(?:[A-Z]:\\[\w\\.-]+))/g,
        '<span class="cyber-path">$1</span>');
    return html;
}

/* ── Escape HTML ── */
function esc(s){
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

/* ── Boot ── */
if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
})();
