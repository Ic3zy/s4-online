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
from server_commands.lighting_commands import set_color_and_intensity
from server_commands.sim_commands import (
    set_active_sim,
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
from server_commands.career_commands import find_career, select_career
from server_commands.inventory_commands import (
    purchase_picker_response,
    purchase_picker_response_by_ids,
    inventory_view_update,
    open_inventory_ui,
    # create_and_add_object_to_inventory,
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
from .live_drag_command import (
    live_drag_start as custom_live_drag_start,
    live_drag_canceled as custom_live_drag_canceled,
    live_drag_sell as custom_live_drag_sell,
    live_drag_end as custom_live_drag_end,
    client_live_drag_end,
)
from .interaction_command import (
    has_choices as custom_has_choices,
    generate_choices as custom_generate_choices,
)

COMMAND_LIST = {
    "clock.setspeed": set_speed,
    "clock.toggle_pause_unpause": toggle_pause_unpause,
    # "clock.request_pause": request_pause,
    # "clock.unrequest_pause": unrequest_pause,
    "interactions.choices": generate_choices,
    "interactions.phone_choices": generate_phone_choices,
    "interactions.select": select_choice,
    "interactions.cancel": cancel_mixer_interaction,
    "interactions.cancel_si": cancel_super_interaction,
    "interactions.push": push_interaction,
    "lighting.set_color_and_intensity": set_color_and_intensity,
    "sims.set_active": set_active_sim,
    "ui.dialog.respond": ui_dialog_respond,
    "ui.dialog.pick_result": ui_dialog_pick_result,
    "ui.dialog.text_input": ui_dialog_text_input,
    "ui.dialog.multi_picker_result": ui_dialog_multi_picker_result,
    "ui.toggle_silence_phone": toggle_silence_phone,
    "careers.find_career": find_career,
    "careers.select": select_career,
    "inventory.purchase_picker_response": purchase_picker_response,
    "inventory.purchase_picker_response_by_ids": purchase_picker_response_by_ids,
    "inventory.view_update": inventory_view_update,
    "inventory.open_ui": open_inventory_ui,
    "outfits.copy_outfit": copy_outfit,
    "photography.get_photo_list": get_photo_list,
    "ui.aspirations.set_primary": set_primary_track,
    "business.set_open_small_business": set_open_small_business,
    "bucks.request_perks_list": request_perks_list,
    "bucks.unlock_perk": unlock_perk_by_name_or_id,
    "bucks.unlock_multiple_perks": unlock_multiple_perks_with_buck_type,
    "bucks.lock_perk": lock_perk_by_name_or_id,
    "bucks.lock_all_perks_for_bucks_type": lock_all_perks_for_bucks_type,
    "sims.request_satisfaction_reward_list": request_satisfaction_reward_list,
    "sims.whims_award_prize": whims_award_prize,
    # Live drag
    # the only reason I added this here is to be able to restore the original function.
    # It doesnt serve any other purpose.
    "live_drag.start": live_drag_start,
    "live_drag.end": live_drag_end,
    "live_drag.canceled": live_drag_canceled,
    "live_drag.sell": live_drag_sell,
    "interactions.has_choices": has_choices,
    "clock.request_pause": request_pause,
    "clock.unrequest_pause": unrequest_pause,
}
# ---------- Replace Lists ----------
HOST_REPLACEMENT_LIST = {
    "interactions.has_choices": custom_has_choices,
    "interactions.choices": custom_generate_choices,
    "live_drag.start": custom_live_drag_start,
    # NOT working
    # "live_drag.end": custom_live_drag_end,
    "live_drag.canceled": custom_live_drag_canceled,
    "live_drag.sell": custom_live_drag_sell,
}
CLIENT_REPLACEMENT_LIST = {
    "interactions.has_choices": custom_has_choices,
    "live_drag.end": client_live_drag_end,
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
