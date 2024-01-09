import sys, os

#sys.path.append('/octv')

from octv_cffi import ffi, lib



debug = True
debug = False

_, FILE = os.path.split(__file__)

def log(*args):
    print(f'{FILE}:', *args)


class O(object):
    """
    Object with attribute behavior

    >>> o = O(a=None,b=True,c=False)
    >>> o.a is None
    True
    >>> o.b
    True
    >>> o.c
    False
    >>> o
    O({'a': None, 'b': True, 'c': False})
    >>> O({'a': None, 'b': True})
    O({'a': None, 'b': True})
    """
    def __init__(self, d=dict(), **kwargs):
        self.__dict__.update(d)
        self.__dict__.update(kwargs)
    def __repr__(self):
        return f'{type(self).__name__}({self.__dict__})'


@ffi.def_extern()
def octv_flat_feature_cb(flat_feature, user_data):
    cb = ffi.from_handle(user_data) if user_data != ffi.NULL else None
    log(f'octv_flat_feature_cb: flat_feature {flat_feature}, user_data: {user_data}, cb: {cb}')
    return cb(flat_feature) if cb is not None else 0

@ffi.def_extern()
def octv_config_cb(config):
    log(f'octv_config_cb: config {config}')
    return 0

@ffi.def_extern()
def octv_moment_cb(moment):
    log(f'octv_moment_cb: moment {moment}')
    return 0

@ffi.def_extern()
def octv_tick_cb(tick):
    log(f'octv_tick_cb: tick {tick}')
    return 0

@ffi.def_extern()
def octv_feature_cb(feature):
    log(f'octv_feature_cb: feature {feature}')
    return 0

@ffi.def_extern()
def octv_error_cb(code):
    log(f'octv_error_cb: code: {code}')
    return code


octv_flat_feature_fields = dir(ffi.new('OctvFlatFeature *'))
debug and log(f'octv_flat_feature_fields: {tuple(octv_flat_feature_fields)}')
octv_feature_0_range = range(lib.OCTV_FEATURE_0_LOWER, lib.OCTV_FEATURE_0_UPPER)
octv_feature_2_range = range(lib.OCTV_FEATURE_2_LOWER, lib.OCTV_FEATURE_2_UPPER)
octv_feature_3_range = range(lib.OCTV_FEATURE_3_LOWER, lib.OCTV_FEATURE_3_UPPER)

def flat_feature_object(flat_feature):
    ret = O()
    type = flat_feature.type
    for field in octv_flat_feature_fields:
        # set all non-level_* fields, and level_* fields that match the type
        if (not field.startswith('level_')
            or field.startswith('level_0') and type in octv_feature_0_range
            or field.startswith('level_2') and type in octv_feature_2_range
            or field.startswith('level_3') and type in octv_feature_3_range):
            setattr(ret, field, getattr(flat_feature, field))

    return ret

def parse_flat(file_c, flat_feature_cb):
    assert callable(flat_feature_cb), str((file_c, flat_feature_cb))
    sys.stdout.flush()
    lib.octv_parse_flat(file_c, lib.octv_flat_feature_cb, ffi.NULL)
    res = lib.octv_parse_flat(file_c, lib.octv_flat_feature_cb, ffi.new_handle(flat_feature_cb))
    #res = lib.octv_parse_flat(file_c, lib.octv_flat_feature_cb, ffi.NULL)

    return res


# referents holds onto cdata objects until we're done, needed because pointers in cdata structs don't hold on
referents = list()
def new(c_type):
    referents.append(ffi.new(c_type))
    return referents[-1]

def new_parser():
    parser = new('OctvParseCallbacks *')

    parser.config_cb = lib.octv_config_cb
    parser.moment_cb = lib.octv_moment_cb
    parser.tick_cb = lib.octv_tick_cb
    parser.feature_cb = lib.octv_feature_cb

    parser.error_cb = lib.octv_error_cb

    return parser
