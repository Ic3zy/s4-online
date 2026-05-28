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

log = Logger(__name__)
is_client = Config.is_client


rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")


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
    stop_loop()
    uninject_distributor()

    # Fonksiyonu modül üzerinden çağırıyoruz
    networking.stop()

    uninject()
    uninject_omega()


def uninject_distributors():
    new_dist = distributor.system.Distributor()
    new_dist.add_client(services.client_manager().get_first_client())
    distributor.system._distributor_instance = new_dist


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
