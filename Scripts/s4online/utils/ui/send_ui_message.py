import services, omega
from ui.ui_dialog_notification import UiDialogNotification
from sims4.localization import LocalizationHelperTuning

from distributor.ops import GenericProtocolBufferOp
from protocolbuffers import Distributor_pb2, DistributorOps_pb2, Consts_pb2
from protocolbuffers.DistributorOps_pb2 import Operation


def show_notification(text):
    try:
        if services is None:
            return False

        if not hasattr(services, "client_manager"):
            return False

        manager = services.client_manager()

        if manager is None:
            return False

        client = manager.get_first_client()

        if client is None:
            return False

        sim = client.active_sim_info

        if sim is None:
            return False

        dialog = UiDialogNotification.TunableFactory().default(
            sim, title=lambda *_, **__: LocalizationHelperTuning.get_raw_text(text)
        )

        msg = build_dialog_msg(dialog)

        omega.send(
            client.id, Consts_pb2.MSG_OBJECTS_VIEW_UPDATE, msg.SerializeToString()
        )

        return True

    except:
        return False


def build_dialog_msg(dialog):
    data = dialog.build_msg(icon_override=None)
    op = GenericProtocolBufferOp(Operation.UI_NOTIFICATION_SHOW, data)

    view_update = Distributor_pb2.ViewUpdate()
    entry = view_update.entries.add()
    entry.primary_channel.id.manager_id = 0
    entry.primary_channel.id.object_id = 0

    op_proto = DistributorOps_pb2.Operation()
    op.write(op_proto)
    entry.operation_list.operations.append(op_proto)

    return view_update
