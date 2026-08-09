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

/* ── Execute ──
   `onDone(d)`, if given, receives the raw parsed response after all the
   standard side effects below have already run — lets a caller (e.g. the
   Proxy Control Compare button) read one field of the response without
   firing a second /execute call for the same command. */
function exec(cmd, onDone){
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
            renderProxy(d.web_lab_status);
            renderSession(d.web_lab_status);
            renderSqli(d.web_lab_status);
        }
        /* ── Mission complete ── */
        if(d.completed){
            showComplete(d.progress);
        }
        scroll();
        if(onDone) onDone(d);
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
        var isBurp = !!document.querySelector('[data-proxy-badge]');
        status.history.forEach(function(entry){
            var li = document.createElement('li');
            li.className = 'tm-inspector__history-item';
            li.tabIndex = 0;
            li.setAttribute('role', 'button');
            var label = document.createElement('span');
            label.textContent = '#' + entry.index + '  ' + entry.method + ' ' + entry.path + '  → ' + entry.status_code;
            li.appendChild(label);
            var openEntry = function(){
                renderInspector({last_request: entry.request, last_response: entry.response,
                    cookies: status.cookies, history: status.history});
                selectInspectorTab('request');
            };
            li.addEventListener('click', openEntry);
            li.addEventListener('keydown', function(e){
                if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); openEntry(); }
            });
            /* Proxy Control (YC-035.2): a per-entry shortcut into Repeater,
               issuing the same 'repeater N' command the terminal/Repeater
               box already accept — not a separate code path. */
            if(isBurp){
                var toRepeater = document.createElement('button');
                toRepeater.type = 'button';
                toRepeater.className = 'btn btn--outline tm-inspector__history-repeater';
                toRepeater.textContent = '→ Repeater';
                toRepeater.addEventListener('click', function(e){
                    e.stopPropagation();
                    var cmd = 'repeater ' + entry.index;
                    appendCmd(currentPrompt, cmd);
                    exec(cmd);
                });
                li.appendChild(toRepeater);
            }
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

/* ── Proxy Control (YC-035.2) ──
   Every button here does exactly one thing: build a command string and
   submit it through the same exec() the terminal input uses — no new
   endpoints, no client-side proxy logic. renderProxy() is a pure view
   over status.proxy (part of web_lab_status(), already carried on every
   /execute response), the same pattern as renderInspector(). */
function renderProxy(status){
    if(!status || !status.proxy) return;
    var badge = document.querySelector('[data-proxy-badge]');
    var toggle = document.querySelector('[data-proxy-toggle]');
    if(!badge && !toggle) return; /* panel not present on this mission */
    var p = status.proxy;

    if(badge){
        badge.textContent = 'Intercept: ' + (p.intercept_enabled ? 'ON' : 'OFF');
        badge.classList.toggle('tm-proxy__badge--on', p.intercept_enabled);
    }
    if(toggle){
        toggle.textContent = p.intercept_enabled ? 'Turn Intercept Off' : 'Turn Intercept On';
        toggle.dataset.proxyNextMode = p.intercept_enabled ? 'off' : 'on';
    }

    var pendingBox = document.querySelector('[data-proxy-pending-box]');
    var pendingText = document.querySelector('[data-proxy-pending-text]');
    if(pendingBox){
        pendingBox.hidden = !p.pending;
        if(pendingText){
            pendingText.textContent = p.pending
                ? formatRequestLine(p.pending) + '\n' + formatHeaders(p.pending.headers) +
                  (p.pending.body ? '\n\n' + p.pending.body : '')
                : 'No request intercepted.';
        }
    }

    var repText = document.querySelector('[data-proxy-repeater-text]');
    if(repText){
        repText.textContent = p.repeater_request
            ? formatRequestLine(p.repeater_request) + '\n' + formatHeaders(p.repeater_request.headers) +
              (p.repeater_request.body ? '\n\n' + p.repeater_request.body : '')
            : 'Nothing loaded. Use \'repeater N\' or a history entry\'s "→ Repeater" button.';
    }
    var repNote = document.querySelector('[data-proxy-repeater-note]');
    if(repNote) repNote.hidden = !p.pending;
}

/* ── Session State (YC-035.3) ──
   A pure view over status.authenticated/session_present/cookies (part of
   web_lab_status(), already carried on every /execute response) — same
   pattern as renderProxy()/renderInspector(). Logout/Expire buttons build
   the exact terminal commands a student could type themselves and submit
   them through the same exec() path. */
function renderSession(status){
    var badge = document.querySelector('[data-session-badge]');
    if(!badge) return; /* panel not present on this mission */
    var authed = !!status.authenticated;
    badge.textContent = authed ? 'Authenticated' : 'Unauthenticated';
    badge.classList.toggle('tm-session__badge--on', authed);

    var userEl = document.querySelector('[data-session-user]');
    if(userEl) userEl.textContent = authed ? (status.logged_in_as || '—') : 'not logged in';

    var sidEl = document.querySelector('[data-session-id]');
    if(sidEl){
        var sid = status.cookies && status.cookies.session_id;
        sidEl.textContent = sid || '—';
    }

    var expiresEl = document.querySelector('[data-session-expires]');
    if(expiresEl){
        expiresEl.textContent = !status.session_present ? '—'
            : authed ? 'Active' : 'Expired / invalid';
    }

    var cookiesEl = document.querySelector('[data-session-cookies]');
    if(cookiesEl) cookiesEl.textContent = status.cookie_count || 0;
}

var sessionLogout = document.querySelector('[data-session-logout]');
if(sessionLogout){
    sessionLogout.addEventListener('click', function(){
        var cmd = 'open -X POST https://cybershop.training/logout';
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}
var sessionExpire = document.querySelector('[data-session-expire]');
if(sessionExpire){
    sessionExpire.addEventListener('click', function(){
        appendCmd(currentPrompt, 'expire');
        exec('expire');
    });
}

var proxyToggle = document.querySelector('[data-proxy-toggle]');
if(proxyToggle){
    proxyToggle.addEventListener('click', function(){
        var mode = proxyToggle.dataset.proxyNextMode || 'on';
        var cmd = 'intercept ' + mode;
        appendCmd(currentPrompt, cmd);
        exec(cmd);
    });
}
var proxyForward = document.querySelector('[data-proxy-forward]');
if(proxyForward){
    proxyForward.addEventListener('click', function(){ appendCmd(currentPrompt, 'forward'); exec('forward'); });
}
var proxyDrop = document.querySelector('[data-proxy-drop]');
if(proxyDrop){
    proxyDrop.addEventListener('click', function(){ appendCmd(currentPrompt, 'drop'); exec('drop'); });
}
var proxyRepeaterSend = document.querySelector('[data-proxy-repeater-send]');
if(proxyRepeaterSend){
    proxyRepeaterSend.addEventListener('click', function(){
        appendCmd(currentPrompt, 'repeater send'); exec('repeater send');
    });
}
var proxyCompare = document.querySelector('[data-proxy-compare]');
if(proxyCompare){
    proxyCompare.addEventListener('click', function(){
        var a = document.querySelector('[data-proxy-compare-a]').value.trim();
        var b = document.querySelector('[data-proxy-compare-b]').value.trim();
        if(!a || !b) return;
        var cmd = 'compare ' + a + ' ' + b;
        appendCmd(currentPrompt, cmd);
        exec(cmd, function(d){
            var resultEl = document.querySelector('[data-proxy-compare-result]');
            if(resultEl) resultEl.textContent = d.output || 'No comparison yet.';
        });
    });
}

/* Each 'Set' button applies exactly one field to whichever request is
   currently editable (the intercepted one, or the Repeater one — the
   'edit' command itself decides, per its documented priority). Scoped
   via closest('.tm-proxy__box') since the field rows are included twice
   (pending box + Repeater box). */
document.querySelectorAll('[data-proxy-set]').forEach(function(btn){
    btn.addEventListener('click', function(){
        var box = btn.closest('.tm-proxy__box');
        if(!box) return;
        var field = btn.dataset.proxySet;
        var cmd = null;
        if(field === 'method'){
            cmd = 'edit method ' + box.querySelector('[data-proxy-method]').value;
        } else if(field === 'path'){
            var path = box.querySelector('[data-proxy-path]').value.trim();
            if(path) cmd = 'edit path ' + shQuote(path);
        } else if(field === 'query'){
            var qk = box.querySelector('[data-proxy-query-key]').value.trim();
            var qv = box.querySelector('[data-proxy-query-value]').value.trim();
            if(qk) cmd = 'edit query ' + shQuote(qk) + ' ' + shQuote(qv);
        } else if(field === 'header'){
            var hn = box.querySelector('[data-proxy-header-name]').value.trim();
            var hv = box.querySelector('[data-proxy-header-value]').value.trim();
            if(hn) cmd = 'edit header ' + shQuote(hn) + ' ' + shQuote(hv);
        } else if(field === 'body'){
            var bodyVal = box.querySelector('[data-proxy-body]').value;
            cmd = 'edit body ' + shQuote(bodyVal);
        }
        if(cmd){ appendCmd(currentPrompt, cmd); exec(cmd); }
    });
});

/* ── SQL Injection Fundamentals (YC-035.4) ──
   Query Visualizer + evidence badges are a pure view over
   status.last_request/last_response (whose headers already carry
   X-Sim-Query / X-Sim-Query-Kind, set by WebApp's fixed training
   routes — see web.py) and status.sqli's counters/flags — same
   pattern as renderProxy()/renderSession(). Every button below only
   ever builds an 'open ...' command a student could type themselves
   and submits it through the same exec() path. Payload constants
   mirror web.py's TRAINING_*_PAYLOAD exactly. */
var SQLI_TRUE = "' OR '1'='1";
var SQLI_FALSE = "' AND '1'='2";
var SQLI_ERROR = "'";
var SQLI_BYPASS_USERNAME = "admin'--";

function renderSqli(status){
    if(!status) return;
    var panel = document.querySelector('[data-sqli-badges]');
    if(!panel) return; /* panel not present on this mission */

    var req = status.last_request, resp = status.last_response;
    var qEl = document.querySelector('[data-sqli-qv-input]');
    var queryEl = document.querySelector('[data-sqli-qv-query]');
    var respEl = document.querySelector('[data-sqli-qv-response]');
    var explainEl = document.querySelector('[data-sqli-qv-explain]');
    if(req && resp && resp.headers && resp.headers['X-Sim-Query']){
        var kind = resp.headers['X-Sim-Query-Kind'];
        if(qEl) qEl.textContent = (req.query && req.query.q) || req.body || '(none)';
        if(queryEl) queryEl.textContent = resp.headers['X-Sim-Query'];
        if(respEl) respEl.textContent = resp.status_code + ' ' + resp.reason;
        if(explainEl){
            explainEl.textContent = (kind !== 'normal' && kind !== 'parameterized')
                ? 'Unsafe string concatenation let the input change the query\'s structure.'
                : (kind === 'parameterized'
                    ? 'Parameterized query: the input stayed data — the query structure never changed.'
                    : '');
        }
    }

    var s = status.sqli || {};
    var trueBadge = document.querySelector('[data-sqli-badge-true]');
    if(trueBadge){
        trueBadge.textContent = 'TRUE: ' + (s.boolean_true_seen ? 'seen' : 'not seen');
        trueBadge.classList.toggle('tm-proxy__badge--on', !!s.boolean_true_seen);
    }
    var falseBadge = document.querySelector('[data-sqli-badge-false]');
    if(falseBadge){
        falseBadge.textContent = 'FALSE: ' + (s.boolean_false_seen ? 'seen' : 'not seen');
        falseBadge.classList.toggle('tm-proxy__badge--on', !!s.boolean_false_seen);
    }
    var bypassBadge = document.querySelector('[data-sqli-badge-bypass]');
    if(bypassBadge){
        bypassBadge.textContent = 'Auth bypass: ' + (s.auth_bypass_triggered ? 'triggered' : 'not triggered');
        bypassBadge.classList.toggle('tm-proxy__badge--on', !!s.auth_bypass_triggered);
    }
    var secureBadge = document.querySelector('[data-sqli-badge-secure]');
    if(secureBadge){
        secureBadge.textContent = 'Secure endpoint: ' + (s.secure_search_tested ? 'tested' : 'not tested');
        secureBadge.classList.toggle('tm-proxy__badge--on', !!s.secure_search_tested);
    }
    var inspBadge = document.querySelector('[data-sqli-badge-inspections]');
    if(inspBadge) inspBadge.textContent = 'Query inspections: ' + (s.query_inspections || 0);
}

var sqliSearchInput = document.querySelector('[data-sqli-search-input]');
document.querySelectorAll('[data-sqli-quickpick]').forEach(function(btn){
    btn.addEventListener('click', function(){
        if(!sqliSearchInput) return;
        var picks = {normal: 'laptop', 'true': SQLI_TRUE, 'false': SQLI_FALSE, error: SQLI_ERROR};
        sqliSearchInput.value = picks[btn.dataset.sqliQuickpick] || '';
        sqliSearchInput.focus();
    });
});

function sqliRunSearch(path, onDone){
    var q = sqliSearchInput ? sqliSearchInput.value : '';
    var url = 'https://cybershop.training' + path + '?q=' + q;
    var cmd = 'open ' + shQuote(url);
    appendCmd(currentPrompt, cmd);
    exec(cmd, onDone);
}
var sqliSearchVuln = document.querySelector('[data-sqli-search-vuln]');
if(sqliSearchVuln) sqliSearchVuln.addEventListener('click', function(){ sqliRunSearch('/search'); });
var sqliSearchSecure = document.querySelector('[data-sqli-search-secure]');
if(sqliSearchSecure) sqliSearchSecure.addEventListener('click', function(){ sqliRunSearch('/secure-search'); });

var sqliLoginBypassFill = document.querySelector('[data-sqli-login-bypass]');
if(sqliLoginBypassFill){
    sqliLoginBypassFill.addEventListener('click', function(){
        var u = document.querySelector('[data-sqli-login-username]');
        var p = document.querySelector('[data-sqli-login-password]');
        if(u) u.value = SQLI_BYPASS_USERNAME;
        if(p) p.value = 'anything';
    });
}
function sqliRunLogin(path){
    var u = document.querySelector('[data-sqli-login-username]');
    var p = document.querySelector('[data-sqli-login-password]');
    var uv = u ? u.value : '', pv = p ? p.value : '';
    var body = 'username=' + uv + '&password=' + pv;
    var cmd = 'open -X POST -d ' + shQuote(body) + ' https://cybershop.training' + path;
    appendCmd(currentPrompt, cmd);
    exec(cmd);
}
var sqliLoginVuln = document.querySelector('[data-sqli-login-vuln]');
if(sqliLoginVuln) sqliLoginVuln.addEventListener('click', function(){ sqliRunLogin('/training-login'); });
var sqliLoginSecure = document.querySelector('[data-sqli-login-secure]');
if(sqliLoginSecure) sqliLoginSecure.addEventListener('click', function(){ sqliRunLogin('/secure-login'); });

var sqliCompareRun = document.querySelector('[data-sqli-compare-run]');
if(sqliCompareRun){
    sqliCompareRun.addEventListener('click', function(){
        var input = document.querySelector('[data-sqli-compare-input]');
        var q = input ? input.value : '';
        if(!q) return;
        var vulnCmd = 'open ' + shQuote('https://cybershop.training/search?q=' + q);
        var secureCmd = 'open ' + shQuote('https://cybershop.training/secure-search?q=' + q);
        appendCmd(currentPrompt, vulnCmd);
        exec(vulnCmd, function(d1){
            var vulnEl = document.querySelector('[data-sqli-compare-vuln]');
            if(vulnEl) vulnEl.textContent = d1.output || 'No comparison yet.';
            appendCmd(currentPrompt, secureCmd);
            exec(secureCmd, function(d2){
                var secureEl = document.querySelector('[data-sqli-compare-secure]');
                if(secureEl) secureEl.textContent = d2.output || 'No comparison yet.';
            });
        });
    });
}

/* Initial render from server-rendered state, so the panel isn't empty
   until the student's first command. */
var initialWebLabEl = document.getElementById('tm-web-lab-initial');
if(initialWebLabEl){
    try{
        var initialWebLab = JSON.parse(initialWebLabEl.textContent);
        renderInspector(initialWebLab);
        renderProxy(initialWebLab);
        renderSession(initialWebLab);
        renderSqli(initialWebLab);
    }catch(err){ /* absent/malformed — inspector keeps its placeholder text */ }
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
            renderProxy(d.web_lab_status);
            renderSession(d.web_lab_status);
            renderSqli(d.web_lab_status);
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
