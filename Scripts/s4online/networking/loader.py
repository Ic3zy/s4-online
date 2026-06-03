from s4online.utils import Config, pydLoader, Logger
from s4online.base import Ctx

# loopmod = pydLoader.load_pyd("loopmod", "loopmod.pyd")
log = Logger(__name__)


def send_auth():
    # log.debug("send_auth")
    if Ctx.get("network_instance") is not None:
        _network_instance = Ctx["network_instance"]
        _network_instance.send_auth()
        log.log("AUTH sent")


if Config.is_client:
    Ctx.add_callback("client_manager_load", send_auth)
