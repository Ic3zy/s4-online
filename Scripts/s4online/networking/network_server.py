from .network_client import Network_client
from .ev import ev
from .listener import Listener
from threading import Thread
from s4online.utils import Logger, show_notification, load_pyd
from s4online.base import Ctx
import time

log = Logger(__name__)

rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")
s4cpoxide = load_pyd("s4cpoxide", "s4cpoxide.pyd")


class NetworkServer:
    def __init__(self, is_client, port, host, account_name=None):
        self.port = port
        self.host = host
        self.is_client = is_client
        self.account_name = account_name
        self.ev = ev

        self.running = True
        self.net_tick = 30
        self.engine = None
        self.peer = None
        self.clients = dict()

        self.create_socket()
        self.tick_thread = Thread(target=self.loop, daemon=True)
        self.tick_thread.start()

    def __len__(self):
        return len(self.clients)

    def create_socket(self):
        if self.is_client:
            self.create_client_socket()
        else:
            self.create_server_socket()

        self.listener = Listener(self)

    def process_clients(self):
        for client in self.clients.values():
            client.process()

    def loop(self):
        while True:
            self.on_tick()

    def on_tick(self):
        self.process_clients()
        time.sleep(1 / self.net_tick)

    def add_client(self, client):
        self.clients[client._g_client.id] = client

    def send_auth(self, reconnect=False):
        if self.peer is None:
            log.error("Peer bağlı değil, auth gönderilemedi.")
            return

        auth_payload = {
            "type": "auth",
            "account_name": self.account_name,
            "reconnect": reconnect,
        }
        data = rapid.dumps(auth_payload, default=str).encode("latin1")

        self.peer.send(data)

    def create_client(self, g_client, account_name):
        n_client = Network_client(g_client, account_name)
        self.add_client(n_client)

        return n_client

    # ----- CLIENT -----
    def create_client_socket(self, re_connect=False):
        peer, engine = s4cpoxide.start_client(f"{self.host}:{self.port}")

        self.peer = peer
        self.engine = engine

        if re_connect:
            self.send_auth(reconnect=True)

    # ----- SERVER -----
    def create_server_socket(self):
        self.engine = s4cpoxide.start_server(f"{self.host}:{self.port}")

    # network client get
    def get_n_client_by_name(self, name):
        for client in self.clients.values():
            if client.account_name == name:
                return client

    def accept_thread(self, peer, name, reconnect=False):
        log.info("accept func")
        if not reconnect:
            show_notification(
                f"Yeni bir kullanıcı bağlanıyor...\nKullanıcı adı: {name}"
            )

            n_client = self.get_n_client_by_name(name)
            if n_client is None:
                show_notification(f"{name} geçerli bir oyuncu değil.")
                return

            # Direkt peer'i referans vermek yerine yeni bir içerisinde bu peeri tutan obje veriyoruz
            n_client.set_peer(peer)
            g_client = n_client._g_client

            if g_client is None:
                return

            client_id = g_client.id

            self.clients[client_id] = n_client
            show_notification(f"{name} başarı ile bağlandı.")

        else:
            show_notification(f"Bağlantısı kopan {name} yeniden bağlanıyor...")

            n_client = self.get_n_client_by_name(name)
            if n_client is None:
                return show_notification(f"{name} gelecek bir oyuncu değil.")

            n_client.set_peer(peer)
            show_notification(f"{name} yeniden bağlandı.")

    def send_message_from_client_id(self, client_id: int, message: dict):
        client = self.clients.get(client_id)
        if client is None:
            log.error("client not found")
            return

        self.send_message_by_client(message, client)

    def send_message_all_clients(self, message: dict):
        try:
            if self.is_client:
                log.debug("send_message_all_clients Client")
                if message.get("account_name") is None:
                    message["account_name"] = self.account_name

                if self.peer is None:
                    log.warning("peer yok; veri gönderilemedi")
                    return

                payload = rapid.dumps(message, default=str).encode("latin1")

                self.peer.send(payload)
                log.debug("veri gönderildi")
            else:
                for client in self.clients.values():
                    try:
                        client.send_message(message)
                    except Exception as e:
                        log.error(f"gönderi sırasında hata {e}")
                        continue
        except Exception as e:
            log.error(f"send_message_all_clients hata: {e}")

    def send_message_by_client(self, message, n_client):
        try:
            n_client.send_message(message)

            return True
        except Exception:
            return False
