import io, json, unittest
from urllib import error
from unittest import mock
from nvlx.k8s_api_v16 import KubeClient, ApiError, ApiResponse
from nvlx.runtime_v16 import Runtime

class EventClient:
    def __init__(self):
        self.patches=0
        self.events=0
    def patch_status(self,name,rv,status):
        self.patches += 1
        return ApiResponse(200,{"metadata":{"name":name,"uid":"u1","generation":1,"resourceVersion":"11"},"status":status},"11")
    def create_event(self,*args,**kwargs):
        self.events += 1
        return ApiResponse(201,{"metadata":{"resourceVersion":"1"}},"1")

class V1611Tests(unittest.TestCase):
    def fleet(self):
        return {"metadata":{"name":"prod","uid":"u1","resourceVersion":"10","generation":1,"annotations":{"nvlx.io/approved":"true"}}}

    def test_event_post_is_fenced_after_status_write_if_leadership_is_lost(self):
        client=EventClient(); calls=iter([True,True,False])
        runtime=Runtime(client,"pod-a",leader_check=lambda:next(calls,False))
        self.assertEqual(runtime.reconcile_object(self.fleet()),"patched")
        self.assertEqual(client.patches,1)
        self.assertEqual(client.events,0)
        self.assertFalse(runtime.stats.leader)

    def test_event_post_occurs_when_leadership_remains_valid(self):
        client=EventClient(); runtime=Runtime(client,"pod-a",leader_check=lambda:True)
        self.assertEqual(runtime.reconcile_object(self.fleet()),"patched")
        self.assertEqual(client.patches,1)
        self.assertEqual(client.events,1)

    def test_http_error_reflected_bearer_token_is_redacted(self):
        token="secret-service-account-token"
        payload=json.dumps({"message":f"authorization Bearer {token} rejected"}).encode()
        exc=error.HTTPError("http://kube/api",500,"server error",{},io.BytesIO(payload))
        client=KubeClient("http://127.0.0.1:1",token=token,timeout=1)
        with mock.patch("urllib.request.urlopen",side_effect=exc):
            with self.assertRaises(ApiError) as ctx: client.list_fleets()
        rendered=str(ctx.exception)
        self.assertNotIn(token,rendered)
        self.assertIn("<redacted>",rendered)

    def test_watch_http_error_reflected_bearer_token_is_redacted(self):
        token="watch-secret-token"
        payload=json.dumps({"message":f"Bearer {token} denied"}).encode()
        exc=error.HTTPError("http://kube/watch",403,"forbidden",{},io.BytesIO(payload))
        client=KubeClient("http://127.0.0.1:1",token=token,timeout=1)
        with mock.patch("urllib.request.urlopen",side_effect=exc):
            with self.assertRaises(ApiError) as ctx:
                list(client.watch_lines("/apis/nvlx.io/v1alpha1/gpufleets?watch=true"))
        self.assertNotIn(token,str(ctx.exception))

if __name__=="__main__": unittest.main()
