from s4online.base import Ctx
import game_services

# Burası travel girişi ve çıkışı sırasında tetiklenir.
# Enable yani is_travel = False kısmını şimdilik çok kullanmıyorum.
# Callback ataması yok onun üzerine


def new_enable_shutdown():
    if game_services.service_manager is not None:
        game_services.service_manager.allow_shutdown = True
        # Tam tersi veriliyor çünkü oyun işleyişi bu şekilde.
        Ctx.is_travel = False


def new_disable_shutdown():
    if game_services.service_manager is not None:
        game_services.service_manager.allow_shutdown = False
        Ctx.is_travel = True


def update_game_load():
    if Ctx.is_travel:
        Ctx.game_load = False


game_services.enable_shutdown = new_enable_shutdown
game_services.disable_shutdown = new_disable_shutdown

# Travel'a girdiğimizde game_load false olması gerekli,
# çünkü travel esnasında oyun kapalı.
Ctx.add_callback("is_travel", update_game_load)
