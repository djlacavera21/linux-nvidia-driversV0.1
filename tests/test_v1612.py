import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v16 import Runtime

class Client:
    def __init__(self, patch_body=None, list_body=None, watch_events=None):
        self.patch_body=patch_body
        self.list_body=list_body
        self.watch_events=watch_events or []
        self.events=0
    def patch_status(self,name,rv,status):
        body=self.patch_body if self.patch_body is not None else {"metadata":{"name":name,"resourceVersion":"11"},"status":status}
        return ApiResponse(200,body)
    def create_event(self,*args,**kwargs):
        self.events += 1
        return ApiResponse(201,{"metadata":{"resourceVersion":"1"}})
    def list_fleets(self):
        body=self.list_body if self.list_body is not None else {"metadata":{"resourceVersion":"10"},"items":[]}
        return ApiResponse(200,body)
    def watch_path(self,rv): return "/watch"
    def watch_lines(self,path): yield from self.watch_events

class V1612Tests(unittest.TestCase):
    def fleet(self):
        return {"metadata":{"name":"prod","uid":"u1","resourceVersion":"10","generation":1,"annotations":{"nvlx.io/approved":"true"}}}

    def test_status_success_without_metadata_fails_closed(self):
        client=Client(patch_body={"status":{"phase":"Ready"}})
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(self.fleet()),"fenced")
        self.assertEqual(client.events,0)

    def test_status_success_for_wrong_object_fails_closed(self):
        client=Client(patch_body={"metadata":{"name":"other","resourceVersion":"11"}})
        runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(self.fleet()),"fenced")

    def test_list_metadata_must_be_object(self):
        runtime=Runtime(Client(list_body={"metadata":"bad","items":[]}),"pod-a")
        with self.assertRaises(RuntimeError): runtime.list_and_watch_once()
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_list_body_must_be_object(self):
        runtime=Runtime(Client(list_body=[]),"pod-a")
        with self.assertRaises(RuntimeError): runtime.list_and_watch_once()
        self.assertFalse(runtime.stats.inventory_fresh)

    def test_malformed_bookmark_metadata_does_not_replace_cursor(self):
        event={"type":"BOOKMARK","object":{"metadata":"bad"}}
        runtime=Runtime(Client(watch_events=[event]),"pod-a")
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.last_resource_version,"10")

    def test_non_string_object_identity_is_invalid(self):
        obj={"metadata":{"name":123,"uid":"u1","resourceVersion":"10","generation":1}}
        runtime=Runtime(Client(),"pod-a")
        self.assertEqual(runtime.reconcile_object(obj),"invalid")

if __name__=="__main__": unittest.main()
