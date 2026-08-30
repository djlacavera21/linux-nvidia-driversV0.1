import unittest
from nvlx.k8s_api_v16 import ApiResponse
from nvlx.runtime_v16 import Runtime

class WatchClient:
    def __init__(self, events):
        self.events=list(events)
    def list_fleets(self):
        return ApiResponse(200,{"metadata":{"resourceVersion":"10"},"items":[]})
    def watch_path(self,rv): return "/watch"
    def watch_lines(self,path): yield from self.events


def fleet(*, rv="11", generation=1, uid="u1", name="prod"):
    return {"metadata":{"name":name,"uid":uid,"resourceVersion":rv,"generation":generation}}


class V1616Tests(unittest.TestCase):
    def runtime(self, events):
        return Runtime(WatchClient(events),"pod-a",leader_check=lambda:False)

    def test_exact_duplicate_watch_delivery_is_suppressed(self):
        event={"type":"MODIFIED","object":fleet(rv="11",generation=2)}
        runtime=self.runtime([event,event])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_total,1)
        self.assertEqual(runtime.stats.duplicate_watch_events,1)
        self.assertEqual(runtime.stats.reconcile_failures,0)

    def test_same_uid_generation_regression_is_fenced(self):
        newer={"type":"MODIFIED","object":fleet(rv="11",generation=5)}
        older={"type":"MODIFIED","object":fleet(rv="different-opaque-rv",generation=4)}
        runtime=self.runtime([newer,older])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_total,1)
        self.assertEqual(runtime.stats.stale_generation_events,1)
        self.assertEqual(runtime.stats.reconcile_failures,1)

    def test_same_generation_different_resource_version_is_not_ordered(self):
        first={"type":"MODIFIED","object":fleet(rv="opaque-a",generation=5)}
        second={"type":"MODIFIED","object":fleet(rv="opaque-b",generation=5)}
        runtime=self.runtime([first,second])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_total,2)
        self.assertEqual(runtime.stats.duplicate_watch_events,0)
        self.assertEqual(runtime.stats.stale_generation_events,0)

    def test_new_uid_is_new_incarnation_even_with_lower_generation(self):
        old={"type":"MODIFIED","object":fleet(rv="11",generation=9,uid="old")}
        replacement={"type":"ADDED","object":fleet(rv="12",generation=1,uid="new")}
        runtime=self.runtime([old,replacement])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_total,2)
        self.assertEqual(runtime.stats.stale_generation_events,0)

    def test_different_event_type_is_not_exact_duplicate(self):
        modified={"type":"MODIFIED","object":fleet(rv="11",generation=2)}
        deleted={"type":"DELETED","object":fleet(rv="11",generation=2)}
        runtime=self.runtime([modified,deleted])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_total,2)
        self.assertEqual(runtime.stats.duplicate_watch_events,0)

    def test_invalid_watch_object_still_fails_closed(self):
        runtime=self.runtime([{"type":"MODIFIED","object":{"metadata":{"name":"prod","resourceVersion":""}}}])
        self.assertEqual(runtime.list_and_watch_once(),"eof")
        self.assertEqual(runtime.stats.reconcile_total,0)
        self.assertEqual(runtime.stats.reconcile_failures,1)

if __name__=="__main__": unittest.main()
