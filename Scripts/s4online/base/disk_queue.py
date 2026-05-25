from queue import Queue, Empty
from s4online.utils import Logger
import threading, json

log = Logger(__name__)

DiskQueue_instance = None


class DiskQueue:

    def __init__(self):
        self.running = True
        self.io_queue = Queue()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    @classmethod
    def instance(cls):
        return DiskQueue_instance

    def _write_file(self, path, data, is_json=False):
        try:
            with open(path, "w", encoding="utf-8") as f:
                if is_json:
                    json.dump(data, f)
                else:
                    f.write(data)
        except Exception as e:
            log.error(f"write file error: {e}")

    def add(self, file_path, data, is_json=False):
        self.io_queue.put((file_path, data, is_json))

    def loop(self):
        while self.running:
            try:
                file_path, data, is_json = self.io_queue.get(timeout=1)
                self._write_file(file_path, data, is_json)
            except Empty:
                continue

    def stop(self):
        self.running = False
        self.thread.join()


DiskQueue_instance = DiskQueue()
