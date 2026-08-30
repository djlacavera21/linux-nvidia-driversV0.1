import socket, unittest
from unittest import mock
from nvlx.k8s_api_v16 import KubeClient, ApiError
from nvlx.runtime_guard_v161 import classify_watch_line, reconnect_delay
from nvlx.runtime_v16 import Runtime

class FakeClient:
    def __init__(self): self.patches=0; self.gets=0
    def patch_status(self,name,rv,status):
        self.patches += 1
        if self.patches == 1: raise ApiError(409,"conflict")
        return None
    def get_fleet(self,name):
        self.gets += 1
        return type("R",(),{"body":{"metadata":{"resourceVersion":"11"}}})()
    def create_event(self,*args,**kwargs): pass

class V161Tests(unittest.TestCase):
    def test_watch_transient_error_reconnects(self):
        self.assertEqual(classify_watch_line({"type":"ERROR","object":{"code":503}}).action,"reconnect")
    def test_watch_410_relists(self):
        self.assertEqual(classify_watch_line({"type":"ERROR","object":{"code":410}}).action,"relist")
    def test_malformed_watch_event_is_ignored(self):
        self.assertEqual(classify_watch_line({}).action,"ignore-malformed")
        self.assertEqual(classify_watch_line("bad").action,"ignore-malformed")
    def test_unknown_watch_event_is_ignored(self):
        self.assertEqual(classify_watch_line({"type":"FUTURE","object":{}}).action,"ignore-unknown")
    def test_reconnect_delay_is_bounded(self):
        self.assertEqual(reconnect_delay(0,maximum=8),1)
        self.assertEqual(reconnect_delay(10,maximum=8),8)
    def test_reconnect_delay_rejects_bool_attempt(self):
        with self.assertRaises(ValueError): reconnect_delay(True)
    def test_api_timeout_is_sanitized(self):
        c=KubeClient("http://127.0.0.1:1",token="super-secret",timeout=1)
        with mock.patch("urllib.request.urlopen",side_effect=socket.timeout()):
            with self.assertRaises(ApiError) as ctx: c.list_fleets()
        self.assertEqual(ctx.exception.status,0)
        self.assertNotIn("super-secret",str(ctx.exception))
    def test_leader_loss_after_conflict_blocks_retry_write(self):
        client=FakeClient(); calls=iter([True,False])
        r=Runtime(client,"pod-a",leader_check=lambda:next(calls,False))
        obj={"metadata":{"name":"prod","uid":"u1","resourceVersion":"10","generation":1,"annotations":{"nvlx.io/approved":"true"}}}
        self.assertEqual(r.reconcile_object(obj),"fenced")
        self.assertEqual(client.patches,1)
        self.assertEqual(client.gets,0)
    def test_stop_revokes_leader_immediately(self):
        r=Runtime(FakeClient(),"pod-a",leader_check=lambda:True)
        r.stop()
        self.assertFalse(r._leader())
        self.assertTrue(r.stats.terminating)

if __name__=="__main__": unittest.main()
