import threading, time, omega, _omega
from s4online.utils import Logger
from s4online.base import Ctx
log = Logger(__name__)
Thread = threading.Thread
MAX_CHUNK = 128


class Omega_host:
    def __init__(self, enetServer=None):
        if enetServer is None:
            raise Exception("enetServer is None")
        log.info("omega kurulacak...")
        self.enetServer = enetServer
        self.outgoing = []
        self.outgoing_lock = threading.Lock()
        self.runing = True
        # 15 Hz tick
        self.tick_rate = 5
        self.tick_interval = 1 / self.tick_rate
        self.min_sleep_time = 0.001  # cpu korumak için maksimum 1000 hz
        omega.send = self.custom_omega
        Thread(target=self.process, daemon=True).start()

        log.log("omega kuruldu")

    def custom_omega(self, client_id, msg_id, msg_bytes, global_distributor=False):

        # Host'taki kendi local client
        # Oyuncu clientleri 100000 üzerinde oluyor
        if client_id < 100000:
            _omega.send(client_id, msg_id, msg_bytes)

            if Ctx.get('game_load') or global_distributor:
                return
            else:
                client_id = "all"

        # heartbeat byte filtreliyorum
        if (
            msg_bytes
            == b"\n\x14\n\x06\n\x04\x08\x00\x10\x00\x12\n\n\x08\x08\x8b\x04%\x00\x00\x00\x00"
        ):
            return

        with self.outgoing_lock:
            self.outgoing.append({"client_id": client_id, "msg_id": msg_id, "msg": msg_bytes.decode("latin1")})


    def send_outgoing_list(self):
        if len(self.enetServer) == 0:
            # wait for client
            return
        with self.outgoing_lock:
            outgoing = self.outgoing
            self.outgoing = []

        if not outgoing:
            return

        # chunking
        for chunk in outgoing:
            client_id = chunk["client_id"]
            if client_id is None:
                log.error("client id is none")
                continue
            
            data = {"pattern": {"type": "omega"}, "data": [chunk]}
            if client_id == "all":
                self.enetServer.send_message_all_clients(data)
            else:
                self.enetServer.send_message_from_client_id(client_id, data)

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
                self.on_tick()

            time.sleep(self.tick_interval)

    def close(self):
        omega.send = _omega.send
        self.runing = False
