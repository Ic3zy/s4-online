import distributor.distributor_service
import distributor.system
from .system import DistributorNew
from s4online.base import Ctx


def start(*a) -> None:
    import animation.arb

    animation.arb.set_tag_functions(
        distributor.system.get_next_tag_id, distributor.system.get_current_tag_set
    )
    distributor.system._distributor_instance = DistributorNew()


distributor.distributor_service.DistributorService.start = start
