from s4online.base import Ctx
from zone import Zone

_original_finished = Zone.on_loading_screen_animation_finished

def custom_finished_load_screen(*a, **kw):
    result = _original_finished(*a, **kw) 
    Ctx.game_load = True
    return result

# Client'lar için selected sim_id ataması yapacak kısım burası.
# TODO: simlerin yaratılmasından sonra buranın tetikleniyor olması lazım
# TODO: yani simlerin yaratılmasını da hook ederek bağlı tüm game_client'lara yollamamız lazım

# def custom_do_zone_spin_up(*a, **kw):
#     result = Zone.do_zone_spin_up(*a, **kw) 
#     return result

def start():
    Zone.on_loading_screen_animation_finished = custom_finished_load_screen
