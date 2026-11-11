"""Distributor event IDs that must be delivered only to their requesting client."""

from protocolbuffers.Consts_pb2 import (
    MSG_OBJECT_IS_INTERACTABLE,
    MSG_PIE_MENU_CREATE,
    MSG_UI_DIALOG_SHOW,
    MSG_UI_DIALOG_CLOSE,
    MSG_PHONE_MENU_CREATE,
    MSG_UI_PHONE_RING,
    MSG_MULTI_PICKER_CONTENT_UPDATE,
    MSG_SHOW_SIM_PROFILE,
)

OWNER_SCOPED_EVENTS = frozenset(
    {
        MSG_OBJECT_IS_INTERACTABLE,
        MSG_PIE_MENU_CREATE,
        MSG_UI_DIALOG_SHOW,
        MSG_UI_DIALOG_CLOSE,
        MSG_PHONE_MENU_CREATE,
        MSG_UI_PHONE_RING,
        MSG_MULTI_PICKER_CONTENT_UPDATE,
        MSG_SHOW_SIM_PROFILE,
    }
)
