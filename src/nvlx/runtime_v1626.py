"""Semantic finalizer preservation for nvlx 1.6.2.6."""
from __future__ import annotations
from .k8s_api_v16 import ApiResponse
from .runtime_v16 import PROTECTIVE_FINALIZER
from .runtime_v1625 import Runtime as RuntimeV1625


class Runtime(RuntimeV1625):
    """Verify finalizer preservation as a duplicate-free semantic set."""

    @staticmethod
    def _duplicate_free_finalizers(value: object) -> bool:
        return (
            isinstance(value, list)
            and all(isinstance(item, str) and item for item in value)
            and len(value) == len(set(value))
        )

    @staticmethod
    def _finalizer_plan(obj: dict) -> tuple[bool, bool, list[str]]:
        if not isinstance(obj, dict):
            return False, False, []
        meta = obj.get("metadata")
        if not isinstance(meta, dict):
            return False, False, []
        finalizers = meta.get("finalizers") or []
        if not Runtime._duplicate_free_finalizers(finalizers):
            return False, False, []
        return RuntimeV1625._finalizer_plan(obj)

    @classmethod
    def _finalizer_response_verified_for_meta(
        cls,
        response: ApiResponse | None,
        expected_meta: dict,
        expected_finalizers: list[str],
    ) -> bool:
        name = expected_meta.get("name", "")
        uid = expected_meta.get("uid", "")
        if not isinstance(name, str) or not name or not isinstance(uid, str) or not uid:
            return False
        if not cls._duplicate_free_finalizers(expected_finalizers):
            return False
        if PROTECTIVE_FINALIZER in expected_finalizers:
            return False

        meta = cls._response_meta(response, name)
        if meta is None or meta.get("uid") != uid:
            return False
        returned_finalizers = meta.get("finalizers")
        if not cls._duplicate_free_finalizers(returned_finalizers):
            return False
        if PROTECTIVE_FINALIZER in returned_finalizers:
            return False
        if set(returned_finalizers) != set(expected_finalizers):
            return False

        expected_generation = cls._required_generation(expected_meta)
        returned_generation = cls._required_generation(meta)
        return expected_generation is not None and returned_generation == expected_generation
