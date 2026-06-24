from contextlib import contextmanager
from protocolbuffers import Distributor_pb2 as protocols
from graph_algos import topological_sort
from gsi_handlers.distributor_handlers import archive_operation
from sims4.callback_utils import consume_exceptions
from distributor.system import get_current_tag_set, _current_tag_set, DEFAULT_MASK
from server.client import Client
import gsi_handlers, services, distributor.system, weakref, random
from collections import namedtuple
from contextlib import contextmanager
import weakref
from protocolbuffers import Distributor_pb2 as protocols
from protocolbuffers.Consts_pb2 import (
    MSG_OBJECTS_VIEW_UPDATE,
    MGR_UNMANAGED,
    MGR_OBJECT,
    MGR_SIM_INFO,
)
import protocolbuffers.DistributorOps_pb2
from distributor.rollback import ProtocolBufferRollback
from sims4.repr_utils import standard_repr
import elements
import reset
import services

from s4online.utils import Logger, Config
from s4online.base import Ctx
from .journal_list import OpObject, S4OnlineProxyList

log = Logger(__name__)
_send_index = 0


class Journal:
    JournalEntry = namedtuple(
        "JournalEntry",
        (
            "object",
            "protocol_buffer",
            "payload_type",
            "manager_id",
            "debug_object_name",
        ),
    )
    JournalEntry.__repr__ = lambda self: standard_repr(
        self,
        self.object,
        self.protocol_buffer,
        self.payload_type,
        self.manager_id,
        self.debug_object_name,
    )
    JournalSeed = namedtuple(
        "JournalSeed", ("op", "object_id", "manager_id", "debug_object_name")
    )

    def __init__(self):
        self.entries = S4OnlineProxyList()
        self._deferred_journal_seeds = S4OnlineProxyList()
        self.deferring = False

    def __repr__(self):
        return "<Journal ops={}>".format(self.op_count)

    @property
    def op_count(self):
        return len(self.entries)

    def get_custom_ops(self):
        return self.entries.get_custom_ops()

    def start_deferring(self):
        self.deferring = True

    def stop_deferring(self):
        self.deferring = False
        index = 0
        for journal_seed in self._deferred_journal_seeds:
            entry = self._build_journal_entry(journal_seed)

            custom_op = self._deferred_journal_seeds.get_custom_op(index)
            op_obj = OpObject(
                entry,
                custom_op.client_id,
            )

            self.entries.append(op_obj)

            index += 1

        self._deferred_journal_seeds.clear()

    def add(self, obj, op, ignore_deferral=False, client_id="all"):
        for tag in _current_tag_set:
            op.block_on_tag(tag)

        manager_id_override = None

        if op.block_on_task_owner:
            op_task_owner = None
            time_service = services.time_service()

            if time_service is not None and time_service.sim_timeline is not None:
                timeline = time_service.sim_timeline
                current_element = timeline.get_current_element()
                while current_element is not None:
                    if isinstance(current_element, reset.ResettableElement):
                        op_task_owner = current_element.obj
                        break
                    else:
                        if isinstance(current_element, elements.AllElement):
                            break
                        else:
                            if current_element._parent_handle is None:
                                break
                            else:
                                current_element = current_element._parent_handle.element
            if (
                op_task_owner is not None
                and op_task_owner is not obj
                and (obj is None or op_task_owner.id != obj.id)
            ):
                op_task_owner_manager = getattr(op_task_owner, "manager", None)
                if op_task_owner_manager is not None and hasattr(
                    op_task_owner_manager, "id"
                ):
                    op.add_additional_channel(
                        op_task_owner_manager.id,
                        op_task_owner.id,
                        mask=op._primary_channel_mask_override,
                    )
                    op._primary_channel_mask_override = 0
        else:
            if obj.manager is not None and obj.manager.id == MGR_SIM_INFO:
                manager_id_override = MGR_OBJECT
        journal_seed = self._build_journal_seed(op, obj, manager_id_override)
        if not self.deferring or ignore_deferral:
            entry = self._build_journal_entry(journal_seed)
            op_obj = OpObject(entry, client_id)
            self.entries.append(op_obj)
        else:
            op_obj = OpObject(journal_seed, client_id)
            self._deferred_journal_seeds.append(op_obj)

    def _build_journal_seed(self, op, obj, manager_id):
        object_name = None
        if obj is None:
            object_id = 0
            if manager_id is None:
                manager_id = MGR_UNMANAGED
        else:
            object_id = obj.id
            if manager_id is None:
                manager_id = (
                    obj.manager.id if obj.manager is not None else MGR_UNMANAGED
                )
        return Journal.JournalSeed(op, object_id, manager_id, object_name)

    def _build_journal_entry(self, journal_seed):
        op = journal_seed.op
        object_id = journal_seed.object_id
        manager_id = journal_seed.manager_id
        object_name = journal_seed.debug_object_name
        proto_buff = protocolbuffers.DistributorOps_pb2.Operation()
        mask_override = None
        if manager_id == MGR_UNMANAGED:
            mask_override = 0
        if op._force_execution_on_tag:
            mask_override = 0
        else:
            if op._primary_channel_mask_override is not None:
                mask_override = op._primary_channel_mask_override
        if mask_override is not None and mask_override != DEFAULT_MASK:
            proto_buff.primary_channel_mask_override = mask_override
        for channel in op._additional_channels:
            with ProtocolBufferRollback(
                proto_buff.additional_channels
            ) as additional_channel_msg:
                additional_channel_msg.id.manager_id = channel[0]
                additional_channel_msg.id.object_id = channel[1]
                if channel[1] == object_id and mask_override is not None:
                    additional_channel_msg.mask = mask_override
                else:
                    additional_channel_msg.mask = channel[2]
        op.write(proto_buff)
        if not proto_buff.IsInitialized():
            log.error(
                "Message generated by {} is missing required fields: "
                + str(proto_buff.FindInitializationErrors()),
                op,
            )
        payload_type = op.payload_type
        entry = Journal.JournalEntry(
            object_id, proto_buff, payload_type, manager_id, object_name
        )
        return entry

    def clear(self):
        self.entries.clear()


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
        self.clients = dict()
        self.is_client = Config.is_client
        log.info("distributor oluşturuldu")

    def __repr__(self):
        return "<Distributor events={}>".format(len(self.events))

    @property
    def client(self):
        client = None
        for client in self.clients.values():
            if client.id < 10000:
                return client

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
        if self.clients.get(client.id) is not None:
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

        client.account_name = account_name
        self.clients[client.id] = client
        self._add_ops_for_client_connect(client)
        # YENİ AKIŞTA GEREK YOK

        # new_dist = distributor.system.Distributor()
        # self.distributors.append(new_dist)
        # new_dist.add_client(client)
        # new_dist.account_name = account_name

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

        if client.id in self.clients:
            del self.clients[client.id]

    def _debug_validate_op(self, obj, op):
        objs = getattr(obj, "client_objects_gen", None)
        if objs:
            for sub_obj in objs:
                self._debug_validate_op(sub_obj, op)

    def add_op(self, obj, op):
        if self.client is None:
            return None

        if isinstance(obj, Client):
            client = self.clients.get(obj.id)
            if client is not None:
                # TODO: büyük hata çıkarabilir burası
                # seyehat yönetiminde oyuncu taraftaki id ile buradaki id eşleşmez ise oyun çöp
                # oyuncu tarafının id'si muhtemelen eşleşir

                # Burda default clienti görsel update olarak işleme sebebim oyuncu tarafında UI default client olarak sayılır.
                # Eğer bunu kullanıcı clienti verirsen örnek olarak 100011 (ilk bağlanan kullanıcı clienti)
                # 100011 idli client oyuncu tarafında tanımlı değil.
                # Oyuncu tarafında sadece idsi 3 olan client tanımlı.
                # Normal olarak id 3 de oyunun kendi default clienti
                main_client = self.client
                game_load = Ctx.get("game_load")
                if game_load:
                    return self.journal.add(main_client, op, client_id=obj.id)

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

        self.send_message_all_clients(MSG_OBJECTS_VIEW_UPDATE, view_update)

    def add_event(self, msg_id, msg, immediate=False):
        self.events.append((msg_id, msg))
        if immediate:
            self.process_events()

    def process(self):
        if self.is_client:
            omega_ref = get_omega_ref()
            if omega_ref is not None:
                omega_ref.omega_emitter()
            # self.journal.clear()
        else:
            self.process_events()
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
            ops = journal.get_custom_ops()
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
        view_updates = {}

        # bağımsız takip etmek için akıllı bir takip sözlüğü açıyoruz
        client_last_processed = {}

        for op_obj in all_ops:
            obj_id, operation, payload_type, manager_id, obj_name = op_obj.op
            client_id = op_obj.client_id

            if view_updates.get(client_id) is None:
                view_updates[client_id] = protocols.ViewUpdate()
                client_last_processed[client_id] = (None, None)

            view_update = view_updates[client_id]
            last_obj_id, last_manager_id = client_last_processed[client_id]

            if obj_id != last_obj_id or manager_id != last_manager_id:
                entry = view_update.entries.add()
                entry.primary_channel.id.manager_id = manager_id
                entry.primary_channel.id.object_id = obj_id

                client_last_processed[client_id] = (obj_id, manager_id)
            else:
                entry = view_update.entries[-1]

            entry.operation_list.operations.append(operation)

        if view_updates:
            for client_id, view_up in view_updates.items():
                if client != "all" and client is not None and client.id == client_id:
                    client.send_message(
                        MSG_OBJECTS_VIEW_UPDATE, view_up, global_distributor=False
                    )
                elif client == "all":
                    self.send_view_up(view_up, client_id)

    def send_view_up(self, view_up, client_id):
        if client_id == "all":
            self.send_message_all_clients(MSG_OBJECTS_VIEW_UPDATE, view_up)
            return

        client = self.clients.get(client_id)
        if client is not None:
            client.send_message(MSG_OBJECTS_VIEW_UPDATE, view_up)

    def send_message_all_clients(self, msg_id, msg):
        for client in self.clients.values():
            try:
                client.send_message(msg_id, msg, global_distributor=True)
            except Exception as e:
                log.error(f"send_message_all_clients error: {e}")

    # ESKİ METHODLAR DÜZENLENECEK ŞİMDİLİK KALSIN
    def get_client_distributor_for_client_id(self, client_id):
        for dist in self.distributors:
            if dist.client.id == client_id:
                return dist

    def get_client_by_account_name(self, name):
        for client in self.clients.values():
            if client.account_name == name:
                return client
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

    def get_first_client(self):
        for dist in self.distributors:
            if dist.client is not None and dist.client.id < 10000:
                return dist.client
