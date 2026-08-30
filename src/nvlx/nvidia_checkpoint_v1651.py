"""Narrow ambiguous checkpoint write reconciliation for nvlx 1.6.5.1."""
from __future__ import annotations

import socket
from urllib import error as urlerror

from .k8s_api_v16 import ApiError
from .nvidia_checkpoint_v1635 import ANNOTATION, FLOOR_ANNOTATION, decode_checkpoint, encode_checkpoint
from .nvidia_checkpoint_v165 import CheckpointCommitReceipt, LeaseCheckpointStore as LeaseCheckpointStoreV165
from .nvidia_inventory_v1631 import NvidiaInventoryError


class CheckpointWriteOutcomeUnknown(NvidiaInventoryError):
    """The transport failed after a checkpoint write may have reached Kubernetes."""


_RAW_TRANSPORT_ERRORS = (TimeoutError, ConnectionError, socket.timeout, urlerror.URLError)


def _transport_outcome_unknown(exc: BaseException) -> bool:
    if isinstance(exc, ApiError):
        return exc.status == 0
    return isinstance(exc, _RAW_TRANSPORT_ERRORS)


class LeaseCheckpointStore(LeaseCheckpointStoreV165):
    """Reconcile only transport-ambiguous writes; deterministic safety failures stay failures."""

    def _verified_write(self, baseline, candidate) -> tuple[int, int]:
        for _attempt in range(2):
            try:
                current = self.client.request_json("GET", self.path)
            except Exception as exc:
                raise NvidiaInventoryError(
                    f"cannot read Lease before NVIDIA checkpoint write: {exc}"
                ) from None

            meta, spec, transition = self._lease_identity(current.body)
            if spec.get("holderIdentity") != self.identity:
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint write requires current Lease leadership"
                )
            rv = meta.get("resourceVersion")
            if not isinstance(rv, str) or not rv.strip():
                raise NvidiaInventoryError(
                    "NVIDIA continuity Lease resourceVersion is missing"
                )
            anns = meta.get("annotations") or {}
            if not isinstance(anns, dict):
                raise NvidiaInventoryError(
                    "NVIDIA continuity Lease annotations are malformed"
                )
            floor = self._floor(anns)
            current_raw = anns.get(ANNOTATION)
            if current_raw is not None:
                _b, _c, _t, current_sequence = decode_checkpoint(current_raw)
                if current_sequence != floor:
                    raise NvidiaInventoryError(
                        "NVIDIA continuity checkpoint/floor mismatch before write"
                    )
            elif floor != 0:
                raise NvidiaInventoryError(
                    "NVIDIA continuity sequence floor exists without current checkpoint"
                )

            sequence = floor + 1
            raw = encode_checkpoint(baseline, candidate, transition, sequence)
            patch = {
                "metadata": {
                    "resourceVersion": rv,
                    "annotations": {
                        ANNOTATION: raw,
                        FLOOR_ANNOTATION: str(sequence),
                    },
                }
            }

            try:
                updated = self.client.request_json(
                    "PATCH",
                    self.path,
                    patch,
                    content_type="application/merge-patch+json",
                )
            except ApiError as exc:
                if exc.status in {409, 412}:
                    continue
                if exc.status == 0:
                    raise CheckpointWriteOutcomeUnknown(
                        f"NVIDIA continuity checkpoint write outcome is unknown: {exc}"
                    ) from None
                raise NvidiaInventoryError(
                    f"cannot write NVIDIA continuity checkpoint: {exc}"
                ) from None
            except _RAW_TRANSPORT_ERRORS as exc:
                raise CheckpointWriteOutcomeUnknown(
                    f"NVIDIA continuity checkpoint write outcome is unknown: {exc}"
                ) from None
            except Exception as exc:
                raise NvidiaInventoryError(
                    f"cannot write NVIDIA continuity checkpoint: {exc}"
                ) from None

            out_meta, out_spec, out_transition = self._lease_identity(updated.body)
            out_anns = out_meta.get("annotations")
            out_rv = out_meta.get("resourceVersion")
            if out_spec.get("holderIdentity") != self.identity or out_transition != transition:
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint Lease epoch changed during write"
                )
            if (
                not isinstance(out_rv, str)
                or not out_rv.strip()
                or not isinstance(out_anns, dict)
            ):
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint write response is malformed"
                )
            if (
                out_anns.get(ANNOTATION) != raw
                or out_anns.get(FLOOR_ANNOTATION) != str(sequence)
            ):
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint write was not verified"
                )

            try:
                readback = self.client.request_json("GET", self.path)
            except Exception as exc:
                if _transport_outcome_unknown(exc):
                    raise CheckpointWriteOutcomeUnknown(
                        f"NVIDIA continuity checkpoint readback outcome is unknown: {exc}"
                    ) from None
                raise NvidiaInventoryError(
                    f"cannot read back NVIDIA continuity checkpoint: {exc}"
                ) from None

            rb_meta, rb_spec, rb_transition = self._lease_identity(readback.body)
            if rb_spec.get("holderIdentity") != self.identity:
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint readback lost Lease leadership"
                )
            if rb_transition != transition:
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint Lease epoch changed before readback"
                )
            rb_rv = rb_meta.get("resourceVersion")
            rb_anns = rb_meta.get("annotations")
            if (
                not isinstance(rb_rv, str)
                or not rb_rv.strip()
                or not isinstance(rb_anns, dict)
            ):
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint readback is malformed"
                )
            if rb_anns.get(FLOOR_ANNOTATION) != str(sequence):
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint readback floor mismatch"
                )
            rb_raw = rb_anns.get(ANNOTATION)
            if not isinstance(rb_raw, str):
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint missing on readback"
                )
            rb, rc, rt, rs = decode_checkpoint(rb_raw)
            if (
                rt != transition
                or rs != sequence
                or rb != baseline
                or rc != candidate
            ):
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint readback does not match committed state"
                )
            if rb_raw != raw:
                raise NvidiaInventoryError(
                    "NVIDIA continuity checkpoint canonical readback mismatch"
                )
            return transition, sequence

        raise NvidiaInventoryError(
            "NVIDIA continuity checkpoint write conflicted twice"
        )

    def save_receipt(self, baseline, candidate) -> CheckpointCommitReceipt:
        existing = self._matching_current_commit(baseline, candidate)
        if existing is not None:
            transition, sequence = existing
            return self._receipt(
                baseline,
                candidate,
                transition,
                sequence,
                idempotent=True,
                reconciled=False,
            )

        try:
            transition, sequence = self._verified_write(baseline, candidate)
        except CheckpointWriteOutcomeUnknown as write_error:
            existing = self._matching_current_commit(baseline, candidate)
            if existing is not None:
                transition, sequence = existing
                return self._receipt(
                    baseline,
                    candidate,
                    transition,
                    sequence,
                    idempotent=True,
                    reconciled=True,
                )
            raise NvidiaInventoryError(
                f"cannot establish NVIDIA continuity checkpoint write outcome: {write_error}"
            ) from None

        return self._receipt(
            baseline,
            candidate,
            transition,
            sequence,
            idempotent=False,
            reconciled=False,
        )


__all__ = [
    "CheckpointCommitReceipt",
    "CheckpointWriteOutcomeUnknown",
    "LeaseCheckpointStore",
]
