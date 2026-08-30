import json
import unittest

from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.nvidia_checkpoint_v1633 import ANNOTATION, LeaseCheckpointStore, decode_checkpoint, encode_checkpoint
from nvlx.nvidia_continuity_v1632 import SnapshotIdentity
from nvlx.nvidia_inventory_v1631 import NvidiaInventoryError


def ident(uid="u1"):
    return SnapshotIdentity(
        api_versions=(("nvidia.com","v1"),),
        available_resources=(("nvidia.com",("clusterpolicies",)),),
        gpuclusters=(), clusterpolicies=(("cluster-policy",uid,"nvidia.com/v1"),), drivers=(),
        computedomains=(), computedomaincliques=(), gpu_nodes=(("gpu-1","node-u1","v1"),),
    )


class Client:
    def __init__(self, holder="pod-a", annotation=None):
        self.rv=1; self.holder=holder; self.annotation=annotation; self.conflict_once=False
    def body(self):
        anns={} if self.annotation is None else {ANNOTATION:self.annotation}
        return {"metadata":{"name":"nvlx-controller","namespace":"nvlx-system","resourceVersion":str(self.rv),"annotations":anns},"spec":{"holderIdentity":self.holder}}
    def request_json(self, method, path, body=None, **kwargs):
        if method=="GET": return ApiResponse(200,self.body())
        if method=="PATCH":
            if self.conflict_once:
                self.conflict_once=False; self.rv += 1; raise ApiError(409,"conflict")
            if body["metadata"]["resourceVersion"] != str(self.rv): raise ApiError(409,"conflict")
            self.annotation=body["metadata"]["annotations"][ANNOTATION]; self.rv += 1
            return ApiResponse(200,self.body())
        raise AssertionError(method)


class CheckpointTests(unittest.TestCase):
    def test_round_trip(self):
        base=ident(); cand=ident("u2")
        self.assertEqual(decode_checkpoint(encode_checkpoint(base,cand)),(base,cand))

    def test_integrity_mismatch_fails_closed(self):
        raw=json.loads(encode_checkpoint(ident(),None)); raw["payload"]["baseline"]["clusterpolicies"][0][1]="evil"
        with self.assertRaises(NvidiaInventoryError): decode_checkpoint(json.dumps(raw))

    def test_candidate_without_baseline_rejected(self):
        with self.assertRaises(NvidiaInventoryError): encode_checkpoint(None,ident())

    def test_store_persists_and_loads(self):
        c=Client(); store=LeaseCheckpointStore(c,"pod-a")
        store.save(ident(),None)
        self.assertEqual(store.load(),(ident(),None))

    def test_store_requires_current_holder(self):
        with self.assertRaises(NvidiaInventoryError): LeaseCheckpointStore(Client(holder="pod-b"),"pod-a").save(ident(),None)

    def test_store_retries_one_cas_conflict(self):
        c=Client(); c.conflict_once=True
        LeaseCheckpointStore(c,"pod-a").save(ident(),None)
        self.assertEqual(LeaseCheckpointStore(c,"pod-a").load()[0],ident())

    def test_corrupt_persisted_annotation_fails(self):
        c=Client(annotation="not-json")
        with self.assertRaises(NvidiaInventoryError): LeaseCheckpointStore(c,"pod-a").load()


if __name__ == "__main__": unittest.main()
