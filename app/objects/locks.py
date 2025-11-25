
from collections.abc import MutableMapping as _MutableMapping
from contextlib import contextmanager
from threading import RLock
from typing import (
    MutableMapping,
    Iterator,
    Optional,
    Iterable,
    TypeVar,
    Tuple,
    List,
    Any,
    Set
)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

class ReadWriteLock:
    def __init__(self):
        self.write_lock = RLock()
        self.read_lock = RLock()
        self.readers = 0

    def acquire_read(self):
        """Acquire a read lock."""
        with self.read_lock:
            self.readers += 1
            if self.readers == 1:
                self.write_lock.acquire()

    def release_read(self):
        """Release a read lock."""
        with self.read_lock:
            assert self.readers > 0, "Attempted to release read lock without acquiring it"
            self.readers -= 1
            if self.readers == 0:
                self.write_lock.release()

    def acquire_write(self):
        """Acquire a write lock."""
        self.write_lock.acquire()

    def release_write(self):
        """Release a write lock."""
        self.write_lock.release()

    @contextmanager
    def read_context(self):
        """Context manager for read lock."""
        try:
            self.acquire_read()
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_context(self):
        """Context manager for write lock."""
        try:
            self.acquire_write()
            yield
        finally:
            self.release_write()

class LockedSet(Set[T]):
    """A set that is thread-safe for concurrent read and write operations."""

    def __init__(self) -> None:
        self.set: Set[T] = set()
        self.lock = ReadWriteLock()

    def __iter__(self) -> Iterable[T]:
        return iter(self.snapshot())

    def __len__(self) -> int:
        return len(self.snapshot())

    def __contains__(self, item: T) -> bool:
        return item in self.snapshot()

    def snapshot(self) -> Set[T]:
        """Returns a snapshot of the set."""
        with self.lock.read_context():
            items = set(self.set)
        return items

    def add(self, item: T) -> None:
        with self.lock.write_context():
            self.set.add(item)

    def update(self, *args, **kwargs) -> None:
        with self.lock.write_context():
            self.set.update(*args, **kwargs)

    def remove(self, item: T) -> None:
        with self.lock.write_context():
            self.set.remove(item)

    def discard(self, item: T) -> None:
        with self.lock.write_context():
            self.set.discard(item)

class LockedList(List[T]):
    """A list that is thread-safe for concurrent read and write operations."""

    def __init__(self) -> None:
        super().__init__()
        self.lock = ReadWriteLock()

    def __getitem__(self, index) -> T:
        with self.lock.read_context():
            return super().__getitem__(index)

    def __setitem__(self, index: int, value: T):
        with self.lock.write_context():
            super().__setitem__(index, value)

    def __delitem__(self, index: int):
        with self.lock.write_context():
            super().__delitem__(index)

    def __len__(self) -> int:
        with self.lock.read_context():
            return super().__len__()

    def __contains__(self, item: T) -> bool:
        with self.lock.read_context():
            return super().__contains__(item)

    def __iter__(self) -> Iterable[T]:
        with self.lock.read_context():
            return super().__iter__()

    def append(self, item: T) -> None:
        with self.lock.write_context():
            super().append(item)

    def extend(self, iterable: Iterable[T]) -> None:
        with self.lock.write_context():
            super().extend(iterable)

    def remove(self, item: T) -> None:
        with self.lock.write_context():
            super().remove(item)

    def discard(self, item: T) -> None:
        """Remove an item if it exists, without raising an error."""
        with self.lock.write_context():
            try:
                super().remove(item)
            except ValueError:
                pass

class LockedDict(_MutableMapping, MutableMapping[K, V]):
    """A dict that is thread-safe for concurrent read and write operations."""

    def __init__(self, *args, **kwargs):
        self.dict: dict[K, V] = dict(*args, **kwargs)
        self.lock = ReadWriteLock()

    def __getitem__(self, key: K) -> V:
        with self.lock.read_context():
            return self.dict[key]

    def __setitem__(self, key: K, value: V) -> None:
        with self.lock.write_context():
            self.dict[key] = value

    def __delitem__(self, key: K) -> None:
        with self.lock.write_context():
            del self.dict[key]

    def __len__(self) -> int:
        with self.lock.read_context():
            return len(self.dict)

    def __iter__(self) -> Iterator[K]:
        with self.lock.read_context():
            snapshot = list(self.dict.keys())
        return iter(snapshot)

    def __contains__(self, key: object) -> bool:
        with self.lock.read_context():
            return key in self.dict

    def __repr__(self) -> str:
        with self.lock.read_context():
            return f"{self.__class__.__name__}({self.dict!r})"

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        with self.lock.read_context():
            return self.dict.get(key, default)

    def pop(self, key: K, default: Any = None) -> Any:
        with self.lock.write_context():
            return self.dict.pop(key, default)

    def popitem(self) -> Tuple[K, V]:
        with self.lock.write_context():
            return self.dict.popitem()

    def clear(self) -> None:
        with self.lock.write_context():
            self.dict.clear()

    def update(self, *args, **kwargs) -> None:
        with self.lock.write_context():
            self.dict.update(*args, **kwargs)

    def keys(self) -> Iterable[K]:
        with self.lock.read_context():
            snapshot = list(self.dict.keys())
        return iter(snapshot)

    def values(self) -> Iterable[V]:
        with self.lock.read_context():
            snapshot = list(self.dict.values())
        return iter(snapshot)

    def items(self) -> Iterable[Tuple[K, V]]:
        with self.lock.read_context():
            snapshot = list(self.dict.items())
        return iter(snapshot)

    def setdefault(self, key: K, default: V = None) -> V:
        with self.lock.write_context():
            return self.dict.setdefault(key, default)
