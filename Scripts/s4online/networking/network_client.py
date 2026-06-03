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
        if self.peer is None:
            return

        # Tek callda en fazla 1 paket gitmeli.
        for _ in range(20):
            msg = self._queue.get_next()
            if msg is None:
                return
            try:
                msg["pattern"]["times"] = time.time()
                if isinstance(msg, dict):
                    payload = rapid.dumps(msg, default=str)
                else:
                    payload = str(msg)

                data = payload
                # ama peer koptuysa veya buffer doluysa exception atabilir.
                self.peer.send(data.encode("latin1"))
                # Buraya geldiysek gönderim başarılı (veya kuyruğa alındı)
                self._queue.confirm_success()

            except RuntimeError as e:
                log.error(f"Peer bağlanamadı, hata: {e}")
                self.peer = None
                return

            except Exception as e:
                # Gönderim başarısız! confirm_success() ÇAĞRILMADI.
                # Paket hala kuyruğun başında bekliyor.
                log.error(
                    f"Gönderim hatası ({self.account_name}), paket saklanıyor: {e}"
                )
                return  # bir sonraki tick'te tekrar dene.
