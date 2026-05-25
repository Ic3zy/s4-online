from s4online.utils import Logger

EV_LIST = list()

log = Logger(__name__)


def on(pattern, func) -> None:
    EV_LIST.append({"pattern": pattern, "func": func})


def emit(event_type, message, output) -> bool:
    try:
        log.info(f"Emit başlatılıyor.. Json. {EV_LIST}")
        for ev in EV_LIST:
            pattern = ev.get("pattern")
            if pattern is None:
                continue
            
            evType = pattern.get("type")
            if event_type != evType:
                continue
            
            output("func bulundu çağırılacak.")
            func = ev["func"]
            try:
                func(message)
            except Exception as e:
                log.error(f"func içi hata: {e}")
                import traceback
                log.error(traceback.format_exc())

        return True
    except Exception as e:
        log.error(f"emit hata: {e}")
        return False
