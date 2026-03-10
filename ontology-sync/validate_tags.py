import requests, re, yaml, sys
BOOKSTACK_URL = "https://wiki.cegeka.com/api"
TOKEN_ID = "sCFoRe5YsD8VxJa8WT90i2fWGSZxV4Ml"
TOKEN_SECRET = "d6H2eumWx1561V9ju33EeXMH6nAS9TwT"
def bks_headers(): return {"Authorization": f"Token {TOKEN_ID}:{TOKEN_SECRET}"}
def get_pages():
 r=requests.get(f"{BOOKSTACK_URL}/pages?count=5000",headers=bks_headers()); r.raise_for_status(); return r.json()["data"]
def load_rules():
 with open("ontology_tags.yaml") as f: return yaml.safe_load(f)
def validate():
 rules=load_rules()["tag_patterns"]; pages=get_pages(); errors=[]
 for p in pages:
  title=p["name"]; tags=[t["name"] for t in p.get("tags",[])]
  for tag in tags:
   if not any(re.match(pattern,tag) for pattern in rules.values()): errors.append((title,tag))
 if errors:
  print("INVALID TAGS:"); [print(f" - {t}: {g}") for t,g in errors]; sys.exit(1)
 print("All tags valid.")
if __name__=="__main__": validate()