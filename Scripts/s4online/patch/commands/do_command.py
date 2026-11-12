from .map_commands import COMMAND_LIST, HOST_REPLACEMENT_LIST, HOST_BLOCK
from s4online.utils import Logger, load_pyd
from s4online.base import Ctx, TaskScheduler, UserPickContext
from distributor.system import Distributor
from server.live_drag_tuning import LiveDragState
import inspect
import services
import threading
import time
import sims4.commands

log = Logger(__name__)
dispatcher = load_pyd("dispatcher", "dispatcher.pyd")


def get_command(command_name):
    if command_name in HOST_BLOCK:
        return
    if command_name in HOST_REPLACEMENT_LIST:
        return HOST_REPLACEMENT_LIST[command_name]
    return COMMAND_LIST.get(command_name)


class Commander:
    def __init__(self):
        self.spam_lock_set = set()
        self.lock = threading.Lock()
        self.live_drag_queue = []

    def _live_drag_command_gate(self, command_name, client_id, args, kwargs):
        terminal_commands = ("live_drag.end", "live_drag.canceled", "live_drag.sell")
        with self.lock:
            owner_id = UserPickContext.live_drag_owner_id
            object_id = UserPickContext.live_drag_object_id
            if owner_id is None:
                return False

            if command_name in terminal_commands:
                if client_id != owner_id:
                    self.live_drag_queue.append((command_name, client_id, args, kwargs))
                    return True
                requested_id = args[0] if args else kwargs.get(
                    "live_drag_object_id", kwargs.get("object_source_id")
                )
                if requested_id is not None and requested_id != object_id:
                    log.warning(f"Ignoring mismatched live drag terminal command: {command_name}")
                    return True
                return False

            self.live_drag_queue.append((command_name, client_id, args, kwargs))
            return True

    def _begin_live_drag(self, client_id, object_id):
        with self.lock:
            generation = UserPickContext.begin_live_drag(
                client_id, object_id, "live_drag.start"
            )
        TaskScheduler.add({
            "command": self._live_drag_timeout,
            "args": [generation],
            "kwargs": {},
            "called_time": time.time() + 8,
        })
        return generation

    def _live_drag_is_active(self, object_id):
        try:
            obj = services.current_zone().find_object(object_id)
            component = obj.live_drag_component if obj is not None else None
            return (
                component is not None
                and component.live_drag_state == LiveDragState.LIVE_DRAGGING
            )
        except Exception as e:
            log.error(f"live drag state check failed: {e}")
            return False

    def _start_live_drag_after_command(self, command_name, client_id, parsed_args, succeeded):
        if command_name != "live_drag.start" or not succeeded or not parsed_args:
            return
        object_id = parsed_args[0]
        if self._live_drag_is_active(object_id):
            self._begin_live_drag(client_id, object_id)

    def _finish_live_drag(self, generation=None):
        with self.lock:
            ended = UserPickContext.end_live_drag(generation)
        if ended:
            self._flush_live_drag_queue()
        return ended

    def _flush_live_drag_queue(self):
        with self.lock:
            queued = self.live_drag_queue
            self.live_drag_queue = []
        for command_name, client_id, args, kwargs in queued:
            self._do_command(command_name, client_id, *args, **kwargs)

    def _schedule_live_drag_completion_check(self, generation, delay=0):
        TaskScheduler.add({
            "command": self._live_drag_completion_check,
            "args": [generation],
            "kwargs": {},
            "called_time": time.time() + delay,
        })

    def _live_drag_completion_check(self, generation):
        # Scheduler callbacks run on a worker: inspect game state on main thread.
        try:
            dispatcher.enqueue(self._live_drag_completion_check_main_thread, (generation,))
        except Exception as e:
            log.error(f"live drag completion dispatch failed: {e}")

    def _live_drag_completion_check_main_thread(self, generation):
        with self.lock:
            if generation != UserPickContext.live_drag_generation:
                return
            object_id = UserPickContext.live_drag_object_id
            if object_id is None:
                return
        if self._live_drag_is_active(object_id):
            self._schedule_live_drag_completion_check(generation, 0.25)
        else:
            self._finish_live_drag(generation)

    def _live_drag_timeout(self, generation):
        # Scheduler worker only dispatches; game APIs stay on the main thread.
        try:
            dispatcher.enqueue(self._live_drag_timeout_main_thread, (generation,))
        except Exception as e:
            log.error(f"live drag timeout dispatch failed: {e}")

    def _live_drag_timeout_main_thread(self, generation):
        with self.lock:
            if generation != UserPickContext.live_drag_generation:
                return
            owner_id = UserPickContext.live_drag_owner_id
            object_id = UserPickContext.live_drag_object_id
            if owner_id is None:
                return

        log.warning(f"Live drag timed out: owner={owner_id}, object={object_id}")
        try:
            command = get_command("live_drag.canceled")
            if command is not None:
                parsed_args = sims4.commands.parse_args(
                    inspect.getfullargspec(command), [object_id], owner_id
                )
                with UserPickContext.activate(owner_id, "live_drag.canceled"):
                    command(*parsed_args, _connection=owner_id)
        except Exception as e:
            log.error(f"live drag timeout cancel failed: {e}")
        finally:
            self._finish_live_drag(generation)

    def _finish_live_drag_after_command(self, command_name, client_id, parsed_args):
        if command_name not in ("live_drag.end", "live_drag.canceled", "live_drag.sell"):
            return
        with self.lock:
            owner_id = UserPickContext.live_drag_owner_id
            object_id = UserPickContext.live_drag_object_id
            generation = UserPickContext.live_drag_generation
        if owner_id != client_id or not parsed_args or parsed_args[0] != object_id:
            return
        # End/cancel are normally synchronous; sell may wait on a dialog.
        # Polling the component handles both without releasing commands early.
        self._schedule_live_drag_completion_check(generation)

    def spam_locker(self, command_name, client_id):
        with self.lock:
            self.spam_lock_set.add(f"{command_name} {client_id}")

    def release_spam_lock(self, command_name, client_id):
        with self.lock:
            self.spam_lock_set.discard(f"{command_name} {client_id}")

    def _do_command(self, command_name, client_id, *args, **kwargs):
        kwargs["_connection"] = client_id
        try:
            command = get_command(command_name)
            command_doc = f"{command_name} {client_id}"
            with self.lock:
                if command_doc in self.spam_lock_set:
                    return

            if self._live_drag_command_gate(command_name, client_id, args, kwargs):
                return

            if command is None:
                log.warning("command bulunamadı")
                return

            parsed_args = sims4.commands.parse_args(
                inspect.getfullargspec(command), list(args), client_id
            )
            succeeded = False
            try:
                with UserPickContext.activate(client_id, command_name):
                    command(*parsed_args, **kwargs)
                succeeded = True
            except Exception as e:
                log.error(f"hata: {e}")

            self._start_live_drag_after_command(
                command_name, client_id, parsed_args, succeeded
            )
            self._finish_live_drag_after_command(command_name, client_id, parsed_args)

            self.spam_locker(command_name, client_id)
            TaskScheduler.add({
                "command": self.release_spam_lock,
                "args": [command_name, client_id],
                "kwargs": {},
                "called_time": time.time() + 0.8,
            })
        except Exception as e:
            log.error(f"{e}")

    def do_command_main_thread(self, data):
        try:
            command_name = data.get("command_name")
            account_name = data.get("account_name")
            if account_name is None:
                return log.error("account name yok")

            distributor_instance = Distributor.instance()
            if distributor_instance is None:
                return log.error("distributor yok")
            client = distributor_instance.get_client_by_account_name(account_name)
            if client is None:
                return log.error("client yok")

            client_id = client.id
            args = data.get("args") or ()
            kwargs = data.get("kwargs") or {}
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
    if network_instance is not None and network_instance.ev is not None:
        network_instance.ev.on(
            {"type": "server_command"}, Commander_instance.do_command_from_network
        )


Ctx.add_callback("network_instance", add_network_server)
