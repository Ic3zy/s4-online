from business.business_enums import BusinessType
from distributor.system import Distributor

from interactions.choices import ChoiceMenu
from server.pick_info import (
    PickInfo,
    PickType,
)
import gsi_handlers.sim_handlers_log, interactions.social.social_mixer_interaction, interactions.utils.outcome, services, telemetry_helper

import sims4.math

from server_commands.interaction_commands import (
    _active_sim,
    should_generate_pie_menu,
    PieMenuActions,
    _get_targets_from_pick,
    create_pie_menu_message,
    writer,
    TELEMETRY_HOOK_CREATE_PIE_MENU,
)

import sims4
import services
import autonomy.content_sets
import interactions.social.social_mixer_interaction
import interactions.utils.outcome

from interactions.choices import ChoiceMenu

from server.pick_info import PickInfo, PickType

from server_commands.interaction_commands import (
    _get_targets_from_pick,
    _active_sim,
    _get_interactable_flags,
)

from distributor.system import Distributor

from protocolbuffers import (
    InteractionOps_pb2 as interaction_protocol,
    Sims_pb2 as protocols,
    Consts_pb2,
)

from sims4.commands import Command, CommandType, unregister, CheatOutput
from s4online.utils import Logger

import _omega, omega

log = Logger(__name__)


def generate_choices(
    target_id: int = None,
    pick_type: PickType = PickType.PICK_TERRAIN,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    lot_id: int = 0,
    level: int = 0,
    control: int = 0,
    alt: int = 0,
    shift: int = 0,
    reference_id: int = 0,
    referred_object_id: int = 0,
    preferred_object_id: int = 0,
    is_routable: bool = True,
    _connection=None,
):
    # Early outs
    if alt or control:
        return 0
    if target_id is None:
        return 0

    zone = services.current_zone()
    client = services.client_manager().get(_connection)
    sim = _active_sim(client)
    shift_held = bool(shift)

    context = None
    choice_menu = ChoiceMenu(sim)
    pick_target = zone.find_object(target_id)

    preferred_object = None
    if preferred_object_id is not None:
        preferred_object = services.object_manager().get(preferred_object_id)
    preferred_objects = set() if preferred_object is None else {preferred_object}

    pie_menu_action = should_generate_pie_menu(client, sim, shift_held)
    show_pie_menu = pie_menu_action == PieMenuActions.SHOW_PIE_MENU
    show_debug_pie_menu = pie_menu_action == PieMenuActions.SHOW_DEBUG_PIE_MENU

    suppress_social_front_page = False
    scoring_gsi_handler = (
        {}
        if gsi_handlers.sim_handlers_log.pie_menu_generation_archiver.enabled
        else None
    )

    if show_pie_menu or show_debug_pie_menu:
        # 1) Portrait / Club Panel
        if pick_type in (PickType.PICK_PORTRAIT, PickType.PICK_CLUB_PANEL):
            sim_info = services.sim_info_manager().get(target_id)
            object_info = services.object_manager().get(target_id)
            inventory_object_info = services.inventory_manager().get(target_id)

            if (
                sim_info is None
                and object_info is None
                and inventory_object_info is None
            ):
                return 0
            if sim is None:
                return 0

            picked_item_ids = {target_id}
            context = client.create_interaction_context(sim, target_sim_id=target_id)
            context.add_preferred_objects(preferred_objects)

            target = object_info or inventory_object_info or sim
            potential_interactions = list(
                sim.potential_relation_panel_interactions(
                    target, context, picked_item_ids=picked_item_ids
                )
            )
            choice_menu.add_potential_aops(
                sim_info, context, potential_interactions, scoring_gsi_handler
            )
            client.set_choices(choice_menu)

        # 2) Skewer
        elif pick_type == PickType.PICK_SKEWER:
            sim_info = services.sim_info_manager().get(target_id)
            if sim_info is None:
                return 0
            skewer_sim = sim_info.get_sim_instance()
            context = client.create_interaction_context(skewer_sim)
            context.add_preferred_objects(preferred_objects)
            potential_interactions = list(
                sim_info.sim_skewer_affordance_gen(
                    context, picked_item_ids={client.active_sim_info.sim_id}
                )
            )
            choice_menu.add_potential_aops(
                pick_target, context, potential_interactions, scoring_gsi_handler
            )
            client.set_choices(choice_menu)

        # 3) Manage Outfits
        elif pick_type == PickType.PICK_MANAGE_OUTFITS:
            context = client.create_interaction_context(sim)
            retail_manager = services.business_service().get_retail_manager_for_zone()
            potential_interactions = []
            if retail_manager is not None:
                potential_interactions = list(
                    retail_manager.potential_manage_outfit_interactions_gen(context)
                )
            choice_menu.add_potential_aops(
                pick_target, context, potential_interactions, scoring_gsi_handler
            )
            client.set_choices(choice_menu)

        # 4) Small Business Manage Outfit
        elif pick_type == PickType.PICK_MANAGE_SMALL_BUSINESS_OUTFIT:
            context = client.create_interaction_context(sim)
            potential_interactions = []
            business_manager = services.business_service().get_business_manager_for_sim(
                sim_id=sim.id
            )
            if (
                business_manager is not None
                and business_manager.business_type == BusinessType.SMALL_BUSINESS
            ):
                potential_interactions = list(
                    business_manager.potential_manage_outfit_interactions_gen(context)
                )
            choice_menu.add_potential_aops(
                pick_target, context, potential_interactions, scoring_gsi_handler
            )
            client.set_choices(choice_menu)

        # 5) Generic pick (terrain / sim / object in world)
        else:
            if show_pie_menu:
                shift_held = False

            position = sims4.math.Vector3(x, y, z)
            pick_target, pick_type, potential_targets = _get_targets_from_pick(
                sim,
                pick_target,
                pick_type,
                position,
                level,
                zone.id,
                lot_id,
                is_routable,
                preferred_objects=preferred_objects,
            )
            if pick_target is None:
                return 0

            interaction_parameters = client.get_interaction_parameters()

            if potential_targets:
                alt_bool = bool(alt)
                control_bool = bool(control)

                def _add_potential_object_aops(potential_target, routing_surface):
                    pick = PickInfo(
                        pick_type=pick_type,
                        target=potential_target,
                        location=position,
                        routing_surface=routing_surface,
                        lot_id=lot_id,
                        level=level,
                        alt=alt_bool,
                        control=control_bool,
                        shift=shift_held,
                    )
                    ctx = client.create_interaction_context(
                        sim, pick=pick, shift_held=shift_held
                    )
                    ctx.add_preferred_objects(preferred_objects)
                    potential_aops = list(
                        potential_target.potential_interactions(
                            ctx, **interaction_parameters
                        )
                    )
                    choice_menu.add_potential_aops(
                        potential_target, ctx, potential_aops, scoring_gsi_handler
                    )
                    return pick

                for potential_target, routing_surface in potential_targets:
                    if potential_target.is_sim:
                        suppress_social_front_page |= (
                            potential_target.should_suppress_social_front_page_when_targeted()
                        )
                    pick = _add_potential_object_aops(potential_target, routing_surface)

                if not shift_held and sim is not None:
                    ctx = client.create_interaction_context(
                        sim, pick=pick, shift_held=shift_held
                    )
                    ctx.add_preferred_objects(preferred_objects)
                    sim.fill_choices_menu_with_si_state_aops(
                        pick_target, ctx, choice_menu, scoring_gsi_handler
                    )

                if len(choice_menu) == 0:
                    fire_service = services.get_fire_service()
                    if fire_service.fire_is_active:
                        fires = fire_service.get_fires_in_potential_targets(
                            potential_targets
                        )
                        if fires:
                            potential_target = fires[0]
                            _add_potential_object_aops(
                                potential_target, potential_target.routing_surface
                            )

                client.set_choices(choice_menu)

    # GSI archive
    if gsi_handlers.sim_handlers_log.pie_menu_generation_archiver.enabled:
        gsi_handlers.sim_handlers_log.archive_pie_menu_option(
            sim, pick_target, scoring_gsi_handler
        )

    # Build & send UI message
    ref_id = reference_id or (sim.id if sim is not None else 0)
    msg = create_pie_menu_message(
        sim,
        choice_menu,
        ref_id,
        pie_menu_action,
        target=pick_target,
        suppress_front_page=suppress_social_front_page,
    )
    try:
        # immadiate tarzı hız için distributoru pas geçerek omegaya sendliyorum.
        omega.send(client.id, Consts_pb2.MSG_PIE_MENU_CREATE, msg.SerializeToString())
    except Exception as e:
        log.error(f"send pie menu error: {e}")
        import traceback

        log.error(traceback.format_exc())
    # (isteğe bağlı, UI flush güvence)
    # Distributor.instance().process_events()

    num_choices = len(msg.items)

    if num_choices > 0:
        if pick_type in (
            PickType.PICK_PORTRAIT,
            PickType.PICK_SIM,
            PickType.PICK_CLUB_PANEL,
        ):
            with telemetry_helper.begin_hook(
                writer, TELEMETRY_HOOK_CREATE_PIE_MENU, sim=sim
            ) as hook:
                hook.write_int("piid", ref_id)
                hook.write_enum("kind", pick_type)
                hook.write_int("tsim", target_id)
        else:
            with telemetry_helper.begin_hook(
                writer, TELEMETRY_HOOK_CREATE_PIE_MENU, sim=sim
            ) as hook:
                hook.write_int("piid", ref_id)
                if pick_target is not None and getattr(pick_target, "definition"):
                    hook.write_guid("tobj", pick_target.definition.id)
                else:
                    hook.write_int("tobj", 0)
                hook.write_enum("kind", pick_type)

    return num_choices


# it is not fully working
# TODO: bug fix
def has_choices(
    target_id: int = None,
    pick_type=PickType.PICK_TERRAIN,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    lot_id: int = 0,
    level: int = 0,
    control: int = 0,
    alt: int = 0,
    shift: int = 0,
    reference_id: int = 0,
    is_routable: bool = True,
    _connection=None,
):
    if target_id is None:
        return
    zone = services.current_zone()
    client = services.client_manager().get(_connection)
    if client is None:
        return
    sim = _active_sim(client)
    shift_held = bool(shift)
    if shift_held:
        cheat_service = services.get_cheat_service()
        if False or cheat_service.cheats_enabled:
            _send_interactable_message(
                client,
                target_id,
                True,
                interactable_flags=(interaction_protocol.Interactable.INTERACTABLE),
            )
        else:
            _send_interactable_message(client, target_id, False)
        return
    situation_manager = services.get_zone_situation_manager()
    for situation in situation_manager.get_all():
        if situation.disabled_interaction_tooltip is not None:
            if situation.is_sim_in_situation(sim):
                return

    position = sims4.math.Vector3(x, y, z)
    pick_target = zone.find_object(target_id)
    (pick_target, pick_type, potential_targets) = _get_targets_from_pick(
        sim,
        pick_target,
        pick_type,
        position,
        level,
        (zone.id),
        lot_id,
        is_routable,
        preferred_objects=(set()),
    )
    is_interactable = False
    if pick_target is not None:
        tutorial_service = services.get_tutorial_service()
        alt_bool = bool(alt)
        control_bool = bool(control)
        for potential_target, routing_surface in potential_targets:
            pick = PickInfo(
                pick_type=pick_type,
                target=potential_target,
                location=position,
                routing_surface=routing_surface,
                lot_id=lot_id,
                level=level,
                alt=alt_bool,
                control=control_bool,
                shift=shift_held,
            )
            context = client.create_interaction_context(sim, pick=pick)
            for aop in potential_target.potential_interactions(context):
                if tutorial_service is not None:
                    if not tutorial_service.is_affordance_visible(aop.affordance):
                        continue
                    result = ChoiceMenu.is_valid_aop(
                        aop, context, user_pick_target=potential_target
                    )
                    if not result:
                        if not result.tooltip:
                            continue
                        is_interactable = aop.affordance.allow_user_directed
                        if not is_interactable:
                            is_interactable = (
                                aop.affordance.has_pie_menu_sub_interactions
                            )(
                                (aop.target),
                                context,
                                **aop.interaction_parameters,
                            )
                        if is_interactable:
                            break

            if sim is not None:
                for si in sim.si_state:
                    potential_mixer_targets = si.get_potential_mixer_targets()
                    for potential_mixer_target in potential_mixer_targets:
                        if potential_target is potential_mixer_target:
                            break
                        if potential_mixer_target.is_part:
                            if potential_mixer_target.part_owner is potential_target:
                                break
                    else:
                        continue
                    if autonomy.content_sets.any_content_set_available(
                        sim,
                        (si.super_affordance),
                        si,
                        context,
                        potential_targets=(potential_target,),
                        include_failed_aops_with_tooltip=True,
                    ):
                        is_interactable = True
                        break
                else:
                    continue

        if not is_interactable:
            fire_service = services.get_fire_service()
            if fire_service.fire_is_active:
                fires = fire_service.get_fires_in_potential_targets(potential_targets)
                if fires:
                    potential_target = fires[0]
                    pick = PickInfo(
                        pick_type=pick_type,
                        target=potential_target,
                        location=position,
                        routing_surface=routing_surface,
                        lot_id=lot_id,
                        level=level,
                        alt=alt_bool,
                        control=control_bool,
                        shift=shift_held,
                    )
                    context = client.create_interaction_context(sim, pick=pick)
                    for aop in potential_target.potential_interactions(context):
                        if not aop.affordance.allow_user_directed:
                            continue
                        else:
                            result = ChoiceMenu.is_valid_aop(
                                aop,
                                context,
                                user_pick_target=potential_target,
                            )
                        if result:
                            is_interactable = True
                            break

    interactable_flags = _get_interactable_flags(pick_target, is_interactable)
    _send_interactable_message(
        client,
        target_id,
        is_interactable,
        True,
        interactable_flags=interactable_flags,
    )


def _send_interactable_message(
    client,
    target_id,
    is_interactable,
    immediate=False,
    interactable_flags=0,
):
    try:
        msg = interaction_protocol.Interactable()

        # 🔥 kritik satır
        try:
            target_id_int = int(target_id)
        except (TypeError, ValueError):
            target_id_int = 0  # terrain / invalid pick fallback

        msg.object_id = target_id_int
        msg.is_interactable = is_interactable
        msg.interactable_flags = interactable_flags
        # TODO: client id sadece travel öncesi 3 olur. Bir travels sonrası bu değişecektir. Güncelle.
        _omega.send(3, Consts_pb2.MSG_OBJECT_IS_INTERACTABLE, msg.SerializeToString())
    except Exception as e:
        log.error(f"ANA HATA{str(e)}")
        import traceback

        log.error(traceback.format_exc())


def air_div(*a, **k):
    log.debug("call air div")
    pass


# def interaction_inject(is_client):
#     if not is_client:
#         unregister("interactions.choices")
#         Command("interactions.choices", command_type=CommandType.Live)(generate_choices)

#     unregister("interactions.has_choices")
#     unregister("clock.request_pause")
#     unregister("clock.unrequest_pause")
#     Command("interactions.has_choices", command_type=CommandType.Live)(has_choices)
#     Command("clock.request_pause", command_type=CommandType.Live)(air_div)
#     Command("clock.unrequest_pause", command_type=CommandType.Live)(air_div)


# DEBUG
@Command("gentest", command_type=CommandType.Live)
def fenss(a: bool = True, _connection=None):
    outputs = CheatOutput(_connection)
    outputs("gen test")
    if a:
        unregister("interactions.has_choices")
        Command("interactions.has_choices", command_type=CommandType.Live)(has_choices)
        outputs("ok gen")

    else:
        unregister("interactions.has_choices")
        from server_commands.interaction_commands import has_choices as hs

        Command("interactions.has_choices", command_type=CommandType.Live)(hs)
        outputs("ok has")
