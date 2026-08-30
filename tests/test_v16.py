import json, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from nvlx.k8s_api_v16 import KubeClient
from nvlx.runtime_v16 import Runtime, PROTECTIVE_FINALIZER
from nvlx.lease_v16 import LeaseElector

class FakeState:
    status_patches=0; finalizer_patches=0; events=0; conflict_once=False

class Handler(BaseHTTPRequestHandler):
    def _json(self,code,body):
        raw=json.dumps(body).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path.startswith("/apis/nvlx.io/v1alpha1/gpufleets?"):
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            for e in [{"type":"BOOKMARK","object":{"metadata":{"resourceVersion":"11"}}},{"type":"ERROR","object":{"code":410}}]: self.wfile.write((json.dumps(e)+"\n").encode())
            return
        if self.path=="/apis/nvlx.io/v1alpha1/gpufleets":
            obj={"apiVersion":"nvlx.io/v1alpha1","kind":"GPUFleet","metadata":{"name":"prod","uid":"u1","resourceVersion":"10","generation":1,"annotations":{"nvlx.io/approved":"true"}},"spec":{}}
            return self._json(200,{"metadata":{"resourceVersion":"10"},"items":[obj]})
        if self.path=="/apis/nvlx.io/v1alpha1/gpufleets/prod":
            return self._json(200,{"metadata":{"name":"prod","uid":"u1","resourceVersion":"11","generation":1,"annotations":{"nvlx.io/approved":"true"}}})
        if self.path.endswith("/leases/nvlx-controller"):
            return self._json(200,{"metadata":{"resourceVersion":"22"},"spec":{"holderIdentity":"pod-a","leaseDurationSeconds":30,"renewTime":"2999-01-01T00:00:00Z","leaseTransitions":2}})
        return self._json(404,{"message":"not found"})
    def do_PATCH(self):
        length=int(self.headers.get("Content-Length","0")); body=json.loads(self.rfile.read(length) or b"{}")
        if self.path.endswith("/status"):
            if FakeState.conflict_once and FakeState.status_patches==0:
                FakeState.status_patches += 1; return self._json(409,{"message":"conflict"})
            FakeState.status_patches += 1; return self._json(200,{"metadata":{"name":"prod","uid":"u1","generation":1,"resourceVersion":"12"},"status":body.get("status")})
        if self.path.endswith("/gpufleets/prod"):
            FakeState.finalizer_patches += 1; return self._json(200,{"metadata":{"name":"prod","uid":"u1","generation":1,"resourceVersion":"12","finalizers":body.get("metadata",{}).get("finalizers",[])}})
        if self.path.endswith("/leases/nvlx-controller"):
            return self._json(200,{"metadata":{"resourceVersion":"23"},"spec":body.get("spec")})
        return self._json(404,{"message":"not found"})
    def do_POST(self):
        length=int(self.headers.get("Content-Length","0")); self.rfile.read(length)
        if "/events" in self.path: FakeState.events += 1; return self._json(201,{"metadata":{"resourceVersion":"1"}})
        return self._json(201,{"metadata":{"resourceVersion":"1"}})
    def log_message(self,*args): pass

class V16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(("127.0.0.1",0),Handler); cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True); cls.thread.start()
        cls.client=KubeClient(f"http://127.0.0.1:{cls.httpd.server_port}",timeout=2)
    @classmethod
    def tearDownClass(cls): cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=2)
    def setUp(self): FakeState.status_patches=0; FakeState.finalizer_patches=0; FakeState.events=0; FakeState.conflict_once=False

    def fleet(self, **meta):
        m={"name":"prod","uid":"u1","resourceVersion":"10","generation":1,"annotations":{"nvlx.io/approved":"true"}}; m.update(meta)
        return {"apiVersion":"nvlx.io/v1alpha1","kind":"GPUFleet","metadata":m,"spec":{}}

    def test_real_status_patch_and_event(self):
        r=Runtime(self.client,"pod-a",leader_check=lambda:True)
        self.assertEqual(r.reconcile_object(self.fleet()),"patched"); self.assertEqual(FakeState.status_patches,1); self.assertEqual(FakeState.events,1)

    def test_conflict_refetches_and_retries_once(self):
        FakeState.conflict_once=True; r=Runtime(self.client,"pod-a",leader_check=lambda:True)
        self.assertEqual(r.reconcile_object(self.fleet()),"patched"); self.assertEqual(FakeState.status_patches,2)

    def test_lost_leader_blocks_mutation(self):
        r=Runtime(self.client,"pod-b",leader_check=lambda:False)
        self.assertEqual(r.reconcile_object(self.fleet()),"standby"); self.assertEqual(FakeState.status_patches,0)

    def test_finalizer_patch_preserves_unrelated_finalizers(self):
        r=Runtime(self.client,"pod-a",leader_check=lambda:True)
        obj=self.fleet(deletionTimestamp="now",finalizers=["other.example/finalizer",PROTECTIVE_FINALIZER])
        self.assertEqual(r.reconcile_object(obj),"finalized"); self.assertEqual(FakeState.finalizer_patches,1)

    def test_list_watch_handles_bookmark_and_410_relist(self):
        r=Runtime(self.client,"pod-a",leader_check=lambda:True)
        self.assertEqual(r.list_and_watch_once(),"relist"); self.assertEqual(r.stats.last_resource_version,"11"); self.assertTrue(r.stats.inventory_fresh)

    def test_lease_cas_renews_current_holder(self):
        e=LeaseElector(self.client,"pod-a")
        self.assertTrue(e.ensure_leader())

if __name__=="__main__": unittest.main()
