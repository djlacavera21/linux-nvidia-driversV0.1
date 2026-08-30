"""Generation-bound mutation verification for nvlx 1.6.2.5."""
from __future__ import annotations
from .k8s_api_v16 import ApiError, ApiResponse
from .runtime_v1624 import Runtime as RuntimeV1624

class Runtime(RuntimeV1624):
    """Require successful mutation responses to prove generation continuity."""

    @staticmethod
    def _required_generation(meta: object) -> int | None:
        if not isinstance(meta,dict) or "generation" not in meta:
            return None
        value=meta.get("generation")
        if isinstance(value,bool):
            return None
        try:
            generation=int(value)
        except (TypeError,ValueError):
            return None
        return generation if generation >= 0 else None

    @classmethod
    def _status_response_verified(cls, response: ApiResponse | None, expected_meta: dict, expected_status: dict) -> bool:
        if not super()._status_response_verified(response,expected_meta,expected_status):
            return False
        expected_generation=cls._required_generation(expected_meta)
        returned_meta=cls._response_meta(response,expected_meta.get("name", ""))
        returned_generation=cls._required_generation(returned_meta)
        return expected_generation is not None and returned_generation == expected_generation

    @classmethod
    def _finalizer_response_verified_for_meta(cls, response: ApiResponse | None, expected_meta: dict, expected_finalizers: list[str]) -> bool:
        name=expected_meta.get("name","")
        uid=expected_meta.get("uid","")
        if not super()._finalizer_response_verified(response,name,expected_finalizers,uid):
            return False
        expected_generation=cls._required_generation(expected_meta)
        returned_meta=cls._response_meta(response,name)
        returned_generation=cls._required_generation(returned_meta)
        return expected_generation is not None and returned_generation == expected_generation

    def _finalize(self, obj: dict) -> bool:
        allowed,already_done,remaining=self._finalizer_plan(obj)
        if already_done:
            return True
        if not allowed or not self._leader():
            return False
        meta=obj["metadata"]
        if self._required_generation(meta) is None:
            return False
        try:
            response=self.client.patch_finalizers(meta["name"],meta["resourceVersion"],remaining)
            return self._finalizer_response_verified_for_meta(response,meta,remaining)
        except ApiError as e:
            if e.status not in {409,412}:
                if e.status in {404,410}:
                    return False
                raise
        if not self._leader():
            return False
        try:
            response=self.client.get_fleet(meta["name"])
        except ApiError:
            self.stats.finalizer_conflict_fenced += 1
            return False
        fresh=response.body if response is not None else None
        if not self._same_incarnation(fresh,meta):
            self.stats.finalizer_conflict_fenced += 1
            return False
        allowed,already_done,remaining=self._finalizer_plan(fresh)
        if already_done:
            return True
        if not allowed or self._required_generation(fresh["metadata"]) is None:
            self.stats.finalizer_conflict_fenced += 1
            return False
        self.stats.finalizer_conflict_recomputes += 1
        if not self._leader():
            self.stats.finalizer_conflict_fenced += 1
            return False
        fresh_meta=fresh["metadata"]
        try:
            retry=self.client.patch_finalizers(fresh_meta["name"],fresh_meta["resourceVersion"],remaining)
        except ApiError:
            self.stats.finalizer_conflict_fenced += 1
            return False
        ok=self._finalizer_response_verified_for_meta(retry,fresh_meta,remaining)
        if not ok:
            self.stats.finalizer_conflict_fenced += 1
        return ok
