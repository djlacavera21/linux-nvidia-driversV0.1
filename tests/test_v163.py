import unittest
from unittest.mock import patch

from nvlx.k8s_api_v16 import ApiError, ApiResponse
from nvlx.nvidia_inventory_v163 import NvidiaInventory, NvidiaInventoryError, NvidiaPreflight, NvidiaSnapshot
from nvlx.runtime_v1629 import Runtime as RuntimeV1629
from nvlx.runtime_v163 import Runtime


def obj(name, *, state="ready", spec=None, labels=None):
    value={"metadata":{"name":name}}
    if labels is not None:
        value["metadata"]["labels"]=labels
    if state is not None:
        value["status"]={"state":state}
    if spec is not None:
        value["spec"]=spec
    return value


class FakeClient:
    def __init__(self, *, gpuclusters=(), policies=(), drivers=(), domains=(), cliques=(), nodes=(), resource_group=True):
        self.values={
            "/apis/nvidia.com":{"preferredVersion":{"groupVersion":"nvidia.com/v1"}},
            "/apis/nvidia.com/v1":{"resources":[{"name":"gpuclusters"},{"name":"clusterpolicies"},{"name":"nvidiadrivers"}]},
            "/apis/nvidia.com/v1/gpuclusters":{"items":list(gpuclusters)},
            "/apis/nvidia.com/v1/clusterpolicies":{"items":list(policies)},
            "/apis/nvidia.com/v1/nvidiadrivers":{"items":list(drivers)},
            "/api/v1/nodes":{"items":list(nodes)},
        }
        if resource_group:
            self.values.update({
                "/apis/resource.nvidia.com":{"preferredVersion":{"groupVersion":"resource.nvidia.com/v1beta1"}},
                "/apis/resource.nvidia.com/v1beta1":{"resources":[{"name":"computedomains"},{"name":"computedomaincliques"}]},
                "/apis/resource.nvidia.com/v1beta1/computedomains":{"items":list(domains)},
                "/apis/resource.nvidia.com/v1beta1/computedomaincliques":{"items":list(cliques)},
            })
        self.calls=[]

    def request_json(self, method, path, body=None, **kwargs):
        self.calls.append((method,path))
        if path not in self.values:
            raise ApiError(404,"not found")
        return ApiResponse(200,self.values[path])


class InventoryTests(unittest.TestCase):
    def test_gpucluster_dra_inventory_is_ready(self):
        client=FakeClient(
            gpuclusters=[obj("gpu-cluster")],
            drivers=[obj("default",spec={"default":True,"version":"580"})],
            domains=[obj("domain-a")],
            cliques=[obj("clique-a")],
            nodes=[obj("gpu-1",state=None,labels={"nvidia.com/gpu.present":"true"})],
        )
        result=NvidiaInventory(client).check()
        self.assertTrue(result.ready)
        self.assertEqual(result.mode,"dra")
        self.assertEqual(len(result.snapshot.gpu_nodes),1)
        self.assertIn(("resource.nvidia.com","v1beta1"),result.snapshot.api_versions)

    def test_clusterpolicy_device_plugin_inventory_is_ready(self):
        client=FakeClient(
            policies=[obj("cluster-policy")],
            nodes=[obj("gpu-1",state=None,labels={"nvidia.com/gpu.present":"true"})],
            resource_group=False,
        )
        result=NvidiaInventory(client).check()
        self.assertTrue(result.ready)
        self.assertEqual(result.mode,"device-plugin")

    def test_gpucluster_and_clusterpolicy_coexistence_fails_closed(self):
        result=NvidiaInventory(FakeClient(
            gpuclusters=[obj("gpu-cluster")], policies=[obj("cluster-policy")]
        )).check()
        self.assertFalse(result.ready)
        self.assertIn("GPUCluster and ClusterPolicy cannot coexist",result.reasons)

    def test_gpucluster_singleton_name_is_enforced(self):
        result=NvidiaInventory(FakeClient(gpuclusters=[obj("wrong-name")])).check()
        self.assertFalse(result.ready)
        self.assertIn("GPUCluster singleton must be named gpu-cluster",result.reasons)

    def test_explicit_not_ready_control_plane_fails(self):
        result=NvidiaInventory(FakeClient(policies=[obj("cluster-policy",state="notReady")])).check()
        self.assertFalse(result.ready)
        self.assertTrue(any("reports notready" in reason for reason in result.reasons))

    def test_multiple_default_drivers_fail(self):
        result=NvidiaInventory(FakeClient(
            policies=[obj("cluster-policy")],
            drivers=[obj("a",spec={"default":True}),obj("b",spec={"default":True})],
        )).check()
        self.assertFalse(result.ready)
        self.assertIn("more than one default NVIDIADriver exists",result.reasons)

    def test_gpu_nodes_without_control_plane_fail(self):
        result=NvidiaInventory(FakeClient(
            nodes=[obj("gpu-1",state=None,labels={"nvidia.com/gpu.present":"true"})]
        )).check()
        self.assertFalse(result.ready)
        self.assertEqual(result.mode,"unmanaged")

    def test_no_gpu_and_no_nvidia_api_is_safe_no_gpu_mode(self):
        client=FakeClient(resource_group=False)
        del client.values["/apis/nvidia.com"]
        del client.values["/apis/nvidia.com/v1"]
        del client.values["/apis/nvidia.com/v1/gpuclusters"]
        del client.values["/apis/nvidia.com/v1/clusterpolicies"]
        del client.values["/apis/nvidia.com/v1/nvidiadrivers"]
        result=NvidiaInventory(client).check()
        self.assertTrue(result.ready)
        self.assertEqual(result.mode,"no-gpu")

    def test_explicit_computedomain_enable_requires_served_resource(self):
        client=FakeClient(gpuclusters=[obj("gpu-cluster",spec={"draDriver":{"computeDomains":{"enabled":True}}})])
        client.values["/apis/resource.nvidia.com/v1beta1"]={"resources":[]}
        result=NvidiaInventory(client).check()
        self.assertFalse(result.ready)
        self.assertTrue(any("computedomains is not served" in reason for reason in result.reasons))

    def test_malformed_discovery_fails_closed(self):
        client=FakeClient(policies=[obj("cluster-policy")])
        client.values["/apis/nvidia.com"]={"preferredVersion":{}}
        client.values.pop("/apis/nvidia.com/v1",None)
        with self.assertRaises(NvidiaInventoryError):
            NvidiaInventory(client).snapshot()


class RuntimeTests(unittest.TestCase):
    @staticmethod
    def snapshot():
        return NvidiaSnapshot((),(),(),(),(),(),(),())

    def test_preflight_failure_blocks_gpufleet_cycle(self):
        r=Runtime(object(),"pod-a",leader_check=lambda:True)
        r.nvidia_inventory_check=lambda: NvidiaPreflight(False,"unmanaged",("blocked",),self.snapshot())
        with patch.object(RuntimeV1629,"list_and_watch_once",side_effect=AssertionError("must not enter GPUFleet cycle")):
            self.assertEqual(r.list_and_watch_once(),"relist")
        self.assertFalse(r.nvidia_preflight_ok)
        self.assertFalse(r.stats.inventory_fresh)

    def test_preflight_success_allows_base_cycle(self):
        r=Runtime(object(),"pod-a",leader_check=lambda:True)
        r.nvidia_inventory_check=lambda: NvidiaPreflight(True,"no-gpu",(),self.snapshot())
        with patch.object(RuntimeV1629,"list_and_watch_once",return_value="eof") as base:
            self.assertEqual(r.list_and_watch_once(),"eof")
            base.assert_called_once()
        self.assertTrue(r.nvidia_preflight_ok)
        self.assertEqual(r.nvidia_preflight_mode,"no-gpu")

    def test_inventory_error_returns_reconnect(self):
        r=Runtime(object(),"pod-a",leader_check=lambda:True)
        def boom(): raise NvidiaInventoryError("denied")
        r.nvidia_inventory_check=boom
        self.assertEqual(r.list_and_watch_once(),"reconnect")
        self.assertEqual(r.nvidia_preflight_mode,"error")
        self.assertFalse(r.nvidia_preflight_ok)


if __name__ == "__main__":
    unittest.main()
