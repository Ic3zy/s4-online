import os, json, random


class Config:
    def __init__(self):
        self.appdata = os.getenv("APPDATA")
        self.mods_data_directory = os.path.join(self.appdata, "s4online")
        os.makedirs(self.mods_data_directory, exist_ok=True)

        self.config_directory = os.path.join(
            self.mods_data_directory, "s4online_config.json"
        )
        self.game_load = False
        self.manager_load = False
        self.name = None

    @property
    def account_name(self):
        if not self.name:
            self.name = self.db.get("account_name")
            if self.name is None:
                self.name = "guest" + str(random.randint(10000, 99999))

        return self.name

    @property
    def is_client(self):
        is_client = self.db.get("is_client")
        if is_client is None:
            return False
        else:
            return is_client

    @property
    def player_count(self):
        return len(self.clients_info)
    
    @property
    def clients_info(self):
        return self.db.get("connected_clients_info") or list()
    
    @property
    def db(self):
        return self.read_db(self.config_directory)

    def read_db(self, directory):
        try:
            with open(directory, "r") as f:
                return json.load(f)
        except:
            return None

    @property
    def logger_directory(self):
        if self.db is None:
            return None
        else:
            db_logger_directory = self.db.get("logger_directory")
            if db_logger_directory:
                _dirname = os.path.dirname(db_logger_directory)
                os.makedirs(_dirname, exist_ok=True)
                return db_logger_directory
            else:
                default_db_directory = os.path.join(self.mods_data_directory, "log")
                os.makedirs(default_db_directory, exist_ok=True)
                return default_db_directory


config = Config()
