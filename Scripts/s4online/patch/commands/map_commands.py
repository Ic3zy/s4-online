# from s4online.utils import Logger

# log = Logger(__name__)

from server_commands.clock_commands import (
    set_speed,
    request_pause,
    unrequest_pause,
    toggle_pause_unpause,
)
from server_commands.interaction_commands import (
    has_choices,
    generate_choices,
    generate_phone_choices,
    select_choice,
    cancel_mixer_interaction,
    cancel_super_interaction,
    push_interaction,
)
from server_commands.lighting_commands import (
    set_color_and_intensity,
    auto_room_light_status,
    show_light_editor,
)
from server_commands.sim_commands import (
    set_active_sim,
    set_next_sim,
    skewer_icon_activated,
    request_satisfaction_reward_list,
    whims_award_prize,
)
from server_commands.ui_commands import (
    ui_dialog_respond,
    ui_dialog_pick_result,
    ui_dialog_text_input,
    ui_dialog_multi_picker_result,
    # ui_create_hovertip,
    toggle_silence_phone,
)
from server_commands.career_commands import (
    find_career,
    select_career,
    send_to_work,
    leave_work,
)
from server_commands.inventory_commands import (
    purchase_picker_response,
    purchase_picker_response_by_ids,
    sell_picker_response_by_ids,
    # create_and_add_object_to_inventory,
    # inventory_view_update, open_inventory_ui: oyunun içsel çağrıları, ağ komutu değil
)

from server_commands.outfit_commands import (
    copy_outfit,
    # set_outfit_sharing_mode,
    # switch_outfit,
    # generate_outfit,
    # show_outfit_info,
    # remove_outfit,
)
from server_commands.photo_commands import get_photo_list
from server_commands.aspiration_commands import set_primary_track

from business.business_commands import set_open_small_business
from bucks.bucks_commands import (
    request_perks_list,
    unlock_perk_by_name_or_id,
    unlock_multiple_perks_with_buck_type,
    lock_perk_by_name_or_id,
    lock_all_perks_for_bucks_type,
)
from server_commands.live_drag_commands import (
    live_drag_start,
    live_drag_end,
    live_drag_canceled,
    live_drag_sell,
)
from server_commands.travel_group_commands import (
    create_vacation,
    end_stayover,
    extend_vacation,
    end_vacation,
)
from .interaction_command import (
    has_choices as custom_has_choices,
    generate_choices as custom_generate_choices,
)


from clubs.club_commands import start_gathering_by_club_id, end_gathering_by_club_id

COMMAND_LIST = {
    # clocks
    "clock.toggle_pause_unpause": toggle_pause_unpause,
    "clock.unrequest_pause": unrequest_pause,
    "clock.request_pause": request_pause,
    "clock.setspeed": set_speed,
    # interactions
    "interactions.phone_choices": generate_phone_choices,
    "interactions.has_choices": has_choices,
    "interactions.cancel_si": cancel_super_interaction,
    "interactions.choices": generate_choices,
    "interactions.select": select_choice,
    "interactions.cancel": cancel_mixer_interaction,
    "interactions.push": push_interaction,
    # light
    "lighting.set_color_and_intensity": set_color_and_intensity,
    "lighting.auto_room_light_status": auto_room_light_status,
    "lighting.showlighteditor": show_light_editor,
    # sim commands
    "sims.request_satisfaction_reward_list": request_satisfaction_reward_list,
    "sims.skewer_icon_activated": skewer_icon_activated,
    "sims.whims_award_prize": whims_award_prize,
    "sims.set_active": set_active_sim,
    "sims.set_next": set_next_sim,
    # ui's
    "ui.dialog.multi_picker_result": ui_dialog_multi_picker_result,
    "ui.aspirations.set_primary": set_primary_track,
    "ui.toggle_silence_phone": toggle_silence_phone,
    "ui.dialog.pick_result": ui_dialog_pick_result,
    "ui.dialog.text_input": ui_dialog_text_input,
    "ui.dialog.respond": ui_dialog_respond,
    # career
    "careers.send_to_work": send_to_work,
    "careers.find_career": find_career,
    "careers.leave_work": leave_work,
    "careers.select": select_career,
    # inventory (client → host ağ komutları: picker response'lar)
    "inventory.purchase_picker_response_by_ids": purchase_picker_response_by_ids,
    "inventory.sell_picker_response_by_ids": sell_picker_response_by_ids,
    "inventory.purchase_picker_response": purchase_picker_response,
    # bucks
    "bucks.lock_all_perks_for_bucks_type": lock_all_perks_for_bucks_type,
    "bucks.unlock_multiple_perks": unlock_multiple_perks_with_buck_type,
    "bucks.request_perks_list": request_perks_list,
    "bucks.unlock_perk": unlock_perk_by_name_or_id,
    "bucks.lock_perk": lock_perk_by_name_or_id,
    # live drag
    "live_drag.canceled": live_drag_canceled,
    "live_drag.start": live_drag_start,
    "live_drag.sell": live_drag_sell,
    "live_drag.end": live_drag_end,
    # club commands
    "clubs.start_gathering_by_club_id": start_gathering_by_club_id,
    "clubs.end_gathering_by_club_id": end_gathering_by_club_id,
    # travels
    "travel_groups.create_vacation": create_vacation,
    "travel_groups.extend_vacation": extend_vacation,
    "travel_groups.end_stayover": end_stayover,
    "travel_groups.end_vacation": end_vacation,
    # other
    "business.set_open_small_business": set_open_small_business,
    "photography.get_photo_list": get_photo_list,
    "outfits.copy_outfit": copy_outfit,
}

# ---------- Replace Lists ----------
HOST_REPLACEMENT_LIST = {
    "interactions.has_choices": custom_has_choices,
    "interactions.choices": custom_generate_choices,
}
CLIENT_REPLACEMENT_LIST = {
    "interactions.has_choices": custom_has_choices,
}

# ---------- Blocked lists ----------
CLIENT_BLOCK = [
    "clock.request_pause",
    "clock.unrequest_pause",
]
HOST_BLOCK = [
    "clock.request_pause",
    "clock.unrequest_pause",
]
