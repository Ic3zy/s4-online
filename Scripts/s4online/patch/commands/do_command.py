from .map_commands import (
    COMMAND_LIST,
    HOST_REPLACEMENT_LIST,
    HOST_BLOCK,
)
from s4online.utils import Logger, load_pyd
from s4online.base import Ctx, TaskScheduler
from distributor.system import Distributor

import sims4.commands, inspect, time, threading

log = Logger(__name__)

dispatcher = load_pyd("dispatcher", "dispatcher.pyd")


def get_command(command_name):
    if command_name in HOST_BLOCK:
        return
    if command_name in HOST_REPLACEMENT_LIST:
        return HOST_REPLACEMENT_LIST[command_name]
    return COMMAND_LIST.get(command_name)


# TODO: spam riskini durdurmak için son komutları kaydeden ve tamamlandıktan sonra silen bir yapıya ihtiyacım var
# TODO: bu bir liste olacak ve içerisinde aynı komut aynı kullanıcıdan girmiş ise yeniden işleme asla alınmayacak.


class Commander:
    def __init__(self):
        self.spam_lock_set = set()
        self.lock = threading.Lock()

    def spam_locker(self, command_name, client_id):
        with self.lock:
            command_doc = f"{command_name} {client_id}"
            self.spam_lock_set.add(command_doc)

    def release_spam_lock(self, command_name, client_id):
        with self.lock:
            command_doc = f"{command_name} {client_id}"
            self.spam_lock_set.discard(command_doc)

    def _do_command(self, command_name, client_id, *args, **kwargs):
        kwargs["_connection"] = client_id

        try:
            command = get_command(command_name)

            command_doc = f"{command_name} {client_id}"
            if command_doc in self.spam_lock_set:
                return

            if command:
                spec = inspect.getfullargspec(command)
                parsed_args = sims4.commands.parse_args(spec, list(args), client_id)

                kwargs["_connection"] = client_id

                try:
                    command(*parsed_args, **kwargs)
                except Exception as e:
                    log.error(f"hata: {e}")

                self.spam_locker(command_name, client_id)
                TaskScheduler.add(
                    {
                        "command": self.release_spam_lock,
                        "args": [command_name, client_id],
                        "kwargs": {},
                        "called_time": time.time() + 0.8,
                    }
                )

            else:
                log.warning("command bulunamadı")
        except Exception as e:
            log.error(f"{e}")

    def do_command_main_thread(self, data):
        try:
            command_name = data.get("command_name")
            account_name = data.get("account_name")
            if account_name is None:
                return log.error("account name yok")
            else:
                distributor_instance = Distributor.instance()
                if distributor_instance is None:
                    return log.error("distributor yok")

                client = distributor_instance.get_client_by_account_name(account_name)
                if client is None:
                    return log.error("client yok")

                client_id = client.id
                log.debug(f"client id: {client_id}")

            args = data.get("args")
            kwargs = data.get("kwargs")
            log.debug(f"do_command_from_network: {command_name} {args} {kwargs}")
            self._do_command(command_name, client_id, *args, **kwargs)

        except Exception as e:
            log.error(f"do_command_from_network hata: {e}")

    def do_command_from_network(self, data):
        try:
            dispatcher.enqueue(self.do_command_main_thread, (data,))
        except Exception as e:
            log.error(f"dispatcher hata {e}")


Commander_instance = Commander()


def add_network_server():
    network_instance = Ctx.get("network_instance")
    if network_instance is not None:
        ev = network_instance.ev

        if ev is not None:
            ev.on({"type": "server_command"}, Commander_instance.do_command_from_network)


Ctx.add_callback("network_instance", add_network_server)
