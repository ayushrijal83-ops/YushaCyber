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
        /* ── Update packet lab status panel (YC-034.9) ── */
        if(d.packet_lab_status){
            updatePacketLabStatus(d.packet_lab_status);
        }
        /* ── Update web session status panel (YC-035.0) + HTTP Inspector (YC-035.1) ── */
        if(d.web_lab_status){
            updateWebLabStatus(d.web_lab_status);
            renderInspector(d.web_lab_status);
        }
        /* ── Update Proxy Dashboard (YC-035.2) ── */
        if(d.proxy_lab_status){
            renderProxy(d.proxy_lab_status);
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

function updatePacketLabStatus(pkt){
    var panel = document.querySelector('[data-pkt-status]');
    if(!panel) return;
    var capture = panel.querySelector('[data-pkt-capture]');
    var count = panel.querySelector('[data-pkt-count]');
    var selected = panel.querySelector('[data-pkt-selected]');
    var filter = panel.querySelector('[data-pkt-filter]');
    if(capture) capture.textContent = pkt.active_capture || 'none open';
    if(count) count.textContent = pkt.total_packets || 0;
    if(selected) selected.textContent = pkt.selected_packet || '—';
    if(filter) filter.textContent = pkt.last_filter || '—';
}

function updateWebLabStatus(web){
    var panel = document.querySelector('[data-web-status]');
    if(!panel) return;
    var user = panel.querySelector('[data-web-user]');
    var status = panel.querySelector('[data-web-status-code]');
    var path = panel.querySelector('[data-web-path]');
    var cookies = panel.querySelector('[data-web-cookies]');
    if(user) user.textContent = web.logged_in_as || 'not logged in';
    if(status) status.textContent = web.last_status || '—';
    if(path) path.textContent = web.last_path || '—';
    if(cookies) cookies.textContent = web.cookie_count || 0;
}

/* ── HTTP Inspector (YC-035.1) ──
   Renders the live request/response/history from mission.web_lab_status
   (also carried on every /execute response) into the tabbed inspector
   panel. Purely a view over data the server already computes — no new
   API calls, same pattern as updateNetStatus/updatePacketLabStatus. */
function formatHeaders(headers){
    return Object.keys(headers || {}).map(function(k){ return k + ': ' + headers[k]; }).join('\n');
}
function formatQuery(query){
    var keys = Object.keys(query || {});
    if(!keys.length) return '';
    return '?' + keys.map(function(k){ return k + '=' + query[k]; }).join('&');
}
function formatRequestLine(req){
    return req.method + ' ' + req.path + formatQuery(req.query) + ' HTTP/1.1';
}
function formatStatusLine(resp){
    return 'HTTP/1.1 ' + resp.status_code + ' ' + resp.reason;
}

function renderInspector(status){
    if(!status) return;
    var req = status.last_request, resp = status.last_response;

    var reqEl = document.querySelector('[data-inspector-request]');
    if(reqEl){
        reqEl.textContent = req
            ? formatRequestLine(req) + '\n' + formatHeaders(req.headers) + (req.body ? '\n\n' + req.body : '')
            : "No request yet. Use 'open URL' in the terminal, or the Request Builder below.";
    }
    var respEl = document.querySelector('[data-inspector-response]');
    if(respEl){
        respEl.textContent = resp
            ? formatStatusLine(resp) + '\n' + formatHeaders(resp.headers) + (resp.body ? '\n\n' + resp.body : '')
            : 'No response yet.';
    }
    var headersEl = document.querySelector('[data-inspector-headers]');
    if(headersEl){
        var lines = [];
        if(req){ lines.push('Request headers:'); lines.push(formatHeaders(req.headers) || '(none)'); }
        if(resp){ lines.push(''); lines.push('Response headers:'); lines.push(formatHeaders(resp.headers) || '(none)'); }
        headersEl.textContent = lines.length ? lines.join('\n') : 'No headers yet.';
    }
    var bodyEl = document.querySelector('[data-inspector-body]');
    if(bodyEl){
        var parts = [];
        if(req && req.body) parts.push('Request body:\n' + req.body);
        if(resp && resp.body) parts.push((parts.length ? '\n\n' : '') + 'Response body:\n' + resp.body);
        bodyEl.textContent = parts.length ? parts.join('') : 'No body in the last exchange.';
    }
    var cookiesEl = document.querySelector('[data-inspector-cookies]');
    if(cookiesEl){
        var entries = Object.keys(status.cookies || {});
        cookiesEl.textContent = entries.length
            ? entries.map(function(k){ return k + '=' + status.cookies[k]; }).join('\n')
            : 'No cookies stored.';
    }
    var historyEl = document.querySelector('[data-inspector-history]');
    if(historyEl && status.history){
        historyEl.innerHTML = '';
        if(!status.history.length){
            var empty = document.createElement('li');
            empty.className = 'tm-inspector__history-item';
            empty.textContent = 'No requests made yet.';
            historyEl.appendChild(empty);
        }
        status.history.forEach(function(entry){
            var li = document.createElement('li');
            li.className = 'tm-inspector__history-item';
            li.tabIndex = 0;
            li.setAttribute('role', 'button');
            li.textContent = '#' + entry.index + '  ' + entry.method + ' ' + entry.path + '  → ' + entry.status_code;
            var openEntry = function(){
                renderInspector({last_request: entry.request, last_response: entry.response,
                    cookies: status.cookies, history: status.history});
                selectInspectorTab('request');
            };
            li.addEventListener('click', openEntry);
            li.addEventListener('keydown', function(e){
                if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); openEntry(); }
            });
            historyEl.appendChild(li);
        });
    }
}

function selectInspectorTab(name){
    document.querySelectorAll('.tm-inspector__tab').forEach(function(btn){
        var active = btn.dataset.tab === name;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    document.querySelectorAll('.tm-inspector__panel').forEach(function(panel){
        panel.hidden = panel.dataset.panel !== name;
    });
}

document.querySelectorAll('.tm-inspector__tab').forEach(function(btn){
    btn.addEventListener('click', function(){ selectInspectorTab(btn.dataset.tab); });
});

var inspectorToggle = document.querySelector('[data-inspector-toggle]');
if(inspectorToggle){
    inspectorToggle.addEventListener('click', function(){
        var body = document.getElementById('tm-inspector-body');
        var expanded = inspectorToggle.getAttribute('aria-expanded') === 'true';
        inspectorToggle.setAttribute('aria-expanded', (!expanded).toString());
        if(body) body.hidden = expanded;
    });
}

/* Wraps a value in POSIX single quotes, safely embedding any literal
   single quote it contains — avoids any double-quote/JSON escaping
   headaches when the Request Builder hands its input to the terminal's
   'open' command. */
function shQuote(s){
    return "'" + String(s).replace(/'/g, "'\\''") + "'";
}

var inspectorForm = document.querySelector('[data-inspector-form]');
if(inspectorForm){
    inspectorForm.addEventListener('submit', function(e){
        e.preventDefault();
        var method = document.querySelector('[data-builder-method]').value;
        var path = document.querySelector('[data-builder-path]').value.trim() || '/';
        var query = document.querySelector('[data-builder-query]').value.trim();
        var headersRaw = document.querySelector('[data-builder-headers]').value.trim();
        var bodyRaw = document.querySelector('[data-builder-body]').value.trim();

        var url = 'https://cybershop.training' + path + (query ? '?' + query : '');
        var cmd = 'open -X ' + method;
        if(headersRaw){
            headersRaw.split('\n').forEach(function(line){
                line = line.trim();
                if(line) cmd += ' -H ' + shQuote(line);
            });
        }
        if(bodyRaw) cmd += ' -d ' + shQuote(bodyRaw);
        cmd += ' ' + url;

        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}
var builderClear = document.querySelector('[data-builder-clear]');
if(builderClear && inspectorForm){
    builderClear.addEventListener('click', function(){ inspectorForm.reset(); });
}

/* Initial render from server-rendered state, so the panel isn't empty
   until the student's first command. */
var initialWebLabEl = document.getElementById('tm-web-lab-initial');
if(initialWebLabEl){
    try{
        renderInspector(JSON.parse(initialWebLabEl.textContent));
    }catch(err){ /* absent/malformed — inspector keeps its placeholder text */ }
}

/* ── Proxy Dashboard (YC-035.2) ──
   Every button here just builds the same terminal command a student
   could type by hand ('browse'/'intercept'/'forward'/'drop'/'modify'/
   'send-to-repeater'/'repeater-edit'/'repeater-send'/'compare') and runs
   it through the existing exec() pipeline — no separate API path, so
   "only the simulated proxy, never a real request" is enforced exactly
   once, server-side. Rendering reuses formatHeaders/formatQuery/
   formatRequestLine/formatStatusLine/shQuote already defined above for
   the HTTP Inspector. */
function renderProxy(status){
    if(!status) return;

    var toggle = document.querySelector('[data-proxy-intercept-toggle]');
    var stateEl = document.querySelector('[data-proxy-intercept-state]');
    if(toggle) toggle.setAttribute('aria-pressed', status.intercept_enabled ? 'true' : 'false');
    if(stateEl) stateEl.textContent = status.intercept_enabled ? 'ON' : 'OFF';

    var pendingEl = document.querySelector('[data-proxy-pending]');
    if(pendingEl){
        var p = status.pending_request;
        pendingEl.textContent = p
            ? formatRequestLine(p) + '\n' + formatHeaders(p.headers) + (p.body ? '\n\n' + p.body : '')
            : 'No request intercepted.';
    }

    var req = status.last_request, resp = status.last_response;
    var reqEl = document.querySelector('[data-proxy-request]');
    if(reqEl){
        reqEl.textContent = req
            ? formatRequestLine(req) + '\n' + formatHeaders(req.headers) + (req.body ? '\n\n' + req.body : '')
            : 'No request forwarded yet.';
    }
    var respEl = document.querySelector('[data-proxy-response]');
    if(respEl){
        respEl.textContent = resp
            ? formatStatusLine(resp) + '\n' + formatHeaders(resp.headers) + (resp.body ? '\n\n' + resp.body : '')
            : 'No response yet.';
    }
    var headersEl = document.querySelector('[data-proxy-headers]');
    if(headersEl){
        var hLines = [];
        if(req){ hLines.push('Request headers:'); hLines.push(formatHeaders(req.headers) || '(none)'); }
        if(resp){ hLines.push(''); hLines.push('Response headers:'); hLines.push(formatHeaders(resp.headers) || '(none)'); }
        headersEl.textContent = hLines.length ? hLines.join('\n') : 'No headers yet.';
    }
    var bodyEl = document.querySelector('[data-proxy-body]');
    if(bodyEl){
        var bParts = [];
        if(req && req.body) bParts.push('Request body:\n' + req.body);
        if(resp && resp.body) bParts.push((bParts.length ? '\n\n' : '') + 'Response body:\n' + resp.body);
        bodyEl.textContent = bParts.length ? bParts.join('') : 'No body yet.';
    }
    var cookiesEl = document.querySelector('[data-proxy-cookies]');
    if(cookiesEl){
        var cKeys = Object.keys(status.cookies || {});
        cookiesEl.textContent = cKeys.length
            ? cKeys.map(function(k){ return k + '=' + status.cookies[k]; }).join('\n')
            : 'No cookies stored.';
    }

    var historyEl = document.querySelector('[data-proxy-history]');
    if(historyEl){
        historyEl.innerHTML = '';
        var hist = status.history || [];
        if(!hist.length){
            var emptyLi = document.createElement('li');
            emptyLi.className = 'tm-inspector__history-item';
            emptyLi.textContent = 'No requests forwarded yet.';
            historyEl.appendChild(emptyLi);
        }
        hist.forEach(function(entry){
            var li = document.createElement('li');
            li.className = 'tm-inspector__history-item';
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.alignItems = 'center';
            li.style.gap = '8px';

            var label = document.createElement('span');
            label.tabIndex = 0;
            label.setAttribute('role', 'button');
            label.style.cursor = 'pointer';
            label.textContent = '#' + entry.index + '  ' + entry.method + ' ' + entry.path + '  → ' + entry.status_code;
            var openEntry = function(){
                renderProxy(Object.assign({}, status, {last_request: entry.request, last_response: entry.response}));
                selectProxyTab('request');
            };
            label.addEventListener('click', openEntry);
            label.addEventListener('keydown', function(e){
                if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); openEntry(); }
            });

            var sendBtn = document.createElement('button');
            sendBtn.type = 'button';
            sendBtn.className = 'tm-toolbar__btn';
            sendBtn.textContent = '→ Repeater';
            sendBtn.addEventListener('click', function(){
                var cmd = 'send-to-repeater ' + entry.index;
                appendCmd(currentPrompt, cmd);
                exec(cmd);
            });

            li.appendChild(label);
            li.appendChild(sendBtn);
            historyEl.appendChild(li);
        });
    }

    var repReqEl = document.querySelector('[data-repeater-request]');
    if(repReqEl){
        var rr = status.repeater_request;
        repReqEl.textContent = rr
            ? formatRequestLine(rr) + '\n' + formatHeaders(rr.headers) + (rr.body ? '\n\n' + rr.body : '')
            : 'Repeater is empty. Send a request from History first.';
    }

    var repLog = status.repeater_log || [];
    var repRespEl = document.querySelector('[data-repeater-response]');
    if(repRespEl){
        if(repLog.length){
            var lastSend = repLog[repLog.length - 1];
            repRespEl.textContent = formatStatusLine(lastSend.response) + '\n'
                + formatHeaders(lastSend.response.headers)
                + (lastSend.response.body ? '\n\n' + lastSend.response.body : '');
        } else {
            repRespEl.textContent = 'No response yet.';
        }
    }
    var repLogEl = document.querySelector('[data-repeater-log]');
    if(repLogEl){
        repLogEl.innerHTML = '';
        if(!repLog.length){
            var repEmpty = document.createElement('li');
            repEmpty.className = 'tm-inspector__history-item';
            repEmpty.textContent = 'No Repeater sends yet.';
            repLogEl.appendChild(repEmpty);
        }
        repLog.forEach(function(entry){
            var li = document.createElement('li');
            li.className = 'tm-inspector__history-item';
            li.textContent = '#' + entry.index + '  ' + entry.method + ' ' + entry.path
                + formatQuery(entry.request.query) + '  → ' + entry.status_code;
            repLogEl.appendChild(li);
        });
    }

    var compareEl = document.querySelector('[data-compare-result]');
    if(compareEl){
        compareEl.textContent = status.compared ? (status.last_comparison || '') : '';
    }

    var scopeLog = document.querySelector('[data-scope-log]');
    if(scopeLog){
        var blocked = status.blocked_hosts || [];
        scopeLog.textContent = blocked.length
            ? blocked.length + ' blocked attempt(s) outside scope: ' + blocked.join(', ')
            : '';
    }
}

function selectProxyTab(name){
    document.querySelectorAll('[data-proxy-tab]').forEach(function(btn){
        var active = btn.dataset.proxyTab === name;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    document.querySelectorAll('[data-proxy-panel]').forEach(function(panel){
        panel.hidden = panel.dataset.proxyPanel !== name;
    });
}
document.querySelectorAll('[data-proxy-tab]').forEach(function(btn){
    btn.addEventListener('click', function(){ selectProxyTab(btn.dataset.proxyTab); });
});

/* Scenario buttons — the "simulated browser" triggering a request. */
document.querySelectorAll('[data-scenario-url]').forEach(function(btn){
    btn.addEventListener('click', function(){
        var method = btn.dataset.scenarioMethod || 'GET';
        var url = btn.dataset.scenarioUrl;
        var body = btn.dataset.scenarioBody;
        var headers = btn.dataset.scenarioHeaders;
        var cmd = 'browse -X ' + method;
        if(headers) cmd += ' -H ' + shQuote(headers);
        if(body) cmd += ' -d ' + shQuote(body);
        cmd += ' ' + url;
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
});

var proxyCustomForm = document.querySelector('[data-proxy-custom-form]');
if(proxyCustomForm){
    proxyCustomForm.addEventListener('submit', function(e){
        e.preventDefault();
        var url = document.querySelector('[data-custom-url]').value.trim();
        if(!url) return;
        var cmd = 'browse ' + url;
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}

var interceptToggle = document.querySelector('[data-proxy-intercept-toggle]');
if(interceptToggle){
    interceptToggle.addEventListener('click', function(){
        var isOn = interceptToggle.getAttribute('aria-pressed') === 'true';
        var cmd = 'intercept ' + (isOn ? 'off' : 'on');
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}

var forwardBtn = document.querySelector('[data-proxy-forward]');
if(forwardBtn) forwardBtn.addEventListener('click', function(){
    appendCmd(currentPrompt, 'forward');
    exec('forward');
});

var dropBtn = document.querySelector('[data-proxy-drop]');
if(dropBtn) dropBtn.addEventListener('click', function(){
    appendCmd(currentPrompt, 'drop');
    exec('drop');
});

/* Shared builder for 'modify'/'repeater-edit' — only includes flags for
   fields the student actually filled in, leaving everything else on the
   paused/draft request untouched. */
function buildEditCommand(base, methodSel, pathInput, queryInput, headersArea, bodyArea){
    var cmd = base;
    var method = methodSel.value.trim();
    var path = pathInput.value.trim();
    var query = queryInput.value.trim();
    var headersRaw = headersArea.value.trim();
    var body = bodyArea.value;
    if(method) cmd += ' -X ' + method;
    if(path) cmd += ' -P ' + shQuote(path);
    if(query) cmd += ' -Q ' + shQuote(query);
    if(headersRaw){
        headersRaw.split('\n').forEach(function(line){
            line = line.trim();
            if(line) cmd += ' -H ' + shQuote(line);
        });
    }
    if(body.trim()) cmd += ' -d ' + shQuote(body);
    return cmd;
}

var editForm = document.querySelector('[data-proxy-edit-form]');
if(editForm){
    editForm.addEventListener('submit', function(e){
        e.preventDefault();
        var cmd = buildEditCommand('modify',
            document.querySelector('[data-edit-method]'),
            document.querySelector('[data-edit-path]'),
            document.querySelector('[data-edit-query]'),
            document.querySelector('[data-edit-headers]'),
            document.querySelector('[data-edit-body]'));
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}

var repeaterEditForm = document.querySelector('[data-repeater-edit-form]');
if(repeaterEditForm){
    repeaterEditForm.addEventListener('submit', function(e){
        e.preventDefault();
        var cmd = buildEditCommand('repeater-edit',
            document.querySelector('[data-repeater-edit-method]'),
            document.querySelector('[data-repeater-edit-path]'),
            document.querySelector('[data-repeater-edit-query]'),
            document.querySelector('[data-repeater-edit-headers]'),
            document.querySelector('[data-repeater-edit-body]'));
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}

var repeaterSendBtn = document.querySelector('[data-repeater-send]');
if(repeaterSendBtn) repeaterSendBtn.addEventListener('click', function(){
    appendCmd(currentPrompt, 'repeater-send');
    exec('repeater-send');
});

var compareBtn = document.querySelector('[data-compare-btn]');
if(compareBtn){
    compareBtn.addEventListener('click', function(){
        var a = document.querySelector('[data-compare-a]').value || '1';
        var b = document.querySelector('[data-compare-b]').value || '2';
        var cmd = 'compare ' + a + ' ' + b;
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}

/* Initial render from server-rendered state. */
var initialProxyLabEl = document.getElementById('tm-proxy-lab-initial');
if(initialProxyLabEl){
    try{
        renderProxy(JSON.parse(initialProxyLabEl.textContent));
    }catch(err){ /* absent/malformed — dashboard keeps its placeholder text */ }
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
        if(d.web_lab_status){
            updateWebLabStatus(d.web_lab_status);
            renderInspector(d.web_lab_status);
        }
        if(d.proxy_lab_status){
            renderProxy(d.proxy_lab_status);
        }
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
