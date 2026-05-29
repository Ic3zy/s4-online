from sims4.commands import Command, CommandType, unregister, CheatOutput
from s4online.utils import Logger
from .map_commands import (
    COMMAND_LIST,
    HOST_REPLACEMENT_LIST,
    CLIENT_REPLACEMENT_LIST,
    HOST_BLOCK,
    CLIENT_BLOCK,
)
from .do_command import do_command_from_network
import sims4.math, services
from .do_command import do_command_from_network

log = Logger(__name__)


def check_replacement(command_name, is_client):
    LIST = CLIENT_REPLACEMENT_LIST if is_client else HOST_REPLACEMENT_LIST
    return LIST.get(command_name)


def check_blocked(command_name, is_client):
    LIST = CLIENT_BLOCK if is_client else HOST_BLOCK
    if command_name in LIST:
        return lambda *a, **k: None
    return None


def create_wrap(command_name, enet_Server):
    def wrap(*args, **kwargs):
        try:
            data = {
                "pattern": {"type": "server_command"},
                "args": args,
                "kwargs": kwargs,
                "command_name": command_name,
            }
            enet_Server.send_message_all_clients(data)
        except Exception as e:
            log.error(f"inject error :: {e}")

    return wrap


def get_command(command_name, enet_server, is_client):
    blocked = check_blocked(command_name, is_client)
    if blocked:
        return blocked

    replacement = check_replacement(command_name, is_client)
    if replacement:
        return replacement

    return create_wrap(command_name, enet_server)


def move_object_safe(obj_id, x: int = 0, y: int = 0, z: int = 0):
    obj = services.object_manager().get(obj_id)
    if obj is None:
        log.warning(f"Obje bulunamadı. : {obj_id}")
        return

    pos = sims4.math.Vector3(x, y, z)
    rot = sims4.math.Quaternion(0, 0, 0, 1)

    obj.move_to(translation=pos, orientation=rot)

    log.debug("Obje güvenli şekilde taşındı.")


def live_drag_end_host_render(data):

    log.debug(f"live_drag_end_host_render: {data}")

    # moving the object this way because the games original function doesnt include any move operation.
    object_source_id = data.get("object_source_id")
    position = data.get("position")
    if position and object_source_id:
        move_object_safe(
            object_source_id, x=position["x"], y=position["y"], z=position["z"]
        )
    # Call the original function
    do_command_from_network(data)


def inject(enet_Server, is_client):
    if is_client:
        for command_name, command in COMMAND_LIST.items():
            try:
                unregister(command_name)
                wrap = get_command(command_name, enet_Server, is_client)
                Command(command_name, command_type=CommandType.Live)(wrap)
            except Exception as e:
                log.error(f"ERROR inject :: {e}")
    else:
        for command_name in HOST_BLOCK:
            unregister(command_name)
            Command(command_name, command_type=CommandType.Live)(lambda *a, **k: None)
        for command_name, command in HOST_REPLACEMENT_LIST.items():
            unregister(command_name)
            Command(command_name, command_type=CommandType.Live)(command)

        # enet_Server.ev.on({"type": "server_command"}, do_command_from_network)
        # enet_Server.ev.on({"type": "live_drag_end"}, live_drag_end_host_render)


def uninject():
    for command_name, command in COMMAND_LIST.items():
        try:
            unregister(command_name)
            Command(command_name, command_type=CommandType.Live)(command)
        except Exception as e:
            log.error(f"ERROR inject :: {e}")
