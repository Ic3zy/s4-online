import json, os

# from s4online.base import DiskQueue

from ..pydLoader import load_pyd

# loopmod = load_pyd("loopmod", "loopmod.pyd")

_instance = None


class Tracker:
    def __init__(self):
        self.appdata = os.getenv("APPDATA")
        self.mods_data_directory = os.path.join(self.appdata, "s4online")
        os.makedirs(self.mods_data_directory, exist_ok=True)

        self.tracker_directory = os.path.join(
            self.mods_data_directory, "s4online_config.json"
        )
        self.db_data = {}
        self.read_db()
        # write db
        # self.loop = loopmod.Loop(self.write_db, lambda: 10)
        # self.loop.start()

    @property
    def db(self) -> dict:
        return self.db_data

    def set_db(self, data):
        self.db_data = data

    def read_db(self) -> None:
        try:
            with open(self.tracker_directory, "r") as f:
                self.db_data = json.load(f)
        except:
            self.db_data = {}

    def write_db(self) -> None:
        return
        DiskQueue.add(self.tracker_directory, self.db_data, is_json=True)


# _instance = Tracker()
