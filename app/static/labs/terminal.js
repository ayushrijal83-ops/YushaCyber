/* YC-034.1 — Browser Linux Terminal (+ YC-034.3 Mission UI) */
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

/* ── Mission timer ── */
var timerEl = document.querySelector('[data-tm-timer]');
var timerStart = Date.now();
var timerHandle = null;
if(isMission && timerEl){
    timerHandle = setInterval(function(){
        var secs = Math.floor((Date.now() - timerStart) / 1000);
        timerEl.textContent = fmtTime(secs);
    }, 1000);
}
function fmtTime(totalSeconds){
    var m = Math.floor(totalSeconds / 60);
    var s = totalSeconds % 60;
    return (m<10?'0':'')+m+':'+(s<10?'0':'')+s;
}

/* ── Init ── */
fetch(apiBase+'/start', {method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({slug:slug})})
.then(function(r){return r.json()})
.then(function(d){
    updatePrompt(d.prompt || currentPrompt);
    if(isMission && d.progress && d.progress.started_at){
        timerStart = Date.now() - (d.progress.elapsed||0)*1000;
    }
})
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
    fetch(apiBase+'/execute', {method:'POST', headers:{'Content-Type':'application/json'},
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
                    markObjectiveDone(v.objective_id);
                }
            });
            advanceCurrentObjective();
        }
        /* ── Update progress bars (header + sidebar) ── */
        if(d.progress){
            updateProgress(d.progress);
        }
        /* ── Update network status panel (YC-034.6) ── */
        if(d.network_status){
            updateNetStatus(d.network_status);
        }
        /* ── Mission complete ── */
        if(d.completed){
            showComplete(d.progress);
        }
        scroll();
    })
    .catch(function(){ appendErr('Network error.'); });
}

function updateNetStatus(net){
    var panel = document.querySelector('[data-net-status]');
    if(!panel) return;
    var dot = panel.querySelector('[data-net-dot]');
    var iface = panel.querySelector('[data-net-iface]');
    var ip = panel.querySelector('[data-net-ip]');
    var gw = panel.querySelector('[data-net-gw]');
    var dns = panel.querySelector('[data-net-dns]');
    var isUp = net.interface_state === 'UP';
    if(dot) dot.classList.toggle('tm-netstatus__dot--down', !isUp);
    if(iface) iface.textContent = (net.interface || 'eth0') + ' ' + (net.interface_state || 'UNKNOWN');
    if(ip) ip.textContent = net.interface_ip || '—';
    if(gw) gw.textContent = net.default_gateway || '—';
    if(dns) dns.textContent = net.dns_server || '—';
}

function markObjectiveDone(objId){
    var objEl = document.querySelector('[data-obj-id="'+objId+'"]');
    if(!objEl) return;
    objEl.classList.remove('tm-obj--current');
    objEl.classList.add('tm-obj--done');
    objEl.setAttribute('aria-current', 'false');
    var titleEl = objEl.querySelector('.tm-obj__title');
    if(titleEl && !titleEl.querySelector('.tm-obj__check')){
        titleEl.insertAdjacentHTML('afterbegin','<span class="tm-obj__check" aria-hidden="true">✓</span> ');
    }
}

function advanceCurrentObjective(){
    var all = document.querySelectorAll('[data-mission-objectives] [data-obj-id]');
    for(var i=0;i<all.length;i++){
        if(!all[i].classList.contains('tm-obj--done')){
            all[i].classList.add('tm-obj--current');
            all[i].setAttribute('aria-current', 'true');
            break;
        }
    }
}

function updateProgress(progress){
    document.querySelectorAll('[data-progress-bar], [data-progress-bar-side]').forEach(function(bar){
        bar.style.width = progress.pct + '%';
    });
    var header = document.querySelector('[data-progress-text]');
    if(header){
        header.textContent = progress.completed_ids.length + '/' + progress.total + ' · ' + progress.pct + '%';
    }
    var side = document.querySelector('[data-progress-text-side]');
    if(side){
        side.textContent = progress.pct + '% complete';
    }
    var barWrap = document.querySelector('.tm-mhead__bar');
    if(barWrap) barWrap.setAttribute('aria-valuenow', progress.pct);
}

function showComplete(progress){
    if(timerHandle){ clearInterval(timerHandle); timerHandle = null; }
    var overlay = document.querySelector('[data-tm-complete]');
    if(!overlay) return;
    var xpEl = overlay.querySelector('[data-tm-complete-xp]');
    var objEl = overlay.querySelector('[data-tm-complete-obj]');
    var timeEl = overlay.querySelector('[data-tm-complete-time]');
    var hintsEl = overlay.querySelector('[data-tm-complete-hints]');
    if(xpEl) xpEl.textContent = '+' + (progress.xp_earned||0);
    if(objEl) objEl.textContent = progress.completed_ids.length + '/' + progress.total;
    if(timeEl) timeEl.textContent = fmtTime(progress.elapsed||0);
    if(hintsEl) hintsEl.textContent = progress.hints_used||0;
    overlay.hidden = false;
    var heading = overlay.querySelector('h2');
    if(heading){ heading.setAttribute('tabindex','-1'); heading.focus(); }
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

function doReset(){
    fetch(apiBase+'/reset', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({slug:slug})})
    .then(function(r){return r.json()})
    .then(function(d){
        output.innerHTML = '';
        appendSystem('Lab reset. Fresh environment loaded.\n');
        updatePrompt(d.prompt||currentPrompt);
        if(d.progress) updateProgress(d.progress);
        document.querySelectorAll('[data-mission-objectives] [data-obj-id]').forEach(function(el){
            el.classList.remove('tm-obj--done', 'tm-obj--current');
            el.setAttribute('aria-current', 'false');
            var check = el.querySelector('.tm-obj__check');
            if(check) check.remove();
        });
        advanceCurrentObjective();
        timerStart = Date.now();
        var overlay = document.querySelector('[data-tm-complete]');
        if(overlay) overlay.hidden = true;
        if(isMission && timerEl && !timerHandle){
            timerHandle = setInterval(function(){
                timerEl.textContent = fmtTime(Math.floor((Date.now()-timerStart)/1000));
            }, 1000);
        }
    })
    .catch(function(){});
}

var resetBtn = document.querySelector('[data-tm-reset]');
if(resetBtn) resetBtn.addEventListener('click', doReset);

var restartBtn = document.querySelector('[data-tm-restart]');
if(restartBtn) restartBtn.addEventListener('click', function(){
    if(window.confirm('Restart this mission? Your progress on it will reset.')) doReset();
});

var mentorBtn = document.querySelector('[data-tm-mentor]');
if(mentorBtn) mentorBtn.addEventListener('click', function(){
    var fab = document.querySelector('.mentor-fab');
    if(fab) fab.click();
});

var fullBtn = document.querySelector('[data-tm-full]');
if(fullBtn) fullBtn.addEventListener('click', function(){
    var layout = document.querySelector('.tm-layout');
    if(layout) layout.classList.toggle('tm-layout--full');
});

/* ── Mobile objectives drawer ── */
var drawerBtn = document.querySelector('[data-tm-drawer-toggle]');
var drawerBackdrop = document.querySelector('[data-tm-drawer-backdrop]');
var side = document.getElementById('tm-side');
function closeDrawer(){
    if(side) side.classList.remove('tm-side--open');
    if(drawerBackdrop) drawerBackdrop.hidden = true;
    if(drawerBtn) drawerBtn.setAttribute('aria-expanded', 'false');
}
function openDrawer(){
    if(side) side.classList.add('tm-side--open');
    if(drawerBackdrop) drawerBackdrop.hidden = false;
    if(drawerBtn) drawerBtn.setAttribute('aria-expanded', 'true');
}
if(drawerBtn) drawerBtn.addEventListener('click', function(){
    if(side && side.classList.contains('tm-side--open')) closeDrawer(); else openDrawer();
});
if(drawerBackdrop) drawerBackdrop.addEventListener('click', closeDrawer);

/* ── Focus ── */
output.addEventListener('click', function(){ input.focus(); });
input.focus();

function esc(s){ var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
})();
