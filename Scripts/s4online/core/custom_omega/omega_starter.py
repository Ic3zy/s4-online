from .omega_client import Omega_client
from .omega_host import Omega_host
from s4online.base import Ctx

_omega_instance = None


def ev_add_network_server():
    network_instance = Ctx.get("network_instance")
    if network_instance is not None:
        omega_instance = Ctx.get("omega_ref")
        network_instance.ev.on({"type": "omega"}, omega_instance.add_msg)


def inject_omega(enetServer, is_client):
    global _omega_instance
    _omega = None
    if is_client:
        _omega = Omega_client()
        ev_add_network_server()
        # network_instance = Ctx.get("network_instance")
        # enetServer.ev.on({"type": "omega"}, _omega.add_msg)
    else:
        _omega = Omega_host(enetServer)

    Ctx["omega_ref"] = _omega


def uninject_omega():
    import _omega, omega

    omega.send = _omega.send
