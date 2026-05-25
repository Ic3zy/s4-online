import server.account, services, time
from s4online.utils import Logger
from server.client import Client

log = Logger(__name__)


def create_client(client_id, account_name, household_id):
    new_client = Client(client_id, account_name, household_id)
    return new_client


def setup_client(account_id, client_id, account_name, distributor=None):
    try:
        client_manager = services.client_manager()
        local_client = services.get_first_client()
        if not local_client:
            log.error("local client not found")
            return None

        # create account
        account = server.account.Account(account_id, account_name)
        log.info(f"created account: {account_id} ::: {account_name}")

        # create client via official client_manager method (matches SimSync's clean approach)
        test_client = client_manager.create_client(client_id, account, local_client.household_id)

        log.info(f"created client: {client_id}")

        # ilk client daha yüklenmedi,
        # yüklendiği zaman bize yine bir call geliyor ve orada atıyoruz. 
        # try:
        #     for sim_info in local_client._selectable_sims:
        #         test_client._selectable_sims.add_selectable_sim_info(sim_info)
        # except Exception as e:
        #     log.error(f"error copying selectable sims: {e}")

        try:
            # added client to distributor
            # distributor.add_client(test_client, account_name, call_is_game=False)
            log.info("distributor added client")
        except Exception as e:
            log.error(f"Distributor add client error: {e}")

        first_sim = next(iter(local_client._selectable_sims), None)
        # set active sim
        # if not getattr(test_client, "active_sim", None):
        #     if first_sim is not None:
        #         test_client.set_active_sim_by_id(first_sim.sim_id)
        #         log.debug(f"new client sim: {first_sim}")

        #         for client in client_manager._objects.values():
        #             try:
        #                 client.set_active_sim_by_id(first_sim.sim_id)
        #             except Exception as e:
        #                 log.error(f"set_active_sim error: {e}")

        # wait for client to be ready
        time.sleep(0.2)

        log.log(f"Client created (id={client_id})")
        return test_client

    except Exception as e:
        log.error(f"err: {e}")
        import traceback

        log.error(traceback.format_exc())
        return None


def is_local_client(client):
    if client.id < 10000:
        return True

    return False

def sync_remote_client(remote_client, local_client, target_sim):
    """Tek bir uzak istemciyi yerel istemcinin seçilebilir sim'leri ile senkronize eder."""
    try:
        # Uzak istemcinin aktif sim'ini yerel sim ile eşitle
        remote_client.set_active_sim_by_id(target_sim.sim_id)

        # Yerel istemcideki tüm seçilebilir sim'leri uzak istemciye kopyala
        for sim_info in local_client._selectable_sims:
            remote_client._selectable_sims.add_selectable_sim_info(sim_info)
            
    except Exception as e:
        log.error(f"Uzak istemci senkronizasyon hatası ({remote_client}): {e}")


def setup_sim():
    """Yerel istemcinin sim bilgilerini diğer tüm uzak istemcilere senkronize eder."""
    try:
        local_client = services.get_first_client()
        if not local_client:
            log.error("Local client not found")
            return None

        # İlk seçilebilir sim'i güvenli bir şekilde al
        first_sim = next(iter(local_client._selectable_sims), None)
        if first_sim is None:
            log.warn("No selectable sims found on local client")
            return None

        client_manager = services.client_manager()
        if not client_manager:
            return None

        # Diğer tüm istemcileri (oyuncuları) döngüye al
        for client in client_manager._objects.values():
            # Eğer yerel istemci ise atla (sadece uzak istemcileri senkronize et)
            if is_local_client(client):
                continue

            # Senkronizasyon işini alt fonksiyona pasla
            sync_remote_client(remote_client=client, local_client=local_client, target_sim=first_sim)

    except Exception as e:
        log.error(f"setup_sim genel hatası: {e}")
        return None