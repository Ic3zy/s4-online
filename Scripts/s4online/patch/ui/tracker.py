import distributor.system
from s4online.utils import Tracker, Logger, load_pyd

# loopmod = load_pyd("loopmod", "loopmod.pyd")

log = Logger(__name__)


def update_sim_db(sim_list: list) -> None:
    db = Tracker.db

    for sim in sim_list:
        try:
            a = sim["account_name"]
            sid = sim["sim_id"]

            db.setdefault(a, {}).setdefault(sid, 0)
            db[a][sid] += 1
        except Exception as e:
            log.error(f"update_sim_db error: {e}")


def sims_track():
    try:
        sim_list = distributor.system.Distributor.instance().get_all_client_active_sim()
        update_sim_db(sim_list)
    except Exception as e:
        log.error(f"get_sims error: {e}")
