import unittest
from nvlx.fleet_crd import FleetSpec, crd_manifest, resource, FINALIZER
from nvlx.status_conditions import summarize
from nvlx.finalizer import decide as finalizer_decide
from nvlx.k8s_events import event
from nvlx.admission_v14 import render as admission_render
from nvlx.reconcile_v14 import reconcile

class V14Tests(unittest.TestCase):
    def test_crd_and_resource(self):
        self.assertEqual(crd_manifest()["metadata"]["name"],"gpufleets.nvlx.io")
        r=resource("prod",FleetSpec("610.57.04","26.7.0")); self.assertIn(FINALIZER,r["metadata"]["finalizers"])
    def test_conditions(self):
        c=summarize(ready=True,progressing=False,degraded=False,generation=3); self.assertEqual(c[0]["status"],"True")
    def test_finalizer_holds_on_rollback(self):
        r=finalizer_decide(deleting=True,rollback_pending=True,quarantined_nodes=0,active_execution=False); self.assertFalse(r.remove_finalizer)
    def test_event(self): self.assertEqual(event("prod",reason="Ready",note="ok")["apiVersion"],"events.k8s.io/v1")
    def test_admission(self):
        text=admission_render(); self.assertIn("ValidatingAdmissionPolicyBinding",text); self.assertIn("approved-change",text)
    def test_reconcile_blocked(self):
        r=reconcile("prod",generation=2,allowed=False,runtime_action="hold",runtime_reasons=("circuit open",)); self.assertEqual(r.phase,"Blocked"); self.assertTrue(r.requeue)
    def test_reconcile_progress(self):
        r=reconcile("prod",generation=2,allowed=True,runtime_action="execute",runtime_reasons=(),current_wave=1,promoted=True); self.assertEqual(r.canary_wave,2)

if __name__=="__main__": unittest.main()
