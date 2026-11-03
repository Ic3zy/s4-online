from contextlib import contextmanager


class UserPickContextClass:
    def __init__(self):
        self.client_id = None

    @contextmanager
    def activate(self, client_id):
        self.client_id = client_id
        try:
            yield
        finally:
            self.client_id = None


UserPickContext = UserPickContextClass()
