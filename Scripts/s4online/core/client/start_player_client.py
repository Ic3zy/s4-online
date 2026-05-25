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
    if Ctx.get('network_instance') is not None:
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

        clients_info.append({
            "account_id": account_id,
            "account_name": account_name,
            "client_id": client_id,
        })


    return clients_info

def start_client():
    log.info("Starting clients...")
    try:
        clients_info = create_clients_info()
        start_save_client(clients_info)

        if len(clients_info) == 0:
            log.error("No clients to start")
            return
    except Exception as e:
        log.error(f"Error creating clients: {e}")

if not Config.is_client:
    Ctx.add_callback("client_manager_load", start_client)
    Ctx.add_callback("game_load", setup_sim)