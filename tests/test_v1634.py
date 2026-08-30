import unittest
from unittest.mock import patch

from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.nvidia_checkpoint_v1634 import ANNOTATION, LeaseCheckpointStore, decode_checkpoint, encode_checkpoint
from nvlx.nvidia_continuity_v1632 import SnapshotIdentity
from nvlx.nvidia_inventory_v163 import NvidiaPreflight, NvidiaSnapshot
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError
from nvlx.runtime_v163 import Runtime as BaseRuntime
from nvlx.runtime_v1634 import Runtime


def ident(uid="u1"):
    return SnapshotIdentity(
        api_versions=(("nvidia.com","v1"),),
        available_resources=(("nvidia.com",("clusterpolicies",)),),
        gpuclusters=(), clusterpolicies=(("cluster-policy",uid,"nvidia.com/v1"),), drivers=(),
        computedomains=(), computedomaincliques=(), gpu_nodes=(("gpu-1","node-u1","v1"),),
    )


def obj(uid):
    return {"apiVersion":"nvidia.com/v1","metadata":{"name":"cluster-policy","uid":uid,"resourceVersion":"7"}}


def snap(uid):
    return NvidiaSnapshot((),(obj(uid),),(),(),(),(),(("nvidia.com","v1"),),(('nvidia.com',('clusterpolicies',)),))


class Client:
    def __init__(self, *, holder="pod-a", transition=3, annotation=None):
        self.holder=holder; self.transition=transition; self.annotation=annotation; self.rv=1
    def body(self):
        anns={} if self.annotation is None else {ANNOTATION:self.annotation}
        return {"metadata":{"name":"nvlx-controller","namespace":"nvlx-system","resourceVersion":str(self.rv),"annotations":anns},"spec":{"holderIdentity":self.holder,"leaseTransitions":self.transition}}
    def request_json(self, method, path, body=None, **kwargs):
        if method=="GET": return ApiResponse(200,self.body())
        if method=="PATCH":
            if body["metadata"]["resourceVersion"] != str(self.rv): raise ApiError(409,"conflict")
            self.annotation=body["metadata"]["annotations"][ANNOTATION]
            self.rv += 1
            return ApiResponse(200,self.body())
        raise AssertionError(method)


class CheckpointEpochTests(unittest.TestCase):
    def test_round_trip_binds_lease_transition(self):
        raw=encode_checkpoint(ident(),None,7)
        self.assertEqual(decode_checkpoint(raw),(ident(),None,7))

    def test_transition_mismatch_is_reported_stale(self):
        c=Client(transition=8,annotation=encode_checkpoint(ident(),None,7))
        base,cand,epoch,stale=LeaseCheckpointStore(c,"pod-a").load()
        self.assertEqual(base,ident()); self.assertIsNone(cand); self.assertEqual(epoch,8); self.assertTrue(stale)

    def test_write_verifies_epoch_did_not_change(self):
        class Changing(Client):
            def request_json(self, method, path, body=None, **kwargs):
                if method=="PATCH": self.transition += 1
                return super().request_json(method,path,body,**kwargs)
        with self.assertRaises(NvidiaInventoryError): LeaseCheckpointStore(Changing(),"pod-a").save(ident(),None)

    def test_write_requires_current_holder(self):
        with self.assertRaises(NvidiaInventoryError): LeaseCheckpointStore(Client(holder="pod-b"),"pod-a").save(ident(),None)


class RuntimeEpochTests(unittest.TestCase):
    def test_takeover_requires_two_identical_observations(self):
        c=Client(transition=9,annotation=encode_checkpoint(ident("old"),None,8))
        vals=iter([NvidiaPreflight(True,"device-plugin",(),snap("new")),NvidiaPreflight(True,"device-plugin",(),snap("new"))])
        r=Runtime(object(),"pod-a",leader_check=lambda:True)
        r.nvidia_checkpoint_store=LeaseCheckpointStore(c,"pod-a")
        r.nvidia_inventory_check=lambda: next(vals)
        with patch.object(BaseRuntime,"list_and_watch_once",return_value="eof"):
            self.assertEqual(r.list_and_watch_once(),"relist")
            self.assertTrue(r.nvidia_checkpoint_epoch_stale)
            self.assertEqual(r.list_and_watch_once(),"eof")
        self.assertFalse(r.nvidia_checkpoint_epoch_stale)
        self.assertEqual(r.nvidia_checkpoint_revalidations,1)
        base,cand,epoch,stale=LeaseCheckpointStore(c,"pod-a").load()
        self.assertEqual(base,ident("new")); self.assertIsNone(cand); self.assertEqual(epoch,9); self.assertFalse(stale)

    def test_restart_between_confirmation_one_and_two_preserves_fence(self):
        c=Client(transition=5,annotation=encode_checkpoint(ident("old"),None,4))
        r1=Runtime(object(),"pod-a",leader_check=lambda:True)
        r1.nvidia_checkpoint_store=LeaseCheckpointStore(c,"pod-a")
        r1.nvidia_inventory_check=lambda: NvidiaPreflight(True,"device-plugin",(),snap("new"))
        self.assertEqual(r1.list_and_watch_once(),"relist")
        r2=Runtime(object(),"pod-a",leader_check=lambda:True)
        r2.nvidia_checkpoint_store=LeaseCheckpointStore(c,"pod-a")
        r2.nvidia_inventory_check=lambda: NvidiaPreflight(True,"device-plugin",(),snap("new"))
        with patch.object(BaseRuntime,"list_and_watch_once",return_value="eof"):
            self.assertEqual(r2.list_and_watch_once(),"eof")
        self.assertEqual(r2.nvidia_identity_baseline,ident("new"))

    def test_different_second_observation_keeps_fence_closed(self):
        c=Client(transition=5,annotation=encode_checkpoint(ident("old"),None,4))
        vals=iter([NvidiaPreflight(True,"device-plugin",(),snap("a")),NvidiaPreflight(True,"device-plugin",(),snap("b"))])
        r=Runtime(object(),"pod-a",leader_check=lambda:True); r.nvidia_checkpoint_store=LeaseCheckpointStore(c,"pod-a"); r.nvidia_inventory_check=lambda: next(vals)
        self.assertEqual(r.list_and_watch_once(),"relist")
        self.assertEqual(r.list_and_watch_once(),"relist")
        self.assertEqual(r.nvidia_identity_candidate,ident("b"))


if __name__ == "__main__": unittest.main()
