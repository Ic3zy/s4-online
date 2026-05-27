from threading import Thread
from s4online.utils import Logger, load_pyd
from .ev import ev
import time

rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")
enet = load_pyd("enet", "enet.cp37-win_amd64.pyd")
log = Logger(__name__)


class Listener:
    """
    Tek bir listener; host değişse bile (reconnect) aynı thread çalışmaya devam eder.
    """

    def __init__(self, server):
        self.server = server
        self.tick_interval = 1000 / server.net_tick
        self.lock = server.lock
        self.running = True

    def on_tick(self):
        self.listen_loop()

    def listen_enet(self):
        # with self.lock:
        host = self.server.current_host
        if host is not None:
            data = host.service(self.tick_interval)
        else:
            data = None
        if data is not None:
            try:
                obj = rapid.loads(data.packet.data.decode("latin1"))
            except:
                obj = {}

        return (data, obj)

    def listen_loop(self):
        try:
            data, obj = self.listen_enet()

            if data.type == enet.EVENT_TYPE_RECEIVE:
                log.debug("veri geldi")
                if obj.get("type") == "auth":
                    self.server.accept_thread(
                        data.peer,
                        obj.get("account_name"),
                        reconnect=obj.get("reconnect"),
                    )
                    return

                pattern = obj.get("pattern")
                if pattern is None:
                    log.info(f"veri kısmında hata oluştu! Pattern yok: {obj}")
                    return

                ev.emit(pattern.get("type"), obj, log.debug)

            elif data.type == enet.EVENT_TYPE_DISCONNECT:
                log.info("client disconnected")
                if self.server.is_client:
                    self.server.create_client_socket(re_connect=True)
                    return

        except Exception as e:
            log.error("Recv error:", e)
            import traceback

            log.error(traceback.format_exc())
            return
