from contextlib import contextmanager
from protocolbuffers import Distributor_pb2 as protocols
from protocolbuffers.Consts_pb2 import MSG_OBJECTS_VIEW_UPDATE
from graph_algos import topological_sort
from gsi_handlers.distributor_handlers import archive_operation
from sims4.callback_utils import consume_exceptions
from distributor.system import Journal
from server.client import Client
import gsi_handlers, services, distributor.system, weakref, random
from s4online.utils import Logger, Config
from s4online.base import Ctx

log = Logger(__name__)
_send_index = 0


def get_omega_ref():
    # Önbelleğe (cache) kaydetmiyoruz!
    # Başka yer burayı güncellerse, her çağrıldığında en güncel referansı sys'tan çeker.
    return Ctx.get("omega_ref")


class DistributorNew:
    def __init__(self):
        self.journal = Journal()
        self._pending_creates = weakref.WeakSet()
        self.events = list()
        self.distributors = list()
        self.is_client = Config.is_client
        log.info("distributor oluşturuldu")
        # self.setup()

    # hot install kodu, şu anki akışımızda bu koda ihtiyacımız yok.
    def setup(self):
        client = services.client_manager().get_first_client()
        if client is not None:
            base_distributor = distributor.system.Distributor()
            base_distributor.client = client
            base_distributor.account_name = "base_distributor"
            self.distributors.append(base_distributor)
        else:
            log.warning("client bulunamadı")

    def __repr__(self):
        return "<Distributor events={}>".format(len(self.events))

    @property
    def client(self):
        client = None
        for dist in self.distributors:
            if dist.client is not None and dist.client.id < 10000:
                client = dist.client
                break
        return client

    @contextmanager
    def dependent_block(self):
        if not self.journal.deferring:
            with consume_exceptions(
                "Distributor", "Exception raised during a dependent block:"
            ):
                self.journal.start_deferring()
                try:
                    yield
                finally:
                    self.journal.stop_deferring()
        else:
            yield

    @classmethod
    def instance(cls):
        return distributor.system._distributor_instance

    def add_object(self, obj):
        obj.visible_to_client = True
        if not obj.visible_to_client:
            return
        if not services.client_manager():
            return
        op = obj.get_create_op()
        if op is None:
            obj.visible_to_client = False
            return
        self.journal.add(obj, op, ignore_deferral=True)
        self._pending_creates.add(obj)
        if hasattr(obj, "on_add_to_client"):
            obj.on_add_to_client()

    def remove_object(self, obj, **kwargs):
        was_visible = obj.visible_to_client
        if was_visible and hasattr(obj, "on_remove_from_client"):
            obj.on_remove_from_client()
        if was_visible:
            delete_op = obj.get_delete_op(**kwargs)
            if delete_op is not None:
                self.add_op(obj, delete_op)
            obj.visible_to_client = False

    def add_client(self, client, account_name=None, call_is_game=True):
        for cl in self.distributors:
            if cl.client.id == client.id:
                log.info("Client zaten var")
                raise Exception("Client zaten var")

        self.process()

        if account_name is None:
            persona_name = None
            if hasattr(client, "_account") and hasattr(
                client._account, "_persona_name"
            ):
                persona_name = client._account._persona_name
            if persona_name is None:
                persona_name = "guest_" + random.randint(1, 90000)
            account_name = persona_name

        new_dist = distributor.system.Distributor()
        self.distributors.append(new_dist)
        new_dist.add_client(client)
        new_dist.account_name = account_name

        # self._add_ops_for_client_connect(client)

    def _add_ops_for_client_connect(self, client):
        node_gen = client.get_objects_in_view_gen()
        if node_gen is None:
            return
        parents_gen_fn = lambda obj: obj.get_create_after_objs()
        create_order = topological_sort(node_gen, parents_gen_fn)
        for obj in create_order:
            create_op = obj.get_create_op()
            if create_op is not None:
                self.journal.add(obj, create_op)

    def remove_client(self, client):
        log.info("client kaldırıldı")
        self.process()
        for dist in self.distributors:
            if dist.client.id == client.id:
                dist.remove_client(client)
                self.distributors.remove(dist)

    def _debug_validate_op(self, obj, op):
        objs = getattr(obj, "client_objects_gen", None)
        if objs:
            for sub_obj in objs:
                self._debug_validate_op(sub_obj, op)

    def add_op(self, obj, op):
        if isinstance(obj, Client):
            dist = self.get_client_distributor_for_client_id(obj.id)
            if dist is not None:
                # TODO: büyük hata çıkarabilir burası
                # seyehat yönetiminde oyuncu taraftaki id ile buradaki id eşleşmez ise oyun çöp
                # oyuncu tarafının id'si muhtemelen eşleşir

                # Burda default clienti görsel update olarak işleme sebebim oyuncu tarafında UI default client olarak sayılır.
                # Eğer bunu kullanıcı clienti verirsen örnek olarak 100011 (ilk bağlanan kullanıcı clienti)
                # 100011 idli client oyuncu tarafında tanımlı değil.
                # Oyuncu tarafında sadece idsi 3 olan client tanımlı.
                # Normal olarak id 3 de oyunun kendi default clienti
                main_client = services.client_manager().get_first_client()
                game_load = Ctx.get("game_load")
                if game_load is not None:
                    return dist.add_op(main_client, op)

        self.journal.add(obj, op)

    def add_op_with_no_owner(self, op):
        self.journal.add(None, op)

    def send_op_with_no_owner_immediate(self, op):
        global _send_index
        journal_seed = self.journal._build_journal_seed(op, None, None)
        journal_entry = self.journal._build_journal_entry(journal_seed)
        obj_id, operation, payload_type, manager_id, obj_name = journal_entry
        view_update = protocols.ViewUpdate()
        entry = view_update.entries.add()
        entry.primary_channel.id.manager_id = manager_id
        entry.primary_channel.id.object_id = obj_id
        entry.operation_list.operations.append(operation)
        if (
            gsi_handlers.distributor_handlers.archiver.enabled
            or gsi_handlers.distributor_handlers.sim_archiver.enabled
        ):
            _send_index += 1
            if _send_index >= 4294967295:
                _send_index = 0
            archive_operation(
                obj_id,
                obj_name,
                manager_id,
                operation,
                payload_type,
                _send_index,
                (
                    self.client
                    if self.client is not None
                    else services.client_manager().get_first_client()
                ),
            )
        self.send_message_all_clients(MSG_OBJECTS_VIEW_UPDATE, view_update)

    def add_event(self, msg_id, msg, immediate=False):
        self.events.append((msg_id, msg))
        if immediate:
            self.process_events()

    def process_all_client(self):
        for dist in self.distributors:
            try:
                dist.process()
            except Exception as e:
                log.error(f"process_all_client error: {e}")

    def process(self):
        if self.is_client:
            omega_ref = get_omega_ref()
            if omega_ref is not None:
                omega_ref.omega_emitter()
        else:
            self.process_events()
            self.process_all_client()
            self._send_view_updates()

    def process_events(self):
        try:
            events = self.events
            self.events = list()
            for msg_id, msg in events:
                self.send_message_all_clients(msg_id, msg)
        except Exception as e:
            log.error(f"process_events error: {e}")

    def _send_view_updates(self):
        journal = self.journal
        if journal.entries:
            ops = list(journal.entries)
            journal.clear()
            try:
                # all kullanıyorum burada tüm distributorlere _send etmek de bir çözümdü.
                # ancak tüm distributorlere _send dersem hepsinde VIEW UPDATE yeniden oluşturulur, optimizasyon düşer.
                self._send_view_updates_for_client("all", ops)
            except:
                log.error("Error sending view updates to client!")
        self._pending_creates.clear()

    def _send_view_updates_for_client(self, client, all_ops):
        global _send_index
        view_update = None
        last_obj_id = None
        last_manager_id = None
        for obj_id, operation, payload_type, manager_id, obj_name in all_ops:
            if view_update is None:
                view_update = protocols.ViewUpdate()
            if obj_id != last_obj_id or manager_id != last_manager_id:
                entry = view_update.entries.add()
                entry.primary_channel.id.manager_id = manager_id
                entry.primary_channel.id.object_id = obj_id
                last_obj_id = obj_id
                last_manager_id = manager_id
            entry.operation_list.operations.append(operation)
            if (
                gsi_handlers.distributor_handlers.archiver.enabled
                or gsi_handlers.distributor_handlers.sim_archiver.enabled
            ):
                _send_index += 1
                if _send_index >= 4294967295:
                    _send_index = 0
                archive_operation(
                    obj_id,
                    obj_name,
                    manager_id,
                    operation,
                    payload_type,
                    _send_index,
                    (
                        client
                        if client != "all"
                        else services.client_manager().get_first_client()
                    ),
                )
        if view_update is not None:
            if client != "all" and client is not None:
                client.send_message(
                    MSG_OBJECTS_VIEW_UPDATE, view_update, global_distributor=False
                )
            elif client == "all":
                self.send_message_all_clients(MSG_OBJECTS_VIEW_UPDATE, view_update)

    def send_message_all_clients(self, msg_id, msg):
        for dist in self.distributors:
            try:
                dist.client.send_message(msg_id, msg, global_distributor=True)
            except Exception as e:
                log.error(f"send_message_all_clients error: {e}")
                import traceback

                log.error(traceback.format_exc())

    def get_client_distributor_for_client_id(self, client_id):
        for dist in self.distributors:
            if dist.client.id == client_id:
                return dist
        return None

    def get_distributor_by_account_name(self, name, default="self"):
        for dist in self.distributors:
            if dist.account_name == name:
                return dist
        log.warning("account name ile dist alınamadı")

        if default == "self":
            return self

        return default

    def get_client_by_account_name(self, name):
        for dist in self.distributors:
            if dist.account_name == name:
                return dist.client
        log.warning("account name ile client alınamadı")
        return self.client

    def get_distributor_by_active_sim(self, sim_id):
        top_distibutors = list()
        log.info(f"distributorlar arasında sim_id ile arama: {sim_id}")
        for dist in self.distributors:

            if str(dist.client.active_sim.id) == str(sim_id):
                log.info(f"active sim ile distributor bulundu: {dist.account_name}")
                top_distibutors.append(dist)
        return top_distibutors if len(top_distibutors) > 0 else None

    def get_all_client_active_sim(self):
        sims = list()
        for dist in self.distributors:
            try:
                sims.append(
                    {
                        "account_name": dist.account_name,
                        "sim_id": str(dist.client.active_sim.id),
                    }
                )
            except Exception as e:
                log.error(f"get_all_client_active_sim error: {e}")
        return sims if sims else None
