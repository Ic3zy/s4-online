from s4online.utils import Logger

log = Logger(__name__)


class Ev:
    EV_MAP = {}

    def on(self, pattern, func) -> None:
        event_type = pattern.get("type")
        if event_type is None:
            return

        if event_type not in self.EV_MAP:
            self.EV_MAP[event_type] = []

        self.EV_MAP[event_type].append(func)

    def off(self, pattern, func) -> None:
        event_type = pattern.get("type")
        funcs = self.EV_MAP.get(event_type)
        if funcs is not None and func in funcs:
            funcs.remove(func)
            if not funcs:
                self.EV_MAP.pop(event_type, None)

    def emit(self, event_type, message, output) -> bool:
        try:
            funcs = self.EV_MAP.get(event_type, ())

            for func in funcs:
                try:
                    func(message)

                except Exception as e:
                    log.error(f"func içi hata: {e}")

            return True

        except Exception as e:
            log.error(f"emit hata: {e}")
            return False


ev = Ev()
