import sys
from . import network_client
from .ev import ev
from .listener import Listener
from threading import Thread, RLock
from s4online.utils import Logger, show_notification, load_pyd
from s4online.base import Ctx

log = Logger(__name__)

enet = load_pyd("enet", "enet.cp37-win_amd64.pyd")
rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")


class _Peer:
    # Burda böyle yeni bir peer instance'i yaratıyorum çünkü lock olmaz ise peer'i kullanmak riskli.
    # Normalde enet bunu gil tutarak yapıyordu, yani aynı anda tek thread gerçekten enete erişebiliyordu.
    # Ben bu tek thread kısmını beğenmedim çünkü service(200) yaparsam sadece network thread'i değil tüm threadler uyuyordu.
    # Bu enetin gil'i tutması sebebiyle gerçekleşiyordu ancak ben cython api'ını biraz daha değiştirerek gil tutmadan yaptım.
    # Bunun faydası bana çok fazla ama yanında zararları da var,
    # şu an enet erişimi tamamen python düzeyinde thread safe olmalı.
    # Aksi halde deadlock oluyor.
    def __init__(self, peer, lock):
        self.peer = peer
        self.lock = lock

    def send(self, channel, message):
        with self.lock:
            self.peer.send(channel, message)


class NetworkServer:
    def __init__(self, is_client, port, host, account_name=None):
        self.port = port
        self.host = host
        self.is_client = is_client
        self.account_name = account_name
        self.ev = ev
        self.lock = RLock()

        self.running = True
        self.net_tick = 60
        self.current_host = None
        self.peer = None
        self.clients = dict()

        self.create_socket()
        self.tick_thread = Thread(target=self.loop, daemon=True).start()

    def __len__(self):
        return len(self.clients)

    def create_socket(self):
        if self.is_client:
            log.log("SERVER CLİENT OLARAK KURULUYOR")
            self.create_client_socket()
        else:
            self.create_server_socket()

        self.listener = Listener(self)

    def process_clients(self):
        for client in self.clients.values():
            client.process()

    def loop(self):
        while True:
            # print("tick")
            self.on_tick()

    def on_tick(self):
        self.listener.on_tick()
        self.process_clients()

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
        packet = enet.Packet(data, enet.PACKET_FLAG_RELIABLE)

        with self.lock:
            self.peer.send(0, packet)

    def create_client(self, g_client, account_name):
        n_client = network_client.Network_client(g_client, account_name)
        self.add_client(n_client)
        return n_client

    # ----- CLIENT -----
    def create_client_socket(self, re_connect=False):
        with self.lock:
            client = enet.Host(None, 1, 1, 0, 0)

        self.current_host = client

        address = enet.Address(self.host, self.port)
        peer = client.connect(address, 1)
        self.peer = peer

        for _ in range(50):  # Maksimum ~500ms bekleme
            event = client.service(10)
            if event is not None and event.type == enet.EVENT_TYPE_CONNECT:
                break

        return client

    # ----- SERVER -----
    def create_server_socket(self):
        with self.lock:
            address = enet.Address(self.host, self.port)
            server = enet.Host(address, 32, 1, 0, 0)

            self.current_host = server
        return server

    # network client get
    def get_n_client_by_name(self, name):
        for client in self.clients.values():
            if client.account_name == name:
                return client
        return None

    def accept_thread(self, peer, name, reconnect=False):
        log.info("accept func")
        if reconnect is False:
            show_notification(
                f"Yeni bir kullanıcı bağlanıyor...\nKullanıcı adı: {name}"
            )

            n_client = self.get_n_client_by_name(name)
            if n_client is None:
                show_notification(f"{name} geçerli bir oyuncu değil.")
                return

            # Direkt peer'i referans vermek yerine yeni bir içerisinde bu peeri tutan obje veriyoruz
            n_client.set_peer(_Peer(peer, self.lock))
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

            n_client.set_peer(_Peer(peer, self.lock))
            show_notification(f"{name} yeniden bağlandı.")

    def send_message_from_client_id(self, client_id: int, message: dict):
        log.debug("send msg")

        client = self.clients.get(client_id)
        if client is None:
            log.error("client not found")
            return

        self.send_message_by_client(message, client)

    def send_message_all_clients(self, message: dict):
        log.debug("send msg")

        if self.is_client:
            if message.get("account_name") is None:
                message["account_name"] = self.account_name

            if self.peer is None:
                log.warning("peer yok; veri gönderilemedi")
                return

            payload = rapid.dumps(message, default=str).encode("latin1")
            packet = enet.Packet(payload, enet.PACKET_FLAG_RELIABLE)

            with self.lock:
                self.peer.send(0, packet)

        else:
            for client in self.clients.values():
                try:
                    client.send_message(message)
                except Exception as e:
                    log.error(f"gönderi sırasında hata {e}")
                    continue

    def send_message_by_client(self, message, n_client):
        try:
            n_client.send_message(message)

            return True
        except Exception:
            return False
