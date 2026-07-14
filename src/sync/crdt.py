"""
Conflict-free Replicated Data Types (CRDTs).

These let device and server mutate the same logical records while offline and
then **merge deterministically** — same result regardless of merge order, no
lost updates, no manual conflict resolution.

Implemented:
- ``LWWRegister`` : Last-Writer-Wins single value (scalar fields).
- ``ORSet``       : Observed-Remove Set (tags, attachments, watchers).
- ``LWWMap``      : map of field → LWWRegister (a whole record, e.g. a grievance).

Merge is commutative, associative, and idempotent. Ties on timestamp are broken
by a stable ``actor`` id so two replicas always converge to the same winner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Set, Tuple


def _wins(ts_a: float, actor_a: str, ts_b: float, actor_b: str) -> bool:
    """True if (ts_a, actor_a) beats (ts_b, actor_b). Deterministic tie-break."""
    if ts_a != ts_b:
        return ts_a > ts_b
    return actor_a >= actor_b


@dataclass
class LWWRegister:
    """Last-Writer-Wins register for a single value."""

    value: Any = None
    timestamp: float = 0.0
    actor: str = ""

    def set(self, value: Any, timestamp: float, actor: str) -> "LWWRegister":
        """Apply a write; keeps it only if it wins over the current state."""
        if _wins(timestamp, actor, self.timestamp, self.actor):
            self.value, self.timestamp, self.actor = value, timestamp, actor
        return self

    def merge(self, other: "LWWRegister") -> "LWWRegister":
        if _wins(other.timestamp, other.actor, self.timestamp, self.actor):
            return LWWRegister(other.value, other.timestamp, other.actor)
        return LWWRegister(self.value, self.timestamp, self.actor)

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "timestamp": self.timestamp, "actor": self.actor}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LWWRegister":
        return cls(d.get("value"), float(d.get("timestamp", 0.0)), d.get("actor", ""))


@dataclass
class ORSet:
    """
    Observed-Remove Set.

    Each add creates a unique tag; a remove tombstones exactly the tags it has
    observed. An element is present iff it has at least one live (non-removed)
    tag. This makes concurrent add+remove converge to *add-wins* only for tags
    the remover had not yet seen — the standard OR-Set semantics.
    """

    # element -> set of unique add-tags
    adds: Dict[Any, Set[str]] = field(default_factory=dict)
    # element -> set of removed add-tags (tombstones)
    removes: Dict[Any, Set[str]] = field(default_factory=dict)

    def add(self, element: Any, tag: str) -> "ORSet":
        self.adds.setdefault(element, set()).add(tag)
        return self

    def remove(self, element: Any) -> "ORSet":
        """Tombstone all currently-observed tags for the element."""
        observed = self.adds.get(element, set())
        if observed:
            self.removes.setdefault(element, set()).update(observed)
        return self

    def contains(self, element: Any) -> bool:
        live = self.adds.get(element, set()) - self.removes.get(element, set())
        return len(live) > 0

    def values(self) -> Set[Any]:
        return {e for e in self.adds if self.contains(e)}

    def merge(self, other: "ORSet") -> "ORSet":
        merged = ORSet()
        for src in (self, other):
            for el, tags in src.adds.items():
                merged.adds.setdefault(el, set()).update(tags)
            for el, tags in src.removes.items():
                merged.removes.setdefault(el, set()).update(tags)
        return merged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adds": {str(k): sorted(v) for k, v in self.adds.items()},
            "removes": {str(k): sorted(v) for k, v in self.removes.items()},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ORSet":
        s = cls()
        s.adds = {k: set(v) for k, v in d.get("adds", {}).items()}
        s.removes = {k: set(v) for k, v in d.get("removes", {}).items()}
        return s


@dataclass
class LWWMap:
    """A record as a map of field → LWWRegister (e.g. a grievance row)."""

    fields: Dict[str, LWWRegister] = field(default_factory=dict)

    def set(self, key: str, value: Any, timestamp: float, actor: str) -> "LWWMap":
        reg = self.fields.get(key) or LWWRegister()
        reg.set(value, timestamp, actor)
        self.fields[key] = reg
        return self

    def get(self, key: str, default: Any = None) -> Any:
        reg = self.fields.get(key)
        return reg.value if reg is not None else default

    def to_plain(self) -> Dict[str, Any]:
        """Return the current resolved value of every field."""
        return {k: reg.value for k, reg in self.fields.items()}

    def merge(self, other: "LWWMap") -> "LWWMap":
        out = LWWMap()
        keys = set(self.fields) | set(other.fields)
        for k in keys:
            a = self.fields.get(k)
            b = other.fields.get(k)
            if a is None:
                out.fields[k] = LWWRegister(b.value, b.timestamp, b.actor)
            elif b is None:
                out.fields[k] = LWWRegister(a.value, a.timestamp, a.actor)
            else:
                out.fields[k] = a.merge(b)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"fields": {k: r.to_dict() for k, r in self.fields.items()}}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LWWMap":
        m = cls()
        m.fields = {
            k: LWWRegister.from_dict(v) for k, v in d.get("fields", {}).items()
        }
        return m
