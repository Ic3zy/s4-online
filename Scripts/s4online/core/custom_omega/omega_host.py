import threading, time, omega, _omega
from s4online.utils import Logger
from s4online.base import Ctx
import distributor.system
import time

log = Logger(__name__)
Thread = threading.Thread
MAX_CHUNK = 128


class Omega_host:
    def __init__(self, networkServer):
        log.info("omega kurulacak...")
        self.networkServer = networkServer
        # 15 Hz tick
        self.local_client_id = 0

        omega.send = self.custom_omega

        log.log("omega kuruldu")

    def custom_omega(self, client_id, msg_id, msg_bytes, global_distributor=False):
        # Host'taki kendi local client
        # Oyuncu clientleri 10000 üzerinde oluyor
        if client_id < 10000:
            if self.local_client_id != client_id:
                self.local_client_id = client_id
            _omega.send(client_id, msg_id, msg_bytes)

            if Ctx.get("game_load") or global_distributor:
                return
            else:
                client_id = "all"

        # heartbeat byte filtreliyorum
        if (
            msg_bytes
            == b"\n\x14\n\x06\n\x04\x08\x00\x10\x00\x12\n\n\x08\x08\x8b\x04%\x00\x00\x00\x00"
        ):
            return

        try:
            if self.local_client_id == 0:
                return log.error("custom_omega HOST wait for client")

            chunk = {
                "client_id": self.local_client_id,
                "msg_id": msg_id,
                "msg": msg_bytes.decode("latin1"),
            }

            msg = {
                "pattern": {"type": "omega", "time": time.time()},
                "data": [chunk],
            }
            self.send_message(msg, client_id)
        except Exception as e:
            log.error(f"custom_omega error: {e}")

    def send_message(self, message, client_id):
        if client_id == "all":
            self.networkServer.send_message_all_clients(message)
        else:
            self.networkServer.send_message_from_client_id(client_id, message)

    def close(self):
        omega.send = _omega.send
