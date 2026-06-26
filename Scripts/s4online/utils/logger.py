from .database.main import config as Config
import os


class Logger:
    def __init__(self, log_name):
        self.logger_directory = Config.logger_directory
        self.log_name = log_name

    def write_log(self, message, log_type="log"):
        # print(f"- [{self.log_name}] : {message}")
        # return
        file_path = os.path.join(self.logger_directory, f"{log_type}.log")
        with open(file_path, "a") as f:
            f.write(f"- [{self.log_name}] : {message}\n")

    def log(self, message):
        self.write_log(message)

    def info(self, message):
        self.write_log(message, "info")

    def error(self, message, no_traceback=False):
        self.write_log(message, "error")

        if no_traceback:
            return

        import traceback
        exc = traceback.format_exc()
        # Boş loglar istemiyorum.
        if "NoneType: None" in exc:
            return
        
        self.error(traceback.format_exc(), no_traceback=True)

    def warning(self, message):
        self.write_log(message, "warning")

    def debug(self, message):
        self.write_log(message, "debug")

    def time(self, message):
        self.write_log(message, "time")
