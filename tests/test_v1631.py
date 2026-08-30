import unittest

from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.nvidia_inventory_v1631 import NvidiaInventory, NvidiaInventoryError


def resource(name, *, namespaced=False):
    return {"name":name,"namespaced":namespaced}


def obj(name, api, kind, *, namespace=None, labels=None):
    meta={"name":name,"uid":"uid-"+name,"resourceVersion":"7"}
    if namespace is not None: meta["namespace"]=namespace
    if labels is not None: meta["labels"]=labels
    return {"apiVersion":api,"kind":kind,"metadata":meta,"status":{"state":"ready"}}


class Client:
    def __init__(self):
        self.values={
            "/apis/nvidia.com":{"preferredVersion":{"groupVersion":"nvidia.com/v1"},"versions":[{"groupVersion":"nvidia.com/v1"}]},
            "/apis/nvidia.com/v1":{"groupVersion":"nvidia.com/v1","resources":[resource("clusterpolicies")]},
            "/apis/nvidia.com/v1/clusterpolicies":{"items":[obj("cluster-policy","nvidia.com/v1","ClusterPolicy")]},
            "/api/v1/nodes":{"items":[obj("gpu-1","v1","Node",labels={"nvidia.com/gpu.present":"true"})]},
        }
    def request_json(self, method, path, body=None, **kwargs):
        if path == "/apis/resource.nvidia.com": raise ApiError(404,"not found")
        if path not in self.values: raise ApiError(404,"not found")
        return ApiResponse(200,self.values[path])


class InventoryIdentityTests(unittest.TestCase):
    def test_valid_cluster_scoped_identity_passes(self):
        result=NvidiaInventory(Client()).check()
        self.assertTrue(result.ready)
        self.assertEqual(result.mode,"device-plugin")

    def test_discovery_group_version_mismatch_fails_closed(self):
        c=Client(); c.values["/apis/nvidia.com/v1"]["groupVersion"]="nvidia.com/v1alpha1"
        with self.assertRaises(NvidiaInventoryError): NvidiaInventory(c).snapshot()

    def test_namespaced_discovery_contract_fails_closed(self):
        c=Client(); c.values["/apis/nvidia.com/v1"]["resources"][0]["namespaced"]=True
        with self.assertRaises(NvidiaInventoryError): NvidiaInventory(c).snapshot()

    def test_object_api_version_mismatch_fails_closed(self):
        c=Client(); c.values["/apis/nvidia.com/v1/clusterpolicies"]["items"][0]["apiVersion"]="nvidia.com/v1alpha1"
        with self.assertRaises(NvidiaInventoryError): NvidiaInventory(c).snapshot()

    def test_namespaced_cluster_resource_fails_closed(self):
        c=Client(); c.values["/apis/nvidia.com/v1/clusterpolicies"]["items"][0]["metadata"]["namespace"]="default"
        with self.assertRaises(NvidiaInventoryError): NvidiaInventory(c).snapshot()

    def test_blank_uid_and_resource_version_fail_closed_when_present(self):
        for field in ("uid","resourceVersion"):
            with self.subTest(field=field):
                c=Client(); c.values["/apis/nvidia.com/v1/clusterpolicies"]["items"][0]["metadata"][field]=""
                with self.assertRaises(NvidiaInventoryError): NvidiaInventory(c).snapshot()

    def test_gpu_node_identity_mismatch_fails_closed(self):
        c=Client(); c.values["/api/v1/nodes"]["items"][0]["kind"]="Pod"
        with self.assertRaises(NvidiaInventoryError): NvidiaInventory(c).snapshot()


if __name__ == "__main__": unittest.main()
