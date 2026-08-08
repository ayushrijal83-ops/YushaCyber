from app.core.missions.mission_runner import MissionRunner

r = MissionRunner("http-deep-dive", user_id=7)
r.execute('open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login')
r.execute('open -H "Authorization: Bearer training-token-001" https://cybershop.training/api/me')
state = r.save_state()

r2 = MissionRunner.from_state(state)
print("resumed completed:", sorted(r2.progress.completed_ids))
print("resumed xp:", r2.progress.xp_earned)
print("resumed cookies:", r2.shell.web_lab.session.cookies)
print("resumed investigation log entry 4 content-type:",
      r2.shell.web_lab.investigation_log[3][1].headers.get("Content-Type"))
status = r2.web_lab_status()
print("history preserved len:", len(status["history"]))

# ai_context stays lean
ctx = r2.ai_context()
print("ai_context web section:", ctx.get("web"))
