from .map_commands import (
    COMMAND_LIST,
    HOST_REPLACEMENT_LIST,
    HOST_BLOCK,
)
from s4online.utils import Logger, load_pyd
from s4online.base import Ctx
import sims4.commands, inspect
from distributor.system import Distributor

log = Logger(__name__)

dispatcher = load_pyd("dispatcher", "dispatcher.cp37-win_amd64.pyd")


def parser(value: str):
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
    return value


def args_parser(args: list):
    parsed_args = list()

    for arg in args:
        try:
            parsed = parser(arg)
            if parsed is not None:
                parsed_args.append(parsed)
            else:
                continue
        except ValueError:
            continue

    return parsed_args


def kwargs_parser(kwargs: dict):
    parsed_kwargs = dict()
    for key, value in kwargs.items():
        try:
            parsed = parser(value)
            if parsed is not None:
                parsed_kwargs[key] = parsed
            else:
                continue

        except ValueError:
            continue

    return parsed_kwargs


def get_command(command_name):
    if command_name in HOST_BLOCK:
        return None
    if command_name in HOST_REPLACEMENT_LIST:
        return HOST_REPLACEMENT_LIST[command_name]
    return COMMAND_LIST.get(command_name)


# TODO: spam riskini durdurmak için son komutları kaydeden ve tamamlandıktan sonra silen bir yapıya ihtiyacım var
# TODO: bu bir liste olacak ve içerisinde aynı komut aynı kullanıcıdan girmiş ise yeniden işleme asla alınmayacak.


def _do_command(command_name, client_id, *args, **kwargs):
    kwargs["_connection"] = client_id

    try:
        command = get_command(command_name)

        if command:
            spec = inspect.getfullargspec(command)
            parsed_args = sims4.commands.parse_args(spec, list(args), client_id)
            log.log(f"Parsed_args type : {isinstance(parsed_args, list)}")
            # 🔥 1. KORUMA: C kodumuz kesinlikle Tuple bekliyor! Listeyi Tuple'a çeviriyoruz.
            # c_args = tuple(parsed_args) if parsed_args is not None else ()

            # 🔥 2. KORUMA: Arka plan thread'inin bu sözlüğü havada değiştirmemesi için
            # sözlüğün saniyeler içinde o anki halinin kopyasını (shallow copy) alıyoruz.
            kwargs["_connection"] = client_id
            # c_kwargs = kwargs.copy()

            try:
                # Artık C tarafına tamamen izole edilmiş, thread-safe paketler gidiyor:
                # dispatcher.enqueue(command, args=c_args, kwargs=c_kwargs)
                command(*parsed_args, **kwargs)
            except Exception as e:
                log.error(f"hata: {e}")
                import traceback

                log.error(traceback.format_exc())
        else:
            log.warning("command bulunamadı")
    except Exception as e:
        log.error(f"{e}")


def do_command_from_network(data):
    try:
        command_name = data.get("command_name")
        account_name = data.get("account_name")
        if account_name is None:
            return log.error("account name yok")
        else:
            client_id = (
                Distributor.instance().get_client_by_account_name(account_name).id
            )
            log.debug(f"client id: {client_id}")

        args = data.get("args")
        kwargs = data.get("kwargs")
        log.debug(f"do_command_from_network: {command_name} {args} {kwargs}")
        _do_command(command_name, client_id, *args, **kwargs)

    except Exception as e:
        log.error(f"do_command_from_network hata: {e}")
        import traceback

        log.error(traceback.format_exc())


def add_network_server():
    network_instance = Ctx.get("network_instance")
    if network_instance is not None:
        ev = network_instance.ev

    if ev is not None:
        ev.on({"type": "server_command"}, do_command_from_network)


Ctx.add_callback("network_instance", add_network_server)
