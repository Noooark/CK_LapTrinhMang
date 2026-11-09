"""Run sequential requests and return results to Tk via its own polling loop."""
import logging
import queue
import threading


logger = logging.getLogger(__name__)


class RequestWorker:
    def __init__(self, connection, token):
        self.connection = connection
        self.token = token
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        self.stopped = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def request(self, command, data, callback, attempts=1):
        self.jobs.put((command, data, callback, attempts))

    def dispatch(self):
        while not self.stopped.is_set():
            try:
                callback, response = self.results.get_nowait()
            except queue.Empty:
                break
            callback(response)

    def stop(self):
        if not self.stopped.is_set():
            self.stopped.set()
            for pending in (self.jobs, self.results):
                while True:
                    try:
                        pending.get_nowait()
                    except queue.Empty:
                        break
            self.jobs.put(None)

    def _run(self):
        while not self.stopped.is_set():
            job = self.jobs.get()
            if job is None or self.stopped.is_set():
                break
            command, data, callback, attempts = job
            del job
            if callable(data):
                # Evidence encoding is deferred to this worker and performed only once.
                data = data()
                if data is None or self.stopped.is_set():
                    if not self.stopped.is_set():
                        self.results.put((callback, None))
                    continue
            for attempt in range(attempts):
                response = self.connection.send_request(command, data=data, token=self.token)
                if not (response.get("transport_error") or response.get("retryable")):
                    break
                logger.warning("%s retryable failure (%d/%d)", command, attempt + 1, attempts)
                if attempt + 1 < attempts and self.stopped.wait(0.5):
                    return
            if not self.stopped.is_set():
                self.results.put((callback, response))
            del data, response
