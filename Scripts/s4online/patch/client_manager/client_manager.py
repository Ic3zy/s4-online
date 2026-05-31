from objects.object_manager import DistributableObjectManager
from server.client import Client
import server.clientmanager
from s4online.utils import Logger

log = Logger(__name__)


class ClientManager(DistributableObjectManager):

    def resort_clients(self):
        try:
            if not self._objects:
                return

            # 1. Mevcut sözlükteki tüm client nesnelerini çekiyoruz
            all_clients = list(self._objects.values())

            # 2. Python 3.7+ nimetlerini kullanarak Host ve Guest'leri ayırıp
            # sıralı tek bir liste haline getiriyoruz (Önce Hostlar < 10000, sonra Guestler)
            ordered_clients = [c for c in all_clients if c.id < 10000] + [
                c for c in all_clients if c.id >= 10000
            ]

            # 3. Sihirli dokunuş: Mevcut _objects sözlüğünü, sıralaması kusursuz
            # yeni bir sözlükle bodoslama değiştiriyoruz. Python 3.7 bu sırayı mühürler!
            self._objects = {client.id: client for client in ordered_clients}

            log.debug(
                f"🔄 [S4ONLINE_SORT] Client dict'i yeniden dizildi. Sıralama: {[c.id for c in ordered_clients]}"
            )

        except Exception as e:
            log.error(f"resort_clients error: {e}")

    def create_client(self, client_id, account, household_id):
        new_client = Client(client_id, account, household_id)
        self.add(new_client)
        self.resort_clients()
        return new_client

    def get_client_by_household(self, household):
        for client in self._objects.values():
            if client.id < 10000 and client.household is household:
                return client

    def get_client_by_household_id(self, household_id):
        for client in self._objects.values():
            if client.id < 10000 and client.household_id == household_id:
                return client

    def get_client_by_account(self, account_id):
        for client in self._objects.values():
            if client.id < 10000 and client.account.id == account_id:
                return client

    def get_first_client(self):
        for client in self._objects.values():
            if client.id < 10000:
                return client

    def get_first_client_id(self):
        for client in self._objects.values():
            if client.id < 10000:
                return client.id


server.clientmanager.ClientManager = ClientManager
