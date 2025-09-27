from flask import Flask, jsonify, render_template
import requests, urllib3, random
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)

def find_lockfile():
    for p in [
        Path(r"C:\Riot Games\League of Legends\lockfile"),
        Path(r"C:\Program Files\Riot Games\League of Legends\lockfile"),
        Path(r"C:\Program Files (x86)\Riot Games\League of Legends\lockfile"),
        Path.cwd() / "lockfile",
    ]:
        if p.exists():
            return p
    raise FileNotFoundError("lockfile not found")

def read_auth():
    parts = find_lockfile().read_text().strip().split(":")
    _, _, port, password, protocol = parts[:5]
    return {"port": int(port), "password": password, "protocol": protocol}

def lcu_get(path, auth):
    base = f"{auth['protocol']}://127.0.0.1:{auth['port']}"
    url = base + path
    r = requests.get(url, auth=("riot", auth["password"]), verify=False, timeout=4)
    r.raise_for_status()
    return r.json()

# -------- 이름 보강 --------
def resolve_name(entry, auth):
    name = (entry.get("summonerName") or "").strip()
    if not name and entry.get("summonerId"):
        try:
            detail = lcu_get(f"/lol-summoner/v1/summoners/{entry['summonerId']}", auth)
            name = (detail.get("displayName") or detail.get("gameName") or detail.get("name") or "").strip()
        except Exception:
            pass
    return name

def extract_teams(lobby, auth):
    t1, t2 = [], []
    for e in lobby.get("gameConfig", {}).get("customTeam100", []):
        n = resolve_name(e, auth)
        if n: t1.append(n)
    for e in lobby.get("gameConfig", {}).get("customTeam200", []):
        n = resolve_name(e, auth)
        if n: t2.append(n)
    return t1, t2

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/fetch")
def fetch_teams():
    auth = read_auth()
    lobby = lcu_get("/lol-lobby/v2/lobby", auth)
    t1, t2 = extract_teams(lobby, auth)
    return jsonify({"team1": t1, "team2": t2})

@app.route("/shuffle")
def shuffle_teams():
    auth = read_auth()
    lobby = lcu_get("/lol-lobby/v2/lobby", auth)
    t1, t2 = extract_teams(lobby, auth)
    names = t1 + t2
    random.shuffle(names)
    mid = (len(names)+1)//2
    return jsonify({"team1": names[:mid], "team2": names[mid:]})

if __name__ == "__main__":
    app.run(port=5000)
