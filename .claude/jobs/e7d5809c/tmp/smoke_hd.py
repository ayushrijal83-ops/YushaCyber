import sys
from app.core.missions.mission_runner import MissionRunner

runner = MissionRunner("http-deep-dive", user_id=1)

cmds = [
    "open https://cybershop.training/products",                                  # hd-1, hd-2
    "headers",                                                                    # hd-3, hd-4
    'open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login',  # hd-5, hd-9 (login)
    "open -X POST -H \"Content-Type: application/json\" -d '{\"bio\": \"training\"}' https://cybershop.training/api/profile",  # hd-6
    "open https://cybershop.training/search?q=web%20security",                    # hd-7
    "open https://cybershop.training/login",                                      # hd-8
    'open -H "Authorization: Bearer training-token-001" https://cybershop.training/api/me',  # hd-10
    'open -H "Referer: https://cybershop.training/" https://cybershop.training/products',    # hd-11
    "open https://cybershop.training/products?id=42",                            # hd-12
]

for c in cmds:
    res = runner.execute(c)
    if res["validations"]:
        for v in res["validations"]:
            print("PASS:", v["objective_id"], v["xp"])

print("completed so far:", runner.progress.completed_ids)
print("missing:", [o["id"] for o in runner.mission["objectives"] if o["id"] not in runner.progress.completed_ids])

# Now the chain reconstruction (hd-13) — note some of the above already
# touched /login and /auth/login, so replay the exact chain fresh-ish:
res = runner.execute("open https://cybershop.training/login")
res = runner.execute("open https://cybershop.training/auth/login")
res = runner.execute('open -X POST -d "username=student&password=training123" https://cybershop.training/auth/login')
for v in res["validations"]:
    print("PASS:", v["objective_id"], v["xp"])
print("history via command:\n", runner.shell.execute("requests"))

# hd-14 final investigation
print(runner.shell.execute("evidence"))
print(runner.shell.execute("inspect 4"))
res = runner.execute('echo "Conclusion: the profile response Content-Type is application/json instead of text/html" > web/http-investigation.txt')
for v in res["validations"]:
    print("PASS:", v["objective_id"], v["xp"])

print("\nFINAL completed:", sorted(runner.progress.completed_ids))
print("FINAL xp:", runner.progress.xp_earned, "/", runner.mission["xp_total"])
print("FINAL missing:", [o["id"] for o in runner.mission["objectives"] if o["id"] not in runner.progress.completed_ids])
print("mission complete flag:", runner.progress.completed)

# External host rejection
print("external:", runner.shell.execute("open https://evil.example.com/"))

# web_lab_status shape sanity
status = runner.web_lab_status()
print("status keys:", sorted(status.keys()))
print("history len:", len(status["history"]))
