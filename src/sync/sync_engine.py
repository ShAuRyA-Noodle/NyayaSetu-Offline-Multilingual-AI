"""
Sync Engine — bidirectional CRDT synchronization.

Each node (device or server) holds a store of CRDT records. While offline, a
node mutates its local records and queues the corresponding API operations.
When connectivity returns, ``sync`` merges CRDT state in both directions so both
nodes converge to identical state, and replays queued operations
highest-priority-first (officer actions + grievance updates before cached
citizen queries).

Because the state is CRDT-based, merge is order-independent and lossless — there
is no "last sync wins" clobbering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .crdt import LWWMap, ORSet
from .operation_queue import (
    OperationPriority,
    OperationQueue,
    OperationType,
    QueuedOperation,
)

# Operation types that must be pushed before low-value cached reads.
_HIGH_PRIORITY_TYPES = {
    OperationType.GRIEVANCE_SUBMIT,
    OperationType.GRIEVANCE_UPDATE,
    OperationType.STATUS_UPDATE,
    OperationType.COMMENT_ADD,
}


@dataclass
class SyncResult:
    pushed: int = 0
    push_failed: int = 0
    records_merged: int = 0
    sets_merged: int = 0
    conflicts_resolved: int = 0

    def as_dict(self) -> Dict[str, int]:
        return self.__dict__.copy()


class SyncEngine:
    """A single replica's CRDT store + offline operation queue."""

    def __init__(self, node_id: str, queue: Optional[OperationQueue] = None):
        self.node_id = node_id
        self.records: Dict[str, LWWMap] = {}
        self.sets: Dict[str, ORSet] = {}
        self.queue = queue

    # ---- local mutations ---------------------------------------------------

    def set_field(
        self,
        record_id: str,
        field_name: str,
        value,
        timestamp: float,
        actor: Optional[str] = None,
    ) -> None:
        """Mutate a record field locally (LWW)."""
        rec = self.records.setdefault(record_id, LWWMap())
        rec.set(field_name, value, timestamp, actor or self.node_id)

    def add_to_set(self, set_id: str, element, tag: str) -> None:
        self.sets.setdefault(set_id, ORSet()).add(element, tag)

    def remove_from_set(self, set_id: str, element) -> None:
        if set_id in self.sets:
            self.sets[set_id].remove(element)

    def record(self, record_id: str) -> Dict:
        """Current resolved values for a record."""
        rec = self.records.get(record_id)
        return rec.to_plain() if rec else {}

    # ---- offline queueing --------------------------------------------------

    def queue_operation(
        self,
        endpoint: str,
        op_type: OperationType,
        data: Dict,
    ) -> Optional[str]:
        """Queue an API operation for replay, prioritized by type."""
        if self.queue is None:
            return None
        priority = (
            OperationPriority.HIGH
            if op_type in _HIGH_PRIORITY_TYPES
            else OperationPriority.LOW
        )
        op = QueuedOperation(
            endpoint=endpoint, type=op_type, data=data, priority=priority
        )
        return self.queue.enqueue(op)

    # ---- state merge (CRDT) ------------------------------------------------

    def merge_state(self, other: "SyncEngine") -> SyncResult:
        """
        Merge another replica's CRDT state into this one (one direction).

        Returns counts, including how many records had a genuine conflict
        (both sides wrote the same field) that the CRDT resolved.
        """
        result = SyncResult()
        for rid, other_rec in other.records.items():
            if rid in self.records:
                before = self.records[rid].to_dict()
                # Count fields where both sides had a value (potential conflict).
                for fname, oreg in other_rec.fields.items():
                    mine = self.records[rid].fields.get(fname)
                    if mine is not None and mine.value != oreg.value:
                        result.conflicts_resolved += 1
                self.records[rid] = self.records[rid].merge(other_rec)
                if self.records[rid].to_dict() != before:
                    result.records_merged += 1
            else:
                self.records[rid] = LWWMap.from_dict(other_rec.to_dict())
                result.records_merged += 1
        for sid, other_set in other.sets.items():
            if sid in self.sets:
                self.sets[sid] = self.sets[sid].merge(other_set)
            else:
                self.sets[sid] = ORSet.from_dict(other_set.to_dict())
            result.sets_merged += 1
        return result

    def sync(
        self,
        other: "SyncEngine",
        pusher: Optional[Callable[[QueuedOperation], bool]] = None,
    ) -> SyncResult:
        """
        Bidirectional sync: converge CRDT state on both replicas and (optionally)
        replay this node's queued operations highest-priority-first.

        After ``sync``, both replicas hold identical merged state.
        """
        # 1) Replay queued ops priority-first (officer/grievance before reads).
        result = SyncResult()
        if self.queue is not None and pusher is not None:
            stats = self.queue.process_all(pusher)
            result.pushed = stats["succeeded"]
            result.push_failed = stats["failed"]

        # 2) Merge state both directions → guaranteed convergence.
        forward = self.merge_state(other)
        other.merge_state(self)  # symmetric so `other` converges too

        result.records_merged = forward.records_merged
        result.sets_merged = forward.sets_merged
        result.conflicts_resolved = forward.conflicts_resolved
        return result
