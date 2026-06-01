import services, _buildbuy
import sims4.reload
from s4online.utils import Logger, Config
from s4online.base import Ctx

log = Logger(__name__)

_objects_instance = None


# Bu kodu host tarafında da çalıştırıyor olmamın sebebi şu,
# live drag python tarafındaki objeyi arar eğer bulamaz ise sıkıntı çıkartır.
# Bizde bunu kullanarak client taraftaki live dragın sorunsuz çalışmasını sağlıyoruz.
class Buildbuy_obj:
    def __init__(self):
        self.new_create = False
        self.remove = False
        self.obj_id = 0
        self.zone_id = 0
        self.ok = False

    def add_obj(self, obj_id, zone_id):
        self.new_create = True
        self.obj_id = obj_id
        self.zone_id = zone_id

    def add_invalidate(self, obj_id, zone_id):
        self.obj_id = obj_id
        self.zone_id = zone_id

    def add_outsite(self, zone_id, vector3, air):
        self.vector3 = vector3
        obj = services.object_manager().get(self.obj_id)

        # Fallback: Eğer obje ana yöneticide henüz yoksa, tüm dünyadaki (envanterler dahil) nesneleri tara
        if obj is None:
            obj = services.current_zone().find_object(self.obj_id)

        if obj is None:
            # Obje bulunamıyor ise işlem yapamayız. Ok false atıyorum ve return veriyorum.
            self.ok = False
            return

        self.loc = obj.transform.orientation
        self.def_id = obj.definition.id
        surface_id = obj.routing_surface
        if surface_id is None or hasattr(surface_id, "secondary_id") is False:
            self.ok = False
            return

        self.obj_level = surface_id.secondary_id
        if (
            self.loc is not None
            and self.def_id is not None
            and self.obj_level is not None
            and not Ctx.get("is_processing_network_bb_packet")
        ):
            self.ok = True

        # Debug
        self.prints()

    def end(self):
        if not self.ok:
            return log.error("Buildbuy obj ok false")

        log.debug(f"📡 [S4ONLINE_NET] Paket ağa gönderiliyor...")

        payload = {
            "pattern": {"type": "buildbuy"},
            "data": {
                "new_create": self.new_create,
                "remove": self.remove,
                "obj_id": self.obj_id,
                "zone_id": self.zone_id,
                "def_id": self.def_id,
                "obj_level": self.obj_level,
                # Tuple formatına çeviriyoruz ki network dispatcher veya JSON serialize ederken sıkıntı çıkmasın
                "pos": (
                    (self.vector3.x, self.vector3.y, self.vector3.z)
                    if self.vector3
                    else (0.0, 0.0, 0.0)
                ),
                "rot": (
                    (self.loc.x, self.loc.y, self.loc.z, self.loc.w)
                    if self.loc
                    else (0.0, 0.0, 0.0, 1.0)
                ),
            },
        }
        network_instance = Ctx.get("network_instance")
        if network_instance is not None:
            network_instance.send_message_all_clients(payload)

        log.debug(f"📡 [S4ONLINE_NET] Paket ağa gönderilmeye hazır: {payload}")

    def prints(self):
        log.debug(f"""
            new_create = {self.new_create}
            objeid = {self.obj_id}
            zoneid = {self.zone_id}
            vector3 = {self.vector3}
            loc = {self.loc}
        """)


# HOOK

# Hot-reload olarak bu kodu test edebilmek için reload protect kullanıyorum.
# Kısaca açıklamak gerekirse burayı koymaz isem original referanslara erişimimi kaybederim.
# Sadece test etmek ve geliştirmeyi hızlandırmak için kullandığım bir kısım yani
with sims4.reload.protected(globals()):
    originals = None

if originals is None:
    originals = {
        "add_object_to_buildbuy_system": _buildbuy.add_object_to_buildbuy_system,
        "invalidate_object_location": _buildbuy.invalidate_object_location,
        "is_location_outside": _buildbuy.is_location_outside,
    }


def new_add_object_to_buildbuy_system(obj_id, zone_id):
    global _objects_instance
    _objects_instance = Buildbuy_obj()
    _objects_instance.add_obj(obj_id, zone_id)
    return originals["add_object_to_buildbuy_system"](obj_id, zone_id)


def new_invalidate_object_location(obj_id, zone_id):
    global _objects_instance
    if _objects_instance is None:
        _objects_instance = Buildbuy_obj()

    _objects_instance.add_invalidate(obj_id, zone_id)
    return originals["invalidate_object_location"](obj_id, zone_id)


def new_is_location_outside(zone_id, vector3, a):
    global _objects_instance
    if _objects_instance is not None:
        _objects_instance.add_outsite(zone_id, vector3, a)
        _objects_instance.end()
        _objects_instance = None
    return originals["is_location_outside"](zone_id, vector3, a)


def inject_location_hooks():
    defaults = originals.get("defaults")
    if defaults is None:
        originals["defaults"] = "ok"

        _buildbuy.add_object_to_buildbuy_system *= new_add_object_to_buildbuy_system
        _buildbuy.invalidate_object_location = new_invalidate_object_location
        _buildbuy.is_location_outside = new_is_location_outside
    else:
        log.debug("[BUILDBUY HOOK] ❌ zaten hooklanmış.")


# Oyun tamamen yükleme ekranını bitirip açıldığında hook atıyoruz ki
# ilk açılıştaki o obje oluşturma spamına rastlamayalım.
Ctx.add_callback("game_load", inject_location_hooks)
