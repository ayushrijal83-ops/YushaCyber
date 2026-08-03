/* Live Classroom JS — YC-033.1 */
(function(){
'use strict';

/* ── Waiting room countdown ── */
const countdownEl = document.querySelector('[data-cr-countdown]');
if(countdownEl){
    const target = new Date(countdownEl.dataset.crCountdown).getTime();
    function tick(){
        const now = Date.now();
        const diff = Math.max(0, target - now);
        const h = Math.floor(diff/3600000);
        const m = Math.floor((diff%3600000)/60000);
        const s = Math.floor((diff%60000)/1000);
        countdownEl.textContent = (h>0?h+'h ':'') + m+'m '+s+'s';
        if(diff > 0) requestAnimationFrame(tick);
        else{ countdownEl.textContent = 'Starting now!'; location.reload(); }
    }
    tick();
}

/* ── Elapsed time ── */
const elapsedEl = document.querySelector('[data-cr-elapsed]');
if(elapsedEl){
    const start = new Date(elapsedEl.dataset.crElapsed).getTime();
    setInterval(function(){
        const diff = Math.max(0, Date.now() - start);
        const m = Math.floor(diff/60000);
        const s = Math.floor((diff%60000)/1000);
        elapsedEl.textContent = m+'m '+String(s).padStart(2,'0')+'s';
    }, 1000);
}

/* ── Chat ── */
const chatForm = document.querySelector('[data-cr-chat-form]');
const chatInput = document.querySelector('[data-cr-chat-input]');
const chatMsgs = document.querySelector('[data-cr-chat-msgs]');
if(chatForm && chatInput){
    chatForm.addEventListener('submit', function(e){
        e.preventDefault();
        const text = chatInput.value.trim();
        if(!text) return;
        const div = document.createElement('div');
        div.className = 'cr-chat__msg';
        div.innerHTML = '<b>You</b>' + esc(text);
        chatMsgs.appendChild(div);
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
        chatInput.value = '';
    });
}

/* ── Notes autosave ── */
const notesArea = document.querySelector('[data-cr-notes]');
const notesSave = document.querySelector('[data-cr-notes-save]');
if(notesArea){
    const key = 'cr_notes_' + (notesArea.dataset.crNotes || 'default');
    notesArea.value = localStorage.getItem(key) || '';
    let timer;
    notesArea.addEventListener('input', function(){
        clearTimeout(timer);
        timer = setTimeout(function(){
            localStorage.setItem(key, notesArea.value);
            if(notesSave) notesSave.textContent = 'Saved ✓';
            setTimeout(function(){ if(notesSave) notesSave.textContent = 'Auto-save'; }, 2000);
        }, 1500);
    });
    // Export
    document.querySelectorAll('[data-cr-export]').forEach(function(btn){
        btn.addEventListener('click', function(){
            const fmt = btn.dataset.crExport;
            const text = notesArea.value;
            let blob, ext;
            if(fmt === 'md'){ blob = new Blob([text], {type:'text/markdown'}); ext='md'; }
            else if(fmt === 'txt'){ blob = new Blob([text], {type:'text/plain'}); ext='txt'; }
            else return;
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'class-notes.'+ext; a.click();
            URL.revokeObjectURL(url);
        });
    });
}

/* ── AI Mentor sidebar ── */
const aiForm = document.querySelector('[data-cr-ai-form]');
const aiInput = document.querySelector('[data-cr-ai-input]');
const aiMsgs = document.querySelector('[data-cr-ai-msgs]');
if(aiForm && aiInput){
    aiForm.addEventListener('submit', function(e){
        e.preventDefault();
        const q = aiInput.value.trim();
        if(!q) return;
        appendAI('user', q);
        aiInput.value = '';
        const slug = document.querySelector('[data-cr-slug]');
        fetch('/api/ai/chat', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({message: q, current_lab: slug ? slug.dataset.crSlug : ''})
        }).then(function(r){ return r.json(); })
        .then(function(d){ appendAI('ai', d.content || 'No response.'); })
        .catch(function(){ appendAI('ai', 'AI unavailable.'); });
    });
}
function appendAI(role, text){
    if(!aiMsgs) return;
    const div = document.createElement('div');
    div.className = 'cr-chat__msg';
    div.innerHTML = role==='user' ? '<b>You</b>'+esc(text) : '<b>🤖</b>'+esc(text);
    aiMsgs.appendChild(div);
    aiMsgs.scrollTop = aiMsgs.scrollHeight;
}

/* ── Hand raise ── */
const handBtn = document.querySelector('[data-cr-hand]');
if(handBtn){
    let raised = false;
    handBtn.addEventListener('click', function(){
        raised = !raised;
        handBtn.className = 'cr-hand__btn' + (raised ? ' cr-hand__btn--raised' : '');
        handBtn.textContent = raised ? '✋ Hand Raised' : '✋ Raise Hand';
    });
}

/* ── Mobile tabs ── */
document.querySelectorAll('[data-cr-tab]').forEach(function(btn){
    btn.addEventListener('click', function(){
        const target = btn.dataset.crTab;
        document.querySelectorAll('[data-cr-tab]').forEach(function(b){ b.classList.remove('cr-tabs__btn--active'); });
        btn.classList.add('cr-tabs__btn--active');
        document.querySelectorAll('[data-cr-panel]').forEach(function(p){ p.classList.remove('cr-tabs__panel--active'); });
        const panel = document.querySelector('[data-cr-panel="'+target+'"]');
        if(panel) panel.classList.add('cr-tabs__panel--active');
    });
});

/* ── Fullscreen ── */
const fullBtn = document.querySelector('[data-cr-fullscreen]');
if(fullBtn){
    fullBtn.addEventListener('click', function(){
        const video = document.querySelector('.cr-video');
        if(video && video.requestFullscreen) video.requestFullscreen();
    });
}

/* ── Leave confirmation ── */
const leaveBtn = document.querySelector('[data-cr-leave]');
if(leaveBtn){
    leaveBtn.addEventListener('click', function(e){
        if(!confirm('Leave this class? Your attendance will be recorded.')) e.preventDefault();
    });
}

function esc(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
})();
