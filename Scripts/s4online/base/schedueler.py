import heapq
import threading
import time


class CustomBlockingQueue:
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

        # Eğer iki görev aynı salisede tetiklenecek olursa, Python dict nesnelerini
        # birbiriyle kıyaslayamaz ve TypeError fırlatır. Bunu engellemek için benzersiz sayaç çakıyoruz
        self._counter = 0

    def put(self, item):
        """Kuyruğa mermiyi bırakır ve zaman sıralamasına göre en doğru konuma dizer!"""
        with self._condition:
            if isinstance(item, dict) and "called_time" in item:
                called_time = item.get("called_time")
            else:
                # Zaman yoksa hemen çalıştır
                called_time = time.time()

            self._counter += 1

            heapq.heappush(self._queue, (called_time, self._counter, item))

            # İçeride wait ile uyuyan thread'i dürtüyoruz.
            self._condition.notify_all()

    def check(self, top_item):
        """En yakın paketin zamanını milisaniyelik ölçer."""
        called_time, _, item = top_item
        now = time.time()
        if called_time <= now:
            return True, 0
        else:
            return False, called_time - now

    def get(self, block=True, timeout=None):
        """Zaman ayarlı, katıksız paralel blocking get mekanizması!"""
        with self._condition:
            while True:
                if not self._queue:
                    if not block:
                        return None
                    if not self._condition.wait(timeout=timeout):
                        return None
                    continue

                # kuyrukta eleman var (heap sayesinde [0] daima en yakın zamanlı olandır)
                is_ready, time_to_wait = self.check(self._queue[0])

                if is_ready:
                    # Zamanı gelmiş ise heap'ten söküp sadece asıl item'ı dönüyoruz
                    _, _, item = heapq.heappop(self._queue)
                    return item

                # 3. En yakın paketin bile zamanı henüz gelmemiş
                if not block:
                    return None

                # Eğer bu esnada daha da yakın zamanlı (örn: 1 saniye sonra çalışacak) taze bir paket
                # put() edilirse, put'un içindeki notify_all() bu uykuyu anında BÖLER,
                # döngü başa döner ve o yeni acil paketi [0]da görüp süreyi ona göre günceller
                self._condition.wait(timeout=time_to_wait)


class Task_Schedueler:
    def __init__(self):
        self.queue = CustomBlockingQueue()
        self.thread = threading.Thread(target=self.tick_loop, daemon=True)
        self.thread.start()

    def on_tick(self):
        command_info = self.queue.get()
        if command_info:
            command = command_info.get("command")
            args = command_info.get("args")
            kwargs = command_info.get("kwargs")
            try:
                command(*args, **kwargs)
            except Exception as e:
                print(e)

    def tick_loop(self):
        while True:
            self.on_tick()

    def add(self, item: dict):
        self.queue.put(item)


TaskSchedueler = Task_Schedueler()

# start = time.time()


# def commands(msg):
#     print(f"{msg}, Geçen Süre: {time.time() - start:.2f} saniye")

# TEST
# asyncio.add(
#     {
#         "command": commands,
#         "args": ["5 saniyelik görev"],
#         "kwargs": {},
#         "called_time": time.time() + 10,
#     }
# )
# time.sleep(5)
# asyncio.add(
#     {
#         "command": commands,
#         "args": ["2 saniyelik görev"],
#         "kwargs": {},
#         "called_time": time.time() + 2,
#     }
# )

# while True:
#     time.sleep(0.1)
