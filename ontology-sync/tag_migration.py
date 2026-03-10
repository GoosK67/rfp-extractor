import requests, yaml
BOOKSTACK="https://wiki.cegeka.com/api"; TOKEN_ID="REPLACE"; TOKEN_SECRET="REPLACE"
def bks_headers(): return {"Authorization": f"Token {TOKEN_ID}:{TOKEN_SECRET}","Content-Type":"application/json"}
def update_page_tags(pid,tags):
 r=requests.put(f"{BOOKSTACK}/pages/{pid}",json={"tags":[{"name":t} for t in tags]},headers=bks_headers()); r.raise_for_status()
def run():
 with open("tag_migration_map.yaml") as f: mapping=yaml.safe_load(f)
 pages=requests.get(f"{BOOKSTACK}/pages?count=5000",headers=bks_headers()).json()["data"]
 for p in pages:
  old=[t["name"] for t in p.get("tags",[])]; new=[mapping.get(t,t) for t in old]
  update_page_tags(p["id"],new); print("Updated",p["name"])
if __name__=="__main__": run()