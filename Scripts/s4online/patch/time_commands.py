import time_service, services
from s4online.base import Ctx

_original_update = time_service.TimeService.update


def custom_update(self, time_slice=True, *args, **kwargs):
    if Ctx.get('game_load') is None:
        return _original_update(self, time_slice=time_slice, *args, **kwargs)
        
    return None


def inject_time(is_client):
    if is_client:
        time_service.TimeService.update = custom_update


def uninject_time(is_client):
    if is_client:
        time_service.TimeService.update = _original_update