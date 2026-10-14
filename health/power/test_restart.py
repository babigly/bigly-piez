# Tests for the Bigly Piez helper's health numbers. Run: python3 -m unittest test_restart.py (from this folder).
import json, os, subprocess, sys, tempfile, threading, unittest, urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
json.dump({"allowed_users": [], "pis": {"bigpi2": {"self": True}, "room4": {"disabled": True}}}, CONF)
CONF.close()
os.environ["PIEZ_CONF"] = CONF.name
sys.path.insert(0, HERE)
import restart  # noqa: E402

PI5 = "temp=61200\ncpu1=100 0 50 800 50 0 0 0\ncpu2=160 0 70 880 50 0 0 0\nmem=8000000 6000000\ndisk=100 9 81\nup=93784.51\n"


class ParseHealth(unittest.TestCase):
    def test_pi5_sample(self):
        self.assertEqual(restart.parse_health(PI5),
                         {"temp_c": 61, "cpu_pct": 50, "mem_pct": 25, "disk_pct": 10, "up_s": 93784})

    def test_missing_temperature_is_none(self):
        self.assertIsNone(restart.parse_health(PI5.replace("temp=61200", "temp="))["temp_c"])

    def test_garbage_never_guesses(self):
        out = restart.parse_health("temp=hot\ncpu1=1 2\ncpu2=x\nmem=0 5\ndisk=1 2\nup=soon\nrm -rf /\n")
        self.assertEqual(out, {"temp_c": None, "cpu_pct": None, "mem_pct": None, "disk_pct": None, "up_s": None})

    def test_impossible_temperature_is_none(self):
        self.assertIsNone(restart.parse_health(PI5.replace("61200", "999999"))["temp_c"])

    def test_disk_rounds_up_like_df(self):
        self.assertEqual(restart.parse_health("disk=1000 101 899")["disk_pct"], 11)


class RemoteScript(unittest.TestCase):
    def run_remote(self, cmd):
        env = {**os.environ, "SSH_ORIGINAL_COMMAND": cmd}
        return subprocess.run(["/bin/sh", os.path.join(HERE, "piez-remote")], capture_output=True, text=True, env=env)

    def test_health_output_parses_on_this_machine(self):
        r = self.run_remote("health")
        self.assertEqual(r.returncode, 0)
        out = restart.parse_health(r.stdout)
        for k in ("cpu_pct", "mem_pct", "disk_pct", "up_s"):
            self.assertIsNotNone(out[k], k)

    def test_other_commands_still_refused(self):
        for cmd in ("id", "health; id", "health && reboot", "cat /etc/shadow"):
            r = self.run_remote(cmd)
            self.assertEqual(r.returncode, 1, cmd)
            self.assertIn("not allowed", r.stderr)


class HealthEndpoint(unittest.TestCase):
    def test_health_route_reads_self_and_skips_disabled(self):
        restart.hcache["at"] = 0
        srv = ThreadingHTTPServer(("127.0.0.1", 0), restart.H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            for path in ("/health", "/api/health"):
                d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}{path}"))
                self.assertTrue(d["ok"])
                self.assertEqual(set(d["pis"]), {"bigpi2"})
                self.assertTrue(d["pis"]["bigpi2"]["ok"])
                self.assertIsNotNone(d["pis"]["bigpi2"]["disk_pct"])
        finally:
            srv.shutdown()
            srv.server_close()

    def test_old_key_reports_setup(self):
        r = subprocess.CompletedProcess([], 1, "", "Bigly Piez key: not allowed\n")
        orig, restart.subprocess.run = restart.subprocess.run, lambda *a, **k: r
        restart.CONF["pis"]["anchor"] = {"ssh": "x@y"}
        try:
            self.assertEqual(restart.read_health("anchor"), {"ok": False, "why": "setup"})
        finally:
            restart.subprocess.run = orig
            del restart.CONF["pis"]["anchor"]


if __name__ == "__main__":
    unittest.main()
