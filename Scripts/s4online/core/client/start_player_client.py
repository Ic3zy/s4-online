from s4online.base import Ctx
from s4online.utils import Config, Logger
from .setup import setup_client, setup_sim
import services

log = Logger(__name__)


# example
# clients = [
#     {
#         "client_id": 1,
#         "account_id": 1,
#         "account_name": "guest",
#     }
# ]
def start_save_client(clients_info: list):
    if Ctx.get("network_instance") is not None:
        _network_instance = Ctx.network_instance
        for client_info in clients_info:
            account_id = client_info["account_id"]
            account_name = client_info["account_name"]
            client_id = client_info["client_id"]

            client = setup_client(account_id, client_id, account_name)

            _network_instance.create_client(client, account_name)
    else:
        log.error("Game not loaded")


def create_clients_info():
    clients_info = list()

    for client_info in Config.clients_info:
        account_name = client_info["account_name"]
        client_manager = services.client_manager()
        client_count = len(client_manager._objects) + len(clients_info)
        account_id = 900000 + client_count
        client_id = 100000 + client_count

        clients_info.append(
            {
                "account_id": account_id,
                "account_name": account_name,
                "client_id": client_id,
            }
        )

    return clients_info


def start_client(force=False):
    log.info("Starting clients...")
    try:
        if Ctx.get("custom_clients") is not None and not force:
            return

        Ctx.custom_clients = True

        clients_info = create_clients_info()
        start_save_client(clients_info)

        if len(clients_info) == 0:
            log.error("No clients to start")
            return

    except Exception as e:
        log.error(f"Error creating clients: {e}")


# DEBUG
def travelling_player_clients():
    if not Ctx.get("client_manager_load"):
        return log.debug(f"travelling processer error, client manager not loaded.")

    if Ctx.get("is_travel"):
        client_manager = services.client_manager()
        objects = client_manager._objects

        for client_id, client in list(objects.items()):
            if client.id > 100000:
                log.debug(f"Deleted client: {client.id}")
                del objects[client_id]

        Ctx["client_initialize_wait"] = True

    elif Ctx.get("client_initialize_wait"):
        log.debug("starting after travel clients")
        start_client(force=True)
        setup_sim()

        Ctx["client_initialize_wait"] = False

    else:
        log.debug("pass client process")


if not Config.is_client:
    Ctx.add_callback("client_manager_load", start_client)
    Ctx.add_callback("game_load", setup_sim)
    # DEBUG
    # Ctx.add_callback("is_travel", travelling_player_clients)
