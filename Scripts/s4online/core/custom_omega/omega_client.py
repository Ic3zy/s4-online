import threading, time, omega, _omega
from s4online.utils import Logger, Config
import time

log = Logger(__name__)

Thread = threading.Thread

_first_client_id = None


def set_first_client():
    global _first_client_id
    try:
        import services

        if services is None or hasattr(services, "client_manager") is False:
            return None
        first = services.client_manager().get_first_client()
        if first:
            _first_client_id = first.id
            log.info(f"first client id: {_first_client_id}")
            Config.manager_load = True
        else:
            log.warning("first client not found")
    except Exception as e:
        log.error(f"set_first_client error: {e}")


class Omega_client:
    def __init__(self):
        self.incoming_commands = []
        self.incoming_lock = threading.Lock()

        self.tick_rate = 15
        self.tick_interval = 1 / self.tick_rate

        self.running = True

        omega.send = lambda *a, **kw: None

        self.tick_start()

    def omega_emitter(self):
        try:

            if _first_client_id is None:
                set_first_client()
            if _first_client_id is None:
                # wait for client
                return
            with self.incoming_lock:
                if not self.incoming_commands:
                    return
                events = self.incoming_commands[:]
                self.incoming_commands.clear()

            client_id = _first_client_id
            log.info(f"Sending {len(events)} events to omega, client_id: {client_id}")
            for event in events:
                try:
                    ret = _omega.send(3, event["msg_id"], event["msg"])
                    log.debug(f"omega send result: {ret}")
                except Exception as e:
                    log.error(f"Omega send error: {e}")
        except Exception as e:
            log.error(f"Omega emitter error: {e}")

    def add_msg(self, data):
        try:
            top_event = [
                {"msg_id": e["msg_id"], "msg": e["msg"].encode("latin1")}
                for e in data.get("data", [])
            ]
            pattern = data.get("pattern")
            if pattern is not None:
                times = data.get("time")
                if times is not None:
                    log.debug(f"pattern: {pattern} times: {times - time.time()}")

        except Exception as e:
            log.error(f"Add msg parse error: {e}")
            return

        if top_event:
            with self.incoming_lock:
                self.incoming_commands.extend(top_event)

    def on_tick(self):
        # self.omega_emitter()
        pass

    def tick(self):
        tick_count = 0
        while self.running:
            tick_count += 1

            start = time.time()
            self.on_tick()
            elapsed = time.time() - start

            if tick_count >= 1000:  # 10 saniyede bir avarage basıyorum
                log.debug(f"tick average: {elapsed}")
                tick_count = 0

            time.sleep(self.tick_interval)

    def tick_start(self):
        Thread(target=self.tick, daemon=True).start()

    def close(self):
        self.running = False
        omega.send = _omega.send
