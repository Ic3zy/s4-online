from queue import Queue
from s4online.utils import Logger, load_pyd

loopmod = load_pyd("loopmod", "loopmod.pyd")

# clasic queue
event_queue = Queue()

queue_loop = None
log = Logger(__name__)
if not loopmod:
    log.error("loopmod not found")


def process_callback(func, callback_func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
        callback_func(result)
    except Exception as exc:
        log.error(f"Event Queue Error (callback): {exc}")


# burayı bu şekilde queue uygulayıcıya vermemin sebepleri;
# farklı Thread'lerden oyun Thread'ine ulaştığım zaman oyun DeadLock olması.
def process_queue(*a):
    if not event_queue.empty():
        try:
            item = event_queue.get_nowait()
            func = item.get("func")
            callback = item.get("callback")
            if callable(callback) and callable(func):
                return process_callback(
                    func, callback, *item.get("args", ()), **item.get("kwargs", {})
                )
            elif callable(func):
                func(*item.get("args", ()), **item.get("kwargs", {}))
            else:
                log.warning(f"Event Queue func not found: {item}")
        except Exception as exc:
            log.error(f"Event Queue Error: {exc}")


def start_loop():
    global queue_loop
    queue_loop = loopmod.Loop(process_queue, lambda: 0.2)  # 5 hz
    queue_loop.start()


def stop_loop():
    global queue_loop
    if queue_loop:
        queue_loop.stop()
        queue_loop = None
    else:
        log.warning("queue loop not started")
