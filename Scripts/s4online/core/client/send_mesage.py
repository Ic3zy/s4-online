from server.client import Client
import omega


def send_message(self, msg_id, msg, global_distributor=False):
    if self.active:
        try:
            serialize_msg = msg.SerializeToString()
        except Exception as e:
            serialize_msg = msg
        omega.send(
            self.id,
            msg_id,
            serialize_msg,
            global_distributor=global_distributor,
        )


Client.send_message = send_message
