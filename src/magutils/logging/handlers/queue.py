import os
import pickle
from logging.handlers import QueueHandler


class RawQueueHandler(QueueHandler):
    def emit(self, record):
        if not self.queue:
            return
        try:
            pickle.dumps(record)
        except (pickle.PickleError, AttributeError) as e:
            print(f"Pickle log fail in child {os.getpid()}: {e}")
            self.queue.put(self.prepare(record))
        except Exception:
            self.handleError(record)
        else:
            self.queue.put(record)