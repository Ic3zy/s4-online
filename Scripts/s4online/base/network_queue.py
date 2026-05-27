from collections import deque
from threading import RLock  # Standart Lock yerine RLock kullandık!
import time


class TransactionQueue:
    def __init__(self):
        self._items = deque()
        self._lock = RLock()  # Deadlock'ı önlemek için kesinlikle RLock olmalı

    def is_valid_item(self, item):
        if isinstance(item, dict):
            pattern = item.get("pattern")
            if pattern is None:
                return False

            types = pattern.get("type")
            if types is None:
                return False

            if "data" in item and isinstance(item["data"], list):
                return True

        return False

    def type_check(self, item1, item2):
        item1_pattern = item1.get("pattern")
        item2_pattern = item2.get("pattern")
        if item1_pattern is None or item2_pattern is None:
            return False
        return item1_pattern.get("type") == item2_pattern.get("type")

    def put(self, item):
        item["pattern"]["time_p"] = time.time()
        with self._lock:
            if not self.is_valid_item(item):
                return

            if not self._items:
                self._items.append(item)
                item["pattern"]["time_p_e"] = time.time()

                return

            last = self._items[-1]

            if self.is_valid_item(last) and self.type_check(item, last):
                last["data"].extend(item["data"])
            else:
                self._items.append(item)
        item["pattern"]["time_p_e"] = time.time()

    def get_next(self):
        with self._lock:
            if not self._items:
                return None
            item = self._items[0]
            item["pattern"]["time_q_e"] = time.time()
            return item

    def confirm_success(self):
        with self._lock:
            if self._items:
                self._items.popleft()

    def queue_merge(self):
        """Kuyruktaki tüm paketlerin 'data' listelerini güvenli bir şekilde
        ilk paketin 'data' listesinde birleştirir.
        """
        pass
        # with self._lock:
        #     if len(self._items) <= 1:
        #         # Kuyrukta 0 veya 1 eleman varsa birleştirmeye gerek yok
        #         return

        #     # 1. İlk paketi (referans) kuyruktan tamamen çıkarıyoruz
        #     referance = self._items.popleft()

        #     # 2. Kuyrukta kalan diğer tüm paketleri sırayla eritiyoruz
        #     while len(self._items) > 0:
        #         sonraki_paket = self._items.popleft()

        #         # Sadece içindeki 'data' listesinin elemanlarını çekip ekliyoruz!
        #         # Paket objesinin kendisini değil, içindeki mesaj listesini birleştiriyoruz.
        #         if "data" in sonraki_paket and isinstance(sonraki_paket["data"], list):
        #             referance["data"].extend(sonraki_paket["data"])
        #         elif "data" in sonraki_paket:
        #             # Eğer tekil nesneyse append yapıyoruz
        #             referance["data"].append(sonraki_paket["data"])

        #     # 3. Birleştirilmiş dev paketi kuyruğun en önüne geri koyuyoruz
        #     self._items.appendleft(referance)

    def __len__(self):
        with self._lock:
            return len(self._items)
