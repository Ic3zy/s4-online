from .omega_client import Omega_client
from .omega_host import Omega_host
from s4online.base import Ctx
_omega_instance = None

def inject_omega(enetServer, is_client):
    global _omega_instance
    _omega = None
    if is_client:
        _omega = Omega_client()
        enetServer.ev.on({"type": "omega"}, _omega.add_msg)
    else:
        _omega = Omega_host(enetServer)

    Ctx['omega_ref'] = _omega



def uninject_omega():
    import _omega, omega

    omega.send = _omega.send
