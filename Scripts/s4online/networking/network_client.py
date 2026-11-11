# bu bir network client olacak
# host tarafında çalışacak sadece
# bağlanan kişiler için oluşturulacak ve tutulacak.
from s4online.utils import Logger, load_pyd
from s4online.base import TransactionQueue
import time

rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")
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
        self._queue.put(msg)

    def process(self):
        """Ağ thread'i tarafından çağrılır."""
        peer = self.peer
        if peer is None or not peer.is_connected:
            return

        # En fazla 20 sıradaki mesajı gönder.
        for _ in range(20):
            msg = self._queue.get_next()
            if msg is None:
                return
            try:
                msg["pattern"]["times"] = time.time()
                payload = rapid.dumps(msg, default=str).encode("latin1")
                peer.send(payload)
                self._queue.confirm_success()

            except RuntimeError as e:
                log.error(f"Peer bağlanamadı, hata: {e}")
                self.peer = None
                return

            except Exception as e:
                log.error(
                    f"Gönderim hatası ({self.account_name}), paket saklanıyor: {e}"
                )
                return
