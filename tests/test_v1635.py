import unittest

from nvlx.k8s_api_v16 import ApiResponse
from nvlx.nvidia_checkpoint_v1635 import ANNOTATION, FLOOR_ANNOTATION, LeaseCheckpointStore, decode_checkpoint, encode_checkpoint
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
    def __init__(self, *, annotation=None, floor=None, holder="pod-a", transition=4):
        self.annotation=annotation; self.floor=floor; self.holder=holder; self.transition=transition; self.rv=1
    def body(self):
        anns={}
        if self.annotation is not None: anns[ANNOTATION]=self.annotation
        if self.floor is not None: anns[FLOOR_ANNOTATION]=self.floor
        return {"metadata":{"name":"nvlx-controller","namespace":"nvlx-system","resourceVersion":str(self.rv),"annotations":anns},"spec":{"holderIdentity":self.holder,"leaseTransitions":self.transition}}
    def request_json(self, method, path, body=None, **kwargs):
        if method=="GET": return ApiResponse(200,self.body())
        if method=="PATCH":
            anns=body["metadata"]["annotations"]
            self.annotation=anns[ANNOTATION]; self.floor=anns[FLOOR_ANNOTATION]; self.rv += 1
            return ApiResponse(200,self.body())
        raise AssertionError(method)


class ReplayFloorTests(unittest.TestCase):
    def test_round_trip_includes_positive_sequence(self):
        raw=encode_checkpoint(ident(),None,4,3)
        self.assertEqual(decode_checkpoint(raw),(ident(),None,4,3))

    def test_store_advances_sequence_exactly_once(self):
        c=Client()
        store=LeaseCheckpointStore(c,"pod-a")
        epoch,seq=store.save(ident(),None)
        self.assertEqual((epoch,seq),(4,1))
        epoch,seq=store.save(ident("u2"),None)
        self.assertEqual((epoch,seq),(4,2))
        self.assertEqual(store.load()[4],2)

    def test_replayed_checkpoint_below_retained_floor_fails_closed(self):
        old=encode_checkpoint(ident("old"),None,4,2)
        c=Client(annotation=old,floor="5")
        with self.assertRaisesRegex(NvidiaInventoryError,"replay detected"):
            LeaseCheckpointStore(c,"pod-a").load()

    def test_checkpoint_ahead_of_floor_fails_closed(self):
        raw=encode_checkpoint(ident(),None,4,6)
        c=Client(annotation=raw,floor="5")
        with self.assertRaisesRegex(NvidiaInventoryError,"exceeds retained floor"):
            LeaseCheckpointStore(c,"pod-a").load()

    def test_floor_without_checkpoint_fails_before_write(self):
        c=Client(floor="3")
        with self.assertRaisesRegex(NvidiaInventoryError,"floor exists without current checkpoint"):
            LeaseCheckpointStore(c,"pod-a").save(ident(),None)

    def test_malformed_floor_fails_closed(self):
        c=Client(annotation=encode_checkpoint(ident(),None,4,1),floor="-1")
        with self.assertRaises(NvidiaInventoryError): LeaseCheckpointStore(c,"pod-a").load()


if __name__ == "__main__": unittest.main()
