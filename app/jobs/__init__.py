
from concurrent.futures._base import Future
from concurrent.futures       import ThreadPoolExecutor
from typing                   import Any, Callable, Tuple

import logging

class Jobs(ThreadPoolExecutor):
    def __init__(self, max_workers = None, thread_name_prefix: str = "job", initializer = None, initargs: Tuple[Any, ...] = ...) -> None:
        super().__init__(max_workers, thread_name_prefix, initializer, initargs)

        self.logger = logging.getLogger('anchor')

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        self.logger.info(f'  - Starting job: "{fn.__name__}"')
        return super().submit(fn, *args, **kwargs)
