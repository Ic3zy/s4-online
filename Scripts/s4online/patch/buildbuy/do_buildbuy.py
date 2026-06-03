# import objects.system
# import sims4.math
# import services
# import routing
# from s4online.base import Ctx
# from s4online.utils import Logger
# from .c_api_hook import _objects_instance

# log = Logger(__name__)

# # EXAMPLE INPUT
# SCHEMA = {
#     "new_create": bool,
#     "remove": bool,
#     "obj_id": int,
#     "zone_id": int,
#     "def_id": int,
#     "obj_level": int,
#     "pos": list,
#     "rot": list,
# }


# def type_checking(data):
#     if not isinstance(data, dict):
#         return False

#     for key, expected in SCHEMA.items():
#         if key not in data:
#             return False

#         value = data[key]

#         if not isinstance(value, expected):
#             return False

#     return True


# def do_buildbuy(payload):
#     data = payload.get("data")
#     if not type_checking(data):
#         log.error("TYPE CHECKING FAILED")
#         return

#     new_create = data["new_create"]
#     obj_id = data["obj_id"]
#     zone_id = data["zone_id"]
#     def_id = data["def_id"]
#     obj_level = data["obj_level"]

#     pos_vector3 = sims4.math.Vector3(*tuple(data["pos"]))
#     rot_quaternion = sims4.math.Quaternion(*tuple(data["rot"]))
#     target_transform = sims4.math.Transform(pos_vector3, rot_quaternion)

#     log.debug(
#         f"new_create: {new_create}, obj_id: {obj_id}, zone_id: {zone_id}, def_id: {def_id}, pos: {pos_vector3}, rot: {rot_quaternion}"
#     )

#     try:
#         # Tekrar kancamıza düşmemesi için bir Ctx ataması.
#         Ctx["is_processing_network_bb_packet"] = True

#         obj = services.object_manager().get(obj_id)
#         if obj is None:
#             obj = services.current_zone().find_object(obj_id)

#         if new_create:
#             if obj is not None:
#                 log.error("create_object obje zaten var, obje üretilemedi.")
#                 return

#             obj = objects.system.create_object(definition_or_id=def_id, obj_id=obj_id)
#             if obj is None:
#                 log.error("create_object None döndü, obje üretilemedi.")
#                 return
#         else:
#             if obj is None:
#                 log.error("obje bulunamadı.")
#                 return

#         # Move object
#         zone_id = services.current_zone_id()
#         surface_id = routing.SurfaceIdentifier(
#             zone_id, obj_level, routing.SurfaceType.SURFACETYPE_WORLD
#         )

#         obj.move_to(transform=target_transform, routing_surface=surface_id)
#     except Exception as e:
#         log.error(f"do_buildbuy error: {e}")
#     finally:
#         # Hata olsa da olmasa da serbest bırak.
#         Ctx["is_processing_network_bb_packet"] = False
#         log.debug(f"{_objects_instance}")


# def save_ev_nt():
#     network_instance = Ctx.get("network_instance")
#     if network_instance is not None:
#         network_instance.ev.on({"type": "buildbuy"}, do_buildbuy)
#     else:
#         log.error("network_instance is None")

#     log.debug("save_ev_nt")


# Ctx.add_callback("network_instance", save_ev_nt)
