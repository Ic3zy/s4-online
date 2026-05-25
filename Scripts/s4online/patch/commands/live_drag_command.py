from server.live_drag_tuning import LiveDragLocation
import gsi_handlers, objects.components.live_drag_component, services, sims4.commands, sims4.log, sims4.utils
from sims4.commands import CommandType, Command, unregister
from s4online.utils import Logger, Config
from s4online.networking import network_server

log = Logger(__name__)
logger = log

# TODO: refact this file


def live_drag_start(
    live_drag_object_id: int,
    start_system: LiveDragLocation,
    is_stack: bool = False,
    should_send_start_message: bool = True,
    _connection=None,
):
    current_zone = services.current_zone()
    live_drag_object = current_zone.find_object(live_drag_object_id)
    if gsi_handlers.live_drag_handlers.live_drag_archiver.enabled:
        gsi_handlers.live_drag_handlers.archive_live_drag(
            "Start",
            "Command",
            start_system,
            LiveDragLocation.GAMEPLAY_SCRIPT,
            live_drag_object=live_drag_object,
            live_drag_object_id=live_drag_object_id,
            live_drag_target=None,
        )
    client = services.client_manager().get(_connection)
    if client is None:
        logger.error("Client is not connected", owner="rmccord")
        sims4.commands.output("Client is not connected.", _connection)
        return
    if live_drag_object is None:
        logger.error(
            "Attempting to Live Drag an object that does not exist. object_id: {}".format(
                live_drag_object_id
            ),
            owner="rmccord",
        )
        sims4.commands.output(
            "Live Drag object with id: {} does not exist.".format(live_drag_object_id),
            _connection,
        )
        client.send_live_drag_cancel(
            live_drag_object_id, live_drag_end_system=start_system
        )
        return
    client.start_live_drag(
        live_drag_object, start_system, is_stack, should_send_start_message
    )


def live_drag_end(
    object_source_id: int,
    object_target_id: int,
    end_system: LiveDragLocation,
    _connection=None,
):
    current_zone = services.current_zone()
    source_object = current_zone.find_object(object_source_id)
    target_object = None
    if object_target_id:
        target_object = current_zone.find_object(object_target_id)
    if gsi_handlers.live_drag_handlers.live_drag_archiver.enabled:
        gsi_handlers.live_drag_handlers.archive_live_drag(
            "End",
            "Command",
            end_system,
            LiveDragLocation.GAMEPLAY_SCRIPT,
            live_drag_object=source_object,
            live_drag_object_id=object_source_id,
            live_drag_target=target_object,
        )
    if source_object is None:
        logger.error(
            "Ending Live Drag with an object that does not exist. object_id: {}".format(
                object_source_id
            ),
            owner="rmccord",
        )
        sims4.commands.output(
            "Live Drag object with id: {} does not exist.".format(object_source_id),
            _connection,
        )
        return
    if target_object is None and object_target_id:
        logger.error(
            "Ending Live Drag with a drop target that does not exist. object_id: {}".format(
                object_target_id
            ),
            owner="rmccord",
        )
        sims4.commands.output(
            "Live Drag target object with id: {} does not exist.".format(
                object_target_id
            ),
            _connection,
        )
        return
    client = services.client_manager().get(_connection)
    if client is None:
        logger.error("Client is not connected", owner="rmccord")
        sims4.commands.output("Client is not connected.", _connection)
        return
    if target_object is None:
        parent_obj = source_object.parent_object()
        if parent_obj is not None:
            target_object = parent_obj
    client.end_live_drag(source_object, target_object, end_system)


@sims4.utils.exception_protected(default_return=-1)
def c_api_live_drag_end(
    zone_id,
    obj_id,
    routing_surface,
    transform,
    parent_id,
    joint_name_or_hash,
    slot_hash,
):
    current_zone = services.current_zone()
    obj = current_zone.find_object(obj_id)
    client = services.client_manager().get_first_client()
    if client is None:
        logger.error("Client is not connected", owner="rmccord")
        return
    if obj is None:
        sims4.log.error(
            "BuildBuy",
            "Trying to place an invalid object id: {}",
            obj_id,
            owner="rmccord",
        )
        return
    if parent_id:
        parent_obj = current_zone.find_object(parent_id)
        if parent_obj is None:
            sims4.log.error(
                "BuildBuy",
                "Trying to parent an object to an invalid object id: {}",
                obj_id,
                owner="rmccord",
            )
            client.cancel_live_drag(obj, LiveDragLocation.BUILD_BUY)
            return
        location = sims4.math.Location(
            transform, routing_surface, parent_obj, joint_name_or_hash, slot_hash
        )
    else:
        parent_obj = None
        location = sims4.math.Location(transform, routing_surface)
    if gsi_handlers.live_drag_handlers.live_drag_archiver.enabled:
        gsi_handlers.live_drag_handlers.archive_live_drag(
            "End (C_API)",
            "Command",
            LiveDragLocation.BUILD_BUY,
            LiveDragLocation.GAMEPLAY_SCRIPT,
            live_drag_object=obj,
            live_drag_object_id=obj_id,
            live_drag_target=None,
        )
    client.end_live_drag(
        obj,
        target_object=parent_obj,
        end_system=LiveDragLocation.BUILD_BUY,
        location=location,
    )
    return obj


def live_drag_canceled(
    live_drag_object_id: int,
    end_system: LiveDragLocation = LiveDragLocation.INVALID,
    _connection=None,
):
    current_zone = services.current_zone()
    live_drag_object = current_zone.find_object(live_drag_object_id)
    if gsi_handlers.live_drag_handlers.live_drag_archiver.enabled:
        gsi_handlers.live_drag_handlers.archive_live_drag(
            "Cancel",
            "Command",
            end_system,
            LiveDragLocation.GAMEPLAY_SCRIPT,
            live_drag_object=live_drag_object,
            live_drag_object_id=live_drag_object_id,
        )
    if live_drag_object is None:
        logger.warn(
            "Canceling Live Drag on an object that does not exist. object_id: {}".format(
                live_drag_object_id
            ),
            owner="rmccord",
        )
        sims4.commands.output(
            "Live Drag object with id: {} does not exist.".format(live_drag_object_id),
            _connection,
        )
        return
    client = services.client_manager().get(_connection)
    if client is None:
        logger.error("Client is not connected", owner="rmccord")
        sims4.commands.output("Client is not connected.", _connection)
        return
    client.cancel_live_drag(live_drag_object, end_system)


def live_drag_sell(
    live_drag_object_id: int,
    currency_type: int,
    end_system: LiveDragLocation = LiveDragLocation.GAMEPLAY_UI,
    _connection=None,
):
    current_zone = services.current_zone()
    live_drag_object = current_zone.find_object(live_drag_object_id)
    if gsi_handlers.live_drag_handlers.live_drag_archiver.enabled:
        gsi_handlers.live_drag_handlers.archive_live_drag(
            "Sell",
            "Command",
            end_system,
            LiveDragLocation.GAMEPLAY_SCRIPT,
            live_drag_object=live_drag_object,
            live_drag_object_id=live_drag_object_id,
        )
    if live_drag_object is None:
        logger.error(
            "Attempting to Sell an object that does not exist. object_id: {}".format(
                live_drag_object_id
            ),
            owner="rmccord",
        )
        sims4.commands.output(
            "Live Drag object with id: {} does not exist.".format(live_drag_object_id),
            _connection,
        )
        return
    client = services.client_manager().get_first_client()
    if client is None:
        logger.error("Client is not connected", owner="rmccord")
        sims4.commands.output("Client is not connected.", _connection)
        return
    client.sell_live_drag_object(live_drag_object, currency_type, end_system)


# ---------- Client Works ----------


def client_live_drag_end(
    object_source_id: int,
    object_target_id: int,
    end_system,
    _connection=None,
):
    # eğer target_id boş ise obje dünya üstünde sürüklenmiş olarak algılayacağız.
    if not object_target_id:
        obj = services.object_manager().get(object_source_id)
        if not obj:
            return log.error(f"obje bulunamadı: {object_source_id}")
        else:
            position = obj.position
            send_live_drag_end_message(
                object_source_id=object_source_id,
                position=position,
                end_system=end_system,
            )


# ERROR
# TODO: fix
def send_live_drag_end_message(
    object_source_id: int,
    position,
    end_system,
    target_object=0,
):
    _instance = None
    if _instance is None:
        return log.error(f"network server is None")
    if target_object == 0 or not target_object:
        target_object = 0
        x = position.x
        y = position.y
        z = position.z
        message = {
            "command_name": "live_drag.end",
            "pattern": {"type": "live_drag_end"},
            "position": {"x": x, "y": y, "z": z},
            "object_source_id": object_source_id,
            "end_system": end_system,
            "args": (object_source_id, target_object, end_system),
            "kwargs": {},
        }
        _instance.send_message_all_clients(message)
    else:
        message = {
            "command_name": "live_drag.end",
            "pattern": {"type": "server_command"},
            "args": (object_source_id, target_object, end_system),
            "kwargs": {},
        }
        _instance.send_message_all_clients(message)


# DEBUG
def inject(a: bool = True):
    command_list = {
        "live_drag.start": live_drag_start,
        "live_drag.sell": live_drag_sell,
        "live_drag.canceled": live_drag_canceled,
        "live_drag.end": live_drag_end,
    }
    if a:
        if not Config.is_client:
            # _instance = network_server._network_instance
            _instance = None
            if _instance is not None:
                _instance.ev.on({"type": "live_drag_end"}, live_drag_end_host_render)
            for command_name in command_list:
                command = command_list[command_name]
                unregister(command_name)
                Command(command_name, command_type=CommandType.Live)(command)
        else:
            unregister("live_drag.end")
            Command("live_drag.end", command_type=CommandType.Live)(
                client_live_drag_end
            )
    else:
        if not Config.is_client:
            for command_name in command_list:
                command = command_list[command_name]
                unregister(command_name)
        else:
            unregister("live_drag.end")
            from server_commands.live_drag_commands import live_drag_end as lde

            Command("live_drag.end", command_type=CommandType.Live)(lde)
