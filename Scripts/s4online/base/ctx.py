from s4online.utils import Logger

log = Logger(__name__)

# Global atamalar için daha önce sys.modules kısmını kirletirdim, artık böyle yapmak yerine ctx içerisinde tutuyorum.
class ctx:
    _shared_data = {}
    _callbacks = {}

    # --- 2. Nokta Notasyonu (Ctx.name = 'ali') ---
    def __setattr__(self, name, value):
        log.debug(f"setattr: {name} = {value}")
        if name == "_shared_data":
            super().__setattr__(name, value)
        else:
            self._shared_data[name] = value
            self.callback_call(name)

    def __getattr__(self, name):
        if name in self._shared_data:
            return self._shared_data[name]
        raise AttributeError(f"'Ctx' nesnesinde '{name}' özelliği bulunamadı.")

    # --- 3. Item Assignment (Ctx['key'] = 'val') ---
    def __setitem__(self, key, value):
        log.debug(f"setitem: {key} = {value}")
        self._shared_data[key] = value
        self.callback_call(key)

    def __getitem__(self, key):
        if key in self._shared_data:
            return self._shared_data[key]
        raise KeyError(f"'{key}' anahtarı Ctx içinde bulunamadı.")

    def __delitem__(self, key):
        if key in self._shared_data:
            del self._shared_data[key]

    def __repr__(self):
        return f"Ctx({self._shared_data})"
    
    def get(self, key, default=None): return self._shared_data.get(key, default)
    def keys(self): return self._shared_data.keys()
    def values(self): return self._shared_data.values()
    def items(self): return self._shared_data.items()


    # --- Callbacks ---
    # Callback özellikle game_load gibi işlemlerde inanılmaz bir basitlik sağlayacak bizlere.
    # game_load atandığında direkt ona bağlı callback'ler çağırılabilecek.
    # Aynı bir proxy gibi çalışıyor ancak daha iyisi.
    # Bu kısım, loopmod ile oyunun init olup olmadığını kontrol etme zorunluluğunu kaldırıyor
    def callback_call(self, key):
        if self._callbacks.get(key) is not None:
            for callback in self._callbacks[key]:
                callback()

    def add_callback(self, key, callback):
        if self._callbacks.get(key) is None:
            self._callbacks[key] = []

        if self._shared_data.get(key) is not None:
            callback()

        self._callbacks[key].append(callback)
    
    
    def remove_callback(self, key, callback):
        if self._callbacks.get(key) is not None:
            self._callbacks[key].remove(callback)