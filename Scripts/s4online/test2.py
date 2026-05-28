# from s4online.utils import load_pyd, Logger
# from threading import Thread
# import time
# log = Logger(__name__)

# dispatcher = load_pyd("dispatcher", "dispatcher.pyd")
# try:
#     class test:
#         def __init__(self):
#             self.thread = Thread(target=self.loop, daemon=True).start()
            
#         def runtest(self, *a, **kw):
#             log.log("CALLİNG")

#         def loop(self):
#             while True:
#                 log.log("tick")
#                 time.sleep(0.7)
#                 dispatcher.enqueue(self.runtest, ())

#     a = test()

# except Exception as e:
#     log.error(f"error: {e}")
