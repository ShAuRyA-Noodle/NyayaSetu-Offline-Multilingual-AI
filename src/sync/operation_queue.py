"""
Operation Queue — durable, priority-ordered offline operation log.

When the device is offline, mutating API calls (submit grievance, add comment,
update status) are enqueued here instead of failing. When connectivity returns,
the sync engine replays them highest-priority-first. Officer actions and
grievance updates get higher priority than cached citizen queries.

Backed by SQLite so the queue survives process restarts and power loss — the
norm on rural kiosk hardware.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional


class OperationType(str, Enum):
    API_REQUEST = "api_request"
    GRIEVANCE_SUBMIT = "grievance_submit"
    GRIEVANCE_UPDATE = "grievance_update"
    COMMENT_ADD = "comment_add"
    STATUS_UPDATE = "status_update"
    SCHEME_QUERY = "scheme_query"


class OperationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    RETRY = "retry"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationPriority(IntEnum):
    """Higher value = processed first."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


# Statuses eligible for (re)processing.
_PENDING_STATUSES = (OperationStatus.PENDING.value, OperationStatus.RETRY.value)


@dataclass
class QueuedOperation:
    """A single queued operation."""

    endpoint: str = ""
    type: OperationType = OperationType.API_REQUEST
    method: str = "POST"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: OperationPriority = OperationPriority.NORMAL
    status: OperationStatus = OperationStatus.PENDING
    max_retries: int = 3
    retry_count: int = 0
    last_error: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "endpoint": self.endpoint,
            "type": self.type.value if isinstance(self.type, OperationType) else self.type,
            "method": self.method,
            "data": self.data,
            "metadata": self.metadata,
            "priority": int(self.priority),
            "status": self.status.value if isinstance(self.status, OperationStatus) else self.status,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QueuedOperation":
        def _dt(v):
            return datetime.fromisoformat(v) if v else None

        return cls(
            id=d.get("id") or str(uuid.uuid4()),
            endpoint=d.get("endpoint", ""),
            type=OperationType(d.get("type", "api_request")),
            method=d.get("method", "POST"),
            data=d.get("data") or {},
            metadata=d.get("metadata") or {},
            priority=OperationPriority(int(d.get("priority", 1))),
            status=OperationStatus(d.get("status", "pending")),
            max_retries=int(d.get("max_retries", 3)),
            retry_count=int(d.get("retry_count", 0)),
            last_error=d.get("last_error"),
            scheduled_at=_dt(d.get("scheduled_at")),
            created_at=_dt(d.get("created_at")) or datetime.utcnow(),
        )


class OperationQueue:
    """SQLite-backed durable operation queue."""

    def __init__(self, db_path: str = "data/operation_queue.db"):
        self.db_path = db_path
        self._processing = False
        self._lock = threading.RLock()
        self._auto_thread: Optional[threading.Thread] = None
        self._init_db()

    # ---- lifecycle ---------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    endpoint TEXT,
                    type TEXT,
                    method TEXT,
                    data TEXT,
                    metadata TEXT,
                    priority INTEGER,
                    status TEXT,
                    max_retries INTEGER,
                    retry_count INTEGER,
                    last_error TEXT,
                    scheduled_at TEXT,
                    created_at TEXT,
                    completed_at TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ops_status_priority "
                "ON operations(status, priority DESC)"
            )
            conn.commit()

    def __enter__(self) -> "OperationQueue":
        return self

    def __exit__(self, *exc) -> None:
        if self._processing:
            self.stop_auto_processing()

    # ---- enqueue / dequeue -------------------------------------------------

    def enqueue(self, op: QueuedOperation) -> str:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO operations
                    (id, endpoint, type, method, data, metadata, priority, status,
                     max_retries, retry_count, last_error, scheduled_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    op.id, op.endpoint,
                    op.type.value if isinstance(op.type, OperationType) else op.type,
                    op.method,
                    json.dumps(op.data), json.dumps(op.metadata),
                    int(op.priority),
                    op.status.value if isinstance(op.status, OperationStatus) else op.status,
                    op.max_retries, op.retry_count, op.last_error,
                    op.scheduled_at.isoformat() if op.scheduled_at else None,
                    op.created_at.isoformat(),
                ),
            )
            conn.commit()
        return op.id

    def dequeue(self, priority_only: bool = False) -> Optional[QueuedOperation]:
        """
        Return the highest-priority ready operation and mark it PROCESSING.

        Skips operations scheduled for the future. With ``priority_only``, only
        HIGH/CRITICAL operations are returned.
        """
        now = datetime.utcnow().isoformat()
        with self._lock, self._connect() as conn:
            clause = "status IN (?, ?) AND (scheduled_at IS NULL OR scheduled_at <= ?)"
            params: List[Any] = [_PENDING_STATUSES[0], _PENDING_STATUSES[1], now]
            if priority_only:
                clause += " AND priority >= ?"
                params.append(int(OperationPriority.HIGH))
            row = conn.execute(
                f"SELECT * FROM operations WHERE {clause} "
                f"ORDER BY priority DESC, created_at ASC LIMIT 1",
                params,
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE operations SET status = ? WHERE id = ?",
                (OperationStatus.PROCESSING.value, row["id"]),
            )
            conn.commit()
            op = self._row_to_op(row)
            op.status = OperationStatus.PROCESSING
            return op

    # ---- status transitions ------------------------------------------------

    def mark_completed(self, op_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE operations SET status = ?, completed_at = ? WHERE id = ?",
                (OperationStatus.COMPLETED.value, datetime.utcnow().isoformat(), op_id),
            )
            conn.commit()

    def mark_failed(self, op_id: str, error: str) -> None:
        """Increment retry count; RETRY until max_retries, then FAILED."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT retry_count, max_retries FROM operations WHERE id = ?",
                (op_id,),
            ).fetchone()
            if row is None:
                return
            retry_count = row["retry_count"] + 1
            status = (
                OperationStatus.FAILED.value
                if retry_count >= row["max_retries"]
                else OperationStatus.RETRY.value
            )
            conn.execute(
                "UPDATE operations SET status = ?, retry_count = ?, last_error = ? WHERE id = ?",
                (status, retry_count, error, op_id),
            )
            conn.commit()

    def cancel_operation(self, op_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE operations SET status = ? WHERE id = ?",
                (OperationStatus.CANCELLED.value, op_id),
            )
            conn.commit()

    # ---- queries -----------------------------------------------------------

    def get_operation(self, op_id: str) -> Optional[QueuedOperation]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM operations WHERE id = ?", (op_id,)
            ).fetchone()
            return self._row_to_op(row) if row else None

    def get_pending_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM operations WHERE status IN (?, ?)",
                _PENDING_STATUSES,
            ).fetchone()
            return row["c"]

    def get_stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS c FROM operations GROUP BY status"
            ).fetchall()
            by_status = {r["status"]: r["c"] for r in rows}
            total = sum(by_status.values())
            return {
                "total": total,
                "pending": by_status.get("pending", 0) + by_status.get("retry", 0),
                "processing": by_status.get("processing", 0),
                "completed": by_status.get("completed", 0),
                "failed": by_status.get("failed", 0),
                "cancelled": by_status.get("cancelled", 0),
            }

    # ---- processing --------------------------------------------------------

    def process_all(
        self,
        executor: Callable[[QueuedOperation], bool],
        max_operations: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Dequeue and execute operations highest-priority-first.

        ``executor(op) -> bool`` returns True on success. Successful ops are
        marked completed; failures are marked failed (and re-queued as RETRY
        until max_retries). Operations are claimed (PROCESSING) up front so a
        failing op is not re-processed within the same batch.
        """
        claimed: List[QueuedOperation] = []
        while max_operations is None or len(claimed) < max_operations:
            op = self.dequeue()
            if op is None:
                break
            claimed.append(op)

        succeeded = failed = 0
        for op in claimed:
            try:
                ok = executor(op)
            except Exception as e:  # noqa: BLE001
                ok = False
                op.last_error = str(e)
            if ok:
                self.mark_completed(op.id)
                succeeded += 1
            else:
                self.mark_failed(op.id, op.last_error or "executor returned False")
                failed += 1
        return {"processed": len(claimed), "succeeded": succeeded, "failed": failed}

    def start_auto_processing(
        self,
        executor: Callable[[QueuedOperation], bool],
        interval_seconds: float = 30.0,
    ) -> None:
        """Background loop that drains the queue on an interval."""
        if self._processing:
            return
        self._processing = True

        def _loop() -> None:
            import time
            while self._processing:
                try:
                    self.process_all(executor)
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(interval_seconds)

        self._auto_thread = threading.Thread(target=_loop, daemon=True)
        self._auto_thread.start()

    def stop_auto_processing(self) -> None:
        self._processing = False
        if self._auto_thread:
            self._auto_thread.join(timeout=1.0)
            self._auto_thread = None

    # ---- cleanup -----------------------------------------------------------

    def clear_completed(self, older_than_days: int = 7) -> int:
        cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM operations WHERE status = ? AND "
                "(completed_at IS NULL OR completed_at <= ?)",
                (OperationStatus.COMPLETED.value, cutoff),
            )
            conn.commit()
            return cur.rowcount

    def clear_all(self) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM operations")
            conn.commit()
            return cur.rowcount

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _row_to_op(row: sqlite3.Row) -> QueuedOperation:
        def _dt(v):
            return datetime.fromisoformat(v) if v else None

        return QueuedOperation(
            id=row["id"],
            endpoint=row["endpoint"] or "",
            type=OperationType(row["type"]) if row["type"] else OperationType.API_REQUEST,
            method=row["method"] or "POST",
            data=json.loads(row["data"]) if row["data"] else {},
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            priority=OperationPriority(row["priority"]),
            status=OperationStatus(row["status"]),
            max_retries=row["max_retries"],
            retry_count=row["retry_count"],
            last_error=row["last_error"],
            scheduled_at=_dt(row["scheduled_at"]),
            created_at=_dt(row["created_at"]) or datetime.utcnow(),
        )
