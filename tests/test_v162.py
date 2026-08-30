import tempfile, unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from nvlx.k8s_api_v16 import ApiError, ApiResponse, KubeClient
from nvlx.lease_v16 import LeaseElector
from nvlx.operator_cli_v16 import _read_token_file
from nvlx.runtime_v16 import Runtime, PROTECTIVE_FINALIZER

class StatusConflictClient:
    def __init__(self, fresh):
        self.fresh=fresh
        self.patches=[]
        self.gets=0
    def patch_status(self,name,rv,status):
        self.patches.append((name,rv,status))
        if len(self.patches)==1: raise ApiError(409,"conflict")
        meta=self.fresh["metadata"]
        return ApiResponse(200,{"metadata":{"name":name,"uid":meta["uid"],"generation":meta.get("generation",0),"resourceVersion":"after"},"status":status})
    def get_fleet(self,name):
        self.gets += 1
        return ApiResponse(200,self.fresh)
    def create_event(self,namespace,event):
        return ApiResponse(201,{"metadata":{"resourceVersion":"e1"},"regarding":event["regarding"],"reportingController":event["reportingController"],"reportingInstance":event["reportingInstance"]})

class FinalizerConflictClient:
    def __init__(self, fresh):
        self.fresh=fresh
        self.patches=[]
        self.gets=0
    def patch_finalizers(self,name,rv,finalizers):
        self.patches.append((name,rv,list(finalizers)))
        if len(self.patches)==1: raise ApiError(412,"precondition")
        meta=self.fresh["metadata"]
        return ApiResponse(200,{"metadata":{"name":name,"uid":meta["uid"],"resourceVersion":"after","finalizers":list(finalizers)}})
    def get_fleet(self,name):
        self.gets += 1
        return ApiResponse(200,self.fresh)

class LeaseClient:
    def __init__(self, get_result=None, get_error=None, patch_error=None):
        self.get_result=get_result
        self.get_error=get_error
        self.patch_error=patch_error
        self.calls=[]
    def request_json(self,method,path,body=None,content_type="application/json"):
        self.calls.append((method,path,body,content_type))
        if method=="GET":
            if self.get_error: raise self.get_error
            return ApiResponse(200,self.get_result)
        if method=="POST":
            spec=body["spec"]
            return ApiResponse(201,{"metadata":{"resourceVersion":"1"},"spec":spec})
        if method=="PATCH":
            if self.patch_error: raise self.patch_error
            return ApiResponse(200,{"metadata":{"resourceVersion":"2"},"spec":body["spec"]})
        raise AssertionError(method)

class V162Tests(unittest.TestCase):
    def fleet(self, *, generation=4, approved=True, deletion=False, finalizers=None, extra_annotations=None):
        annotations={}
        if approved: annotations["nvlx.io/approved"]="true"
        if extra_annotations: annotations.update(extra_annotations)
        meta={"name":"prod","uid":"u1","resourceVersion":"10","generation":generation,"annotations":annotations}
        if deletion: meta["deletionTimestamp"]="now"
        if finalizers is not None: meta["finalizers"]=list(finalizers)
        return {"metadata":meta,"status":{}}

    def test_status_conflict_recomputes_new_generation(self):
        fresh=self.fleet(generation=5)
        fresh["metadata"]["resourceVersion"]="11"
        client=StatusConflictClient(fresh)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(self.fleet(generation=4)),"patched")
        self.assertEqual(len(client.patches),2)
        self.assertEqual(client.patches[1][2]["observed_generation"],5)
        self.assertEqual(runtime.stats.status_conflict_recomputes,1)

    def test_status_conflict_approval_transition_fences_retry(self):
        fresh=self.fleet(generation=4,approved=False)
        fresh["metadata"]["resourceVersion"]="11"
        client=StatusConflictClient(fresh)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(self.fleet()),"fenced")
        self.assertEqual(len(client.patches),1)
        self.assertEqual(runtime.stats.status_conflict_fenced,1)

    def test_status_conflict_deletion_fences_retry(self):
        fresh=self.fleet(deletion=True,finalizers=[PROTECTIVE_FINALIZER])
        fresh["metadata"]["resourceVersion"]="11"
        client=StatusConflictClient(fresh)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(self.fleet()),"fenced")
        self.assertEqual(len(client.patches),1)

    def test_finalizer_conflict_recomputes_and_preserves_fresh_finalizers(self):
        original=self.fleet(deletion=True,finalizers=["old.example/f",PROTECTIVE_FINALIZER])
        fresh=self.fleet(deletion=True,finalizers=["old.example/f","new.example/f",PROTECTIVE_FINALIZER])
        fresh["metadata"]["resourceVersion"]="11"
        client=FinalizerConflictClient(fresh)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(original),"finalized")
        self.assertEqual(client.patches[1][2],["old.example/f","new.example/f"])
        self.assertEqual(runtime.stats.finalizer_conflict_recomputes,1)

    def test_finalizer_conflict_rechecks_safety(self):
        original=self.fleet(deletion=True,finalizers=[PROTECTIVE_FINALIZER])
        fresh=self.fleet(deletion=True,finalizers=[PROTECTIVE_FINALIZER],extra_annotations={"nvlx.io/rollback-pending":"true"})
        fresh["metadata"]["resourceVersion"]="11"
        client=FinalizerConflictClient(fresh)
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(original),"finalizer-hold")
        self.assertEqual(len(client.patches),1)
        self.assertEqual(runtime.stats.finalizer_conflict_fenced,1)

    def test_watch_path_has_server_timeout_and_distinct_socket_timeout(self):
        client=KubeClient("http://127.0.0.1:1",timeout=2,watch_timeout=41,watch_timeout_seconds=30)
        query=parse_qs(urlsplit(client.watch_path("opaque-rv")).query)
        self.assertEqual(query["timeoutSeconds"],["30"])
        self.assertEqual(client.watch_timeout,41.0)
        self.assertEqual(client.timeout,2.0)

    def test_watch_timeout_must_exceed_server_timeout(self):
        with self.assertRaises(ValueError):
            KubeClient("http://127.0.0.1:1",watch_timeout=30,watch_timeout_seconds=30)

    def test_token_file_reader_strips_and_rejects_empty(self):
        with tempfile.TemporaryDirectory() as td:
            good=Path(td)/"token"; good.write_text("secret-token\n",encoding="utf-8")
            empty=Path(td)/"empty"; empty.write_text("  \n",encoding="utf-8")
            self.assertEqual(_read_token_file(str(good)),"secret-token")
            with self.assertRaises(ValueError): _read_token_file(str(empty))

    def test_lease_404_create_requires_verified_response(self):
        client=LeaseClient(get_error=ApiError(404,"missing"))
        elector=LeaseElector(client,"pod-a")
        self.assertTrue(elector.ensure_leader())
        self.assertEqual([c[0] for c in client.calls],["GET","POST"])

    def test_lease_fresh_competing_holder_is_not_taken(self):
        lease={"metadata":{"resourceVersion":"1"},"spec":{"holderIdentity":"pod-b","leaseDurationSeconds":30,"renewTime":"2999-01-01T00:00:00Z","leaseTransitions":2}}
        client=LeaseClient(get_result=lease)
        self.assertFalse(LeaseElector(client,"pod-a").ensure_leader())
        self.assertEqual([c[0] for c in client.calls],["GET"])

    def test_lease_stale_takeover_advances_transition_and_verifies(self):
        lease={"metadata":{"resourceVersion":"1"},"spec":{"holderIdentity":"pod-b","leaseDurationSeconds":30,"renewTime":"2000-01-01T00:00:00Z","leaseTransitions":2}}
        client=LeaseClient(get_result=lease)
        self.assertTrue(LeaseElector(client,"pod-a").ensure_leader())
        patch=[c for c in client.calls if c[0]=="PATCH"][0]
        self.assertEqual(patch[2]["spec"]["leaseTransitions"],3)
        self.assertEqual(patch[2]["spec"]["holderIdentity"],"pod-a")

    def test_lease_cas_conflict_fails_closed(self):
        lease={"metadata":{"resourceVersion":"1"},"spec":{"holderIdentity":"pod-a","leaseDurationSeconds":30,"renewTime":"2999-01-01T00:00:00Z","leaseTransitions":2}}
        client=LeaseClient(get_result=lease,patch_error=ApiError(409,"conflict"))
        self.assertFalse(LeaseElector(client,"pod-a").ensure_leader())

if __name__=="__main__": unittest.main()
