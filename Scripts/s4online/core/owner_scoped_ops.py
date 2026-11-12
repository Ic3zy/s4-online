"""Fast allowlist for distributor ops that belong to one requesting client."""

from distributor.ops import (
    GenericProtocolBufferOp,
    LiveDragStart,
    ShowSocialMediaPanel,
    AskAboutClubsDialog,
    CommunityBoardDialog,
    SendUIMessage,
    ShowBillsPanel,
    ShowClubInfoUI,
    ShowHorseCompetitionResults,
    ShowHorseCompetitionSelector,
    ShowMatchmakingDialog,
    SplitHouseholdDialog,
)
from protocolbuffers import DistributorOps_pb2
from restaurants.restaurant_ui import ShowMenu as ShowRestaurantMenu


_OWNER_SCOPED_OP_CLASSES = frozenset(
    {
        LiveDragStart,
        AskAboutClubsDialog,
        CommunityBoardDialog,
        SendUIMessage,
        ShowBillsPanel,
        ShowClubInfoUI,
        ShowHorseCompetitionResults,
        ShowHorseCompetitionSelector,
        ShowMatchmakingDialog,
        ShowRestaurantMenu,
        ShowSocialMediaPanel,
        SplitHouseholdDialog,
    }
)

# GenericProtocolBufferOp is common on the hot path; only inspect its enum
# after the exact-type check, and use a set for constant-time membership.
_OWNER_SCOPED_GENERIC_OP_TYPES = frozenset(
    {
        DistributorOps_pb2.Operation.SELECT_CAREER_UI,
        DistributorOps_pb2.Operation.UI_NOTIFICATION_SHOW,
        DistributorOps_pb2.Operation.SHOW_FAMILY_TREE,
        DistributorOps_pb2.Operation.SHOW_RENTAL_UNIT_MANAGEMENT,
        DistributorOps_pb2.Operation.SHOW_LIFETIME_MILESTONES_PANEL,
        DistributorOps_pb2.Operation.NOTEBOOK_VIEW,
        DistributorOps_pb2.Operation.BOOK_VIEW,
        DistributorOps_pb2.Operation.TRAVEL_MENU_INFO,
        DistributorOps_pb2.Operation.TRAVEL_VIEW_HOUSEHOLDS_INFO,
        DistributorOps_pb2.Operation.TRAVEL_GROUP_LIST,
        DistributorOps_pb2.Operation.TRAVEL_MENU_SHOW,
        DistributorOps_pb2.Operation.OPEN_INVENTORY,
        DistributorOps_pb2.Operation.OPEN_INVENTORY_WITH_FILTERS,
        DistributorOps_pb2.Operation.UNIVERSITY_ENROLLMENT_WIZARD,
        DistributorOps_pb2.Operation.RETAIL_SUMMARY_DIALOG,
        DistributorOps_pb2.Operation.RETAIL_BALANCE_TRANSFER_DIALOG,
        DistributorOps_pb2.Operation.BUSINESS_SUMMARY_DIALOG,
        DistributorOps_pb2.Operation.SIM_SERVER_RESPONSE_FAILED,
        DistributorOps_pb2.Operation.HOVERTIP_CREATED,
    }
)


def is_owner_scoped_op(op):
    op_type = type(op)
    if op_type in _OWNER_SCOPED_OP_CLASSES:
        return True
    return (
        op_type is GenericProtocolBufferOp
        and op.type_constant in _OWNER_SCOPED_GENERIC_OP_TYPES
    )
