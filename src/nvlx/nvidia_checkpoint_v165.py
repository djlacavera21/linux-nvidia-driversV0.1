"""Per-call NVIDIA checkpoint commit receipts for nvlx 1.6.5."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .nvidia_checkpoint_v1635 import encode_checkpoint
from .nvidia_checkpoint_v1637 import LeaseCheckpointStore as LeaseCheckpointStoreV1637
from .nvidia_checkpoint_v1638 import LeaseCheckpointStore as LeaseCheckpointStoreV1638
from .nvidia_inventory_v1631 import NvidiaInventoryError


@dataclass(frozen=True)
class CheckpointCommitReceipt:
    """Proof returned by one checkpoint save operation."""

    lease_transition: int
    sequence: int
    idempotent: bool
    reconciled: bool
    canonical_sha256: str

    def __post_init__(self):
        if (
            isinstance(self.lease_transition, bool)
            or not isinstance(self.lease_transition, int)
            or self.lease_transition < 0
        ):
            raise ValueError("checkpoint receipt Lease transition must be a nonnegative integer")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("checkpoint receipt sequence must be a positive integer")
        if not isinstance(self.idempotent, bool) or not isinstance(self.reconciled, bool):
            raise ValueError("checkpoint receipt flags must be boolean")
        if self.reconciled and not self.idempotent:
            raise ValueError("reconciled checkpoint receipt must be idempotent")
        digest = self.canonical_sha256
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise ValueError("checkpoint receipt canonical SHA-256 is invalid")


class LeaseCheckpointStore(LeaseCheckpointStoreV1638):
    """Return a typed receipt proving the outcome of each checkpoint save call."""

    @staticmethod
    def _canonical_sha256(baseline, candidate, transition: int, sequence: int) -> str:
        raw = encode_checkpoint(baseline, candidate, transition, sequence)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _receipt(
        self,
        baseline,
        candidate,
        transition: int,
        sequence: int,
        *,
        idempotent: bool,
        reconciled: bool,
    ) -> CheckpointCommitReceipt:
        return CheckpointCommitReceipt(
            lease_transition=transition,
            sequence=sequence,
            idempotent=idempotent,
            reconciled=reconciled,
            canonical_sha256=self._canonical_sha256(
                baseline, candidate, transition, sequence
            ),
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
            transition, sequence = LeaseCheckpointStoreV1637.save(
                self, baseline, candidate
            )
            return self._receipt(
                baseline,
                candidate,
                transition,
                sequence,
                idempotent=False,
                reconciled=False,
            )
        except Exception as write_error:
            try:
                existing = self._matching_current_commit(baseline, candidate)
            except NvidiaInventoryError:
                raise

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
            if isinstance(write_error, NvidiaInventoryError):
                raise write_error
            raise NvidiaInventoryError(
                f"cannot establish NVIDIA continuity checkpoint write outcome: {write_error}"
            ) from None

    def save(self, baseline, candidate) -> tuple[int, int]:
        """Preserve the historical tuple API for older callers."""
        receipt = self.save_receipt(baseline, candidate)
        return receipt.lease_transition, receipt.sequence


__all__ = ["CheckpointCommitReceipt", "LeaseCheckpointStore"]
