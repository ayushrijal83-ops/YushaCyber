/* YC-034.1 — Browser Linux Terminal */
(function(){
'use strict';

var slug = document.querySelector('[data-lab-slug]');
slug = slug ? slug.dataset.labSlug : 'terminal';

var output  = document.querySelector('[data-tm-output]');
var input   = document.querySelector('[data-tm-input]');
var promptEl= document.querySelector('[data-tm-prompt]');
if(!output || !input) return;

var historyArr = [];
var historyIdx = -1;
var currentPrompt = 'student@lab:~$ ';
var isMission = !!document.querySelector('[data-mission-objectives]');
var apiBase = isMission ? '/api/terminal/mission' : '/api/terminal';

/* ── Init ── */
var initUrl = isMission ? apiBase+'/start' : apiBase+'/start';
fetch(initUrl, {method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({slug:slug})})
.then(function(r){return r.json()})
.then(function(d){ updatePrompt(d.prompt || currentPrompt); })
.catch(function(){});

appendSystem('YushaCyber Interactive Terminal v1.0');
if(isMission) appendSystem('Complete all objectives to earn XP. Type "help" for commands.\n');
else appendSystem('Type "help" for available commands.\n');

/* ── Key handling ── */
input.addEventListener('keydown', function(e){
    if(e.key === 'Enter'){
        e.preventDefault();
        var cmd = input.value.trim();
        if(!cmd) return;
        historyArr.push(cmd);
        historyIdx = historyArr.length;
        appendCmd(currentPrompt, cmd);
        input.value = '';
        exec(cmd);
    }
    else if(e.key === 'ArrowUp'){
        e.preventDefault();
        if(historyIdx > 0){ historyIdx--; input.value = historyArr[historyIdx]; }
    }
    else if(e.key === 'ArrowDown'){
        e.preventDefault();
        if(historyIdx < historyArr.length - 1){ historyIdx++; input.value = historyArr[historyIdx]; }
        else{ historyIdx = historyArr.length; input.value = ''; }
    }
    else if(e.key === 'Tab'){
        e.preventDefault();
        tabComplete();
    }
    else if(e.key === 'l' && e.ctrlKey){
        e.preventDefault();
        output.innerHTML = '';
    }
    else if(e.key === 'c' && e.ctrlKey){
        e.preventDefault();
        appendCmd(currentPrompt, input.value + '^C');
        input.value = '';
    }
});

/* ── Execute ── */
function exec(cmd){
    if(cmd === 'clear'){
        output.innerHTML = '';
        return;
    }
    var execUrl = isMission ? apiBase+'/execute' : apiBase+'/execute';
    fetch(execUrl, {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({slug:slug, command:cmd})})
    .then(function(r){return r.json()})
    .then(function(d){
        if(d.error){ appendErr(d.error); return; }
        if(d.output && d.output !== '\x1b[clear]'){
            appendOut(d.output);
        } else if(d.output === '\x1b[clear]'){
            output.innerHTML = '';
        }
        updatePrompt(d.prompt || currentPrompt);
        /* ── Mission validations ── */
        if(d.validations && d.validations.length > 0){
            d.validations.forEach(function(v){
                if(v.passed){
                    var div = document.createElement('div');
                    div.className = 'tm-line tm-line--success';
                    div.textContent = '✓ ' + (v.message || 'Objective completed!') + ' (+' + (v.xp||0) + ' XP)';
                    output.appendChild(div);
                    /* Mark objective as done in sidebar */
                    var objEl = document.querySelector('[data-obj-id="'+v.objective_id+'"]');
                    if(objEl){
                        objEl.classList.add('tm-obj--done');
                        var titleEl = objEl.querySelector('.tm-obj__title');
                        if(titleEl && !titleEl.querySelector('.tm-obj__check')){
                            titleEl.insertAdjacentHTML('afterbegin','<span class="tm-obj__check">✓</span> ');
                        }
                    }
                }
            });
        }
        /* ── Update progress bar ── */
        if(d.progress){
            var bar = document.querySelector('[data-progress-bar]');
            var txt = document.querySelector('[data-progress-text]');
            if(bar) bar.style.width = d.progress.pct + '%';
            if(txt) txt.textContent = d.progress.pct + '% complete';
        }
        /* ── Mission complete ── */
        if(d.completed){
            var cdiv = document.createElement('div');
            cdiv.className = 'tm-line tm-line--success';
            cdiv.textContent = '\n🎉 MISSION COMPLETE! Total XP earned: ' + (d.progress?d.progress.xp_earned:0);
            output.appendChild(cdiv);
        }
        scroll();
    })
    .catch(function(){ appendErr('Network error.'); });
}

/* ── Tab complete ── */
function tabComplete(){
    var partial = input.value.split(/\s+/).pop();
    if(!partial) return;
    fetch('/api/terminal/complete', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({slug:slug, partial:partial})})
    .then(function(r){return r.json()})
    .then(function(d){
        var m = d.matches || [];
        if(m.length === 1){
            var parts = input.value.split(/\s+/);
            parts[parts.length-1] = m[0];
            input.value = parts.join(' ');
        } else if(m.length > 1){
            appendOut(m.join('  '));
        }
    }).catch(function(){});
}

/* ── Output helpers ── */
function appendCmd(prompt, cmd){
    var div = document.createElement('div');
    div.className = 'tm-line tm-line--cmd';
    div.innerHTML = '<span class="tm-prompt">' + esc(prompt) + '</span><span class="tm-cmd">' + esc(cmd) + '</span>';
    output.appendChild(div);
    scroll();
}

function appendOut(text){
    var div = document.createElement('div');
    div.className = 'tm-line tm-line--out';
    div.textContent = text;
    output.appendChild(div);
    scroll();
}

function appendErr(text){
    var div = document.createElement('div');
    div.className = 'tm-line tm-line--err';
    div.textContent = text;
    output.appendChild(div);
    scroll();
}

function appendSystem(text){
    var div = document.createElement('div');
    div.className = 'tm-line tm-line--system';
    div.textContent = text;
    output.appendChild(div);
    scroll();
}

function updatePrompt(p){
    currentPrompt = p;
    if(promptEl) promptEl.textContent = p;
}

function scroll(){
    requestAnimationFrame(function(){ output.scrollTop = output.scrollHeight; });
}

/* ── Toolbar buttons ── */
var clearBtn = document.querySelector('[data-tm-clear]');
if(clearBtn) clearBtn.addEventListener('click', function(){ output.innerHTML = ''; });

var resetBtn = document.querySelector('[data-tm-reset]');
if(resetBtn) resetBtn.addEventListener('click', function(){
    var resetUrl = isMission ? apiBase+'/reset' : apiBase+'/reset';
    fetch(resetUrl, {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({slug:slug})})
    .then(function(r){return r.json()})
    .then(function(d){ output.innerHTML = ''; appendSystem('Lab reset. Fresh environment loaded.\n'); updatePrompt(d.prompt||currentPrompt); })
    .catch(function(){});
});

var fullBtn = document.querySelector('[data-tm-full]');
if(fullBtn) fullBtn.addEventListener('click', function(){
    var layout = document.querySelector('.tm-layout');
    if(layout) layout.classList.toggle('tm-layout--full');
});

/* ── Focus ── */
output.addEventListener('click', function(){ input.focus(); });
input.focus();

function esc(s){ var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
})();
