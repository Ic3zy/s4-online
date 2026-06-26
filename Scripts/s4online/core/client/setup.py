from server_commands.sim_commands import set_active_sim
import server.account, services, time, distributor.system
from s4online.utils import Logger
from server.client import Client

log = Logger(__name__)

def setup_client(account_id, client_id, account_name):
    try:
        client_manager = services.client_manager()
        local_client = services.get_first_client()
        distributor_instance = distributor.system._distributor_instance

        if not local_client or not client_manager or not distributor_instance:
            log.error(f"error args: {local_client} {client_manager} {distributor_instance}")
            return 

        # create account
        account = server.account.Account(account_id, account_name)
        log.info(f"created account: {account_id} ::: {account_name}")

        test_client = Client(client_id, account, local_client._household_id)
        client_manager._objects[client_id] = test_client

        if distributor_instance is not None:
            distributor_instance.add_client(
                test_client, account_name, call_is_game=False
            )

        log.log(f"Client created (id={client_id})")
        return test_client

    except Exception as e:
        log.error(f"err: {e}")



def is_local_client(client) -> bool:
    return client.id < 10000

def sync_household(local_client):
    # household normal şartlarda hiç update edilmiyordu.
    # Ancak bu update edilmeme sorunu yakın zamanda fark ettiğim bug'a sebep oluyor.
    # Test aşamasında, çözüp çözmediğini anlamak için çok fazla edge-case denenmeli.

    local_household_id = local_client._household_id
    client_manager = services.client_manager()

    for client in client_manager._objects.values():
        if client._household_id != local_household_id:
            client._household_id = local_household_id


def sync_remote_client(remote_client, local_client, target_sim):
    """Tek bir uzak istemciyi yerel istemcinin seçilebilir sim'leri ile senkronize eder."""
    try:
        # Uzak istemcinin aktif sim'ini yerel sim ile eşitle
        # Yerel istemcideki tüm seçilebilir sim'leri uzak istemciye kopyala
        for sim_info in local_client._selectable_sims:
            # Her seyahat sonrası tetikleniyor burası.
            # Zaten ekliyse eklemeye çok gerek yok.
            if sim_info in remote_client._selectable_sims._selectable_sim_infos:
                continue

            remote_client._selectable_sims._selectable_sim_infos.append(sim_info)

        set_active_sim(target_sim.id, _connection=remote_client.id)

    except Exception as e:
        log.error(f"Uzak istemci senkronizasyon hatası ({remote_client}): {e}")


def setup_sim():
    """Yerel istemcinin sim bilgilerini diğer tüm uzak istemcilere senkronize eder."""
    try:
        local_client = services.get_first_client()
        if not local_client:
            log.error("Local client not found")
            return 

        # İlk seçilebilir sim'i güvenli bir şekilde al
        # first_sim = next(iter(local_client._selectable_sims), None)
        first_sim = local_client.active_sim
        if first_sim is None:
            log.warn("No selectable sims found on local client")
            return 

        client_manager = services.client_manager()
        # Diğer tüm istemcileri (oyuncuları) döngüye al
        for client in client_manager._objects.values():
            try:
            # Local client'lara sim ataması yapmayacağım,
            # nedeni ise zaten atanmış durumda.
                if is_local_client(client):
                    continue

            # Senkronizasyon işini alt fonksiyona pasla
                sync_remote_client(
                    remote_client=client, local_client=local_client, target_sim=first_sim
                )
            except Exception as e:
                log.error(f"setup sim error: {e}")
    except Exception as e:
        log.error(f"setup_sim genel hatası: {e}")
