from contextlib import contextmanager


class UserPickContextClass:
    def __init__(self):
        self.client_id = None
        self.command_name = None
        self.live_drag_owner_id = None
        self.live_drag_object_id = None
        self.live_drag_command_name = None
        self.live_drag_generation = 0

    @contextmanager
    def activate(self, client_id, command_name=None):
        # Keep the last command owner available for later UI/distributor events.
        self.client_id = client_id
        previous_command_name = self.command_name
        self.command_name = command_name
        try:
            yield
        finally:
            self.command_name = previous_command_name

    def begin_live_drag(self, client_id, object_id, command_name=None):
        self.live_drag_generation += 1
        self.live_drag_owner_id = client_id
        self.live_drag_object_id = object_id
        self.live_drag_command_name = command_name or self.command_name
        return self.live_drag_generation

    def end_live_drag(self, generation=None):
        if generation is not None and generation != self.live_drag_generation:
            return False
        if self.live_drag_owner_id is None:
            return False

        self.live_drag_owner_id = None
        self.live_drag_object_id = None
        self.live_drag_command_name = None
        self.live_drag_generation += 1
        return True


UserPickContext = UserPickContextClass()
