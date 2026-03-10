# save as: export_tags_snapshot.py
import csv, requests, os, datetime

BOOKSTACK = "https://wiki.cegeka.com/api"
TOKEN_ID = os.getenv("BOOKSTACK_TOKEN_ID", "REPLACE")
TOKEN_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET", "REPLACE")

def hdr(): return {"Authorization": f"Token {TOKEN_ID}:{TOKEN_SECRET}"}

r = requests.get(f"{BOOKSTACK}/pages?count=5000", headers=hdr()); r.raise_for_status()
pages = r.json()["data"]

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
with open(f"tags_snapshot_{ts}.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["page_id","page_name","tag"])
    for p in pages:
        for t in p.get("tags", []):
            w.writerow([p["id"], p["name"], t["name"]])

print("Snapshot written:", f.name)