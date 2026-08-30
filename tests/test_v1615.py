import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v16 import Runtime

class SnapshotClient:
    def __init__(self, items=None, watch_events=None):
        self.items=[] if items is None else items
        self.watch_events=[] if watch_events is None else watch_events
        self.patches=0
    def list_fleets(self):
        return ApiResponse(200,{"metadata":{"resourceVersion":"10"},"items":self.items})
    def watch_path(self,rv): return "/watch"
    def watch_lines(self,path): yield from self.watch_events
    def patch_status(self,name,rv,status):
        self.patches += 1
        return ApiResponse(200,{"metadata":{"name":name,"resourceVersion":"11"},"status":status})
    def create_event(self,*args,**kwargs):
        return ApiResponse(201,{"metadata":{"resourceVersion":"1"},"regarding":{"name":"prod","uid":"u1"},"reportingController":"nvlx.io/operator","reportingInstance":"pod-a"})

class V1615Tests(unittest.TestCase):
    def test_event_response_must_reference_expected_fleet(self):
        response=ApiResponse(201,{"metadata":{"resourceVersion":"1"},"regarding":{"name":"other","uid":"u1"},"reportingController":"nvlx.io/operator","reportingInstance":"pod-a"})
        self.assertFalse(Runtime._event_response_verified(response,"prod","u1","pod-a"))

    def test_event_response_must_reference_expected_uid(self):
        response=ApiResponse(201,{"metadata":{"resourceVersion":"1"},"regarding":{"name":"prod","uid":"u2"},"reportingController":"nvlx.io/operator","reportingInstance":"pod-a"})
        self.assertFalse(Runtime._event_response_verified(response,"prod","u1","pod-a"))

    def test_event_response_must_echo_reporting_identity(self):
        response=ApiResponse(201,{"metadata":{"resourceVersion":"1"},"regarding":{"name":"prod","uid":"u1"},"reportingController":"nvlx.io/operator","reportingInstance":"pod-b"})
        self.assertFalse(Runtime._event_response_verified(response,"prod","u1","pod-a"))

    def test_event_response_matching_regarding_is_verified(self):
        response=ApiResponse(201,{"metadata":{"resourceVersion":"1"},"regarding":{"name":"prod","uid":"u1"},"reportingController":"nvlx.io/operator","reportingInstance":"pod-a"})
        self.assertTrue(Runtime._event_response_verified(response,"prod","u1","pod-a"))

    def test_invalid_list_item_aborts_snapshot_before_any_reconcile(self):
        valid={"metadata":{"name":"prod","resourceVersion":"10","generation":1}}
        invalid={"metadata":{"name":"bad","resourceVersion":""}}
        client=SnapshotClient(items=[valid,invalid])
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        with self.assertRaises(RuntimeError): runtime.list_and_watch_once()
        self.assertEqual(client.patches,0)
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_invalid_watch_object_is_ignored_without_cursor_advance(self):
        invalid={"type":"MODIFIED","object":{"metadata":{"name":"prod","resourceVersion":""}}}
        client=SnapshotClient(watch_events=[invalid])
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.last_resource_version,"10")
        self.assertEqual(client.patches,0)
        self.assertEqual(runtime.stats.reconcile_failures,1)

if __name__=="__main__": unittest.main()
