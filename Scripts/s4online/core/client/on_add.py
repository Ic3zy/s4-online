from s4online.base import Ctx
from s4online.utils import Logger, injector
from server.client import Client

log = Logger(__name__)
original_on_add = Client.on_add
def on_add(self, *a, **kw):
    # id'yi 10000 altı ise manager load atmamamın sebebi basit ama çok önemli.
    # id 10000 üzerindeki clientlar benim tarafımdan yaratılıyor eğer ayıklamazsam deep loopa girip sürekli client yaratır.
    if self.id < 10000:
        Ctx.client_manager_load = True
    else:
        log.info(f"not load client id: {self.id}")
    log.info("client loaded")

    result = original_on_add(self, *a, **kw)
    Ctx.first_client_load = True
    return result

Client.on_add = on_add