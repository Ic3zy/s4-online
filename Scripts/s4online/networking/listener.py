from threading import Thread
from s4online.utils import Logger, load_pyd
from .ev import ev
import time

log = Logger(__name__)

rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")


class Listener:
    """
    Tek bir listener; host değişse bile (reconnect) aynı thread çalışmaya devam eder.
    """

    def __init__(self, server):
        self.server = server
        self.tick_interval = 1000 / server.net_tick
        self.running = True
        self.thread = Thread(target=self.listen_loop, daemon=True)
        self.thread.start()

    def on_tick(self):
        self.listen_loop()

    def listen_enet(self):
        event = self.server.engine.poll_events()
        data = event.get("payload")

        obj = {}
        if data is not None:
            try:
                obj = rapid.loads(data.decode("latin1"))
                if obj:
                    pattern = obj.get("pattern")
                    if pattern:
                        times = pattern["time"] - time.time()
                        log.time(f"packet time listener: {times}")

            except Exception as e:
                log.error(f"packet parse error: {e}")

        return (event, obj)

    def listen_loop(self):
        while True:
            try:
                data, obj = self.listen_enet()

                if data["type"] == "data":
                    log.debug("veri geldi")
                    if obj.get("type") == "auth":
                        self.server.accept_thread(
                            data["peer"],
                            obj.get("account_name"),
                            reconnect=obj.get("reconnect"),
                        )
                        continue

                    pattern = obj.get("pattern")
                    if pattern is None:
                        log.info(f"veri kısmında hata oluştu! Pattern yok: {obj}")
                        continue

                    ev.emit(pattern.get("type"), obj, log.debug)

                # elif data["type"] == "connected":
                #     self.server.accept_thread(data.peer, self.lock, reconnect=False)
                # elif data.type == enet.EVENT_TYPE_DISCONNECT:
                #     log.info("client disconnected")
                #     if self.server.is_client:
                #         self.server.create_client_socket(re_connect=True)
                #         continue

            except Exception as e:
                log.error("Recv error:", e)
