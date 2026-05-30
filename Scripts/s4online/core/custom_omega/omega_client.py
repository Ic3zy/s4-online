import threading, time, omega, _omega, services
from server.client import Client
from s4online.utils import Logger, Config

log = Logger(__name__)


def get_first_client() -> Client | None:
    try:
        if services is None or hasattr(services, "client_manager") is False:
            return None

        first = services.client_manager().get_first_client()
        if first is None:
            return None

        return first

    except Exception as e:
        log.error(f"set_first_client error: {e}")


class Omega_client:
    def __init__(self):
        self.incoming_commands = []
        self.incoming_lock = threading.Lock()

        omega.send = lambda *a, **kw: None

    def omega_emitter(self):
        try:
            client_id = get_first_client()
            if client_id is None:
                # wait for client
                return

            with self.incoming_lock:
                if not self.incoming_commands:
                    return

                events = self.incoming_commands
                self.incoming_commands = []

            log.info(f"Sending {len(events)} events to omega, client_id: {client_id}")

            for event in events:
                try:
                    ret = _omega.send(client_id, event["msg_id"], event["msg"])
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
                times = pattern.get("time")
                if times is not None:
                    log.debug(f"pattern: {pattern} times: {times - time.time()}")

        except Exception as e:
            log.error(f"Add msg parse error: {e}")
            return

        if top_event:
            with self.incoming_lock:
                self.incoming_commands.extend(top_event)
