"""HTTP liveness, readiness and metrics endpoints for nvlx 1.6."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from .controller_metrics import render as render_metrics

class HealthServer:
    def __init__(self, runtime, host: str="0.0.0.0", port: int=8080):
        self.runtime=runtime
        outer=self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                s=outer.runtime.stats
                if self.path=="/livez":
                    self.send_response(200); self.end_headers(); self.wfile.write(b"ok\n"); return
                if self.path=="/readyz":
                    ready_fn=getattr(outer.runtime,"ready",None)
                    try:
                        ready=bool(ready_fn()) if callable(ready_fn) else bool(s.api_reachable and s.leader and s.inventory_fresh and not s.terminating)
                    except Exception:
                        ready=False
                    self.send_response(200 if ready else 503); self.end_headers(); self.wfile.write(("ready\n" if ready else "not ready\n").encode()); return
                if self.path=="/metrics":
                    body=render_metrics(leader=s.leader,reconcile_total=s.reconcile_total,reconcile_failures=s.reconcile_failures,pending_approvals=0,rollback_required=0)
                    self.send_response(200); self.send_header("Content-Type","text/plain; version=0.0.4"); self.end_headers(); self.wfile.write(body.encode()); return
                self.send_response(404); self.end_headers()
            def log_message(self, *args): pass
        self.httpd=ThreadingHTTPServer((host,port),Handler)
        self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True)
    def start(self): self.thread.start(); return self
    def close(self): self.httpd.shutdown(); self.httpd.server_close(); self.thread.join(timeout=2)
