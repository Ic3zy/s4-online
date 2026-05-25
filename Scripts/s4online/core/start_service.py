from .system import DistributorNew
import distributor.system, services


def inject_distributor(is_client):
    distributor.system.original_instance = distributor.system._distributor_instance
    distributor.system._distributor_instance = DistributorNew(is_client)


def uninject_distributor():
    new_dist = distributor.system.Distributor()
    # add client demiyorum, nedenleri ise şu an oyunun kafasını karıştırıyor direk el ile bu işlemi yapıyorum.
    # new_dist.add_client(services.client_manager().get_first_client())
    new_dist.client = services.client_manager().get_first_client()
    distributor.system._distributor_instance = new_dist
