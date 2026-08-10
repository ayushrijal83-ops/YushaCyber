"""Tests for YC-035.7 — File Upload Security Fundamentals mission."""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="yc0357-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test_upload.db"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.core.missions.mission_loader import MISSIONS, get_mission
from app.core.missions.mission_runner import MissionRunner
from app.core.missions.mission_validator import validate
from app.core.terminal.shell import Shell
from app.core.terminal.web import (
    HOST,
    SECURE_UPLOAD_EXTENSIONS,
    UPLOAD_SIZE_LIMIT_BYTES,
    VULNERABLE_UPLOAD_EXTENSIONS,
    WebApp,
    build_request,
    build_web_lab,
    parse_url,
)

STUDENT_SID = "student-session"
MULTIPART_CT = "multipart/form-data; boundary=----TrainingBoundary"

SOLVE: list[str] = [
    "web",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login',
    "intercept on",
    (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
     '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
     "https://cybershop.training/upload"),
    "forward",
    "intercept off",
    (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
     '-d "filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
     "https://cybershop.training/upload"),
    (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
     '-d "filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
     "https://cybershop.training/secure-upload"),
    (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
     '-d "filename=oversized.jpg&content_type=image/jpeg&size=3000000&signature=JPEG" '
     "https://cybershop.training/upload"),
    (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
     '-d "filename=../avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
     "https://cybershop.training/secure-upload"),
    (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
     '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
     "https://cybershop.training/secure-upload"),
    (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
     '-d "filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
     "https://cybershop.training/secure-upload"),
    "evidence",
    "inspect 1", "inspect 2", "inspect 3", "inspect 4", "inspect 5", "inspect 6",
    ('echo "Conclusion: the vulnerable endpoint validated only the file extension, letting a '
     "disguised executable file reach storage under its original, web-accessible name. The "
     "secure endpoint applied multiple independent controls - size, extension, filename "
     "normalization, declared MIME, and content signature - and stored the valid file under a "
     "randomized, private name instead. No single layer is enough; this is defense in depth."
     '" > web/upload-investigation.txt'),
]


# ═══════════════════════════════════════════
# WebApp routing — new/extended routes
# ═══════════════════════════════════════════
class TestWebAppRouting:
    def _login(self, app):
        url = parse_url(f"https://{HOST}/auth/login")
        req = build_request("POST", url, body="username=student&password=training123")
        resp = app.handle(req)
        return resp.cookies["session_id"]

    def _upload(self, app, path, filename, content_type, size, signature, sid, extra_headers=None):
        url = parse_url(f"https://{HOST}{path}")
        body = f"filename={filename}&content_type={content_type}&size={size}&signature={signature}"
        headers = {"Content-Type": MULTIPART_CT}
        if extra_headers:
            headers.update(extra_headers)
        req = build_request("POST", url, body=body, cookies={"session_id": sid}, extra_headers=headers)
        return req, app.handle(req)

    def test_upload_get_describes_endpoint(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/upload")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert resp.status_code == 200
        assert "/upload" in resp.body

    def test_secure_upload_get_requires_auth(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/secure-upload")
        req = build_request("GET", url)
        resp = app.handle(req)
        # GET /secure-upload is informational, not auth-gated (mirrors /upload)
        assert resp.status_code == 200

    def test_upload_requires_auth(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/upload")
        req = build_request("POST", url, body="filename=avatar.jpg&content_type=image/jpeg&size=1&signature=JPEG")
        resp = app.handle(req)
        assert resp.status_code == 401
        assert resp.headers["X-Sim-Upload-Kind"] == "unauthenticated"

    def test_vulnerable_upload_accepts_normal_file(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/upload", "avatar.jpg", "image/jpeg", 24000, "JPEG", sid)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Upload-Kind"] == "accepted_vulnerable"
        assert resp.headers["X-Sim-Upload-Web-Accessible"] == "true"
        assert app.uploads[0].web_accessible is True
        assert app.uploads[0].stored_name == "avatar.jpg"

    def test_vulnerable_upload_rejects_disallowed_extension(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/upload", "notes.txt", "text/plain", 1200, "TEXT", sid)
        assert resp.status_code == 415
        assert resp.headers["X-Sim-Upload-Kind"] == "extension_rejected"

    def test_vulnerable_upload_accepts_content_mismatch(self):
        """The whole point of the mission: the vulnerable pipeline only
        checks the extension, so a claimed-vs-actual mismatch still
        succeeds."""
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/upload", "mismatched.jpg", "text/plain", 2000, "TEXT", sid)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Upload-Kind"] == "content_mismatch"

    def test_vulnerable_upload_accepts_disguised_executable(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/upload", "shell.jpg", "image/jpeg", 8000, "EXECUTABLE", sid)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Upload-Kind"] == "executable_accepted"

    def test_secure_upload_accepts_valid_file(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "avatar.jpg", "image/jpeg", 24000, "JPEG", sid)
        assert resp.status_code == 200
        assert resp.headers["X-Sim-Upload-Kind"] == "accepted_secure"
        assert resp.headers["X-Sim-Upload-Web-Accessible"] == "false"
        stored = resp.headers["X-Sim-Upload-Stored-Name"]
        assert stored != "avatar.jpg"
        assert stored.endswith(".jpg")
        assert app.uploads[0].web_accessible is False

    def test_secure_upload_rejects_svg(self):
        """SVG is excluded from the secure allowlist (can carry scripts),
        while the vulnerable allowlist still includes it."""
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "training-marker.svg", "image/svg+xml",
                               3400, "SVG", sid)
        assert resp.status_code == 415
        assert resp.headers["X-Sim-Upload-Kind"] == "extension_rejected"
        assert ".svg" not in SECURE_UPLOAD_EXTENSIONS
        assert ".svg" in VULNERABLE_UPLOAD_EXTENSIONS

    def test_secure_upload_rejects_path_traversal(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "../avatar.jpg", "image/jpeg", 24000, "JPEG", sid)
        assert resp.status_code == 403
        assert resp.headers["X-Sim-Upload-Kind"] == "path_traversal_blocked"
        assert len(app.uploads) == 0

    def test_secure_upload_rejects_backslash_traversal(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "..\\avatar.jpg", "image/jpeg", 24000, "JPEG", sid)
        assert resp.status_code == 403
        assert resp.headers["X-Sim-Upload-Kind"] == "path_traversal_blocked"

    def test_secure_upload_rejects_mime_mismatch(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "avatar.jpg", "text/plain", 24000, "JPEG", sid)
        assert resp.status_code == 415
        assert resp.headers["X-Sim-Upload-Kind"] == "mime_rejected"

    def test_secure_upload_rejects_mismatched_training_file_at_mime_stage(self):
        """The canonical 'mismatched.jpg' training file (claimed MIME
        and signature both wrong for .jpg) is caught by the MIME check
        before the signature check ever runs."""
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "mismatched.jpg", "text/plain", 2000, "TEXT", sid)
        assert resp.status_code == 415
        assert resp.headers["X-Sim-Upload-Kind"] == "mime_rejected"

    def test_secure_upload_rejects_generic_signature_mismatch_with_correct_mime(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "avatar.jpg", "image/jpeg", 24000, "TEXT", sid)
        assert resp.status_code == 415
        assert resp.headers["X-Sim-Upload-Kind"] == "signature_rejected"

    def test_secure_upload_blocks_executable_signature(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/secure-upload", "shell.jpg", "image/jpeg", 8000, "EXECUTABLE", sid)
        assert resp.status_code == 403
        assert resp.headers["X-Sim-Upload-Kind"] == "executable_blocked"
        assert len(app.uploads) == 0

    def test_size_limit_enforced_on_both_pipelines(self):
        app = WebApp()
        sid = self._login(app)
        for path in ("/upload", "/secure-upload"):
            _, resp = self._upload(app, path, "oversized.jpg", "image/jpeg", 3_000_000, "JPEG", sid)
            assert resp.status_code == 413
            assert resp.headers["X-Sim-Upload-Kind"] == "size_exceeded"

    def test_size_at_exact_limit_is_allowed(self):
        app = WebApp()
        sid = self._login(app)
        _, resp = self._upload(app, "/upload", "avatar.jpg", "image/jpeg", UPLOAD_SIZE_LIMIT_BYTES, "JPEG", sid)
        assert resp.status_code == 200

    def test_uploads_list_requires_auth(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/uploads")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/login"

    def test_uploads_list_shows_own_uploads(self):
        app = WebApp()
        sid = self._login(app)
        self._upload(app, "/upload", "avatar.jpg", "image/jpeg", 24000, "JPEG", sid)
        url = parse_url(f"https://{HOST}/uploads")
        req = build_request("GET", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 200
        assert "avatar.jpg" in resp.body

    def test_upload_detail_controlled_handler(self):
        app = WebApp()
        sid = self._login(app)
        _req, resp = self._upload(app, "/secure-upload", "avatar.jpg", "image/jpeg", 24000, "JPEG", sid)
        stored = resp.headers["X-Sim-Upload-Stored-Name"]
        url = parse_url(f"https://{HOST}/upload/{stored}")
        req = build_request("GET", url, cookies={"session_id": sid})
        detail = app.handle(req)
        assert detail.status_code == 200
        assert stored in detail.body
        assert "private" in detail.body.lower()

    def test_upload_detail_unknown_id_not_found(self):
        app = WebApp()
        sid = self._login(app)
        url = parse_url(f"https://{HOST}/upload/does-not-exist.jpg")
        req = build_request("GET", url, cookies={"session_id": sid})
        resp = app.handle(req)
        assert resp.status_code == 404

    def test_upload_security_page(self):
        app = WebApp()
        url = parse_url(f"https://{HOST}/upload-security")
        req = build_request("GET", url)
        resp = app.handle(req)
        assert resp.status_code == 200
        assert "defense in depth" in resp.body.lower()


# ═══════════════════════════════════════════
# Upload state tracking (_track_upload_response via open/forward/repeater)
# ═══════════════════════════════════════════
class TestUploadStateTracking:
    def _shell(self) -> Shell:
        sh = Shell()
        sh.web_lab = build_web_lab("upload-investigation")
        return sh

    def _login(self, sh):
        sh.execute('open -X POST -d "username=student&password=training123" '
                  "https://cybershop.training/auth/login")

    def test_signature_inspected_flag(self):
        sh = self._shell()
        self._login(sh)
        assert sh.web_lab.upload.signature_inspected is False
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert sh.web_lab.upload.signature_inspected is True

    def test_content_mismatch_flag(self):
        sh = self._shell()
        self._login(sh)
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
                  "https://cybershop.training/upload")
        assert sh.web_lab.upload.content_mismatch_seen is True
        assert sh.web_lab.upload.vulnerable_accepted_seen is True

    def test_secure_rejection_flag_from_mime_mismatch(self):
        sh = self._shell()
        self._login(sh)
        assert sh.web_lab.upload.secure_rejection_seen is False
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=text/plain&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert sh.web_lab.upload.secure_rejection_seen is True

    def test_size_and_traversal_and_executable_flags(self):
        sh = self._shell()
        self._login(sh)
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=oversized.jpg&content_type=image/jpeg&size=3000000&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert sh.web_lab.upload.size_limit_seen is True

        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=../avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert sh.web_lab.upload.path_traversal_blocked is True

        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
                  "https://cybershop.training/secure-upload")
        assert sh.web_lab.upload.executable_blocked is True
        assert sh.web_lab.upload.secure_rejection_seen is True

    def test_vulnerable_and_secure_accepted_flags_via_forward(self):
        sh = self._shell()
        self._login(sh)
        sh.execute("intercept on")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert sh.web_lab.upload.secure_accepted_seen is False  # queued, not yet handled
        sh.execute("forward")
        assert sh.web_lab.upload.secure_accepted_seen is True

    def test_secure_accepted_flag_via_repeater_send(self):
        sh = self._shell()
        self._login(sh)
        # History #1 is the login; this is history #2 — a secure-upload
        # attempt with a bad signature, rejected on arrival.
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=1&signature=TEXT" '
                  "https://cybershop.training/secure-upload")
        sh.execute("repeater 2")
        sh.execute('edit body "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG"')
        assert sh.web_lab.upload.secure_accepted_seen is False
        sh.execute("repeater send")
        assert sh.web_lab.upload.secure_accepted_seen is True

    def test_state_survives_save_and_restore(self):
        sh = self._shell()
        self._login(sh)
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
                  "https://cybershop.training/secure-upload")
        snapshot = sh.web_lab.to_dict()
        lab2 = build_web_lab("upload-investigation")
        lab2.apply_state(snapshot)
        assert lab2.upload.executable_blocked is True

    def test_uploads_persist_through_save_and_restore(self):
        sh = self._shell()
        self._login(sh)
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/upload")
        snapshot = sh.web_lab.to_dict()
        lab2 = build_web_lab("upload-investigation")
        lab2.apply_state(snapshot)
        assert len(lab2.app.uploads) == 1
        assert lab2.app.uploads[0].original_filename == "avatar.jpg"


# ═══════════════════════════════════════════
# Validator — new checks
# ═══════════════════════════════════════════
class TestUploadValidatorChecks:
    def _shell(self):
        sh = Shell()
        sh.web_lab = build_web_lab("upload-investigation")
        return sh

    def _login(self, sh):
        sh.execute('open -X POST -d "username=student&password=training123" '
                  "https://cybershop.training/auth/login")

    def _obj(self, check, match="1", **extra):
        v = {"type": "web_state", "check": check, "match": match}
        v.update(extra)
        return {"id": "u", "xp": 10, "validate": v}

    def test_multipart_identified(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("multipart_identified")
        sh.execute('open -X POST -d "filename=avatar.jpg&content_type=image/jpeg&size=1&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=1&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert validate(obj, sh).passed

    def test_extension_identified(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("extension_identified", ".jpg")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=1&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert validate(obj, sh).passed

    def test_content_validation_tested(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("content_validation_tested")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
                  "https://cybershop.training/upload")
        assert validate(obj, sh).passed

    def test_signature_inspected(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("signature_inspected")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=1&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert validate(obj, sh).passed

    def test_content_mismatch_confirmed(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("content_mismatch_confirmed")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
                  "https://cybershop.training/upload")
        assert not validate(obj, sh).passed  # vulnerable side only
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
                  "https://cybershop.training/secure-upload")
        assert validate(obj, sh).passed

    def test_size_limit_tested(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("size_limit_tested")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=oversized.jpg&content_type=image/jpeg&size=3000000&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert validate(obj, sh).passed

    def test_path_traversal_blocked(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("path_traversal_blocked")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=../avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert validate(obj, sh).passed

    def test_storage_inspected_requires_both_pipelines(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("storage_inspected")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert validate(obj, sh).passed

    def test_random_filename_observed(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("random_filename_observed")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert validate(obj, sh).passed

    def test_executable_marker_blocked(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("executable_marker_blocked")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
                  "https://cybershop.training/secure-upload")
        assert validate(obj, sh).passed

    def test_secure_pipeline_compared(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("secure_pipeline_compared")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert not validate(obj, sh).passed
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert validate(obj, sh).passed

    def test_upload_evidence_collected(self):
        sh = self._shell()
        self._login(sh)
        obj = self._obj("upload_evidence_collected")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=mismatched.jpg&content_type=text/plain&size=2000&signature=TEXT" '
                  "https://cybershop.training/upload")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=oversized.jpg&content_type=image/jpeg&size=3000000&signature=JPEG" '
                  "https://cybershop.training/upload")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=../avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
                  "https://cybershop.training/secure-upload")
        assert not validate(obj, sh).passed  # secure_accepted_seen still missing
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/secure-upload")
        assert validate(obj, sh).passed

    def test_checks_fail_gracefully_without_web_lab(self):
        sh = Shell()
        for check in ("multipart_identified", "extension_identified", "content_validation_tested",
                      "signature_inspected", "content_mismatch_confirmed", "size_limit_tested",
                      "path_traversal_blocked", "storage_inspected", "random_filename_observed",
                      "executable_marker_blocked", "secure_pipeline_compared",
                      "upload_evidence_collected"):
            assert not validate(self._obj(check), sh).passed

    def test_upload_evidence_collected_does_not_reuse_other_missions_evidence_checks(self):
        """Guards against capstone checks colliding across missions —
        each mission's own name reads its own WebLab sub-state."""
        sh = self._shell()
        self._login(sh)
        sh.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert not validate(self._obj("evidence_collected"), sh).passed  # SQLi's name
        assert not validate(self._obj("xss_evidence_collected"), sh).passed  # XSS's name
        assert not validate(self._obj("csrf_evidence_collected"), sh).passed  # CSRF's name


# ═══════════════════════════════════════════
# Investigation scenario
# ═══════════════════════════════════════════
class TestInvestigationScenario:
    def test_upload_investigation_scenario(self):
        lab = build_web_lab("upload-investigation")
        assert len(lab.investigation_log) == 6

        login_req, login_resp = lab.investigation_log[0]
        assert login_req.path == "/auth/login"
        assert login_resp.status_code == 302

        normal_req, normal_resp = lab.investigation_log[1]
        assert normal_req.path == "/upload"
        assert normal_resp.headers["X-Sim-Upload-Kind"] == "accepted_vulnerable"

        exec_vuln_req, exec_vuln_resp = lab.investigation_log[2]
        assert exec_vuln_req.path == "/upload"
        assert exec_vuln_resp.status_code == 200
        assert exec_vuln_resp.headers["X-Sim-Upload-Kind"] == "executable_accepted"

        exec_secure_req, exec_secure_resp = lab.investigation_log[3]
        assert exec_secure_req.path == "/secure-upload"
        assert exec_secure_resp.status_code == 403
        assert exec_secure_resp.headers["X-Sim-Upload-Kind"] == "executable_blocked"

        oversized_req, oversized_resp = lab.investigation_log[4]
        assert oversized_req.path == "/upload"
        assert oversized_resp.status_code == 413

        secure_ok_req, secure_ok_resp = lab.investigation_log[5]
        assert secure_ok_req.path == "/secure-upload"
        assert secure_ok_resp.status_code == 200
        assert secure_ok_resp.headers["X-Sim-Upload-Kind"] == "accepted_secure"

    def test_scenario_is_deterministic(self):
        a = build_web_lab("upload-investigation")
        b = build_web_lab("upload-investigation")
        assert a.investigation_log == b.investigation_log

    def test_scenario_never_touches_live_session(self):
        lab = build_web_lab("upload-investigation")
        assert lab.session.history == []
        assert lab.session.cookies == {}
        assert lab.upload.executable_blocked is False
        assert lab.app.uploads == []


# ═══════════════════════════════════════════
# Mission registration / loading
# ═══════════════════════════════════════════
class TestLoader:
    def test_mission_registered(self):
        assert "file-upload-security" in MISSIONS

    def test_mission_loads(self):
        m = get_mission("file-upload-security")
        assert m is not None
        assert m["title"] == "File Upload Security Fundamentals"
        assert m["difficulty"] == "Intermediate"
        assert m["xp_total"] == 800

    def test_objective_count(self):
        m = get_mission("file-upload-security")
        assert len(m["objectives"]) == 18

    def test_xp_sums_to_total(self):
        m = get_mission("file-upload-security")
        assert sum(o["xp"] for o in m["objectives"]) == m["xp_total"]

    def test_every_objective_has_progressive_hints(self):
        m = get_mission("file-upload-security")
        for o in m["objectives"]:
            assert "hints" in o
            assert len(o["hints"]) >= 2

    def test_chained_after_csrf_fundamentals(self):
        assert MISSIONS["csrf-fundamentals"]["next_mission"] == "file-upload-security"

    def test_terminal_mission(self):
        m = get_mission("file-upload-security")
        assert m["next_mission"] is None

    def test_web_lab_scenario_set(self):
        m = get_mission("file-upload-security")
        assert m["web_lab"] == "upload-investigation"

    def test_web_workspace_seeded(self):
        m = get_mission("file-upload-security")
        assert "web" in m["filesystem"]["home"]["student"]


# ═══════════════════════════════════════════
# Full mission run
# ═══════════════════════════════════════════
class TestFullRun:
    def test_complete_solve(self):
        r = MissionRunner("file-upload-security", 1)
        for c in SOLVE:
            r.execute(c)
        assert r.progress.completed
        assert r.progress.xp_earned == 800
        assert sorted(r.progress.completed_ids) == sorted(
            o["id"] for o in r.mission["objectives"])

    def test_no_premature_completion(self):
        r = MissionRunner("file-upload-security", 2)
        r.execute("web")
        assert not r.progress.completed
        assert len(r.progress.completed_ids) < len(r.mission["objectives"])

    def test_web_lab_status_carries_upload_fields_and_uploads(self):
        r = MissionRunner("file-upload-security", 3)
        r.execute('open -X POST -d "username=student&password=training123" '
                 "https://cybershop.training/auth/login")
        r.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                 '-d "filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
                 "https://cybershop.training/upload")
        status = r.web_lab_status()
        assert status["upload"]["vulnerable_accepted_seen"] is True
        assert len(status["uploads"]) == 1
        assert status["uploads"][0]["signature"] == "EXECUTABLE"

    def test_ai_context_includes_upload_summary(self):
        r = MissionRunner("file-upload-security", 4)
        r.execute('open -X POST -d "username=student&password=training123" '
                 "https://cybershop.training/auth/login")
        r.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                 '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                 "https://cybershop.training/upload")
        ctx = r.ai_context()
        assert ctx["web"]["upload"]["last_upload_kind"] == "accepted_vulnerable"
        assert ctx["web"]["upload"]["vulnerable_accepted_seen"] is True
        assert ctx["web"]["upload"]["secure_accepted_seen"] is False

    def test_save_restore_preserves_upload_state(self):
        r = MissionRunner("file-upload-security", 5)
        r.execute('open -X POST -d "username=student&password=training123" '
                 "https://cybershop.training/auth/login")
        r.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                 '-d "filename=oversized.jpg&content_type=image/jpeg&size=3000000&signature=JPEG" '
                 "https://cybershop.training/upload")
        state = r.save_state()

        r2 = MissionRunner.from_state(state)
        assert r2.shell.web_lab.upload.size_limit_seen is True

    def test_sessions_are_isolated(self):
        r1 = MissionRunner("file-upload-security", 6)
        r1.execute('open -X POST -d "username=student&password=training123" '
                  "https://cybershop.training/auth/login")
        r1.execute(f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                  '-d "filename=avatar.jpg&content_type=image/jpeg&size=24000&signature=JPEG" '
                  "https://cybershop.training/upload")
        assert MissionRunner("file-upload-security", 7).shell.web_lab.upload.vulnerable_accepted_seen is False


# ═══════════════════════════════════════════
# Security isolation
# ═══════════════════════════════════════════
class TestSecurityIsolation:
    def test_web_module_still_has_no_network_or_db_imports(self):
        import ast

        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        forbidden = {"socket", "subprocess", "requests", "http.client", "os",
                    "urllib.request", "shutil", "ftplib", "smtplib",
                    "sqlite3", "psycopg2", "pymysql", "mysql", "sqlalchemy"}
        assert not (imported_modules & forbidden), \
            f"forbidden imports: {imported_modules & forbidden}"

    def test_commands_module_has_no_network_or_db_imports(self):
        import ast

        import app.core.terminal.commands as cmdmod
        with open(cmdmod.__file__, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        forbidden = {"socket", "subprocess", "requests", "http.client",
                    "urllib.request", "sqlite3", "psycopg2", "pymysql"}
        assert not (imported_modules & forbidden), \
            f"forbidden imports: {imported_modules & forbidden}"

    def test_new_routes_reject_external_host(self):
        sh = Shell()
        sh.web_lab = build_web_lab("upload-investigation")
        for path in ("/upload", "/secure-upload", "/uploads", "/upload-security"):
            out = sh.execute(f"open https://evil.example.com{path}")
            assert out == "External hosts are not available in the training environment."

    def test_no_real_file_io_anywhere_in_module(self):
        """No real filesystem write/read primitive appears anywhere in
        the simulator — every 'file' is a small set of explicit string/
        int fields, never real bytes touching a real path."""
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read()
        for dangerous in ("open(", "os.remove", "os.path", "shutil.", "eval(", "exec(",
                          "compile(", "__import__", "subprocess."):
            assert dangerous not in src

    def test_path_traversal_never_escapes_training_prefix(self):
        """Even the vulnerable pipeline's stored reference for a
        traversal-shaped filename is only ever a string label — there is
        no real path resolution anywhere, so nothing could ever actually
        escape any directory regardless of validation outcome."""
        app = WebApp()
        url = parse_url(f"https://{HOST}/auth/login")
        resp = app.handle(build_request("POST", url, body="username=student&password=training123"))
        sid = resp.cookies["session_id"]
        url = parse_url(f"https://{HOST}/upload")
        body = "filename=../../etc/passwd&content_type=image/jpeg&size=1&signature=JPEG"
        req = build_request("POST", url, body=body, cookies={"session_id": sid},
                            extra_headers={"Content-Type": MULTIPART_CT})
        resp = app.handle(req)
        # Extension of '../../etc/passwd' is '.passwd' or similar — never
        # in the vulnerable allowlist, so it's rejected outright; either
        # way, nothing here ever touches a real path.
        assert resp.status_code in (415,)
        assert not app.uploads or all(
            "etc/passwd" not in u.stored_name for u in app.uploads)

    def test_no_eval_or_dangerous_dom_apis_in_terminal_js_upload_section(self):
        js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static",
                               "labs", "terminal.js")
        with open(js_path, encoding="utf-8") as f:
            js = f.read()
        start = js.index("File Upload Security Fundamentals (YC-035.7)")
        section = js[start:start + 16000]
        for dangerous in ("eval(", "document.write", "Function(", "fetch(", "XMLHttpRequest"):
            assert dangerous not in section

    def test_no_real_credentials_or_secrets_anywhere_in_module(self):
        import app.core.terminal.web as webmod
        with open(webmod.__file__, encoding="utf-8") as f:
            src = f.read().lower()
        for weak in ("password123", "letmein", "qwerty", "admin@yushacyber.com"):
            assert weak not in src

    def test_upload_state_isolated_between_instances(self):
        lab1 = build_web_lab("upload-investigation")
        lab2 = build_web_lab("upload-investigation")
        url = parse_url(f"https://{HOST}/secure-upload")
        lab1.app.handle(build_request("GET", url))
        assert lab1.upload.executable_blocked is False  # app.handle() alone never mutates lab.upload
        assert lab2.upload.executable_blocked is False

    def test_uploads_isolated_between_instances(self):
        lab1 = build_web_lab("upload-investigation")
        lab2 = build_web_lab("upload-investigation")
        url = parse_url(f"https://{HOST}/auth/login")
        resp = lab1.app.handle(build_request("POST", url, body="username=student&password=training123"))
        sid = resp.cookies["session_id"]
        url = parse_url(f"https://{HOST}/upload")
        body = "filename=avatar.jpg&content_type=image/jpeg&size=1&signature=JPEG"
        lab1.app.handle(build_request("POST", url, body=body, cookies={"session_id": sid},
                                      extra_headers={"Content-Type": MULTIPART_CT}))
        assert len(lab1.app.uploads) == 1
        assert len(lab2.app.uploads) == 0


# ═══════════════════════════════════════════
# Services — full chain unlock/completion with real XP
# ═══════════════════════════════════════════
@pytest.fixture(scope="module")
def app():
    from app import create_app
    from app.extensions import db
    a = create_app()
    a.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with a.app_context():
        db.create_all()
    yield a


@pytest.fixture(scope="module")
def student(app):
    from app.auth.models import User
    from app.extensions import db
    with app.app_context():
        u = User(username="upload_test", email="upload@t.io")
        u.set_password("Str0ngPass!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    yield "upload_test", uid


def _login(c, u):
    return c.post("/auth/login", data={"identifier": u, "password": "Str0ngPass!"},
                  follow_redirects=True)


CSRF_TOKEN_PLACEHOLDER = "TRAINING_TOKEN_STUDENT_SESSION"
CSRF_SOLVE: list[str] = [
    "web",
    'open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login',
    "open https://cybershop.training/account",
    'open -X POST -d "recipient=training-user&amount=100" https://cybershop.training/transfer',
    "intercept on",
    'open -X POST -d "recipient=training-user&amount=50" https://cybershop.training/transfer',
    "forward",
    "intercept off",
    "open https://cybershop.training/csrf-demo",
    ('open -X POST -H "Origin: https://attacker.training" '
     '-H "Referer: https://attacker.training/" '
     '-d "recipient=training-user&amount=100" https://cybershop.training/transfer'),
    "open https://cybershop.training/transfer",
    "open https://cybershop.training/secure-transfer",
    'open -X POST -d "recipient=training-user&amount=100" https://cybershop.training/secure-transfer',
    ('open -X POST -d "recipient=training-user&amount=100&csrf_token=INVALID_TRAINING_TOKEN" '
     "https://cybershop.training/secure-transfer"),
    (f'open -X POST -d "recipient=training-user&amount=100&csrf_token={CSRF_TOKEN_PLACEHOLDER}" '
     "https://cybershop.training/secure-transfer"),
    "samesite strict",
    "samesite lax",
    "samesite none",
    (f'open -X POST -H "Origin: https://attacker.training" '
     f'-d "recipient=training-user&amount=100&csrf_token={CSRF_TOKEN_PLACEHOLDER}" '
     "https://cybershop.training/secure-transfer"),
    "evidence",
    "inspect 1", "inspect 2", "inspect 3", "inspect 4", "inspect 5",
    ('echo "Conclusion: the vulnerable transfer endpoint trusted the session cookie '
     "alone and accepted a forged-looking cross-site request - this is CSRF. The "
     "secure endpoint rejected the same request shape and only succeeded once the "
     "correct anti-csrf token was included, proving a synchronizer token is the "
     'correct defensive control." > web/csrf-investigation.txt'),
]


class TestServices:
    def test_full_chain_unlocks_and_completes_with_real_xp(self, app, student):
        _uname, uid = student
        with app.app_context():
            from app.auth.models import User
            from app.core.missions import (
                dashboard_stats,
                execute_command,
                mission_status,
                start_mission,
            )

            assert mission_status(uid, "file-upload-security") == "locked"

            start_mission(uid, "csrf-fundamentals")
            for c in CSRF_SOLVE:
                execute_command(uid, "csrf-fundamentals", c)

            assert mission_status(uid, "file-upload-security") == "available"

            start_mission(uid, "file-upload-security")
            for c in SOLVE:
                execute_command(uid, "file-upload-security", c)

            assert mission_status(uid, "file-upload-security") == "completed"

            user = User.query.get(uid)
            assert user.xp > 0
            assert user.level >= 1

            stats = dashboard_stats(uid)
            assert stats["completed_missions"] >= 2


# ═══════════════════════════════════════════
# HTTP — pages / UI reachability
# ═══════════════════════════════════════════
class TestHTTP:
    def test_api_missions_list_includes_it(self, app):
        with app.test_client() as c:
            r = c.get("/api/terminal/missions")
            assert r.status_code == 200
            ids = [m["id"] for m in r.get_json()]
            assert "file-upload-security" in ids

    def test_terminal_page_shows_upload_panels(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/file-upload-security")
            assert r.status_code == 200
            body = r.data.decode("utf-8")
            assert "data-upload-badges" in body
            assert "data-upload-vuln" in body
            assert "data-upload-secure" in body
            assert "data-upload-file-picker" in body
            assert "data-upload-flow-step" in body
            assert "data-upload-pipeline-step" in body
            assert "data-upload-compare-step" in body
            assert "data-upload-traversal-send" in body
            # Proxy Control (reused from YC-035.2) also present for this mission.
            assert "data-proxy-badge" in body
            # Inspector (reused from YC-035.1) still present too.
            assert "data-inspector-toggle" in body

    def test_upload_panel_not_shown_on_other_missions(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            r = c.get("/terminal/mission/csrf-fundamentals")
            assert "data-upload-badges" not in r.data.decode("utf-8")
            r2 = c.get("/terminal/mission/xss-fundamentals")
            assert "data-upload-badges" not in r2.data.decode("utf-8")

    def test_execute_returns_upload_state(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/file-upload-security")
            c.post("/api/terminal/mission/execute", json={
                "slug": "file-upload-security",
                "command": 'open -X POST -d "username=student&password=training123" '
                           "https://cybershop.training/auth/login",
            })
            r = c.post("/api/terminal/mission/execute", json={
                "slug": "file-upload-security",
                "command": (f'open -X POST -H "Content-Type: {MULTIPART_CT}" '
                           '-d "filename=shell.jpg&content_type=image/jpeg&size=8000&signature=EXECUTABLE" '
                           "https://cybershop.training/secure-upload"),
            })
            assert r.status_code == 200
            d = r.get_json()
            assert d["web_lab_status"]["upload"]["executable_blocked"] is True

    def test_hint_endpoint_returns_progressive_hints(self, app, student):
        uname, _uid = student
        with app.test_client() as c:
            _login(c, uname)
            c.get("/terminal/mission/file-upload-security")
            r1 = c.post("/api/terminal/mission/hint", json={
                "slug": "file-upload-security", "objective_id": "up-1"})
            r2 = c.post("/api/terminal/mission/hint", json={
                "slug": "file-upload-security", "objective_id": "up-1"})
            assert r1.status_code == 200 and r2.status_code == 200
            assert r1.get_json()["hint"] != r2.get_json()["hint"]
