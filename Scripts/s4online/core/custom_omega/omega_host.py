import threading, time, omega, _omega
from s4online.utils import Logger
from s4online.base import Ctx
import distributor.system
import time

log = Logger(__name__)
Thread = threading.Thread
MAX_CHUNK = 128


class Omega_host:
    def __init__(self, enetServer):
        log.info("omega kurulacak...")
        self.enetServer = enetServer
        self.outgoing = {}
        self.outgoing_lock = threading.Lock()
        self.runing = True
        # 15 Hz tick
        self.tick_rate = 15
        self.tick_interval = 1 / self.tick_rate
        self.min_sleep_time = 0.001  # cpu korumak için maksimum 1000 hz
        self.local_client_id = 0
        omega.send = self.custom_omega
        Thread(target=self.process, daemon=True).start()

        log.log("omega kuruldu")

    def custom_omega(self, client_id, msg_id, msg_bytes, global_distributor=False):
        # Host'taki kendi local client
        # Oyuncu clientleri 100000 üzerinde oluyor
        if client_id < 100000:
            if self.local_client_id != client_id:
                self.local_client_id = client_id
            log.debug(f"sending ops local client id: {self.local_client_id}")
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
                # wait for client
                return log.error("custom_omega HOST wait for client")

            chunk = {
                "client_id": self.local_client_id,
                "msg_id": msg_id,
                "msg": msg_bytes.decode("latin1"),
            }

            # if isinstance(self.outgoing.get(client_id), dict):
            #     self.outgoing[client_id]["data"].append(chunk)
            #     return

            msg = {
                "pattern": {"type": "omega", "time": time.time()},
                "data": [chunk],
            }
            self.send_message(msg, client_id)
        except Exception as e:
            log.error(f"custom_omega error: {e}")

    def send_message(self, message, client_id):
        if client_id == "all":
            self.enetServer.send_message_all_clients(message)
        else:
            self.enetServer.send_message_from_client_id(client_id, message)

        # self.enetServer.on_tick()

    def send_outgoing_list(self):
        if len(self.enetServer) == 0:
            # wait for client
            return
        with self.outgoing_lock:
            outgoing = self.outgoing
            self.outgoing = {}

        if not outgoing:
            return

        # chunking
        for client_id, outgoing_list in outgoing.items():
            if client_id == "all":
                self.enetServer.send_message_all_clients(outgoing_list)
            else:
                self.enetServer.send_message_from_client_id(client_id, outgoing_list)

    def on_tick(self):
        self.send_outgoing_list()

    def process(self):
        tick_count = 1
        while self.runing:
            tick_count += 1
            if tick_count > 1000:
                start = time.time()
                self.on_tick()
                elapsed = time.time() - start
                log.debug(f"tick avarage: {elapsed}")
                tick_count = 1
            else:
                try:
                    self.on_tick()
                except Exception as e:
                    log.error(f"on_tick error: {e}")

            time.sleep(self.tick_interval)

    def close(self):
        omega.send = _omega.send
        self.runing = False
