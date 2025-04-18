
from contextlib import contextmanager
from typing import TypeVar, Set
from threading import Lock

class ReadWriteLock:
    def __init__(self):
        self.write_lock = Lock()
        self.read_lock = Lock()
        self.readers = 0

    def acquire_read(self):
        """Acquire a read lock."""
        self.read_lock.acquire()
        self.readers += 1
        if self.readers == 1:
            self.write_lock.acquire()
        self.read_lock.release()

    def release_read(self):
        """Release a read lock."""
        assert self.readers > 0
        self.read_lock.acquire()
        self.readers -= 1
        if self.readers == 0:
            self.write_lock.release()
        self.read_lock.release()

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

T = TypeVar('T')

class LockedSet(Set[T]):
    """A set that is thread-safe for concurrent read and write operations."""

    def __init__(self):
        self.set = set()
        self.lock = ReadWriteLock()

    def __iter__(self):
        with self.lock.read_context():
            return iter(self.set)

    def __len__(self) -> int:
        with self.lock.read_context():
            return len(self.set)

    def __contains__(self, item: T) -> bool:
        with self.lock.read_context():
            return item in self.set

    def add(self, item: T) -> None:
        with self.lock.write_context():
            self.set.add(item)

    def update(self, *args, **kwargs) -> None:
        with self.lock.write_context():
            self.set.update(*args, **kwargs)

    def remove(self, item: T) -> None:
        with self.lock.write_context():
            try:
                self.set.remove(item)
            except KeyError:
                pass

class LockedList(list):
    """A list that is thread-safe for concurrent read and write operations."""

    def __init__(self):
        super().__init__()
        self.lock = ReadWriteLock()

    def __getitem__(self, index):
        with self.lock.read_context():
            return super().__getitem__(index)

    def __setitem__(self, index, value):
        with self.lock.write_context():
            super().__setitem__(index, value)

    def __delitem__(self, index):
        with self.lock.write_context():
            super().__delitem__(index)

    def __len__(self) -> int:
        with self.lock.read_context():
            return super().__len__()

    def __contains__(self, item) -> bool:
        with self.lock.read_context():
            return super().__contains__(item)

    def __iter__(self):
        with self.lock.read_context():
            return super().__iter__()

    def append(self, item) -> None:
        with self.lock.write_context():
            super().append(item)

    def extend(self, iterable) -> None:
        with self.lock.write_context():
            super().extend(iterable)

    def remove(self, item) -> None:
        with self.lock.write_context():
            try:
                super().remove(item)
            except ValueError:
                pass
