"""
Offline sync package.

Provides the offline-first data synchronization layer claimed by the system:

- ``operation_queue`` : a durable, priority-ordered queue of API operations made
  while offline, replayed when connectivity returns.
- ``crdt``            : conflict-free replicated data types (LWW-Register,
  OR-Set, LWW-Map) so concurrent edits on device and server merge without
  conflicts or lost updates.
- ``sync_engine``     : bidirectional CRDT sync with officer-action / grievance
  priority over cached read queries.
"""

from .operation_queue import (
    OperationPriority,
    OperationQueue,
    OperationStatus,
    OperationType,
    QueuedOperation,
)
from .crdt import LWWRegister, LWWMap, ORSet
from .sync_engine import SyncEngine, SyncResult

__all__ = [
    "OperationQueue",
    "QueuedOperation",
    "OperationType",
    "OperationStatus",
    "OperationPriority",
    "LWWRegister",
    "ORSet",
    "LWWMap",
    "SyncEngine",
    "SyncResult",
]
