"""
Tests for CRDT primitives and the bidirectional sync engine.

Proves the core offline-sync guarantees: commutative/idempotent merge,
add-wins set semantics, deterministic conflict resolution, guaranteed
convergence of two replicas, and officer-priority operation replay.
"""

from src.sync.crdt import LWWMap, LWWRegister, ORSet
from src.sync.operation_queue import OperationQueue, OperationType
from src.sync.sync_engine import SyncEngine


# ---- LWWRegister -----------------------------------------------------------


def test_lww_latest_timestamp_wins():
    r = LWWRegister()
    r.set("old", 100.0, "device")
    r.set("new", 200.0, "server")
    assert r.value == "new"


def test_lww_older_write_ignored():
    r = LWWRegister()
    r.set("new", 200.0, "server")
    r.set("old", 100.0, "device")  # arrives late but older
    assert r.value == "new"


def test_lww_merge_commutative():
    a = LWWRegister("A", 150.0, "x")
    b = LWWRegister("B", 160.0, "y")
    assert a.merge(b).value == b.merge(a).value == "B"


def test_lww_tie_broken_deterministically():
    a = LWWRegister("A", 100.0, "actor_a")
    b = LWWRegister("B", 100.0, "actor_b")
    # Same timestamp → higher actor id wins, both orders agree.
    assert a.merge(b).value == b.merge(a).value


# ---- ORSet -----------------------------------------------------------------


def test_orset_add_and_contains():
    s = ORSet()
    s.add("water-photo.jpg", "t1")
    assert s.contains("water-photo.jpg")


def test_orset_remove():
    s = ORSet()
    s.add("x", "t1")
    s.remove("x")
    assert not s.contains("x")


def test_orset_add_wins_on_concurrent_add_remove():
    # Replica A removes an element it has seen; replica B concurrently re-adds
    # with a NEW tag B's remove never observed → element survives (add-wins).
    a = ORSet(); a.add("tag", "t1")
    b = a.merge(ORSet())  # b observes t1
    a.remove("tag")               # a tombstones t1
    b.add("tag", "t2")            # b adds a fresh, unobserved tag
    merged = a.merge(b)
    assert merged.contains("tag")


def test_orset_merge_idempotent():
    s = ORSet(); s.add("e", "t1")
    assert s.merge(s).values() == {"e"}


# ---- LWWMap ----------------------------------------------------------------


def test_lwwmap_field_merge():
    a = LWWMap(); a.set("status", "pending", 100.0, "device")
    b = LWWMap(); b.set("status", "resolved", 200.0, "officer")
    merged = a.merge(b)
    assert merged.get("status") == "resolved"


# ---- SyncEngine ------------------------------------------------------------


def test_two_replicas_converge():
    device = SyncEngine("device")
    server = SyncEngine("server")
    device.set_field("GR-1", "title", "Water shortage", 100.0)
    server.set_field("GR-1", "status", "assigned", 150.0)
    device.set_field("GR-2", "title", "Road broken", 120.0)

    device.sync(server)
    # Both replicas hold identical, fully-merged state.
    assert device.record("GR-1") == server.record("GR-1")
    assert device.record("GR-2") == server.record("GR-2")
    assert device.record("GR-1")["title"] == "Water shortage"
    assert device.record("GR-1")["status"] == "assigned"


def test_conflicting_field_resolved_by_timestamp():
    device = SyncEngine("device")
    server = SyncEngine("server")
    # Same field written on both sides — later write must win.
    device.set_field("GR-9", "status", "in_progress", 100.0)
    server.set_field("GR-9", "status", "resolved", 300.0)
    res = device.sync(server)
    assert device.record("GR-9")["status"] == "resolved"
    assert server.record("GR-9")["status"] == "resolved"
    assert res.conflicts_resolved >= 1


def test_officer_ops_replayed_before_queries(tmp_path):
    q = OperationQueue(db_path=str(tmp_path / "q.db"))
    engine = SyncEngine("device", queue=q)
    # Queue a low-priority cached query first, then a high-priority grievance.
    engine.queue_operation("/api/v1/query", OperationType.SCHEME_QUERY, {"q": "pmkisan"})
    engine.queue_operation(
        "/api/v1/grievances", OperationType.GRIEVANCE_SUBMIT, {"title": "urgent"}
    )
    order = []

    def pusher(op):
        order.append(op.type)
        return True

    server = SyncEngine("server")
    res = engine.sync(server, pusher=pusher)
    # Grievance submit (HIGH) is replayed before the cached query (LOW).
    assert order[0] == OperationType.GRIEVANCE_SUBMIT
    assert order[1] == OperationType.SCHEME_QUERY
    assert res.pushed == 2
