from s4online.utils import Logger
from build_buy import c_api_set_object_location

log = Logger(__name__)

def new_set_loc(*a, **kw):
    log.info(f"set loc: {a} {kw}")
    # return c_api_set_object_location(*a, **kw)

c_api_set_object_location = new_set_loc