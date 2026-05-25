# from .networking import *
from .utils import *
from .utils import Logger
log = Logger(__name__)
try:
    from .base import *
    from .networking import *
    from .core import *
    from .patch import *
    from .main import start
    start()

except Exception as e:
    log.error(f"import error: {e}")
    import traceback

    log.error(traceback.format_exc())