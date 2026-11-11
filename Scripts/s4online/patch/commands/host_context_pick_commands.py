import functools
import inspect

from s4online.base import UserPickContext
from s4online.utils import Logger
from server_commands.interaction_commands import select_choice

log = Logger(__name__)


def hcp_hook(org):
    """Wrap a host command with its caller's pick context."""
    original_signature = inspect.signature(org)

    @functools.wraps(org)
    def wrapped(*args, **kwargs):
        bound = original_signature.bind_partial(*args, **kwargs)
        client_id = bound.arguments.get("_connection")
        if client_id is None:
            client_id = "MainClient"
        with UserPickContext.activate(client_id):
            return org(*args, **kwargs)

    # Sims command parsing uses getfullargspec; expose the original typed args.
    wrapped.__signature__ = original_signature
    return wrapped


def hcp_select_choice_hook(choice_id: int, reference_id: int = 0, _connection=None):
    try:
        client_id = _connection
        if client_id is None:
            client_id = "MainClient"

        with UserPickContext.activate(client_id):
            return select_choice(choice_id, reference_id, _connection)
    except Exception as exc:
        log.error(f"hcp_select_choice_hook failed: {exc}")
