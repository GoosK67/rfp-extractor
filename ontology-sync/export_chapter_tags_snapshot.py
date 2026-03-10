import csv, requests, os, datetime

BOOKSTACK = os.getenv("BOOKSTACK_BASE_URL", "https://wiki.cegeka.com/api").rstrip("/")
TOKEN_ID = os.getenv("BOOKSTACK_TOKEN_ID", "REPLACE")
TOKEN_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET", "REPLACE")

def hdr():
    return {"Authorization": f"Token {TOKEN_ID}:{TOKEN_SECRET}"}

def fetch(endpoint):
    url = f"{BOOKSTACK}{endpoint}"
    r = requests.get(url, headers=hdr(), timeout=60)
    try:
        r.raise_for_status()
    except Exception:
        print(f"[ERR] GET {url} -> {r.status_code}")
        print(r.text)
        raise
    return r.json()

def main():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"chapter_tags_snapshot_{ts}.csv"

    print("[INFO] Fetching all chapters …")
    chapters = fetch("/chapters?count=5000").get("data", [])
    print(f"[INFO] Chapters returned: {len(chapters)}")

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chapter_id", "chapter_name", "book_id", "book_name", "tag_name", "tag_value"])

        for ch in chapters:
            cid = ch["id"]
            cname = ch["name"]
            book_id = ch["book_id"]

            # fetch book name
            book = fetch(f"/books/{book_id}")
            book_name = book.get("name", "")

            tags = ch.get("tags", [])
            if not tags:
                w.writerow([cid, cname, book_id, book_name, "", ""])
                print(f"[CH] {cid} '{cname}' -> 0 tags")
            else:
                for t in tags:
                    w.writerow([cid, cname, book_id, book_name, t["name"], t.get("value", "")])
                print(f"[CH] {cid} '{cname}' -> {len(tags)} tags: {[t['name'] for t in tags]}")

    print(f"[OK] Snapshot written: {out}")

if __name__ == "__main__":
    main()