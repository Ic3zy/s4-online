from . import network_server
from .network_server import NetworkServer
from s4online.utils import Config, Logger
from s4online.base import Ctx
log = Logger(__name__)

def start():
    log.info("Starting server...")
    account_name = Config.account_name
    is_client = Config.is_client
    port = Config.db.get("port")
    host = Config.db.get("ip")
    if port is None or host is None:
        raise Exception("port and host must be set in config.json")

    server_instance = NetworkServer(is_client, port, host, account_name)
    Ctx['network_instance'] = server_instance

    return server_instance


def stop():
    instance = Ctx.get('network_instance')
    if instance is not None:
        instance.closetcp()
        del Ctx['network_instance']
    else:
        raise Exception("network is server not started")