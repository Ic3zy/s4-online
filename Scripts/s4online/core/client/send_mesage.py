from server.client import Client
import omega


def send_message(self, msg_id, msg, global_distributor=False):
    if self.active:
        omega.send(self.id, msg_id, msg.SerializeToString(), global_distributor=global_distributor)

Client.send_message = send_message