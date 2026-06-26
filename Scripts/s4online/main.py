# YANLIŞ OLANLAR:
# from s4online.networking import start as start_server
# from s4online.networking import stop as stop_server

# DOĞRU OLAN: Modülü direkt olarak import et
from s4online import networking
import distributor.system, services
from s4online.core import (
    inject_distributor,
    inject_omega,
    uninject_distributor,
    uninject_omega,
)
from s4online.patch import inject, inject_time, uninject, uninject_time
from s4online.utils import Config, Logger, show_notification
from sims4.commands import CheatOutput, Command, CommandType, unregister
from s4online.utils import load_pyd
from s4online.base import Ctx

log = Logger(__name__)
is_client = Config.is_client


rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")
s4cpoxide = load_pyd("s4cpoxide", "s4cpoxide.pyd")

# print = log.log

# active_client_peer = None


# def on_packet_received(packet):
#     global active_client_peer
#     print(f"📥 [HOST] -> Paket Geldi: {packet}")

#     # Eğer gelen paket PING ise, client'a anında PONG üfle!
#     if packet == "PING":
#         if active_client_peer is not None:
#             # Rust içi try_send kullanan o kurşun geçirmez, non-blocking mermi!
#             active_client_peer.send("PONG")
#         else:
#             print("🚨 [HOST] -> Paket geldi ama active peer referansı henüz yok!")


# def on_peer_connected(peer):
#     global active_client_peer
#     active_client_peer = peer
#     print(f"🟢 [HOST] -> YENİ BİR PEER SIZDI AQ! Adres: {peer.ip_address}")


# print("🚀 [HOST] -> Rust Network Core 127.0.0.1:8888 üzerinde tetikleniyor...")

# # Rust makine dairesini host modunda asenkron fırlatıyoruz. GIL anında boşa çıkıyor!
# s4cpoxide.start_host("0.0.0.0:8888", on_packet_received, on_peer_connected)


def inject_all(is_client, b) -> bool:
    # Fonksiyonu modül üzerinden çağırıyoruz
    network_server = networking.start()
    if network_server is None:
        return False
    # omega inject
    inject_omega(network_server, is_client)
    # distributor inject
    # yeni akışta gerek yok çünkü hot install
    # if b:
    #     inject_distributor(is_client)
    # inject_distributor(is_client)
    # commands inject
    inject(network_server, is_client)
    # inject_time(is_client)
    return True


def uninject_all():
    uninject_time(is_client)
    # stop_loop()
    uninject_distributor()

    # Fonksiyonu modül üzerinden çağırıyoruz
    networking.stop()

    uninject()
    uninject_omega()


def uninject_distributors():
    new_dist = distributor.system.Distributor()
    new_dist.add_client(services.client_manager().get_first_client())
    distributor.system._distributor_instance = new_dist

@Command("blockevent", command_type=CommandType.Live)
def eventblocker(_connection=None):
    output = CheatOutput(_connection)
    output("event blocker")
    if not Ctx.get("block_events"):
        Ctx.block_events = True
    else:
        Ctx.block_events = not Ctx.block_events

    output(f"block events: {Ctx.get('block_events')}")

@Command("start", command_type=CommandType.Live)
def start(a: bool = False, b: bool = False, _connection=None):
    output = log.log
    try:
        if not a:
            output("injecting...")
            output("you are client" if is_client else "you are server")
            result = inject_all(is_client, b=b)
            output("inject done" if result else "inject fail")
            show_notification(
                f"created s4online.\nYou are: {'Client' if is_client else 'Server'}"
            )
        else:
            uninject_all()
            output("uninject done")
            show_notification("closed s4online.")
    except Exception as e:
        show_notification("occured error.")
        output(f"error: {e}")
        import traceback

        log.error(traceback.format_exc())


start()


@Command("alive", command_type=CommandType.Live)
def alive(_connection=None):
    output = CheatOutput(_connection)
    output("I'm alive")
    output(f"connection: {_connection}")
    import services

    clients_count = services.client_manager()._objects
    output(f"clients: {clients_count}")
