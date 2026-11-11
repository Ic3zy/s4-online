from contextlib import contextmanager


class UserPickContextClass:
    def __init__(self):
        self.client_id = None

    @contextmanager
    def activate(self, client_id):
        # Keep the last command owner available for later UI/distributor events.
        self.client_id = client_id
        yield


UserPickContext = UserPickContextClass()
