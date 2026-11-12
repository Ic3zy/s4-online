# YANLIŞ OLANLAR:
# from s4online.networking import start as start_server
# from s4online.networking import stop as stop_server

# DOĞRU OLAN: Modülü direkt olarak import et
from s4online import networking
import distributor.system, services
from s4online.core import (
    inject_distributor,
    inject_omega,
    uninject_distributor,
    uninject_omega,
)
from s4online.patch import inject, inject_time, uninject, uninject_time
from s4online.patch.object_sync import inject_object_sync, uninject_object_sync
from s4online.patch.stair_portal_guard import (
    inject_stair_portal_guard,
    uninject_stair_portal_guard,
)
from s4online.utils import Config, Logger, show_notification
from sims4.commands import CheatOutput, Command, CommandType, unregister
from s4online.utils import load_pyd
from s4online.base import Ctx

from social_media.social_media_service import SocialMediaService

from server_commands.interaction_commands import has_choices
from server.pick_info import (
    PickInfo,
    PickType,
    PICK_USE_TERRAIN_OBJECT,
    PICK_NEVER_USE_POOL,
)
import objects.system

log = Logger(__name__)
is_client = Config.is_client


rapid = load_pyd("rapidjson", "rapidjson.cp37-win_amd64.pyd")
s4cpoxide = load_pyd("s4cpoxide", "s4cpoxide.pyd")

# print = log.log

# active_client_peer = None


# def on_packet_received(packet):
#     global active_client_peer
#     print(f"📥 [HOST] -> Paket Geldi: {packet}")

#     # Eğer gelen paket PING ise, client'a anında PONG üfle!
#     if packet == "PING":
#         if active_client_peer is not None:
#             # Rust içi try_send kullanan o kurşun geçirmez, non-blocking mermi!
#             active_client_peer.send("PONG")
#         else:
#             print("🚨 [HOST] -> Paket geldi ama active peer referansı henüz yok!")


# def on_peer_connected(peer):
#     global active_client_peer
#     active_client_peer = peer
#     print(f"🟢 [HOST] -> YENİ BİR PEER SIZDI AQ! Adres: {peer.ip_address}")


# print("🚀 [HOST] -> Rust Network Core 127.0.0.1:8888 üzerinde tetikleniyor...")

# # Rust makine dairesini host modunda asenkron fırlatıyoruz. GIL anında boşa çıkıyor!
# s4cpoxide.start_host("0.0.0.0:8888", on_packet_received, on_peer_connected)


def inject_all(is_client, b) -> bool:
    # Fonksiyonu modül üzerinden çağırıyoruz
    network_server = networking.start()
    if network_server is None:
        return False
    # omega inject
    inject_omega(network_server, is_client)
    # distributor inject
    # yeni akışta gerek yok çünkü hot install
    # if b:
    #     inject_distributor(is_client)
    # inject_distributor(is_client)
    # Ignore missing native stair data on clients only.
    inject_stair_portal_guard(is_client)
    # host-authoritative object lifecycle and parent/location sync
    inject_object_sync(network_server, is_client)
    # commands inject
    inject(network_server, is_client)
    # inject_time(is_client)
    return True


def uninject_all():
    uninject_stair_portal_guard()
    uninject_object_sync()
    uninject_time(is_client)
    # stop_loop()
    uninject_distributor()

    # Fonksiyonu modül üzerinden çağırıyoruz
    networking.stop()

    uninject()
    uninject_omega()


def uninject_distributors():
    new_dist = distributor.system.Distributor()
    new_dist.add_client(services.client_manager().get_first_client())
    distributor.system._distributor_instance = new_dist


@Command("blockevent", command_type=CommandType.Live)
def eventblocker(_connection=None):
    output = CheatOutput(_connection)
    output("event blocker")
    if not Ctx.get("block_events"):
        Ctx.block_events = True
    else:
        Ctx.block_events = not Ctx.block_events

    output(f"block events: {Ctx.get('block_events')}")


@Command("start", command_type=CommandType.Live)
def start(a: bool = False, b: bool = False, _connection=None):
    output = log.log
    try:
        if not a:
            output("injecting...")
            output("you are client" if is_client else "you are server")
            result = inject_all(is_client, b=b)
            output("inject done" if result else "inject fail")
            show_notification(
                f"created s4online.\nYou are: {'Client' if is_client else 'Server'}"
            )
        else:
            uninject_all()
            output("uninject done")
            show_notification("closed s4online.")
    except Exception as e:
        show_notification("occured error.")
        output(f"error: {e}")
        import traceback

        log.error(traceback.format_exc())


start()


@Command("alive", command_type=CommandType.Live)
def alive(_connection=None):
    output = CheatOutput(_connection)
    output("I'm alive")
    output(f"connection: {_connection}")
    import services

    clients_count = services.client_manager()._objects
    output(f"clients: {clients_count}")

    cur_ac = services.account_service().get_current_account()
    output(f"account: {cur_ac}")


@Command("time_advence", command_type=CommandType.Live)
def time_advence(hours: int, mint: int, _connection=None):
    services.game_clock_service().advance_game_time(
        hours=hours, minutes=mint, seconds=0
    )
    CheatOutput(_connection)(f"Oyun {hours} saat {mint} dakika ilerletildi")


@Command("testphone", command_type=CommandType.Live)
def testphone(_connection=None):
    output = CheatOutput(_connection)
    output("testphone")
    try:

        unregister("careers.send_to_work")

        def new_phc(*a, **kw):
            output(f"{a}, {kw}")

        Command("careers.send_to_work", command_type=CommandType.Live)(new_phc)

    except Exception as e:
        output(f"error: {e}")


@Command("testphone2", command_type=CommandType.Live)
def testphone2(_connection=None):
    output = CheatOutput(_connection)
    output("testphone")
    try:
        pass
    except Exception as e:
        output(f"error: {e}")


@Command("debughaschoices", command_type=CommandType.Live)
def debughaschoices(reverse: bool = False, _connection=None):
    output = CheatOutput(_connection)
    output("debughaschoices")
    try:
        unregister("interactions.has_choices")

        def debugger(
            target_id=None,
            pick_type=PickType.PICK_TERRAIN,
            x=0.0,
            y=0.0,
            z=0.0,
            lot_id=0,
            level=0,
            control=0,
            alt=0,
            shift=0,
            reference_id=0,
            is_routable=True,
            _connection=None,
        ):
            output(
                f"{target_id}, {pick_type}, {x}, {y}, {z}, {lot_id}, {level}, {control}, {alt}, {shift}, {reference_id}, {is_routable}"
            )
            log.debug(
                f"{target_id}, {pick_type}, {x}, {y}, {z}, {lot_id}, {level}, {control}, {alt}, {shift}, {reference_id}, {is_routable}"
            )
            return has_choices(
                target_id,
                pick_type,
                x,
                y,
                z,
                lot_id,
                level,
                control,
                alt,
                shift,
                reference_id,
                is_routable,
            )

        com = debugger
        if reverse:
            com = has_choices

        Command("interactions.has_choices", command_type=CommandType.Live)(com)

    except Exception as e:
        output(f"error: {e}")


import functools

_capi_transform_watch_id = 0
_capi_transform_watch_installed = False
_capi_transform_originals = {}


def _install_capi_transform_watch():
    global _capi_transform_watch_installed

    if _capi_transform_watch_installed:
        return

    original_set_parent = objects.system.c_api_set_parent_object
    original_clear_parent = objects.system.c_api_clear_parent_object
    _capi_transform_originals.update(
        set_parent=original_set_parent,
        clear_parent=original_clear_parent,
    )

    @functools.wraps(original_set_parent)
    def hooked_set_parent(obj_id, parent_id, transform, joint_name, slot_hash, zone_id):
        if not _capi_transform_watch_id or obj_id == _capi_transform_watch_id:
            log.debug(
                f"[CAPI-TRANSFORM] c_api_set_parent_object id={obj_id} "
                f"parent_id={parent_id} transform={transform!r} "
                f"joint={joint_name!r} slot={slot_hash!r} zone={zone_id}"
            )
        return original_set_parent(
            obj_id, parent_id, transform, joint_name, slot_hash, zone_id
        )

    @functools.wraps(original_clear_parent)
    def hooked_clear_parent(obj_id, transform, zone_id, surface):
        if not _capi_transform_watch_id or obj_id == _capi_transform_watch_id:
            log.debug(
                f"[CAPI-TRANSFORM] c_api_clear_parent_object id={obj_id} "
                f"transform={transform!r} zone={zone_id} surface={surface!r}"
            )
        return original_clear_parent(obj_id, transform, zone_id, surface)

    objects.system.c_api_set_parent_object = hooked_set_parent
    objects.system.c_api_clear_parent_object = hooked_clear_parent
    _capi_transform_watch_installed = True


def _remove_capi_transform_watch():
    global _capi_transform_watch_installed

    if not _capi_transform_watch_installed:
        return

    objects.system.c_api_set_parent_object = _capi_transform_originals["set_parent"]
    objects.system.c_api_clear_parent_object = _capi_transform_originals["clear_parent"]
    _capi_transform_originals.clear()
    _capi_transform_watch_installed = False


@Command("capi_transform_watch", command_type=CommandType.Live)
def capi_transform_watch(obj_id: int = 0, enabled: bool = True, _connection=None):
    global _capi_transform_watch_id

    if not enabled:
        _remove_capi_transform_watch()
        log.debug("[CAPI-TRANSFORM] Watch disabled.")
        return

    _capi_transform_watch_id = obj_id
    _install_capi_transform_watch()
    if obj_id:
        log.debug(f"[CAPI-TRANSFORM] Watching ID {obj_id}.")
    else:
        log.debug("[CAPI-TRANSFORM] Watching all IDs.")


@Command("object_location", command_type=CommandType.Live)
def object_location(obj_id: int, _connection=None):
    output = CheatOutput(_connection)
    obj = services.current_zone().find_object(obj_id)
    if obj is None:
        message = f"[OBJECT-LOCATION] Object not found in Python: id={obj_id}"
        log.debug(message)
        output(message)
        return

    parent = obj.parent_object()
    message = (
        f"[OBJECT-LOCATION] id={obj_id} location={obj.location!r} "
        f"parent_id={getattr(parent, 'id', None)} slot={obj.parent_slot!r}"
    )
    log.debug(message)
    output(message)


import objects.system
from indexed_manager import IndexedManager
import traceback


@Command("objtest", command_type=CommandType.Live)
def objtest(_connection=None):
    output = CheatOutput(_connection)
    object_id = 530043180955533337

    manager = services.object_manager()

    try:
        original = manager.get(object_id)

        if original is None:
            output("Original object not found")
            return

        definition = original.definition
        position = original.position
        orientation = original.orientation
        routing_surface = original.routing_surface

        # Create a new Python GameObject without registering it.
        new_obj = objects.system.create_script_object(definition)

        if new_obj is None:
            output("Script object creation failed")
            return

        # Set location while ID is still 0 and manager is None.
        new_obj.move_to(
            translation=position,
            orientation=orientation,
            routing_surface=routing_surface,
        )

        # Assign the original ID only after location initialization.
        new_obj.id = object_id

        # Temporarily suppress distributor removal.
        had_remove_override = "remove_from_client" in manager.__dict__
        old_remove_override = manager.__dict__.get("remove_from_client")

        manager.remove_from_client = lambda obj, **kwargs: None

        try:
            manager.remove(original)
        finally:
            if had_remove_override:
                manager.remove_from_client = old_remove_override
            else:
                del manager.remove_from_client

        if manager.get(object_id) is not None:
            output("Original object removal failed")
            return

        # Suppress Distributor.add_object while preserving normal callbacks.
        had_add_override = "call_on_add" in manager.__dict__
        old_add_override = manager.__dict__.get("call_on_add")

        manager.call_on_add = IndexedManager.call_on_add.__get__(manager, type(manager))

        # try:
        #     manager.add(new_obj)
        # finally:
        #     if had_add_override:
        #         manager.call_on_add = old_add_override
        #     else:
        #         del manager.call_on_add

        result = manager.get(object_id)

        if result is not new_obj:
            output("Replacement registration failed")
            return

        output(
            f"Replacement successful: ID={new_obj.id}, "
            f"same_id={new_obj.id == object_id}"
        )

        log.debug(
            "Object replacement: id={} definition={} class={} position={}".format(
                new_obj.id,
                new_obj.definition.id,
                type(new_obj).__name__,
                new_obj.position,
            )
        )

    except Exception:
        error_traceback = traceback.format_exc()

        output("Object replacement failed. Check log.")
        log.error("Object replacement traceback:\n{}".format(error_traceback))


@Command("logsc", command_type=CommandType.Live)
def logsc(name: str, _connection=None):
    output = CheatOutput(_connection)
    try:

        def logger(*a, **k):
            output(f"{name}, args: [{a}], kwargs: [{k}]")

        unregister(name)
        Command(name, command_type=CommandType.live)(logger)
    except Exception as e:
        output(f"Error: {e}")
