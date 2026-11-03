from s4online.base import UserPickContext
from s4online.utils import Logger
from server_commands.interaction_commands import select_choice

log = Logger(__name__)


def hcp_select_choice_hook(choice_id: int, reference_id: int=0, _connection=None):
    try:
        client_id = _connection

        if client_id is None:
            client_id = "MainClient"

        with UserPickContext.activate(client_id):
            return select_choice(choice_id, reference_id, _connection)
    except Exception as e:
        log.error(f"hcp_select_choice_hook, error: {e}")
