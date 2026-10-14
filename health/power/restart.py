#!/usr/bin/env python3
# Bigly Piez restart helper: live "is it answering?" checks, read-only health numbers, and a Restart button.
# Listens on 127.0.0.1 only; `tailscale serve` puts it at /api next to the page. Stdlib only.
import json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = json.load(open(os.environ.get("PIEZ_CONF", os.path.join(HERE, "restart.json"))))
DRY = os.environ.get("PIEZ_DRYRUN") == "1"
TEST_USER = os.environ.get("PIEZ_TEST_USER", "")
FAKE = json.loads(os.environ.get("PIEZ_FAKE_STATUS") or "null")
FAKE_HEALTH = json.loads(os.environ.get("PIEZ_FAKE_HEALTH") or "null")
LOG = os.path.join(HERE, "restarts.log")
REBOOT = "sudo -n /usr/bin/systemctl reboot"
COOLDOWN = 120
HEALTH_EVERY = 120
last, cache, lock = {}, {"at": 0, "data": {}}, threading.Lock()
hcache, hlock = {"at": 0, "data": {}, "checked": ""}, threading.Lock()


def ssh_args(t):
    key = CONF.get("ssh_key")
    a = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6"] + (["-i", key, "-o", "IdentitiesOnly=yes"] if key else [])
    if t.get("jump"):
        # ProxyCommand, not -J, so the jump hop uses the same restricted key.
        a += ["-o", f"ProxyCommand=ssh -o BatchMode=yes {'-i ' + key + ' -o IdentitiesOnly=yes ' if key else ''}-W %h:%p {t['jump']}"]
    return a + [t["ssh"]]


def usable(pid):
    t = CONF["pis"][pid]
    return bool(t.get("ssh") or t.get("self")) and not t.get("disabled")


def probe(t):
    try:
        r = subprocess.run(ssh_args(t) + ["true"], capture_output=True, text=True, timeout=15)
        return r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        return 255, "timed out"


def answering(pid):
    if FAKE is not None:
        return bool(FAKE.get(pid))
    t = CONF["pis"][pid]
    if t.get("self"):
        return True
    rc, err = probe(t)
    # A refused key still means the Pi is up; it just hasn't had its one-time setup.
    return rc == 0 or "Permission denied" in err


def status():
    with lock:
        if time.time() - cache["at"] < 15:
            return cache["data"]
    ids = [p for p in CONF["pis"] if usable(p)]
    with ThreadPoolExecutor(8) as ex:
        data = dict(zip(ids, ex.map(answering, ids)))
    with lock:
        cache.update(at=time.time(), data=data)
    return data


def parse_health(text):
    # Turns piez-remote's raw "health" lines into a few rounded numbers; anything odd becomes None, never a guess.
    raw = dict(l.split("=", 1) for l in text.splitlines() if "=" in l)
    nums = lambda k: [int(x) for x in raw.get(k, "").split()] if raw.get(k, "").replace(" ", "").isdigit() else []
    out = {"temp_c": None, "cpu_pct": None, "mem_pct": None, "disk_pct": None, "up_s": None}
    if raw.get("temp", "").lstrip("-").isdigit() and -40000 < int(raw["temp"]) < 150000:
        out["temp_c"] = round(int(raw["temp"]) / 1000)
    a, b = nums("cpu1"), nums("cpu2")
    if len(a) == len(b) == 8 and sum(b) > sum(a):
        busy = (sum(b) - sum(a)) - ((b[3] + b[4]) - (a[3] + a[4]))
        out["cpu_pct"] = max(0, min(100, round(100 * busy / (sum(b) - sum(a)))))
    m = nums("mem")
    if len(m) == 2 and 0 < m[0] and 0 <= m[1] <= m[0]:
        out["mem_pct"] = round(100 * (m[0] - m[1]) / m[0])
    d = nums("disk")
    if len(d) == 3 and d[1] + d[2] > 0:
        out["disk_pct"] = min(100, -(-100 * d[1] // (d[1] + d[2])))  # rounds up, like df's Use%
    try:
        out["up_s"] = int(float(raw["up"])) if float(raw.get("up", "-1")) >= 0 else None
    except ValueError:
        pass
    return out


def read_health(pid):
    t = CONF["pis"][pid]
    if FAKE_HEALTH is not None:
        return FAKE_HEALTH.get(pid) or {"ok": False, "why": "offline"}
    if t.get("self"):
        # This Pi reads itself with the same script the other Pis use.
        cmd, env = ["/bin/sh", os.path.join(HERE, "piez-remote")], {**os.environ, "SSH_ORIGINAL_COMMAND": "health"}
    else:
        cmd, env = ssh_args(t) + ["health"], None
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20, env=env)
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "offline"}
    if r.returncode != 0:
        # An old piez-remote says "not allowed": the Pi is fine, it just needs the health update.
        return {"ok": False, "why": "setup" if "not allowed" in r.stderr or "Permission denied" in r.stderr else "offline"}
    return {"ok": True, **parse_health(r.stdout[:4000])}


def health():
    # One refresh at a time; numbers are reused for HEALTH_EVERY seconds so the Pis aren't asked too often.
    with hlock:
        if time.time() - hcache["at"] >= HEALTH_EVERY:
            ids = [p for p in CONF["pis"] if usable(p)]
            with ThreadPoolExecutor(8) as ex:
                hcache.update(data=dict(zip(ids, ex.map(read_health, ids))), at=time.time(),
                              checked=time.strftime("%H:%M"))
        return hcache["checked"], hcache["data"]


def restart(pid, user):
    ok, msg = do_restart(CONF["pis"][pid])
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {user} restart {pid}: {msg}\n")
    return ok, msg


def do_restart(t):
    # The page's own Pi waits a minute so this reply, and the other Pis' restarts, get out first.
    cmd = ["sudo", "-n", "/usr/sbin/shutdown", "-r", "+1"] if t.get("self") else ssh_args(t) + [REBOOT]
    if DRY:
        return True, "Dry run: nothing was restarted."
    if not t.get("self"):
        # Check in first, so a Pi that is off or not set up gets a clear answer instead of a false "Restarting."
        rc, err = probe(t)
        if rc != 0:
            if "Permission denied" in err or "not allowed" in err:
                return False, "The Pi said no. Its one-time setup may be missing."
            return False, "It isn't answering, so Restart can't reach it. Unplug it and plug it back in."
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    except subprocess.TimeoutExpired:
        return True, "Sent. The connection dropped as it went down."
    # 255 means SSH lost the link because the Pi went down, which is success here.
    if r.returncode in (0, 255) and "password" not in r.stderr and "not allowed" not in r.stderr:
        return True, "Restarting."
    return False, "The Pi said no. Its one-time setup may be missing."


class H(BaseHTTPRequestHandler):
    def reply(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def user(self):
        u = self.headers.get("Tailscale-User-Login", "") or TEST_USER
        return u if u and u in CONF.get("allowed_users", []) else None

    def log_message(self, *a):
        pass

    def route(self):
        # tailscale serve may or may not strip the /api mount, so accept both.
        p = self.path.split("?")[0]
        return p[4:] if p.startswith("/api/") else p

    def do_GET(self):
        if self.route() == "/status":
            up = status()
            pis = {p: {"can": usable(p), "self": bool(t.get("self")), "online": up.get(p)} for p, t in CONF["pis"].items()}
            return self.reply(200, {"ok": True, "checked": time.strftime("%H:%M"), "pis": pis,
                                    "allowed": self.user() is not None, "dry": DRY})
        if self.route() == "/health":
            checked, data = health()
            return self.reply(200, {"ok": True, "checked": checked, "every": HEALTH_EVERY, "pis": data})
        if STATIC and self.path in ("/", "/index.html"):
            b = open(STATIC, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            return self.wfile.write(b)
        self.reply(404, {"ok": False, "error": "Not found"})

    def do_POST(self):
        if self.route() != "/restart":
            return self.reply(404, {"ok": False, "error": "Not found"})
        # JSON only, and no CORS headers ever, so other sites can't press the button for you.
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.reply(415, {"ok": False, "error": "JSON only"})
        user = self.user()
        if not user:
            return self.reply(403, {"ok": False, "error": "Your login isn't on the allowed list."})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 2000)))
            target, confirm = str(body["pi"]), str(body["confirm"])
        except Exception:
            return self.reply(400, {"ok": False, "error": "Bad request"})
        if confirm != target:
            return self.reply(400, {"ok": False, "error": "Not confirmed"})
        if target == "all":
            ids = sorted((p for p in CONF["pis"] if usable(p)),
                         key=lambda p: (bool(CONF["pis"][p].get("self")), CONF["pis"][p].get("order", 5)))
        elif target in CONF["pis"] and usable(target):
            ids = [target]
        else:
            return self.reply(400, {"ok": False, "error": "That Pi can't be restarted from here."})
        now, results = time.time(), {}
        for p in ids:
            if now - last.get(p, 0) < COOLDOWN:
                results[p] = {"ok": False, "msg": "Restarted moments ago. Give it two minutes."}
                continue
            last[p] = now
            ok, msg = restart(p, user)
            results[p] = {"ok": ok, "msg": msg}
        with lock:
            cache["at"] = 0
        self.reply(200, {"ok": all(r["ok"] for r in results.values()), "results": results})


STATIC = sys.argv[sys.argv.index("--static") + 1] if "--static" in sys.argv else None
if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PIEZ_PORT", "8452"))), H).serve_forever()
