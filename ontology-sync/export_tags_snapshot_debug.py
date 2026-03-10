import csv, requests, os, datetime

BOOKSTACK = os.getenv("BOOKSTACK_BASE_URL", "https://wiki.cegeka.com/api").rstrip("/")
TOKEN_ID = os.getenv("BOOKSTACK_TOKEN_ID", "REPLACE")
TOKEN_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET", "REPLACE")

def hdr():
    return {"Authorization": f"Token {TOKEN_ID}:{TOKEN_SECRET}"}

def main():
    # haal tot 5000 pagina's op (pas aan indien nodig)
    url = f"{BOOKSTACK}/pages?count=5000"
    r = requests.get(url, headers=hdr(), timeout=60)
    try:
        r.raise_for_status()
    except Exception as e:
        print(f"[ERR] GET {url} -> {r.status_code} {r.text}")
        raise

    payload = r.json()
    pages = payload.get("data", [])
    total = payload.get("total", len(pages))
    print(f"[INFO] pages returned: {len(pages)} / total: {total}")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"tags_snapshot_debug_{ts}.csv"

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        # schrijf altijd een rij per pagina, zelfs als er 0 tags zijn
        w.writerow(["page_id","page_name","tag_count","tag"])
        for p in pages:
            page_id = p.get("id")
            page_name = p.get("name")
            tags = [t["name"] for t in p.get("tags", [])]
            tag_count = len(tags)
            if tag_count == 0:
                # schrijf lege tag-record voor zichtbaarheid
                w.writerow([page_id, page_name, 0, ""])
                print(f"[PAGE] {page_id} '{page_name}' -> 0 tags")
            else:
                for t in tags:
                    w.writerow([page_id, page_name, tag_count, t])
                print(f"[PAGE] {page_id} '{page_name}' -> {tag_count} tags: {tags}")

    print(f"[OK] Snapshot written: {out}")

if __name__ == "__main__":
    main()