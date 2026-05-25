import json, time, traceback, sys
from . import ev, network_client
from threading import Thread
from s4online.utils import Logger, show_notification, load_pyd
from s4online.core import setup_client
from s4online.base import Ctx
log = Logger(__name__)

enet = load_pyd("enet", "enet.cp37-win_amd64.pyd")


class Listener:
    """
    Tek bir listener; host değişse bile (reconnect) aynı thread çalışmaya devam eder.
    """

    def __init__(self, server):
        self.server = server
        self.running = True
        self.net_tick = 40
        self.thread = Thread(target=self.listen_loop, daemon=True)
        self.thread.start()

    def stop(self):
        log.info("Listener thread durduruluyor...")
        self.running = False

        thread = getattr(self, "thread", None)
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
            log.info("Listener thread başarıyla sonlandı.")
        else:
            log.info("Listener thread zaten kapalıydı veya hiç başlatılmadı.")

    def listen_loop(self):
        # Orijinal döngü yapısı ve akış tamamen korundu
        while self.running and self.server.runing:
            try:
                self.server.on_tick()
                host = self.server.current_host
                if host is None:
                    time.sleep(0.01)
                    continue

                data = host.service(0)

                if data is None:
                    # Gecikmeyi önlemek için veri yoksa net_tick uykusuna sadık kalınıyor
                    time.sleep(1.0 / self.net_tick)
                    continue

                try:
                    if data.type == enet.EVENT_TYPE_RECEIVE:
                        log.debug("veri geldi")
                        obj = json.loads(data.packet.data.decode("latin1"))
                        if obj.get("type") == "auth":
                            self.server.accept_thread(
                                data.peer,
                                obj.get("account_name"),
                                reconnect=obj.get("reconnect"),
                            )
                            continue

                        pattern = obj.get("pattern")
                        if pattern is None:
                            log.info(f"veri kısmında hata oluştu! Pattern yok: {obj}")
                            continue

                        ev.emit(pattern.get("type"), obj, log.debug)

                    elif data.type == enet.EVENT_TYPE_DISCONNECT:
                        log.info("client disconnected")
                        if self.server.is_client:
                            self.server.create_client_socket(re_connect=True)
                            continue

                except Exception:
                    log.error("veri kısmında hata oluştu!")
                    log.error(traceback.format_exc())
                    continue

            except Exception as e:
                log.error("Recv error:", e)
                log.error(traceback.format_exc())
                continue

            time.sleep(1.0 / self.net_tick)


class NetworkServer:
    def __init__(self, is_client, port, host, account_name=None):
        self.runing = True
        self.port = port
        self.host = host
        self.is_client = is_client
        self.account_name = account_name
        self.ev = ev
        if ev.EV_LIST:
            ev.EV_LIST.clear()

        self.net_tick = 40
        self.current_host = None  
        self.peer = None  
        self.clients = dict()  

        if is_client:
            log.log("SERVER CLİENT OLARAK KURULUYOR")
            self.create_client_socket()

            # Ctx üzerinden game_load callback'i kaydediyorum,
            # yapma sebebim hostun client oyununun durumunu bilmesi.
            self.save_send_game_load_from_ctx()
        else:
            self.create_server_socket()

        self.listener = Listener(self)
        
    def __len__(self):
        return len(self.clients)

    def save_send_game_load_from_ctx(self):
        Ctx.add_callback("game_load", self.send_game_load)

    def add_client(self, client):
        self.clients[client._g_client.id] = client

    def create_client(self, g_client, account_name):
        n_client = network_client.Network_client(g_client, account_name)
        self.add_client(n_client)
        return n_client


    def on_tick(self):
        try:
            for client in self.clients.values():
                client.process_queue()
        except Exception as e:
            log.error(f"on_tick error: {e}")

    def send_game_load(self):
        if self.peer is None:
            log.error("Peer bağlı değil, game load gönderilemedi.")
            return
        # True: oyun açık çalışıyor tüm yükleme ekranları bitti
        # False: ya travel esnasında yada oyun hiç açılmadı

        message = {"pattern": {"type": "omega"}, "data": {"game_load": True}}
        data = json.dumps(message, separators=(",", ":"), default=str).encode("latin1")
        packet = enet.Packet(data, enet.PACKET_FLAG_RELIABLE)
        self.peer.send(0, packet)

    def send_auth(self, reconnect=False):
        if self.peer is None:
            log.error("Peer bağlı değil, auth gönderilemedi.")
            return
            
        auth_payload = {
            "type": "auth",
            "account_name": self.account_name,
            "reconnect": reconnect,
        }
        data = json.dumps(auth_payload, separators=(",", ":"), default=str).encode("latin1")
        packet = enet.Packet(data, enet.PACKET_FLAG_RELIABLE)
        self.peer.send(0, packet)
        
        # Auth paketinin kuyrukta beklemeden hemen gitmesini sağla
        self.flush()

    # ----- CLIENT -----
    def create_client_socket(self, re_connect=False):
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
    
    def flush(self):
        if self.current_host is None:
            return
        self.current_host.flush()

    # ----- SERVER -----
    def create_server_socket(self):
        address = enet.Address(self.host, self.port)
        server = enet.Host(address, 32, 1, 0, 0)
        self.current_host = server
        return server
    
    def distributor_get_game_client(self, name):
        import distributor.system
        _distributor_instance = distributor.system._distributor_instance

        client = _distributor_instance.get_client_by_account_name(name, default=None)
        if client is None:
            log.error("client not found")
            show_notification(f"{name} bağlanamadı.")
            return None

        return client

    # network client get
    def get_n_client_by_name(self, name):
        for client in self.clients.values():
            if client.account_name == name:
                return client
        return None

    def accept_thread(self, peer, name, reconnect=False):
        log.info("accept func")
        if reconnect is False:
            show_notification(f"Yeni bir kullanıcı bağlanıyor...\nKullanıcı adı: {name}")

            n_client = self.get_n_client_by_name(name)
            if n_client is None:
                show_notification(f"{name} geçerli bir oyuncu değil.")
                return
            
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

        self.flush()

    def send_message_from_client_id(self, client_id: int, message: dict):
        log.debug("send msg")

        client = self.clients.get(client_id)
        if client is None:
            log.error("client not found")
            return

        self.send_message_by_client(message, client)

        self.flush()

    def send_message_all_clients(self, message: dict):
        log.debug("send msg")

        if self.is_client:
            if message.get("account_name") is None:
                message["account_name"] = self.account_name

            if self.peer is None:
                log.warning("peer yok; veri gönderilemedi")
                return
            
            payload = json.dumps(message, separators=(",", ":"), default=str).encode("latin1")
            packet = enet.Packet(payload, enet.PACKET_FLAG_RELIABLE)
            self.peer.send(0, packet)
        else:
            for client in self.clients.values():
                try:
                    client.send_message(message)
                except Exception as e:
                    log.error(f"gönderi sırasında hata {e}")
                    continue

        self.flush()

    def get_client_by_account_name(self, account_name):
        for cid, client in self.clients.items():
            if client.account_name == account_name:
                return client["peer"]
        return None  

    # ----- CLIENTE ÖZEL MESAJ -----
    def send_messsage_by_account_name(self, message, account_name):
        client = self.get_client_by_account_name(account_name)
        if client is None:
            return log.warning("tcp: client bulunamadı")
        
        # message doğrudan send_message_by_client fonksiyonuna güvenle iletiliyor
        if self.send_message_by_client(message, client) is False:
            return log.warning("tcp: mesaj gönderilemedi")

    def send_message_by_client(self, message, n_client):
        try:
            # Gelen veri dict ise otomatik json string'e dönüştürerek hata olasılığını sıfırla


            n_client.send_message(message)
            
            # Gönderilen tekil mesajı anında ilet
            self.flush()

            return True
        except Exception:
            return False

    # ----- KAPAT -----
    def closetcp(self):
        log.info("server kapatılıyor...")
        self.runing = False

        try:
            if self.listener:
                self.listener.stop()
        except:
            pass

        try:
            if self.current_host:
                if not self.is_client:
                    for cid, c in list(self.clients.items()):
                        try:
                            c["peer"].disconnect_now(0)
                        except:
                            pass

                if self.is_client and self.peer:
                    try:
                        self.peer.disconnect_now(0)
                    except:
                        pass

                for _ in range(10):
                    self.current_host.service(0)

                self.current_host = None
                self.peer = None
                self.clients.clear()

                sys.modules.pop("enet", None)
                load_pyd("enet", "enet.cp37-win_amd64.pyd")
                log.info("ENet host tamamen kapatıldı.")
        except Exception as e:
            log.error(f"ENet kapatma hatası: {e}")