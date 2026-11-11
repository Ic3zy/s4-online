"""Host-authoritative object lifecycle and parenting mirror."""

import copy
import functools

import objects.system
import routing
import services
from indexed_manager import CallbackTypes
from objects.object_enums import ItemLocation
from protocolbuffers import FileSerialization_pb2
from s4online.base import Ctx
from s4online.utils import Logger, load_pyd

log = Logger(__name__)
dispatcher = load_pyd("dispatcher", "dispatcher.pyd")
_EVENT = "object_sync"

_enabled = False
_is_client = False
_network = None
_manager = None
_original_add = None
_original_remove = None
_original_add_attr = None
_original_remove_attr = None
_original_send_auth = None
_original_send_auth_attr = None
_original_accept_thread = None
_original_accept_attr = None
_synced_ids = set()
_authorized_remove_ids = set()
_pending = {}
_applying = 0
_snapshot_ready = False
_bind_callback_registered = False


def _transform_data(transform):
    position, orientation = transform.translation, transform.orientation
    return [
        float(position.x), float(position.y), float(position.z),
        float(orientation.x), float(orientation.y),
        float(orientation.z), float(orientation.w),
    ]


def _make_transform(values):
    import sims4.math

    position = sims4.math.Vector3(float(values[0]), float(values[1]), float(values[2]))
    orientation = sims4.math.Quaternion(
        float(values[3]), float(values[4]), float(values[5]), float(values[6])
    )
    return sims4.math.Transform(position, orientation)


def _surface_data(surface):
    if surface is None:
        return None
    return [int(surface.primary_id), int(surface.secondary_id), int(surface.type)]


def _make_surface(values):
    if values is None:
        return None
    return routing.SurfaceIdentifier(
        int(values[0]), int(values[1]), routing.SurfaceType(int(values[2]))
    )


def _location_data(obj):
    location = obj.location
    parent = obj.parent_object()
    joint = location.joint_name_or_hash
    if joint is not None and not isinstance(joint, (str, int, float, bool)):
        joint = None
    return {
        "transform": _transform_data(location.transform),
        "surface": _surface_data(location.routing_surface),
        "parent_id": int(parent.id) if parent is not None else 0,
        "joint": joint,
        "slot": int(location.slot_hash or 0),
    }


def _serialize_object(obj):
    object_list = FileSerialization_pb2.ObjectList()
    saved = obj.save_object(object_list.objects, ItemLocation.ON_LOT, 0, from_bb=True)
    if saved is None:
        # Some runtime objects opt out of save eligibility. Preserve their
        # component attributes in the same ObjectData envelope where possible.
        saved = FileSerialization_pb2.ObjectData()
        saved.object_id = int(obj.id)
        saved.guid = int(obj.definition.id)
        saved.state_index = int(obj.state_index)
        attribute_data = obj.get_attribute_save_data()
        if attribute_data is not None:
            saved.attributes = attribute_data.SerializeToString()
    return saved.SerializeToString().hex()


def _send(data, client=None):
    # TransactionQueue only accepts list payloads and coalesces adjacent
    # messages of the same event type by extending this list. Give every
    # client's queue a distinct message/list; the network fan-out otherwise
    # shares the same mutable payload object between queues.
    if client is not None:
        client.send_message({"pattern": {"type": _EVENT}, "data": [data]})
    elif _network is not None and not _is_client:
        for target in tuple(_network.clients.values()):
            target.send_message({"pattern": {"type": _EVENT}, "data": [copy.deepcopy(data)]})


def _host_add(obj):
    if not _enabled or _is_client:
        return
    if getattr(obj, "is_sim", False) or getattr(obj, "is_prop", False):
        return
    try:
        data = {
            "action": "add",
            "object_id": int(obj.id),
            "definition_id": int(obj.definition.id),
            "state_index": int(obj.state_index),
            "item_location": int(obj.item_location),
            "content_source": int(obj.content_source),
            "object_data": _serialize_object(obj),
        }
        data.update(_location_data(obj))
        _send(data)
    except Exception as exc:
        log.exception(f"[OBJECT-SYNC] add serialization failed id={getattr(obj, 'id', None)}: {exc}")


def _host_remove(object_id):
    if _enabled and not _is_client:
        _send({"action": "remove", "object_id": int(object_id)})


def _host_location(obj):
    if not _enabled or _is_client or _applying or getattr(obj, "is_sim", False):
        return
    try:
        data = {"action": "location", "object_id": int(obj.id)}
        data.update(_location_data(obj))
        _send(data)
    except Exception as exc:
        log.exception(f"[OBJECT-SYNC] location send failed id={getattr(obj, 'id', None)}: {exc}")


def _client_location(obj):
    if not _enabled or not _is_client or _applying:
        return
    if getattr(obj, "is_sim", False) or getattr(obj, "is_prop", False):
        return
    try:
        data = {"action": "client_location", "object_id": int(obj.id)}
        data.update(_location_data(obj))
        _send_client_location(data)
    except Exception as exc:
        log.exception(f"[OBJECT-SYNC] client location send failed id={getattr(obj, 'id', None)}: {exc}")


def _send_client_location(data):
    if _network is None or not _is_client:
        return
    _network.send_message_all_clients({"pattern": {"type": _EVENT}, "data": [data]})
    log.info("[OBJECT-SYNC] client location queued id={} parent={}".format(data["object_id"], data.get("parent_id", 0)))


def _apply_host_client_location(data):
    object_id = int(data["object_id"])
    obj = services.object_manager().get(object_id)
    if obj is None or getattr(obj, "is_sim", False) or getattr(obj, "is_prop", False):
        log.warning("[OBJECT-SYNC] rejected client location for unavailable id={}".format(object_id))
        return
    if _apply_location(obj, data):
        log.info("[OBJECT-SYNC] host applied client location id={}".format(object_id))
        # Host becomes authoritative after accepting the client's transform.
        _host_location(obj)
    else:
        log.warning("[OBJECT-SYNC] host deferred client location id={}".format(object_id))


def _apply_location(obj, data):
    global _applying
    transform = _make_transform(data["transform"])
    surface = _make_surface(data.get("surface"))
    parent_id = int(data.get("parent_id") or 0)
    _applying += 1
    try:
        if parent_id:
            parent = services.current_zone().find_object(parent_id)
            if parent is None:
                return False
            obj.set_parent(
                parent,
                transform=transform,
                joint_name_or_hash=data.get("joint"),
                slot_hash=int(data.get("slot") or 0),
                routing_surface=surface,
            )
        elif obj.parent_object() is not None:
            obj.clear_parent(transform, surface)
        else:
            obj.move_to(transform=transform, routing_surface=surface)
        return True
    finally:
        _applying -= 1


def _apply_add(data):
    manager = services.object_manager()
    object_id = int(data["object_id"])
    existing = manager.get(object_id)
    if existing is not None:
        _synced_ids.add(object_id)
        return _apply_location(existing, data)

    parent_id = int(data.get("parent_id") or 0)
    if parent_id and services.current_zone().find_object(parent_id) is None:
        return False

    object_data = FileSerialization_pb2.ObjectData()
    object_data.ParseFromString(bytes.fromhex(data["object_data"]))

    def initialize(obj):
        pass

    def finalize(obj):
        # create_object's init callback runs before assigning obj_id and adding
        # the object to its manager. Restore persistence and location only after
        # it has been registered, as ScriptObject.clone() does for persistence.
        obj.load_object(object_data)
        obj.move_to(
            transform=_make_transform(data["transform"]),
            routing_surface=_make_surface(data.get("surface")),
        )

    global _applying
    _applying += 1
    try:
        obj = objects.system.create_object(
            int(data["definition_id"]),
            obj_id=object_id,
            obj_state=int(data.get("state_index", 0)),
            init=initialize,
            post_add=finalize,
            loc_type=int(data.get("item_location", int(ItemLocation.ON_LOT))),
            content_source=int(data.get("content_source", 0)),
            disable_object_commodity_callbacks=True,
        )
    finally:
        _applying -= 1

    if obj is None:
        log.error(f"[OBJECT-SYNC] client create failed id={object_id}")
        return True
    _synced_ids.add(object_id)
    if parent_id and not _apply_location(obj, data):
        return False
    log.info(f"[OBJECT-SYNC] client created id={object_id} definition={data['definition_id']}")
    return True


def _apply_remove(data):
    object_id = int(data["object_id"])
    _pending.pop(object_id, None)
    obj = services.object_manager().get(object_id)
    if obj is None:
        _synced_ids.discard(object_id)
        return
    _authorized_remove_ids.add(object_id)
    try:
        obj.destroy(source=obj, cause="Host-authoritative object sync removal")
        log.info(f"[OBJECT-SYNC] client removed id={object_id}")
    except Exception:
        _authorized_remove_ids.discard(object_id)
        raise


def _apply_message(data):
    global _snapshot_ready
    action = data.get("action")
    object_id = int(data.get("object_id", 0) or 0)
    if action == "snapshot_done":
        _pending.clear()
        # Treat the existing client world as host-owned now that the initial
        # authoritative snapshot is complete.
        for obj in services.object_manager().get_all():
            _synced_ids.add(int(obj.id))
        _snapshot_ready = True
        log.info(f"[OBJECT-SYNC] client snapshot applied objects={len(_synced_ids)}")
        return
    if action == "add":
        if not _apply_add(data):
            _pending[object_id] = data
    elif action == "remove":
        _apply_remove(data)
    elif action == "location":
        obj = services.object_manager().get(object_id)
        if obj is None or not _apply_location(obj, data):
            _pending[object_id] = data
        else:
            log.info(f"[OBJECT-SYNC] client location applied id={object_id}")

    # Child add/parent operations can arrive before their parent in a snapshot.
    for pending_id, pending_data in list(_pending.items()):
        if pending_id == object_id:
            continue
        if pending_data.get("action") == "add":
            if _apply_add(pending_data):
                _pending.pop(pending_id, None)
        elif pending_data.get("action") == "location":
            pending_obj = services.object_manager().get(pending_id)
            if pending_obj is not None and _apply_location(pending_obj, pending_data):
                _pending.pop(pending_id, None)


def _send_snapshot(message):
    requester = message.get("account_name")
    if not requester or _network is None:
        return
    target = next(
        (client for client in _network.clients.values() if client.account_name == requester),
        None,
    )
    if target is None:
        log.warning(f"[OBJECT-SYNC] snapshot requester not connected: {requester}")
        return
    queued = 0
    for obj in tuple(services.object_manager().get_all()):
        try:
            if getattr(obj, "is_sim", False) or getattr(obj, "is_prop", False):
                continue
            data = {
                "action": "add",
                "object_id": int(obj.id),
                "definition_id": int(obj.definition.id),
                "state_index": int(obj.state_index),
                "item_location": int(obj.item_location),
                "content_source": int(obj.content_source),
                "object_data": _serialize_object(obj),
            }
            data.update(_location_data(obj))
            _send(data, client=target)
            queued += 1
        except Exception as exc:
            log.exception(f"[OBJECT-SYNC] snapshot failed id={getattr(obj, 'id', None)}: {exc}")
    _send({"action": "snapshot_done"}, client=target)
    log.info(f"[OBJECT-SYNC] snapshot queued account={requester} objects={queued}")


def _process_client_batch(payload):
    for data in payload:
        if not isinstance(data, dict) or data.get("action") == "snapshot_request":
            continue
        try:
            _apply_message(data)
        except Exception as exc:
            log.exception("[OBJECT-SYNC] client apply failed action={}: {}".format(data.get("action"), exc))


def _process_host_batch(payload, requester):
    connected = any(
        client.account_name == requester
        for client in _network.clients.values()
    ) if requester and _network is not None else False
    for data in payload:
        if not isinstance(data, dict):
            continue
        action = data.get("action")
        if action == "snapshot_request":
            if not requester:
                log.warning("[OBJECT-SYNC] snapshot request missing account name")
                continue
            try:
                _send_snapshot({"account_name": requester})
            except Exception as exc:
                log.exception("[OBJECT-SYNC] snapshot failed: {}".format(exc))
        elif action == "client_location":
            if not connected:
                log.warning("[OBJECT-SYNC] rejected client location sender={}".format(requester))
                continue
            try:
                _apply_host_client_location(data)
            except Exception as exc:
                log.exception("[OBJECT-SYNC] host location apply failed: {}".format(exc))


def _receive(message):
    payload = message.get("data")
    # TransactionQueue batches adjacent events. Marshal each received packet
    # with one C-dispatcher call instead of one Py_AddPendingCall per object.
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return
    batch = [copy.deepcopy(data) for data in payload if isinstance(data, dict)]
    if not batch:
        return
    if _is_client:
        callback, args = _process_client_batch, (batch,)
    else:
        callback, args = _process_host_batch, (batch, message.get("account_name"))
    try:
        dispatcher.enqueue(callback, args)
    except Exception as exc:
        log.error("[OBJECT-SYNC] packet dispatch failed count={}: {}".format(len(batch), exc))
        return
    log.debug("[OBJECT-SYNC] packet scheduled count={} client={}".format(len(batch), _is_client))


def _request_snapshot():
    if _network is not None and _is_client:
        _network.send_message_all_clients(
            {"pattern": {"type": _EVENT}, "data": [{"action": "snapshot_request"}]}
        )


def _client_send_auth(*args, **kwargs):
    result = _original_send_auth(*args, **kwargs)
    _request_snapshot()
    return result


def _client_add(obj, *args, **kwargs):
    if _snapshot_ready and not _applying:
        log.warning(f"[OBJECT-SYNC] blocked client add id={getattr(obj, 'id', None)}")
        return None
    return _original_add(obj, *args, **kwargs)


def _client_remove(obj, *args, **kwargs):
    object_id = int(getattr(obj, "id", 0) or 0)
    if object_id in _authorized_remove_ids:
        _authorized_remove_ids.discard(object_id)
        result = _original_remove(obj, *args, **kwargs)
        _synced_ids.discard(object_id)
        return result
    if _snapshot_ready:
        log.warning(f"[OBJECT-SYNC] blocked client remove id={object_id}")
        return None
    return _original_remove(obj, *args, **kwargs)


def _host_add_wrapper(original):
    @functools.wraps(original)
    def add(obj, *args, **kwargs):
        result = original(obj, *args, **kwargs)
        if _manager.get(getattr(obj, "id", 0)) is obj:
            _host_add(obj)
        return result
    return add


def _host_remove_wrapper(original):
    @functools.wraps(original)
    def remove(obj, *args, **kwargs):
        object_id = int(getattr(obj, "id", 0) or 0)
        result = original(obj, *args, **kwargs)
        if object_id and _manager.get(object_id) is not obj:
            _host_remove(object_id)
        return result
    return remove


def _host_accept_thread_wrapper(original):
    @functools.wraps(original)
    def accept_thread(peer, name, reconnect=False):
        result = original(peer, name, reconnect=reconnect)
        try:
            dispatcher.enqueue(_send_snapshot, ({"account_name": name},))
        except Exception as exc:
            log.error(f"[OBJECT-SYNC] connect snapshot dispatch failed: {exc}")
        return result
    return accept_thread


def _bind_manager():
    global _manager, _original_add, _original_remove
    global _original_add_attr, _original_remove_attr
    manager = services.object_manager()
    if manager is None or manager is _manager:
        return
    _unbind_manager()
    _manager = manager
    _original_add_attr = manager.__dict__.get("add")
    _original_remove_attr = manager.__dict__.get("remove")
    _original_add, _original_remove = manager.add, manager.remove
    if _is_client:
        manager.add = _client_add
        manager.remove = _client_remove
        manager.register_callback(CallbackTypes.ON_OBJECT_LOCATION_CHANGED, _client_location)
        for obj in manager.get_all():
            _synced_ids.add(int(obj.id))
    else:
        manager.add = _host_add_wrapper(_original_add)
        manager.remove = _host_remove_wrapper(_original_remove)
        manager.register_callback(CallbackTypes.ON_OBJECT_LOCATION_CHANGED, _host_location)
    log.info(f"[OBJECT-SYNC] bound ObjectManager client={_is_client}")


def _restore_manager_method(manager, name, original_attr):
    if original_attr is None:
        if name in manager.__dict__:
            delattr(manager, name)
    else:
        setattr(manager, name, original_attr)


def _unbind_manager():
    global _manager, _original_add, _original_remove
    global _original_add_attr, _original_remove_attr
    manager = _manager
    if manager is None:
        return
    _restore_manager_method(manager, "add", _original_add_attr)
    _restore_manager_method(manager, "remove", _original_remove_attr)
    callback = _client_location if _is_client else _host_location
    try:
        manager.unregister_callback(CallbackTypes.ON_OBJECT_LOCATION_CHANGED, callback)
    except Exception as exc:
        log.warning(f"[OBJECT-SYNC] callback cleanup failed: {exc}")
    _manager = None
    _original_add = _original_remove = None
    _original_add_attr = _original_remove_attr = None


def _bind_on_game_load():
    global _bind_callback_registered
    try:
        _bind_manager()
    finally:
        _bind_callback_registered = False


def inject_object_sync(network, is_client):
    global _enabled, _is_client, _network, _original_send_auth, _original_send_auth_attr, _snapshot_ready
    global _original_accept_thread, _original_accept_attr, _bind_callback_registered
    if _enabled:
        uninject_object_sync()
    _enabled = True
    _is_client = bool(is_client)
    _network = network
    _snapshot_ready = False
    _synced_ids.clear()
    _authorized_remove_ids.clear()
    _pending.clear()
    network.ev.on({"type": _EVENT}, _receive)
    if _is_client:
        _original_send_auth_attr = network.__dict__.get("send_auth")
        _original_send_auth = network.send_auth
        network.send_auth = _client_send_auth
    else:
        _original_accept_attr = network.__dict__.get("accept_thread")
        _original_accept_thread = network.accept_thread
        network.accept_thread = _host_accept_thread_wrapper(_original_accept_thread)
        for existing_client in tuple(network.clients.values()):
            try:
                dispatcher.enqueue(_send_snapshot, ({"account_name": existing_client.account_name},))
            except Exception as exc:
                log.error(f"[OBJECT-SYNC] initial snapshot dispatch failed: {exc}")

    if services.object_manager() is None:
        log.info("[OBJECT-SYNC] ObjectManager not ready; binding deferred until game_load")
        if not _bind_callback_registered:
            Ctx.add_callback("game_load", _bind_on_game_load)
            _bind_callback_registered = True
    else:
        _bind_manager()


def uninject_object_sync():
    global _enabled, _network, _original_send_auth, _original_accept_thread
    global _original_accept_attr, _original_send_auth_attr, _bind_callback_registered, _snapshot_ready
    if not _enabled:
        return
    network = _network
    if network is not None:
        network.ev.off({"type": _EVENT}, _receive)
        if _is_client and _original_send_auth is not None:
            if _original_send_auth_attr is None:
                del network.send_auth
            else:
                network.send_auth = _original_send_auth_attr
        if not _is_client and _original_accept_thread is not None:
            if _original_accept_attr is None:
                del network.accept_thread
            else:
                network.accept_thread = _original_accept_attr
    if _bind_callback_registered:
        try:
            Ctx.remove_callback("game_load", _bind_on_game_load)
        except Exception:
            pass
    _bind_callback_registered = False
    _unbind_manager()
    _enabled = False
    _network = None
    _original_send_auth = None
    _original_send_auth_attr = None
    _original_accept_thread = None
    _original_accept_attr = None
    _snapshot_ready = False
    _synced_ids.clear()
    _authorized_remove_ids.clear()
    _pending.clear()
