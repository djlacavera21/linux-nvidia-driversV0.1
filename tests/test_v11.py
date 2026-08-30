import unittest
from datetime import datetime,timezone,timedelta
from nvlx.audit_chain import append,verify
from nvlx.approvals import ExecutionPlan,approve
from nvlx.approval_lifecycle import evaluate
from nvlx.state_migration import migrate
from nvlx.runtime import tick
from nvlx.execution_record import start,finish
from nvlx.k8s_controller import manifests

class V11Tests(unittest.TestCase):
    def test_audit_chain_detects_tamper(self):
        a=append(None,{"action":"plan"}); b=append(a,{"action":"execute"})
        self.assertTrue(verify([a,b])[0])
        bad=type(b)(b.sequence,b.previous_hash,{"action":"tampered"},b.record_hash)
        self.assertFalse(verify([a,bad])[0])
    def test_approval_expiry(self):
        p=ExecutionPlan("upgrade","gpu01",("step",),"cfg","fp")
        a=approve(p,"ci")
        future=datetime.now(timezone.utc)+timedelta(hours=2)
        self.assertFalse(evaluate(p,a,ttl_seconds=3600,now=future).allowed)
    def test_state_migration(self):
        r=migrate({"generation":1})
        self.assertEqual(r.to_version,2); self.assertTrue(r.migrated)
    def test_runtime_standby(self):
        self.assertEqual(tick(observed_generation=1,desired_generation=2,leader=False).action,"standby")
    def test_failed_execution_requires_rollback(self):
        self.assertTrue(finish(start("abc"),success=False).rollback_required)
    def test_ha_manifests_require_two_replicas(self):
        resources=manifests(replicas=2)
        kinds={x["kind"] for x in resources}
        self.assertTrue({"ServiceAccount","ClusterRole","ClusterRoleBinding","Deployment"}.issubset(kinds))
        deployment=next(x for x in resources if x["kind"]=="Deployment")
        self.assertEqual(deployment["spec"]["replicas"],2)
        with self.assertRaises(ValueError): manifests(replicas=1)

if __name__ == "__main__": unittest.main()
