"""Suppress missing native stair data on clients only."""

from functools import wraps

from routing.portals.portal_data_stairs import _PortalTypeDataStairs
from sims4.log import Logger


log = Logger("S4OnlineStairPortalGuard")
_original_get_portal_locations = _PortalTypeDataStairs.get_portal_locations
_injected = False
_warned_object_ids = set()
_ERROR_PREFIX = "Unable to acquire stair data for objID"


def _client_get_portal_locations(self, obj):
    try:
        return _original_get_portal_locations(self, obj)
    except RuntimeError as exc:
        if _ERROR_PREFIX not in str(exc):
            raise

        object_id = getattr(obj, "id", None)
        if object_id not in _warned_object_ids:
            _warned_object_ids.add(object_id)
            log.warn(
                "Skipping unavailable stair portal data on client for objID {}: {}".format(
                    object_id, exc
                )
            )
        return ()


@wraps(_original_get_portal_locations)
def _wrapped_get_portal_locations(self, obj):
    return _client_get_portal_locations(self, obj)


def inject_stair_portal_guard(is_client):
    global _injected
    if is_client and not _injected:
        _PortalTypeDataStairs.get_portal_locations = _wrapped_get_portal_locations
        _injected = True


def uninject_stair_portal_guard():
    global _injected
    if _injected:
        _PortalTypeDataStairs.get_portal_locations = _original_get_portal_locations
        _injected = False
        _warned_object_ids.clear()
