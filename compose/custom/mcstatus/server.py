"""Tiny status API for the custom front doors.

  GET /java?host=192.168.1.5&port=25565     -> {online, players, max, version, latency, sample:[names]}
  GET /bedrock?host=192.168.1.5&port=19132  -> {online, players, max, version, latency}

Runs a real status handshake (mcstatus), so a port that accepts TCP but never
answers (the AtM zombie of 2026-09-02) reads offline here.
"""
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from mcstatus import BedrockServer, JavaServer

TIMEOUT = 4


def java(host, port):
    s = JavaServer(host, port, timeout=TIMEOUT).status()
    names = [p.name for p in (s.players.sample or [])]
    return {"online": True, "players": s.players.online, "max": s.players.max,
            "version": s.version.name, "latency": round(s.latency), "sample": names}


def bedrock(host, port):
    try:
        s = BedrockServer(host, port, timeout=TIMEOUT).status()
        return {"online": True, "players": s.players.online, "max": s.players.max,
                "version": s.version.name, "latency": round(s.latency), "sample": []}
    except Exception:
        return nethernet(host, port)


def nethernet(host, port):
    """Bedrock 1.26.52+ accepts only the NetherNet transport: HTTP signaling on server-port (TCP),
    then WebRTC/UDP gameplay. RakNet pings go unanswered, so check that the signaling endpoint
    speaks HTTP. There's no player count on this path, so players/max read 0/0."""
    t0 = time.monotonic()
    with socket.create_connection((host, port), timeout=TIMEOUT) as c:
        c.settimeout(TIMEOUT)
        c.sendall(f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
        head = c.recv(16)
    if not head.startswith(b"HTTP/"):
        raise ConnectionError("no NetherNet signaling reply")
    return {"online": True, "players": 0, "max": 0, "version": "NetherNet",
            "latency": round((time.monotonic() - t0) * 1000), "sample": []}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        host = q.get("host", ["192.168.1.5"])[0]
        port = int(q.get("port", ["25565"])[0])
        fn = {"/java": java, "/bedrock": bedrock}.get(u.path)
        if not fn:
            self.send_response(404); self.end_headers(); return
        try:
            body = fn(host, port)
        except Exception as e:  # offline, timeout, refused
            body = {"online": False, "players": 0, "max": 0, "version": "", "latency": None,
                    "sample": [], "error": type(e).__name__}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", 8000), H)
    srv.daemon_threads = True
    srv.serve_forever()
