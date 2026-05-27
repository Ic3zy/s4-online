import os, sys, importlib.machinery, importlib.util, traceback
from .logger import Logger

log = Logger(__name__)


def load_pyd(moduleName, fileName):
    log.info("Yükleniyor...")
    # try normal import
    try:
        return importlib.import_module(moduleName)
    except:
        pass

    base = os.path.dirname(os.path.abspath(__file__))
    pyd_path = os.path.join(os.path.dirname(base), "C_Pyd_Locale", fileName)
    # pyd_path = os.path.join(os.path.dirname(base), "C_Pyd", fileName)

    log.info(f"pyd_path: {pyd_path}")

    if not os.path.exists(pyd_path):
        log.info("PYD dosyası bulunamadı")
        return None

    try:
        loader = importlib.machinery.ExtensionFileLoader(moduleName, pyd_path)
        spec = importlib.util.spec_from_loader(moduleName, loader)
        mod = importlib.util.module_from_spec(spec)

        loader.exec_module(mod)

        sys.modules[moduleName] = mod

        log.info("PYD başarıyla yüklendi")
        return mod

    except Exception:
        log.info("Yükleme hatası:\n" + traceback.format_exc())
        return None
