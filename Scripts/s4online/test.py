from sims4.commands import Command, CommandType, unregister, CheatOutput

from s4online.utils import Logger, Config
from s4online.patch import inject, uninject
from s4online.core import (
    inject_distributor,
    uninject_distributor,
    inject_omega,
    uninject_omega,
)
from s4online.networking import start as start_server
from s4online.networking import stop as stop_server
import distributor.system, services
from distributor.system import Distributor
from server_commands.live_drag_commands import live_drag_end
from server.live_drag_tuning import LiveDragLocation
import sims4


from server_commands.interaction_commands import (
    has_choices,
    generate_choices,
    generate_phone_choices,
    select_choice,
    cancel_mixer_interaction,
    cancel_super_interaction,
    push_interaction,
)


log = Logger(__name__)

is_client = Config.is_client


def move_object_safe(obj_id, x: int = 0, y: int = 0, z: int = 0):
    obj = services.object_manager().get(obj_id)
    if obj is None:
        log.error("Obje bulunamadı.")
        return

    pos = sims4.math.Vector3(429.303101, 150.000015, 349.150360)
    rot = sims4.math.Quaternion(0, 0, 0, 1)

    # EA imzasına uygun: sadece keyword arg
    obj.move_to(translation=pos, orientation=rot)


@Command("test", command_type=CommandType.Live)
def a(_connection=None):
    outs = CheatOutput(_connection)
    try:
        unregister("interactions.choices")
        Command("interactions.choices", command_type=CommandType.Live)(generate_choices)
        outs("ok")
    except Exception as e:
        outs(f"Hata: {e}")


@Command("tests", command_type=CommandType.Live)
def tests(a: bool = True, _connection=None):
    outs = CheatOutput(_connection)
    outs("test start")
    try:
        move_object_safe(909187801544464529)
    except Exception as e:
        outs(f"Hata: {e}")


@Command("distres", command_type=CommandType.Live)
def resetdist(_connection=None):
    output = CheatOutput(_connection)
    try:
        new_distributor = Distributor()
        new_distributor.add_client(services.client_manager().get_first_client())
        distributor.system._distributor_instance = new_distributor
        output("distributor reset")
    except Exception as e:
        output(f"error: {e}")


@Command("getcon", command_type=CommandType.Live)
def getcon(_connection=None):
    output = CheatOutput(_connection)
    try:
        output(str(services.client_manager().get_first_client().id))
        output(str(_connection))
    except Exception as e:
        output(f"error: {e}")


@Command("tests2", command_type=CommandType.Live)
def tests(a: bool = True, _connection=None):
    outs = CheatOutput(_connection)
    outs("test start")
    try:
        if a:
            unregister("live_drag.end")

            def new_end(
                object_source_id: int,
                object_target_id: int,
                end_system: LiveDragLocation,
                _connection=None,
            ):
                try:
                    outs(
                        f"new end: {object_source_id}, {object_target_id}, {end_system}"
                    )
                    obj = services.object_manager().get(object_source_id)
                    if obj:
                        pos = obj.position
                        outs(f"Objenin konumu: {pos}")
                    else:
                        outs(f"Obje bulunamadı: {object_source_id}")
                    move_object_safe(object_source_id)
                except Exception as e:
                    outs(f"Hata: {e}")

            Command("live_drag.end", command_type=CommandType.Live)(new_end)
        else:
            unregister("live_drag.end")
            Command("live_drag.end", command_type=CommandType.Live)(live_drag_end)
    except Exception as e:
        outs(f"Hata: {e}")
