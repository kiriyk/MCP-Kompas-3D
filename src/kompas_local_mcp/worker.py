"""A single serial worker; all COM objects stay on this thread."""
from concurrent.futures import Future, TimeoutError
import queue
import threading

class SerialWorker:
    def __init__(self,factory,timeout=60):
        self.factory=factory;self.timeout=timeout;self.queue=queue.Queue()
        self.lock=threading.Lock();self.pending=None;self.closed=False
        self.thread=threading.Thread(target=self._run,name='kompas-sta',daemon=True)
        self.thread.start()
    def _run(self):
        try:adapter=self.factory()
        except Exception as exc:adapter=None;init_error=exc
        while True:
            item=self.queue.get()
            if item is None:break
            future,function=item
            if not future.set_running_or_notify_cancel():continue
            try:
                if adapter is None:raise init_error
                future.set_result(function(adapter))
            except Exception as exc:future.set_exception(exc)
        if adapter is not None and hasattr(adapter,'shutdown'):adapter.shutdown()
    def call(self,function):
        with self.lock:
            if self.closed:raise RuntimeError('Worker closed')
            if self.pending and not self.pending.done():raise RuntimeError('Worker busy; previous operation may still be running')
            future=Future();self.pending=future;self.queue.put((future,function))
        try:return future.result(timeout=self.timeout)
        except TimeoutError as exc:raise RuntimeError('Operation timed out; outcome unknown. Inspect state before retrying.') from exc
    def close(self):
        with self.lock:
            if not self.closed:self.closed=True;self.queue.put(None)
        self.thread.join(timeout=5)
