import unittest

from nvlx.k8s_api_v16 import ApiResponse
from nvlx.nvidia_checkpoint_v1635 import ANNOTATION as LEGACY_V3, FLOOR_ANNOTATION, encode_checkpoint as encode_v3
from nvlx.nvidia_checkpoint_v1636 import ANNOTATION, LeaseCheckpointStore, decode_checkpoint, encode_checkpoint
from nvlx.nvidia_continuity_v1632 import SnapshotIdentity
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError


def ident(uid="u1"):
    return SnapshotIdentity(
        api_versions=(("nvidia.com","v1"),),
        available_resources=(("nvidia.com",("clusterpolicies",)),),
        gpuclusters=(), clusterpolicies=(("cluster-policy",uid,"nvidia.com/v1"),), drivers=(),
        computedomains=(), computedomaincliques=(), gpu_nodes=(),
    )


class Client:
    def __init__(self, *, annotation=None, legacy=None, floor=None, holder="pod-a", transition=4):
        self.annotation=annotation; self.legacy=legacy; self.floor=floor; self.holder=holder; self.transition=transition; self.rv=1
    def body(self):
        anns={}
        if self.annotation is not None: anns[ANNOTATION]=self.annotation
        if self.legacy is not None: anns[LEGACY_V3]=self.legacy
        if self.floor is not None: anns[FLOOR_ANNOTATION]=self.floor
        return {"metadata":{"name":"nvlx-controller","namespace":"nvlx-system","resourceVersion":str(self.rv),"annotations":anns},"spec":{"holderIdentity":self.holder,"leaseTransitions":self.transition}}
    def request_json(self, method, path, body=None, **kwargs):
        if method=="GET": return ApiResponse(200,self.body())
        if method=="PATCH":
            anns=body["metadata"]["annotations"]
            self.annotation=anns[ANNOTATION]; self.floor=anns[FLOOR_ANNOTATION]; self.rv += 1
            return ApiResponse(200,self.body())
        raise AssertionError(method)


class HolderBoundTests(unittest.TestCase):
    def test_round_trip_binds_holder(self):
        raw=encode_checkpoint(ident(),None,4,3,"pod-a")
        self.assertEqual(decode_checkpoint(raw),(ident(),None,4,3,"pod-a"))

    def test_blank_holder_fails_closed(self):
        with self.assertRaises(NvidiaInventoryError): encode_checkpoint(ident(),None,4,1," ")

    def test_same_transition_different_holder_is_stale(self):
        raw=encode_checkpoint(ident(),None,4,3,"pod-a")
        c=Client(annotation=raw,floor="3",holder="pod-b",transition=4)
        base,cand,epoch,stale,seq=LeaseCheckpointStore(c,"pod-b").load()
        self.assertEqual(base,ident()); self.assertIsNone(cand); self.assertEqual((epoch,seq),(4,3)); self.assertTrue(stale)

    def test_matching_holder_and_transition_is_current(self):
        raw=encode_checkpoint(ident(),None,4,3,"pod-a")
        c=Client(annotation=raw,floor="3",holder="pod-a",transition=4)
        self.assertFalse(LeaseCheckpointStore(c,"pod-a").load()[3])

    def test_legacy_v3_load_requires_revalidation(self):
        legacy=encode_v3(ident(),None,4,3)
        c=Client(legacy=legacy,floor="3",holder="pod-a",transition=4)
        base,cand,epoch,stale,seq=LeaseCheckpointStore(c,"pod-a").load()
        self.assertEqual(base,ident()); self.assertIsNone(cand); self.assertEqual((epoch,seq),(4,3)); self.assertTrue(stale)

    def test_legacy_v3_migrates_on_save_without_resetting_sequence(self):
        legacy=encode_v3(ident(),None,4,3)
        c=Client(legacy=legacy,floor="3",holder="pod-a",transition=4)
        epoch,seq=LeaseCheckpointStore(c,"pod-a").save(ident("u2"),None)
        self.assertEqual((epoch,seq),(4,4))
        self.assertEqual(decode_checkpoint(c.annotation)[4],"pod-a")

    def test_current_v4_written_by_other_holder_cannot_be_advanced_directly(self):
        raw=encode_checkpoint(ident(),None,4,3,"pod-a")
        c=Client(annotation=raw,floor="3",holder="pod-b",transition=4)
        with self.assertRaisesRegex(NvidiaInventoryError,"holder mismatch"):
            LeaseCheckpointStore(c,"pod-b").save(ident("u2"),None)

    def test_write_response_holder_change_fails_closed(self):
        class Changing(Client):
            def request_json(self, method, path, body=None, **kwargs):
                result=super().request_json(method,path,body,**kwargs)
                if method=="PATCH":
                    self.holder="pod-b"
                    return ApiResponse(200,self.body())
                return result
        c=Changing(holder="pod-a")
        with self.assertRaisesRegex(NvidiaInventoryError,"Lease identity changed"):
            LeaseCheckpointStore(c,"pod-a").save(ident(),None)


if __name__ == "__main__": unittest.main()
