from collections import deque
from threading import RLock # Standart Lock yerine RLock kullandık!

class TransactionQueue:
    def __init__(self):
        self._items = deque()
        self._lock = RLock() # Deadlock'ı önlemek için kesinlikle RLock olmalı

    def put(self, item):
        with self._lock:
            self._items.append(item)

    def get_next(self):
        with self._lock:
            if not self._items:
                return None
            return self._items[0]

    def confirm_success(self):
        with self._lock:
            if self._items:
                self._items.popleft()

    def queue_merge(self):
        """Kuyruktaki tüm paketlerin 'data' listelerini güvenli bir şekilde 
        ilk paketin 'data' listesinde birleştirir.
        """
        with self._lock:
            if len(self._items) <= 1:
                # Kuyrukta 0 veya 1 eleman varsa birleştirmeye gerek yok
                return

            # 1. İlk paketi (referans) kuyruktan tamamen çıkarıyoruz
            referance = self._items.popleft()
            
            # 2. Kuyrukta kalan diğer tüm paketleri sırayla eritiyoruz
            while len(self._items) > 0:
                sonraki_paket = self._items.popleft()
                
                # Sadece içindeki 'data' listesinin elemanlarını çekip ekliyoruz!
                # Paket objesinin kendisini değil, içindeki mesaj listesini birleştiriyoruz.
                if "data" in sonraki_paket and isinstance(sonraki_paket["data"], list):
                    referance["data"].extend(sonraki_paket["data"])
                elif "data" in sonraki_paket:
                    # Eğer tekil nesneyse append yapıyoruz
                    referance["data"].append(sonraki_paket["data"])

            # 3. Birleştirilmiş dev paketi kuyruğun en önüne geri koyuyoruz
            self._items.appendleft(referance)
            
    def __len__(self):
        with self._lock:
            return len(self._items)