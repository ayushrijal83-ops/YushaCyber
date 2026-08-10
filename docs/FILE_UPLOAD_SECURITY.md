# File Upload Security Fundamentals Mission (YC-035.7)

## Purpose

The eighth mission in the Web Security learning path, chained after
YC-035.0 (Web Fundamentals), YC-035.1 (HTTP Deep Dive), YC-035.2 (Burp
Suite Fundamentals), YC-035.3 (Authentication & Sessions), YC-035.4 (SQL
Injection Fundamentals), YC-035.5 (XSS Fundamentals), and YC-035.6 (CSRF
Fundamentals). Teaches why no single upload-validation layer — filename
extension, declared MIME type, or claimed content alone — is ever
sufficient, and what a defense-in-depth upload pipeline (size limit,
extension allowlist, MIME check, content/signature check, filename
normalization, randomized storage name, non-executable storage,
controlled serving) looks like, entirely inside the existing simulated
training environment (`cybershop.training`), using the same simulated
browser, HTTP inspector, and intercepting proxy the last six missions
already built. Still purely educational: there is no real file content
anywhere in this simulator. An "upload" is always a small set of
explicit, client-supplied fields — filename, claimed `content_type`,
claimed `size`, and a fixed `signature` label standing in for detected
magic bytes — never real bytes. Nothing here ever reads, writes, or
executes a real file, never creates a web shell, and never lets a
student escape the training environment. Real exploitation tooling,
executable payload construction, and arbitrary filesystem access are
explicitly out of scope — they don't belong in this or any future
mission in this series.

## Architecture — extends, doesn't duplicate

No new mission engine, HTTP simulator, proxy, XP engine, AI mentor, or
browser sandbox. Everything lives in the same modules built for
YC-035.0–YC-035.6:

- `app/core/terminal/web.py` — `WebApp` gains eight new routes (`GET
  /upload`, `POST /upload`, `GET /secure-upload`, `POST /secure-upload`,
  `GET /uploads`, `GET /upload/<id>` — a dynamic segment handled as a
  plain string-prefix check, this simulator has no routing framework —
  `GET /upload-security`; `GET /profile` was already present since
  YC-035.0 and is reused unchanged); a fixed, fictional `TRAINING_FILES`
  catalog and `EXPECTED_MIME_FOR_EXTENSION`/
  `EXPECTED_SIGNATURE_FOR_EXTENSION` lookup tables (same "no real
  parser, only fixed classification of explicit fields" discipline as
  the SQLi/XSS payload constants); a `UploadedFile` dataclass and
  `WebApp.uploads`/`WebApp._random_stored_name()` (mirrors YC-035.6's
  `Transfer`/`WebApp.balances`); a new `UploadLabState` dataclass
  (mirrors `CsrfLabState`) attached to `WebLab` as `.upload`; a new
  fixed investigation transcript (`build_upload_investigation_log`)
  registered in the existing `_INVESTIGATION_BUILDERS` registry.
- `app/core/terminal/commands.py` — a new `_track_upload_response()`
  helper (mirrors `_track_csrf_response()`), called from `_open`,
  `_forward`, and `_repeater`'s `send` branch exactly like its CSRF/XSS/
  SQLi counterparts; a new `samesite`-style conceptual command,
  `samesite`'s sibling for this mission is unnecessary (SameSite is
  CSRF-specific) — instead this mission needed no new terminal command
  at all: every upload is just a `POST` with explicit form fields, sent
  through the existing `open`/`request` commands.
- `app/core/missions/mission_validator.py` — twelve new `check` values
  added to the existing `web_state` type (`multipart_identified`,
  `extension_identified`, `content_validation_tested`,
  `signature_inspected`, `content_mismatch_confirmed`,
  `size_limit_tested`, `path_traversal_blocked`, `storage_inspected`,
  `random_filename_observed`, `executable_marker_blocked`,
  `secure_pipeline_compared`, `upload_evidence_collected`); several
  objectives reuse checks YC-035.0–YC-035.6 already built (`command`,
  `request_intercepted`, `body_field`, `header`, `file_contains`) — see
  "Validation" below.
- `app/core/missions/mission_runner.py` — `web_lab_status()` gains an
  `upload` sub-dict (mirrors `csrf`) and an `uploads` list (the
  simulated files, for the Uploads panel); `ai_context()`'s existing
  `web` section gains a small `upload` summary; no new methods.
- `app/core/missions/mission_loader.py` — one new `MISSIONS` entry;
  `csrf-fundamentals`'s `next_mission` now points here instead of
  `None`.
- `app/templates/labs/terminal.html` / `terminal.css` / `terminal.js` —
  a new **Upload Laboratory** section (file picker/metadata, vulnerable
  vs. secure upload, Filename Security tester, Storage/Web-Accessibility
  panel, Upload Flow Visualizer, Upload Security Pipeline, Vulnerable-
  vs-Secure comparison, an Image Processing conceptual panel, an Uploads
  list, evidence badges), reusing the existing Proxy Control panel (now
  also gated on this mission's id) and HTTP Inspector rather than a
  parallel UI or a second HTTP client.

## File upload risks

Uploading a file is a state-changing request like any other, but with an
extra hazard: the *content itself* is untrusted, and a naive server can
be tricked into trusting metadata the client fully controls (filename,
declared Content-Type) instead of the file's actual content. This
mission demonstrates the consequence concretely: a file whose filename
claims `.jpg` but whose actual content signature is `EXECUTABLE` is
accepted by an extension-only pipeline and rejected by one that also
checks content.

## Extension validation

The vulnerable pipeline (`POST /upload`) checks only the filename's
extension against `VULNERABLE_UPLOAD_EXTENSIONS` (`.jpg`, `.jpeg`,
`.png`, `.gif`, `.svg`) — a real-world mistake baked in deliberately:
`.svg` is included, even though SVG can carry embedded scripts. Nothing
else about the request is inspected, so a filename with the right
extension always passes this single check, regardless of what the
declared Content-Type or actual content signature say.

## MIME/content-type validation

`content_type` is an explicit, client-supplied field in this
simulator — the same as it would be in a real request, where the
browser sets `Content-Type` from information the client controls. The
vulnerable pipeline never inspects it at all. The secure pipeline
(`POST /secure-upload`) checks it against `EXPECTED_MIME_FOR_EXTENSION`
and rejects a mismatch (`X-Sim-Upload-Kind: mime_rejected`, `415`) —
still only a claim, not proof, of the actual content, which is why the
next layer exists.

## Magic bytes / file signatures

`signature` is a fixed, explicit training field standing in for
detected magic bytes (`JPEG`, `PNG`, `GIF`, `SVG`, `PDF`, `TEXT`,
`EXECUTABLE`) — never a real byte-level parser, since there is no real
file content anywhere in this simulator. The secure pipeline checks it
against `EXPECTED_SIGNATURE_FOR_EXTENSION` and rejects a mismatch
(`X-Sim-Upload-Kind: signature_rejected`, `415`) or, specifically, an
`EXECUTABLE` signature (`X-Sim-Upload-Kind: executable_blocked`, `403`)
— the strongest layer, since it's checking the content itself rather
than a claim about it.

## Content validation

The canonical training demonstration ties extension, MIME, and
signature together: `mismatched.jpg` claims `content_type=text/plain`
and `signature=TEXT` under a `.jpg` filename. The vulnerable pipeline
accepts it outright (extension-only check passes); the secure pipeline
rejects it (caught at the MIME-check stage, since the declared type
already doesn't match `.jpg`'s expected `image/jpeg`) — proving that
extension and MIME validation alone would both have let it through, and
that checking the actual content is what catches it.

## Size limits

`UPLOAD_SIZE_LIMIT_BYTES` (2,000,000, i.e. 2 MB) is checked first, on
both pipelines, before any other validation — a file exceeding it is
rejected with `413 Payload Too Large` and `X-Sim-Upload-Kind:
size_exceeded`, regardless of which endpoint receives it.

## Filename security / path traversal

`_looks_like_path_traversal()` is a fixed, conceptual detector (`..` in
the filename, or a leading `/` or `\`) — pure substring checks, never
real path resolution, since this module has no filesystem access
anywhere. It exists purely so the secure pipeline can demonstrably
*reject* the shape (`403 Forbidden`, `X-Sim-Upload-Kind:
path_traversal_blocked`), proving the defense instead of merely
asserting it — the vulnerable pipeline never checks this. Because
nothing in this simulator ever touches a real filesystem, a
traversal-shaped filename could never actually escape anything even
without the check; the response body's `resolved_training_path` field
is illustrative text, not a real resolved path.

## Randomized filenames / safe storage

`WebApp._random_stored_name()` returns a deterministic, reproducible
"random-looking" name (`{digest:08x}{extension}`, where `digest` is a
fixed multiplicative-hash transform of `len(self.uploads) + 1`) — never
real randomness, matching this module's established discipline (the
fixed CSRF token, the fixed SQLi/XSS payload constants) so the UI and
tests can predict it exactly. The secure pipeline always stores accepted
files under this name, with `web_accessible: False`; the vulnerable
pipeline always stores them under the original, attacker-chosen
filename, with `web_accessible: True`.

## Executable content

`shell.jpg` — labeled "training-executable-marker" in the UI — is a
fixed training file with an image-looking extension (`.jpg`) but a
`signature` of `EXECUTABLE`, the classic "renamed web shell" shape.
Never a real executable — `signature` is only ever a fixed
classification label, never parsed, compiled, or run. The vulnerable
pipeline accepts it (`X-Sim-Upload-Kind: executable_accepted`) since it
only checks the extension; the secure pipeline blocks it specifically
(`X-Sim-Upload-Kind: executable_blocked`, `403`), distinct from a
generic content mismatch, since executable content is the single most
dangerous outcome this mission demonstrates.

## Web-accessible upload directories

`UploadedFile.web_accessible` records the difference directly:
vulnerable uploads are `True` (stored under their original name, as if
directly reachable at a predictable path); secure uploads are `False`.
`GET /upload/<id>` is the "controlled download handler" — it serves an
upload's metadata only by its opaque id, auth-gated, never by resolving
a client-supplied filesystem path, contrasting with the (conceptual)
direct-path access the vulnerable pipeline's `web_accessible: True`
implies.

## Image processing

A purely conceptual, static panel (`Upload → Validation → Image
processing → Re-encoding → Safe storage`) — there is no real image
library or re-encoding anywhere in this simulator. The accompanying note
is explicit that re-encoding can help reduce risk from malformed
content but is never a complete security solution by itself, per the
ticket's instruction not to overstate any single control.

## Vulnerable pipeline

`POST /upload` — extension allowlist only (`VULNERABLE_UPLOAD_EXTENSIONS`),
no MIME check, no content/signature check, no filename normalization,
original filename preserved, `web_accessible: True`.

## Secure pipeline

`POST /secure-upload` — shared size check, a stricter extension
allowlist (`SECURE_UPLOAD_EXTENSIONS`, no `.svg`), filename
normalization (rejects path-traversal shapes), declared MIME checked
against the extension, detected signature checked against the extension
(with `EXECUTABLE` blocked specifically), randomized storage name,
`web_accessible: False`. Both pipelines share one handler,
`WebApp._upload_post(req, pipeline=...)`, so the only behavioral
difference between them is exactly the checks documented above — never
two independently-drifting code paths.

## Proxy integration

Reused verbatim from YC-035.2. `app/templates/labs/terminal.html`'s
Proxy Control section gate now includes `'file-upload-security'`
alongside the five prior missions. A student can intercept `POST
/upload`, forward it, load it into Repeater, and inspect the `Cookie`/
`filename`/`content_type`/`size`/`signature` fields exactly like any
other captured request.

## Repeater integration

No changes — `repeater`/`repeater send`/`edit body ...`/`edit path ...`
already support everything this mission needs: changing `filename`,
`content_type`, `size`, or `signature` (edit the body), or switching
between the vulnerable and secure endpoint (edit the path), then
resending. Only `_track_upload_response()`'s extra call inside the
`send` branch is new — no second Repeater implementation, no external
requests.

## HTTP history

No changes — the existing `requests`/`history` tab already lists every
`POST /upload`, `POST /secure-upload`, `GET /uploads`, and `GET
/upload-security` exchange in order, exactly like every prior web
mission.

## Request inspector / response inspector

No changes — the existing HTTP Inspector's Request/Response/Headers/
Body/Cookies/History tabs already surface the request's declared
`Content-Type` (visibly `multipart/form-data` for upload requests), body
fields (`filename`, `content_type`, `size`, `signature`), and the
response's `200`/`400`/`401`/`403`/`413`/`415` status codes with their
JSON `message` field — the same shared component every prior mission
uses, never a parallel one. No internal stack traces are ever exposed;
every rejection reason is one of the fixed, deterministic messages
`WebApp._upload_post` returns.

## Evidence collection

The Uploads panel, evidence badges (Content mismatch / Signature
inspected / Size limit / Path traversal / Executable / Vulnerable
pipeline / Secure pipeline), and the Storage panel are all pure views
over `web_lab_status()`'s `upload`/`uploads` fields — the same "server
computes structured state once, the browser only renders it" discipline
as every prior mission's panels. The final objective additionally
requires `evidence`/`inspect N` against the fixed investigation
transcript.

## Mission objectives (18, 800 XP)

Upload basics via `web` (35) → capturing an upload with Proxy (40) →
identifying `multipart/form-data` (40) → identifying the filename field
(35) → identifying the extension (35) → identifying the declared MIME
type (40) → demonstrating extension-validation insufficiency (50) →
demonstrating MIME-validation insufficiency, the same request (35) →
inspecting the signature header (40) → confirming content validation by
comparing vulnerable vs. secure rejection (50) → exceeding the size
limit (45) → a path-traversal filename blocked (50) → comparing storage
behavior across both pipelines (45) → observing the randomized stored
filename (40) → the disguised executable blocked (50) → articulating
the vulnerable-vs-secure comparison (50) → an evidence-collection
checkpoint (55) → the final investigation (65).

### Final investigation — "The Public Profile Picture"

A new, independent scenario (`upload-investigation`), registered in
`_INVESTIGATION_BUILDERS` alongside `login-flow`, `content-type-bug`,
`profile-mismatch`, `auth-lifecycle`, `sqli-investigation`,
`xss-investigation`, and `csrf-investigation`: a bug report says
"someone uploaded a profile picture that isn't actually an image, and
it's sitting in a public folder." The six-request transcript — a login →
a normal accepted upload (vulnerable, web-accessible) → a disguised
executable (`shell.jpg`) accepted by the vulnerable, extension-only
pipeline → the same file rejected by the secure pipeline's signature
check → an oversized file rejected by the shared size limit → a normal
upload accepted by the secure pipeline (randomized name, private) —
shows the vulnerability and its fix side by side. Graded identically to
every prior mission's final objective: `evidence`/`inspect N` to read
the log, then a conclusion recorded via `echo "..." >
web/upload-investigation.txt`, validated with the existing
`file_contains` check (requiring the phrase "defense in depth").

## Validation

Twelve new `check` values on the existing `type: "web_state"` (no new
validator type, per this project's established discipline):

- **`multipart_identified`** — the last request's `Content-Type` header
  contains `multipart/form-data`.
- **`extension_identified`** — the last response's `X-Sim-Upload-
  Extension` header matches the expected value.
- **`content_validation_tested`** — `WebLab.upload.content_mismatch_seen`
  is set (the vulnerable pipeline accepted a claimed-vs-actual
  mismatch).
- **`signature_inspected`** — `WebLab.upload.signature_inspected` is set
  (any response carrying `X-Sim-Upload-Signature` was observed).
- **`content_mismatch_confirmed`** — both `content_mismatch_seen` *and*
  `secure_rejection_seen` are set (the same mismatch sent to both
  endpoints, accepted by one and rejected by the other).
- **`size_limit_tested`** — `WebLab.upload.size_limit_seen` is set (a
  `413` response was observed).
- **`path_traversal_blocked`** — `WebLab.upload.path_traversal_blocked`
  is set (a `403 path_traversal_blocked` response was observed).
- **`storage_inspected`** — both `vulnerable_accepted_seen` *and*
  `secure_accepted_seen` are set.
- **`random_filename_observed`** — the last response is `X-Sim-Upload-
  Kind: accepted_secure` and its `X-Sim-Upload-Stored-Name` differs from
  the submitted `filename`.
- **`executable_marker_blocked`** — `WebLab.upload.executable_blocked`
  is set (a `403 executable_blocked` response was observed).
- **`secure_pipeline_compared`** — both `vulnerable_accepted_seen` *and*
  `secure_accepted_seen` are set (same underlying flags as
  `storage_inspected`, a different teaching moment on the same
  evidence — mirrors the established precedent of two objectives
  reading the same flag, e.g. YC-035.6's `cs-7`/`cs-8`).
- **`upload_evidence_collected`** — a capstone conjunction of seven
  `UploadLabState` flags (content mismatch, signature inspected, size
  limit, path traversal, executable blocked, vulnerable accepted, secure
  accepted). **Deliberately a distinct name from YC-035.4's
  `evidence_collected`, YC-035.5's `xss_evidence_collected`, and
  YC-035.6's `csrf_evidence_collected`** (not a reuse) — each reads its
  own mission's `WebLab` sub-state and would silently never pass for a
  student who only touched this mission's endpoints if the names
  collided;
  `TestUploadValidatorChecks::test_upload_evidence_collected_does_not_reuse_other_missions_evidence_checks`
  guards this directly.

**Explicitly reused, not duplicated**: the opening "upload basics"
objective reuses the existing `command` type (`web`); "capture upload"
reuses YC-035.2's `request_intercepted`; "filename" reuses the existing
generic `body_field` check; "MIME type" reuses the existing generic
`header` check; the final investigation reuses `file_contains`, matching
every prior mission.

## Hints

Every objective has three progressive hints (a nudge, a narrower nudge,
then the exact command), following the same pattern established since
YC-035.1 — `MissionRunner.use_hint()` advances one step per re-ask,
capped at the last entry, unchanged.

## CyberMentor integration

`ai_context()`'s existing `web` section (built up across
YC-035.0–.6) gains a small `upload` summary:

```python
ctx["web"]["upload"] = {
    "last_upload_kind": "accepted_vulnerable" | "accepted_secure" | "content_mismatch"
                       | "executable_accepted" | "extension_rejected" | "mime_rejected"
                       | "signature_rejected" | "executable_blocked" | "size_exceeded"
                       | "path_traversal_blocked" | "unauthenticated" | None,
    "last_filename_extension": str | None,
    "last_mime": str | None,
    "last_signature": str | None,
    "signature_inspected": bool,
    "content_mismatch_seen": bool,
    "size_limit_seen": bool,
    "path_traversal_blocked": bool,
    "executable_blocked": bool,
    "vulnerable_accepted_seen": bool,
    "secure_accepted_seen": bool,
    "upload_count": int,
}
```

Small and structured, so CyberMentor can explain *why* checking `.jpg`
alone isn't enough — e.g. answering "an extension is only a filename
claim; a secure upload pipeline validates the actual content and
applies multiple independent controls" — from actual mission state
(`last_upload_kind`, `content_mismatch_seen`) without repeating full
request/response bodies on every turn, and without ever solving the
objective for the student. As with every mission before it:
`ai_context()` is a documented extension point, but the live
`/api/ai/chat` path doesn't currently thread mission state into the
prompt — this hook is built for consistency with the established
precedent, not as new chat wiring.

## Security isolation

Same guarantees as every prior web mission, re-verified for the new
surface:

- `web.py` and `commands.py` still import nothing network- or
  database-capable, and neither imports a real filesystem primitive
  (`open(`, `os.path`, `shutil.`) — AST/source-text tests, matching
  YC-035.4/.5/.6's precedent.
- Every new route (`/upload`, `/secure-upload`, `/uploads`,
  `/upload-security`) sits behind the exact same `host != HOST`
  rejection `open`/`request` already enforce — tested directly with
  `evil.example.com`.
- There is no real file content, real filesystem write, or real
  filesystem read anywhere in this module — an "upload" is always a
  small set of explicit string/int fields (`filename`, `content_type`,
  `size`, `signature`); nothing here could ever actually write outside
  (or inside) any real directory, regardless of validation outcome.
  `test_path_traversal_never_escapes_training_prefix` and
  `test_no_real_file_io_anywhere_in_module` assert this directly.
- `UploadedFile.stored_name` for a path-traversal-shaped filename is
  only ever rejected before storage on the secure pipeline (never
  stored), and even on the vulnerable pipeline it is only ever a string
  label, never a resolved path.
- `WebLab.upload`/`WebApp.uploads` state is per-instance, like every
  other `WebLab` field — two students, or two test cases, never share
  state.
- No `eval`, `exec`, or dangerous DOM APIs (`document.write`,
  `Function(...)`, `fetch`, `XMLHttpRequest`) appear anywhere in
  `web.py` or the Upload section of `terminal.js` — asserted directly
  against the shipped source.

## UI — Upload Laboratory section

A new section (`app/templates/labs/terminal.html`, styled in
`terminal.css`, driven by `terminal.js`), shown only for this mission
(gated on `mission.mission.id == 'file-upload-security'`), placed above
the existing Proxy Control panel and HTTP Inspector so
Request/Response/Headers/Body/Cookies/History stay a single shared
component rather than being duplicated:

- **Select Training File box**: a dropdown of the fixed training
  catalog, a read-only metadata panel (Filename/Extension/MIME/Size/
  Signature/Content/Hash — the hash is a fixed, non-cryptographic
  display value, never used by any validator check), overridable
  filename/content_type/size/signature fields, and **Upload
  (Vulnerable)** / **Upload (Secure)** buttons.
- **Filename Security box**: a filename input (defaulting to
  `../profile.jpg`), a **Send to Secure Upload** button, and a live
  Requested path / Resolved training path / Status display.
- **Storage & Web-Accessibility box**: the INSECURE vs. SECURE storage
  paths, with live `stored_name`/`web_accessible` values from the most
  recent upload on each pipeline.
- **Upload Flow Visualizer**: seven clickable steps (User Selects File →
  Browser → POST /upload → Server Validation → Storage → File Reference
  → Browser Displays File).
- **Upload Security Pipeline**: ten clickable steps matching the
  numbered pipeline in the mission spec exactly.
- **Vulnerable vs. Secure — Side by Side**: two clickable columns (four
  vulnerable-pipeline steps, six secure-pipeline steps).
- **Image Processing panel**: a static conceptual diagram with its
  "not a complete solution" caveat.
- **Your Uploads**: a live list (from `web_lab_status.uploads`), each
  entry tagged "(vulnerable — web-accessible)" or "(secure — private)".
- **Evidence badges**: a pure view over `WebLab.upload`'s flags —
  always labeled text, never color alone.

Every button here does exactly one thing: build an `open ...` command
string a student could type themselves and submit it through the same
`exec()`/`/execute` path the terminal input and every other mission's
buttons already use — no new HTTP client, no real file upload, no live
file-processing console.

## Accessibility & responsive design

Reuses every existing pattern verbatim: real `<button>` elements,
`:focus-visible` rings, the page's global `prefers-reduced-motion` rule,
`aria-live` already on the terminal output. Every evidence badge and
history entry is communicated as text, never by color alone (e.g.
"Content mismatch: seen" / "not seen", "(vulnerable — web-accessible)" /
"(secure — private)"). Validation outcomes use explicit labels
throughout (Accepted/Rejected/Blocked/Validated/Invalid/Secure/
Vulnerable/Simulated), matching the ticket's explicit accessibility
requirement. The new grids use `repeat(auto-fit, minmax(...))` so they
reflow to a single column under narrow viewports with no bespoke
breakpoint logic, matching how the Proxy Control and CSRF grids already
stack.

## Achievement

"Upload Inspector" was evaluated and **not** added as a database row —
the same reasoning as every prior mission's optional achievement in this
series (HTTP Detective, Proxy Operator, Session Detective, Query
Detective, Context Hunter, Request Guardian): the achievement metric
calculator doesn't yet track a mission-completion metric keyed by
mission id, so a new row would never unlock. The existing generic
mission-completion/XP-based achievements still run unchanged.

## Testing

`tests/test_file_upload_security.py` — `WebApp` routing for every new
route (auth-gated pages, the vulnerable/secure upload split, the
disguised-executable acceptance on the vulnerable endpoint, MIME/
signature/path-traversal/executable rejection paths on the secure
endpoint, the shared size limit, the controlled download handler, the
uploads list), `_track_upload_response()`'s wiring through `open`/
`forward`/`repeater send`, save/restore of `WebLab.upload` and upload
state, the twelve new validator checks (including graceful failure with
no `web_lab`, and a dedicated regression guard against colliding with
YC-035.4/.5/.6's evidence-check names), the `upload-investigation`
scenario's determinism and isolation from live session state, mission
registration/loading (18 objectives, XP sums to 800, progressive hints,
chaining after `csrf-fundamentals`), a full scripted solve plus a "no
premature completion" guard, `web_lab_status`/`ai_context` reflecting
upload state, security isolation (no network/DB-capable or filesystem
imports, no real file I/O anywhere, path traversal never escapes
anything regardless of outcome, no `eval`/dangerous DOM APIs in either
the Python module or the Upload section of `terminal.js`, state never
leaking across instances), a full HTTP-level chain (locked → available
after completing CSRF Fundamentals → completed, with real XP/level/
dashboard stats), and page/API reachability (the Upload Laboratory
section present only on this mission, `/execute` returning upload
state, the hint endpoint advancing progressively).

`tests/test_csrf_fundamentals.py` — one updated assertion:
`csrf-fundamentals["next_mission"]` is now `"file-upload-security"`
instead of `None`, since this mission is no longer terminal in the
chain (same pattern YC-035.6 applied to `test_xss_fundamentals.py`).

## Manual browser test

1. Log in, open `/terminal/mission/file-upload-security` (unlocks after
   completing CSRF Fundamentals).
2. Confirm the mission header, objectives sidebar, the new **Upload
   Laboratory** section (Select Training File, Filename Security,
   Storage & Web-Accessibility boxes, Upload Flow Visualizer, Upload
   Security Pipeline, Vulnerable-vs-Secure comparison, Image Processing,
   Your Uploads, evidence badges), the Proxy Control panel, and the HTTP
   Inspector all render.
3. Select `avatar.jpg` in the file picker — confirm the metadata panel
   shows Filename/Extension/MIME/Size/Signature/Content/Hash.
4. Turn Proxy intercept ON, click **Upload (Vulnerable)** — confirm it's
   intercepted (inspect the `Content-Type: multipart/form-data` request
   header and the `filename`/`content_type`/`size`/`signature` body
   fields), then **Forward**.
5. Select `mismatched.jpg`, click **Upload (Vulnerable)** — confirm it's
   still accepted (`200 OK`) despite the content mismatch, then click
   **Upload (Secure)** with the same fields — confirm it's rejected.
6. Select `oversized.jpg`, click **Upload (Vulnerable)** — confirm
   `413 Payload Too Large`.
7. In the Filename Security box, click **Send to Secure Upload** with
   the default `../profile.jpg` — confirm the Status shows **BLOCKED**.
8. Select `avatar.jpg`, click **Upload (Secure)** — confirm `200 OK` and
   check the Storage & Web-Accessibility panel shows a randomized
   secure `stored_name` different from `avatar.jpg`, alongside the
   earlier vulnerable upload's unchanged original filename.
9. Select `training-executable-marker`, click **Upload (Secure)** —
   confirm `403 Forbidden`; click **Upload (Vulnerable)** with the same
   fields — confirm it's accepted anyway.
10. Click through the Upload Flow Visualizer's seven steps and the
    Upload Security Pipeline's ten steps — confirm each shows a distinct
    explanation.
11. Click through the Vulnerable-vs-Secure comparison's steps on both
    sides — confirm each shows a distinct explanation.
12. Click **Refresh List** in Your Uploads — confirm every upload above
    appears, correctly tagged vulnerable/secure.
13. Open the History tab — confirm every request above is present and
    inspectable.
14. Complete the final investigation objective (`evidence`, `inspect
    1`–`6`, then the `echo ... > web/upload-investigation.txt` command);
    confirm the completion overlay shows 800 XP.
15. Open AI Mentor, ask "why isn't checking .jpg enough?" — confirm the
    answer reflects the actual mission state (the vulnerable pipeline's
    lack of MIME/signature checks), not a generic definition.
16. Refresh the page — confirm mission progress, XP, uploads list, and
    the evidence badges all survive.
17. Attempt `open https://evil.example.com/upload` — confirm the exact
    rejection message and that nothing new appears in the Inspector;
    confirm no button on this page ever performs a real file read/
    write, and that YushaCyber's own source files are untouched
    (nothing in this session writes to disk at all).

## Windows commands

```powershell
$env:PYTHONPATH = "."
python -m pytest tests/test_file_upload_security.py -q
python -m pytest tests/ -q
venv\Scripts\ruff.exe check app\core\terminal\web.py app\core\terminal\commands.py app\core\missions\mission_validator.py app\core\missions\mission_runner.py app\core\missions\mission_loader.py tests\test_file_upload_security.py tests\test_csrf_fundamentals.py
```
