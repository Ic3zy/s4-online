from functools import wraps
import sys
from .logger import Logger

# (module, function_name, original_function)
INJECT_ARCHIVER = []

log = Logger(__name__)


def _update_function(original, new_func):
    """original fonksiyonun bulunduğu modülü bul ve replace et."""
    module = sys.modules[original.__module__]
    name = original.__name__

    # Orijinali restore için arşivle
    INJECT_ARCHIVER.append((module, name, original))

    # Modül içinde fonksiyonu değiştir
    setattr(module, name, new_func)

    return new_func


# ---------------------------------------------------
# REPLACE (PATCH)
# ---------------------------------------------------


def inject_replace(original):
    """
    @inject_replace(original)
    def patch(...):

    → original tamamen patch ile değiştirilir.
    """

    def decorator(patch):
        @wraps(original)
        def wrapper(*args, **kwargs):
            return patch(*args, **kwargs)

        return _update_function(original, wrapper)

    return decorator


# ---------------------------------------------------
# AFTER
# ---------------------------------------------------


def inject_after(original):
    """
    @inject_after(original)
    def patch(...):

    → önce original, sonra patch çalışır.
    """

    def decorator(patch):
        @wraps(original)
        def wrapper(*args, **kwargs):
            result = original(*args, **kwargs)
            patch(*args, **kwargs)
            return result

        return _update_function(original, wrapper)

    return decorator


# ---------------------------------------------------
# SAFE AFTER
# ---------------------------------------------------


def inject_safe_after(original):
    """
    Orijinal çalışır -> patch çalışır. 
    Patch çökse bile orijinalin sonucunu döner.
    """
    def decorator(patch):
        @wraps(original)
        def wrapper(*args, **kwargs):
            result = None
            
            # 1. Orijinali çalıştır
            try:
                result = original(*args, **kwargs)
            except Exception as exc:
                # Orijinal patlarsa logla ama devam et (veya re-raise et seçimine bağlı)
                log.error(f"[inject_safe_after] Original error: {exc}")
                # Genelde orijinal hata verirse bunu dışarı fırlatmak istersin:
                # raise exc 

            # 2. Patch'i çalıştır
            try:
                # original bir method ise, args[0] zaten 'self'dir.
                # patch fonksiyonu da buna göre tasarlanmalıdır.
                patch(*args, **kwargs)
            except Exception as exc:
                log.error(f"[inject_safe_after] Patch error: {exc}")

            return result

        return _update_function(original, wrapper)

    return decorator

# ---------------------------------------------------
# BEFORE
# ---------------------------------------------------


def inject_before(original):
    """
    @inject_before(original)
    def patch(...):

    → önce patch, sonra original.
    """

    def decorator(patch):
        @wraps(original)
        def wrapper(*args, **kwargs):
            patch(*args, **kwargs)
            return original(*args, **kwargs)

        return _update_function(original, wrapper)

    return decorator


# ---------------------------------------------------
# DE-INJECT
# ---------------------------------------------------


def de_inject():
    """Tüm patch'leri eski haline döndür."""
    while INJECT_ARCHIVER:
        module, name, original_func = INJECT_ARCHIVER.pop()
        setattr(module, name, original_func)

