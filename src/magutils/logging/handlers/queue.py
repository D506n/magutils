import os
import pickle
from logging.handlers import QueueHandler
from multiprocessing import Queue

from ...id import gen_id
from .basic import BaseAsyncHandler


class RawQueueHandler(QueueHandler, BaseAsyncHandler):
    def __init__(self, queue):
        super().__init__(queue)
        self.queue: Queue

    def emit(self, record):
        if e := self.extract_exception(record):
            _id = gen_id()
            msgs = self.format_exception(record, e, _id)
            if not isinstance(msgs, list):
                msgs = list(msgs)
            record.call_stack = msgs
        try:
            self.queue.put(pickle.dumps(record))
        except (pickle.PickleError, AttributeError) as e:
            print(f"Pickle log fail in child {os.getpid()}: {e}")
            self.queue.put(pickle.dumps(self.prepare(record)))