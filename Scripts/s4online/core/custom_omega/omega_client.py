import threading, time, omega, _omega, services
from server.client import Client
from s4online.utils import Logger, Config

log = Logger(__name__)


# Her döngüde first client çekip üzerinden id çekmek optimize olmayan yol gibi gözükebilir.
# Bunu düşünmek gayet normal ancak seyahat yönetiminde karışık id değişecek.
# Optimize yol ile bunu çekmeye çalışırsam bu on_add hooku ile yapılır ancak kod yapısı biraz karmaşık olacaktır.
# Optimize edeceğim ileride, şimdilik todo bırakıyorum.
# TODO: Optimize et
def get_first_client():
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
        self.archived = []

        omega.send = lambda *a, **kw: None

    def process_archived(self, client_id):
        try:
            if not self.archived:
                return

            events = self.archived

            log.info(f"Sending {len(events)} archived events to omega")

            for event in events:
                try:
                    if event["client_id"] != client_id:
                        return
                    ret = _omega.send(client_id, event["msg_id"], event["msg"])
                    log.debug(f"omega send result: {ret}")
                except Exception as e:
                    log.error(f"Omega send error: {e}")

            self.archived = []

        except Exception as e:
            log.error(f"Omega emitter error: {e}")

    def omega_emitter(self):
        try:
            client = get_first_client()
            if client is None:
                # wait for client
                return

            client_id = client.id

            with self.incoming_lock:
                if not self.incoming_commands:
                    return

                events = self.incoming_commands
                self.incoming_commands = []

            log.info(f"Sending {len(events)} events to omega, client_id: {client_id}")

            for event in events:
                try:
                    if event["client_id"] != client_id:
                        # host tarafında yeni client oluşmuş ve onun mesajlarını gönderiyor olabilir.
                        # Yeni oluşan id her zaman eskisinden yüksek sayı olur.
                        # Eğer yeni oluşan bir idye ait ise onu çöpe atamayız.
                        if event["client_id"] > client_id:
                            self.archived.append(event)
                        log.debug(
                            f"omega client id mismatch: net: {event['client_id']} != loc : {client_id}"
                        )
                        continue
                    self.process_archived(client_id)
                    ret = _omega.send(client_id, event["msg_id"], event["msg"])
                    log.debug(f"omega send result: {ret}")
                except Exception as e:
                    log.error(f"Omega send error: {e}")

        except Exception as e:
            log.error(f"Omega emitter error: {e}")

    def add_msg(self, data):
        try:
            top_event = [
                {
                    "client_id": e["client_id"],
                    "msg_id": e["msg_id"],
                    "msg": e["msg"].encode("latin1"),
                }
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
