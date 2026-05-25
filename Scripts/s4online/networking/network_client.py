# bu bir network client olacak
# host tarafında çalışacak sadece
# bağlanan kişiler için oluşturulacak ve tutulacak.
from s4online.utils import Logger, load_pyd
from s4online.base import TransactionQueue
import json
enet = load_pyd("enet", "enet.cp37-win_amd64.pyd")

log = Logger(__name__)

class Network_client:
    def __init__(self, g_client, account_name):
        self.peer = None
        self.account_name = account_name
        self._g_client = g_client
        self._queue = TransactionQueue()

    def set_peer(self, peer):
        self.peer = peer

    def send_message(self, msg):
        """Oyun thread'i sadece bunu çağırır: Çok hızlı ve güvenli."""
        log.info("calling sendmessage")
        self._queue.put(msg)

    def process_queue(self):
        """Ağ thread'i tarafından çağrılır."""
        if self.peer is None:
            return
        if len(self._queue) > 10:
            log.warning(f"Queue size too big: {len(self._queue)}")
            try:
                self._queue.queue_merge()
            except Exception as e:
                log.error(f"Queue merge error: {e}")
        # Kuyruk boşalana kadar veya bir hata alana kadar devam et
        while True:
            msg = self._queue.get_next()
            if msg is None:
                break
            log.info(f"Sending message, while")
            try:
                if isinstance(msg, dict):
                    payload = json.dumps(msg, separators=(",", ":"), default=str)
                else:
                    payload = str(msg)
                encoded = payload.encode("latin1")
                data = enet.Packet(encoded, enet.PACKET_FLAG_RELIABLE)
                # ENet'e gönderim yapıyoruz
                # enet.peer.send genellikle paket kopyalandığında hata vermez 
                # ama peer koptuysa veya buffer doluysa exception atabilir.
                self.peer.send(0, data)
                
                # Buraya geldiysek gönderim başarılı (veya kuyruğa alındı)
                self._queue.confirm_success()
                
            except Exception as e:
                # Gönderim başarısız! confirm_success() ÇAĞRILMADI.
                # Paket hala kuyruğun başında bekliyor.
                log.error(f"Gönderim hatası ({self.account_name}), paket saklanıyor: {e}")
                break # Döngüyü kır, bir sonraki tick'te tekrar dene.