import sys, os
import contextlib
import struct
import json
import operator
import collections
import time

from octv_cffi import ffi, lib

debug = False
debug = True

_, FILE = os.path.split(__file__)

def log(*args):
    print(f'{FILE}:', *args)
    sys.stdout.flush()

def octv_assert_invariants():
    """
    Assert some low-level invariants of the Octv stream protocol.

    >>> octv_assert_invariants()
    """
    assert (lib.OCTV_FEATURE_MASK ^ lib.OCTV_NON_FEATURE_MASK) == 0xff, str((hex(lib.OCTV_FEATURE_MASK ^ lib.OCTV_NON_FEATURE_MASK), hex(lib.OCTV_FEATURE_MASK), hex(lib.OCTV_NON_FEATURE_MASK)))

    assert 0 < lib.OCTV_FEATURE_0_LOWER, str((lib.OCTV_FEATURE_0_LOWER,))
    assert lib.OCTV_FEATURE_3_UPPER < lib.OCTV_END_TYPE, str((hex(lib.OCTV_FEATURE_3_UPPER), hex(lib.OCTV_END_TYPE)))
    assert lib.OCTV_END_TYPE < lib.OCTV_SENTINEL_TYPE < lib.OCTV_CONFIG_TYPE < lib.OCTV_MOMENT_TYPE < lib.OCTV_TICK_TYPE, str((hex(lib.OCTV_END_TYPE), hex(lib.OCTV_SENTINEL_TYPE), hex(lib.OCTV_CONFIG_TYPE), hex(lib.OCTV_MOMENT_TYPE), hex(lib.OCTV_TICK_TYPE)))

    assert lib.OCTV_FEATURE_0_UPPER == lib.OCTV_FEATURE_2_LOWER, str((hex(lib.OCTV_FEATURE_0_UPPER), hex(lib.OCTV_FEATURE_2_LOWER)))
    assert lib.OCTV_FEATURE_2_UPPER == lib.OCTV_FEATURE_3_LOWER, str((hex(lib.OCTV_FEATURE_2_UPPER), hex(lib.OCTV_FEATURE_3_LOWER)))


# referents holds onto cdata objects until this module goes away, needed because pointers in cdata
# structs don't hold onto the underlying cdata

referents = list()
def ffi_new(c_type, init=None):
    referents.append(ffi.new(c_type, init))
    return referents[-1]
def ffi_new_handle(obj):
    referents.append(ffi.new_handle(obj))
    return referents[-1]

@contextlib.contextmanager
def open_file_c(filename, *, mode=os.O_RDONLY):
    # open and manage a FILE *
    file_c = None
    try:
        fd = os.open(filename, mode)
        sys.stdout.flush()
        file_c = lib.fdopen(fd, b'r')
        debug and log(f'open_file_c: open: filename: {filename}, fd: {fd}, file_c: {file_c}')
        yield file_c
    finally:
        if file_c is not None:
            debug and log(f'open_file_c: close: filename: {filename}, fd: {fd}, file_c: {file_c}')
            sys.stdout.flush()
            lib.fclose(file_c)

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
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    def __getitem__(self, key):
        return self.__dict__[key]
    def __getattr__(self, name):
        return getattr(self.__dict__, name)


def hexify(value):
    try:
        return hex(value)
    except:
        return value


octv_struct_names = (
    'OctvDelimiter',
    'OctvConfig',
    'OctvMoment',
    'OctvTick',
    'OctvFeature',
    )

octv_struct_name_by_type = {
    lib.OCTV_SENTINEL_TYPE: ('OctvDelimiter', 'sentinel'),
    lib.OCTV_END_TYPE: ('OctvDelimiter', 'end'),
    lib.OCTV_CONFIG_TYPE: ('OctvConfig', 'config'),
    lib.OCTV_MOMENT_TYPE: ('OctvMoment', 'moment'),
    lib.OCTV_TICK_TYPE: ('OctvTick', 'tick'),
    }
for feature_type in range(lib.OCTV_FEATURE_0_LOWER, lib.OCTV_FEATURE_3_UPPER):
    octv_struct_name_by_type[feature_type] = ('OctvFeature', 'feature')

log(f'octv_struct_name_by_type:')
for key, (struct_name, terminal_name) in sorted(octv_struct_name_by_type.items()):
    log(f'  0x{key:02x}:  {struct_name}  {terminal_name}')
assert all(struct_name in octv_struct_names for (struct_name, terminal_name) in octv_struct_name_by_type.values()), str((octv_struct_names, octv_struct_name_by_type))


# stuff for working with Octv objects
octv_fields_by_type = O()
log(f'octv_fields_by_type:')
for  octv_type, (struct_name, terminal_name) in octv_struct_name_by_type.items():
    fields = tuple(field for field in dir(ffi.new(f'{struct_name} *')) if not field.startswith('_'))
    #log(f'  0x{octv_type:02x}  {terminal_name}  {struct_name}  {fields}')
    item = O(
        type = octv_type,
        terminal_name = terminal_name,
        struct_name = struct_name,
        fields = fields,
        )
    #log(f'  item: {item}')
    octv_fields_by_type[octv_type] = item


def octv_struct_str(terminal):
    item = octv_fields_by_type.get(terminal.type)
    if item is None: return f'type: 0x{terminal.type:02x}'

    field_values = ', '.join(f'{field_name}: {hexify(getattr(terminal, field_name))}' for field_name in item.fields)
    return f'type: 0x{item.type:02x}, terminal_name: {item.terminal_name}, struct_name: {item.struct_name} :  fields: {field_values}'

    #return ', '.join(f'{field_name}: {getattr(terminal, field_name)}' for field_name in octv_type_fields.get(terminal.type, ()))

def log_terminal(label, terminal):
    if terminal != ffi.NULL and terminal is not None:
        log(f'log_terminal: {label}: {octv_struct_str(terminal)}')
    else:
        log(f'log_terminal: {label}: {terminal}')


class OctvBase(object):

    @ffi.def_extern()
    @staticmethod
    def octv_error_cb(error_code, payload, user_data_c):
        try:
            log(f'octv_error_cb: error_code: {error_code} payload: {payload}, user_data_c: {user_data_c}')
            send = ffi.from_handle(user_data_c) if user_data_c != ffi.NULL else None
            # TODO: how to handle errors, separate error_user_data_c, or attribute on send
            # want an exception that is raised once we're back in python land...
            return error_code
        finally:
            # we're about to return into C code, so flush stdout
            sys.stdout.flush()

    @property
    def type(self):
        return self.self_c.type

    @property
    def as_json(self):
        return json.dumps(self.as_dict)

    def __str__(self):
        return self.as_json

    @classmethod
    def dict_from(cls, obj_c):
        return dict((field, getattr(obj_c, field)) for field in cls.fields)
        if False:
            res = dict()
            for field in cls.fields:
                res[field] = getattr(obj_c, field)
            return res

    @property
    def as_dict(self):
        res =  self.dict_from(self)
        res.update(
            # derived fields, not in the obj_c
            typename=type(self).__name__,
        )
        try:
            res['payload_hex'] = self.payload_hex
        except AttributeError:
            pass

        return res

    def __init__(self, obj_c):
        # self_c is an instance of a C struct (cffi) and used for getting most attributes
        self.self_c = ffi_new(self.struct_type, self.dict_from(obj_c))
        debug and log(f'{type(self).__name__}.__init__: obj_c: {obj_c}, self.self_c: {self.self_c}')
        payload = ffi.cast('OctvPayload *', obj_c)
        self.payload_hex = '_'.join(f'{byte:02x}' for byte in payload.bytes)

    @staticmethod
    def send(terminal, user_data_c):
        try:
            send = ffi.from_handle(user_data_c) if user_data_c != ffi.NULL else None
            code = send(terminal) if callable(send) else 0
            return code
        except Exception as error:
            # TODO: signal error back to python, e.g. via field in user_data_c?
            # needs to happen in cb function so that this try/except is superfluous
            log(f'OctvBase.send: error: {type(error).__name__}: error: {error}')
            return lib.OCTV_ERROR_CLIENT


class OctvSentinel(OctvBase):

    @ffi.def_extern()
    # classmethod would be preferable, but it doesn't play well with ffi.def_extern
    #   @ffi.def_extern()  TypeError: expected a callable object, not classmethod
    @staticmethod
    def octv_sentinel_cb(sentinel_c, user_data_c):
        try:
            return OctvBase.send(OctvSentinel(sentinel_c), user_data_c)
        finally:
            sys.stdout.flush()

    struct_type = 'OctvDelimiter *'
    fields = 'type',

class OctvEnd(OctvBase):

    @ffi.def_extern()
    @staticmethod
    def octv_end_cb(end_c, user_data_c):
        try:
            return OctvBase.send(OctvEnd(end_c), user_data_c)
        finally:
            sys.stdout.flush()

    struct_type = 'OctvDelimiter *'
    fields = 'type',

class OctvConfig(OctvBase):

    @ffi.def_extern()
    @staticmethod
    def octv_config_cb(config_c, user_data_c):
        try:
            return OctvBase.send(OctvConfig(config_c), user_data_c)
        finally:
            sys.stdout.flush()

    struct_type = 'OctvConfig *'
    fields = 'type', 'octv_version', 'num_audio_channels', 'audio_sample_rate_0', 'audio_sample_rate_1', 'audio_sample_rate_2', 'num_detectors',

    @property
    def octv_version(self):
        return self.self_c.octv_version

    @property
    def num_audio_channels(self):
        return self.self_c.num_audio_channels

    @property
    def audio_sample_rate_0(self):
        return self.self_c.audio_sample_rate_0

    @property
    def audio_sample_rate_1(self):
        return self.self_c.audio_sample_rate_1

    @property
    def audio_sample_rate_2(self):
        return self.self_c.audio_sample_rate_2

    @property
    def num_detectors(self):
        return self.self_c.num_detectors

class OctvMoment(OctvBase):

    @ffi.def_extern()
    @staticmethod
    def octv_moment_cb(moment_c, user_data_c):
        try:
            return OctvBase.send(OctvMoment(moment_c), user_data_c)
        finally:
            sys.stdout.flush()

    struct_type = 'OctvMoment *'
    fields = 'type', 'audio_frame_index_hi_bytes',

    @property
    def audio_frame_index_hi_bytes(self):
        return self.self_c.audio_frame_index_hi_bytes


class OctvTick(OctvBase):

    @ffi.def_extern()
    @staticmethod
    def octv_tick_cb(tick_c, user_data_c):
        try:
            return OctvBase.send(OctvTick(tick_c), user_data_c)
        finally:
            sys.stdout.flush()

    struct_type = 'OctvTick *'
    fields = 'type', 'audio_channel', 'audio_frame_index_lo_bytes', 'audio_sample'

    if False:
        @property
        def type(self):
            return self.self_c.type

    @property
    def audio_channel(self):
        return self.self_c.audio_channel

    @property
    def audio_frame_index_lo_bytes(self):
        return self.self_c.audio_frame_index_lo_bytes

    @property
    def audio_sample(self):
        return self.self_c.audio_sample


# TODO: separate class for each of the feature sub-types
class OctvFeatureBase(OctvBase):

    level_0 = range(lib.OCTV_FEATURE_0_LOWER, lib.OCTV_FEATURE_0_UPPER)
    level_2 = range(lib.OCTV_FEATURE_2_LOWER, lib.OCTV_FEATURE_2_UPPER)
    level_3 = range(lib.OCTV_FEATURE_3_LOWER, lib.OCTV_FEATURE_3_UPPER)

    @ffi.def_extern()
    @staticmethod
    def octv_feature_cb(feature_c, user_data_c):
        try:
            feature_type = feature_c.type
            if feature_type in OctvFeatureBase.level_0:
                cls = OctvFeature_0
            elif feature_type in OctvFeatureBase.level_2:
                cls = OctvFeature_2
            elif feature_type in OctvFeatureBase.level_3:
                cls = OctvFeature_3
            else:
                raise AssertionError(f'unhandled feature type: {feature_type}  0x{feature_type:02x}')

            return OctvBase.send(cls(feature_c), user_data_c)
        finally:
            sys.stdout.flush()

    struct_type = 'OctvFeature *'
    fields = 'type', 'frame_offset', 'detector_index',

    @property
    def frame_offset(self):
        return self.self_c.frame_offset

    @property
    def detector_index(self):
        return self.self_c.detector_index



class OctvFeature_0(OctvFeatureBase):

    fields = OctvFeatureBase.fields + ('level_0_int8_0', 'level_0_int8_1', 'level_0_int8_2', 'level_0_int8_3')

    @property
    def level_0_int8_0(self):
        return self.self_c.level_0_int8_0

    @property
    def level_0_int8_1(self):
        return self.self_c.level_0_int8_1

    @property
    def level_0_int8_2(self):
        return self.self_c.level_0_int8_2

    @property
    def level_0_int8_3(self):
        return self.self_c.level_0_int8_3

class OctvFeature_2(OctvFeatureBase):

    fields = OctvFeatureBase.fields + ('level_2_int8_0', 'level_2_int8_1', 'level_2_int16_0')

    @property
    def level_2_int8_0(self):
        return self.self_c.level_2_int8_0

    @property
    def level_2_int8_1(self):
        return self.self_c.level_2_int8_1

    @property
    def level_2_int16_0(self):
        return self.self_c.level_2_int16_0

class OctvFeature_3(OctvFeatureBase):

    fields = OctvFeatureBase.fields + ('level_3_int16_0', 'level_3_int16_1')

    @property
    def level_3_int16_0(self):
        return self.self_c.level_3_int16_0

    @property
    def level_3_int16_1(self):
        return self.self_c.level_3_int16_1


# class decorator to add getter properties for each of struct_fields, proxy-ing through self.self_c
def octv_terminal(cls):
    for attr_name in cls.struct_fields:
        def get_attr(self, attr_name=attr_name):
            return getattr(self.self_c, attr_name)
        setattr(cls, attr_name, property(get_attr))
    return cls


def proxy_fields(proxy_name, fields_name):
    def octv_terminal(cls):
        struct_name = cls.__name__
        struct = ffi.new(struct_name + '*')
        fields1 = tuple(dir(struct))
        print(f'octv_terminal: cls: {cls}, struct_name: {struct_name}, struct: {struct}, fields1: {fields1}')
        sys.stdout.flush()

        for attr_name in getattr(cls, fields_name):
            def get_attr(self, *, attr_name=attr_name):
                return getattr(getattr(self, proxy_name), attr_name)
            setattr(cls, attr_name, property(get_attr))
        return cls
    return octv_terminal

octv_ffi_proxy = proxy_fields('self_c', 'fields')

class OctvFlatBase(OctvBase):

    def __init__(self, obj_c):
        # self_c is an instance of a C struct (cffi) and used as a proxy for getting most attributes
        # struct pointer type is derived from cls name
        self.self_c = ffi_new(f'{type(self).__name__} *', self.dict_from(obj_c))
        #self.self_c = ffi_new(self.struct_type, self.dict_from(obj_c))
        debug and log(f'{type(self).__name__}.__init__: obj_c: {obj_c}, self.self_c: {self.self_c}')

@octv_ffi_proxy
class OctvFlatFeature(OctvFlatBase):
    pass
    #struct_type = 'OctvFlatFeature *'
    fields = 'octv_version', 'num_audio_channels', 'audio_sample_rate_0', 'audio_sample_rate_1', 'audio_sample_rate_2', 'num_detectors', 'audio_frame_index_hi_bytes', 'audio_channel', 'audio_frame_index_lo_bytes', 'audio_sample', 'type', 'frame_offset', 'detector_index',




if False:
    @octv_ffi_proxy
    class OctvFlatFeature_2(OctvFlatBase):
        #struct_type = 'OctvFlatFeature_2 *'
        fields = 'octv_version','num_audio_channels','audio_sample_rate','audio_frame_index','audio_channel','audio_sample','detector_index','level_2_int8_0','level_2_int8_1','level_2_int16_0',


def octv_proxy(cls, *, proxy_name = 'self_c'):
    slots = proxy_name,
    setattr(cls, '__slots__', slots)
    struct_name = cls.__name__
    struct_fields = tuple(map(operator.itemgetter(0), ffi.typeof(struct_name).fields))
    log(f'octv_proxy: struct_name: {struct_name}, struct_fields: {struct_fields}')
    # TODO: 'struct_fields'
    setattr(cls, 'fields', struct_fields)
    # Note: at first we reverse engineered, before working hard on https://cffi.readthedocs.io/en/latest/ref.html#ffi-cdata-ffi-ctype
    #struct_fields = dir(ffi.new(struct_name + '*'))

    for attr_name in struct_fields:
        setattr(cls, attr_name, property(operator.attrgetter(f'{proxy_name}.{attr_name}')))
        def get_attr(self, *, attr_name=attr_name):
            return getattr(getattr(self, proxy_name), attr_name)
        #setattr(cls, attr_name, property(get_attr))
    return cls

    log(f'octv_proxy: struct_fields 0: {struct_fields}')
    log(f'octv_proxy: ffi.new(struct_name + "*"): {ffi.new(struct_name + "*")}')
    log(f'octv_proxy: type(ffi.new(struct_name + "*")): {type(ffi.new(struct_name + "*"))}')
    log(f'octv_proxy: ffi.typeof(ffi.new(struct_name + "*")): {ffi.typeof(ffi.new(struct_name + "*"))}')
    log(f'octv_proxy: ffi.typeof(struct_name + "*"): {ffi.typeof(struct_name + "*")}')
    log(f'octv_proxy: dir(ffi.typeof(struct_name + "*")): {dir(ffi.typeof(struct_name + "*"))}')
    log(f'octv_proxy: dir(ffi.typeof(struct_name)): {dir(ffi.typeof(struct_name))}')
    x = ffi.typeof(struct_name)
    #x = ffi.typeof(struct_name + "*")
    for field in dir(x):
        log(f'  {field}: {getattr(x,field)}')


    log(f'octv_proxy: ffi.typeof(struct_name).fields: {ffi.typeof(struct_name).fields}')
    fs = ffi.typeof(struct_name).fields
    log(f'  {tuple(x[0] for x in fs)}')

    if False:
        log(f'octv_proxy: ffi.typeof(ffi.new(struct_name + "*")).fields: {ffi.typeof(ffi.new(struct_name + "*")).fields}')

        log(f'octv_proxy: getattr(ffi.new(struct_name + "*")[0], "fields"): {getattr(ffi.new(struct_name + "*")[0], "fields")}')
        log(f'octv_proxy: type(ffi.new(struct_name + "*")[0]): {type(ffi.new(struct_name + "*")[0])}')
        sys.stdout.flush()

        struct_fields = type(ffi.new(struct_name + '*')).fields
        log(f'octv_proxy: struct_fields 1: {struct_fields}')

        sys.stdout.flush()
        1/0

    print(f'octv_terminal: cls: {cls}, struct_name: {struct_name}, struct: {struct}, fields1: {fields1}')

    for attr_name in getattr(cls, fields_name):
        def get_attr(self, *, attr_name=attr_name):
            return getattr(getattr(self, proxy_name), attr_name)
        setattr(cls, attr_name, property(get_attr))
    return cls


class OctvProxy(object):
    proxy_name = 'self_c'

    @classmethod
    def octv_proxy(cls0, cls):
        setattr(cls, '__slots__', (cls0.proxy_name,))

        struct_name = cls.__name__
        struct_fields = tuple(map(operator.itemgetter(0), ffi.typeof(struct_name).fields))
        log(f'octv_proxy: struct_name: {struct_name}, struct_fields: {struct_fields}')
        setattr(cls, 'struct_fields', struct_fields)
        # Note: at first we reverse engineered, before working hard on https://cffi.readthedocs.io/en/latest/ref.html#ffi-cdata-ffi-ctype
        #struct_fields = dir(ffi.new(struct_name + '*'))

        for attr_name in struct_fields:
            setattr(cls, attr_name, property(operator.attrgetter(f'{cls0.proxy_name}.{attr_name}')))

        return cls

    @classmethod
    def dict_from(cls, obj_c):
        return dict((field, getattr(obj_c, field)) for field in cls.struct_fields)

    def __init__(self, obj_c):
        # self_c is an instance of a C struct (cffi) and used as a proxy for getting most attributes
        # struct pointer type is derived from cls name
        setattr(self, self.proxy_name, ffi_new(f'{type(self).__name__} *', self.dict_from(obj_c)))
        #self.self_c = ffi_new(f'{type(self).__name__} *', self.dict_from(obj_c))
        debug and log(f'{type(self).__name__}.__init__: obj_c: {obj_c}, self.self_c: {self.self_c}')



def octv_proxy(cls, *, proxy_name = 'self_c'):
    slots = proxy_name,
    setattr(cls, '__slots__', slots)
    struct_name = cls.__name__
    struct_fields = tuple(map(operator.itemgetter(0), ffi.typeof(struct_name).fields))
    log(f'octv_proxy: struct_name: {struct_name}, struct_fields: {struct_fields}')
    # TODO: 'struct_fields'
    setattr(cls, 'fields', struct_fields)
    # Note: at first we reverse engineered, before working hard on https://cffi.readthedocs.io/en/latest/ref.html#ffi-cdata-ffi-ctype
    #struct_fields = dir(ffi.new(struct_name + '*'))

    for attr_name in struct_fields:
        setattr(cls, attr_name, property(operator.attrgetter(f'{proxy_name}.{attr_name}')))
        def get_attr(self, *, attr_name=attr_name):
            return getattr(getattr(self, proxy_name), attr_name)
        #setattr(cls, attr_name, property(get_attr))
    return cls


@OctvProxy.octv_proxy
class OctvFlatFeature_2(OctvProxy):
#@octv_proxy
#class OctvFlatFeature_2(OctvFlatBase):
    pass
    #struct_type = 'OctvFlatFeature_2 *'
    #fields = 'octv_version','num_audio_channels','audio_sample_rate','audio_frame_index','audio_channel','audio_sample','detector_index','level_2_int8_0','level_2_int8_1','level_2_int16_0',

of_c = ffi.new('OctvFlatFeature_2 *')
of_c.detector_type = 0x2f
of_c.audio_sample = 23.25
of = OctvFlatFeature_2(of_c)
log(f'of: {of}, of.detector_type: {hex(of.detector_type)}')


class foon(collections.namedtuple('foon', ('foo', 'bar'))):
    def __new__(cls, *args):
        log(f'foon.__new__: args: {args}')
        return super().__new__(cls, 'def', 'xxx')
    pass

x = foon('xyz')
log(f'x: {x}')

def foobar(cls):
    log(f'foobar: dir(cls): {dir(cls)}')
    log(f'foobar: cls.__mro__: {cls.__mro__}')
    log(f'foobar: cls.mro(): {cls.mro()}')

    struct_name = cls.__name__
    struct_fields = tuple(map(operator.itemgetter(0), ffi.typeof(struct_name).fields))
    log(f'foobar: struct_name: {struct_name}, struct_fields: {struct_fields}')
    baz = collections.namedtuple(struct_name, struct_fields)

    def __new__(cls, obj_c):
        log(f'{struct_name}.__new__: obj_c: {obj_c}')
        #return super(baz).__new__(cls, struct_fields)
        x = dict((value,key) for key,value in enumerate(struct_fields))
        return baz.__new__(cls, **x)
        #return super(baz, cls).__new__(cls, **x)
        #return super(baz, cls).__new__(cls, struct_fields)
        #return super(baz, me).__new__(cls, struct_fields)
        #return super(baz, me).__new__(cls, *struct_fields)
        #return super().__new__(cls, 'def', 'xxx')


    class classY:
        def hello(self):
            log(f'ClassY.hello: self: {self}')
            return 'yow'

    #me = type(struct_name, (baz, classY), dict(__new__ = staticmethod(__new__)))
    d = dict(cls.__dict__)
    d.update(__new__ = staticmethod(__new__))
    me = type(struct_name, (baz,) + cls.__bases__, d)
    #me = type(struct_name, (baz,) + cls.__bases__, dict(__new__ = staticmethod(__new__)))
    #me = type(struct_name, (baz, cls.__mro__[1]), dict(__new__ = staticmethod(__new__)))
    #me = type(struct_name, (cls.__mro__[1], baz), dict(__new__ = staticmethod(__new__)))
    #me = type(struct_name, (baz,) + cls.__mro__[1:2], dict(__new__ = staticmethod(__new__)))
    #me = type(struct_name, (baz,), {})  # , **dict(__new__=__new__))


    #setattr(baz, '__new__', __new__)

    #setattr(me, '__new__', staticmethod(__new__))

    return me

class classX:
    def hello(self):
        log(f'ClassX.hello: self: {self}')
        return 'zayow'

log(f'classX().hello(): {classX().hello()}')

@foobar
class OctvFlatFeature_2:
#class OctvFlatFeature_2(classX):
    def hello(self):
        log(f'ClassZZ.hello: self: {self}')
        return 'zzzz'

    pass

#foobar(OctvFlatFeature_2)

y = OctvFlatFeature_2(of_c)
log(f'y.audio_sample: {repr(y.audio_sample)}')
log(f'y: {y}')
log(f'y.hello(): {y.hello()}')




# base class for getting ffi struct values, used by octv_struct
class OctvBase:
    __slots__ = ()

    @property
    def _as_json(self):
        # expects there to be a namedtuple in self's __mro__
        return json.dumps(self._asdict())

    def __str__(self):
        return self._as_json

    @ffi.def_extern()
    @staticmethod
    def octv_error_cb(error_code, payload, user_data_c):
        # called from C when the parser has encountered an error
        try:
            log(f'OctvBase.octv_error_cb: error_code: {error_code} payload: {payload}, user_data_c: {user_data_c}')
            send = ffi.from_handle(user_data_c) if user_data_c != ffi.NULL else None
            # TODO: how to handle C errors, separate error_user_data_c, or attribute on send
            return error_code
        except Exception as error:
            # secondary exception (from client's python code reached from send
            # want to create a python exception that is raised once we're back in python land...
            # e.g. via a new_handle attached to user_data
            log(f'OctvBase.octv_error_cb: error: {type(error).__name__}: error: {error}')
            return lib.OCTV_ERROR_CLIENT
        finally:
            # we're about to return into C code, so flush stdout
            sys.stdout.flush()

    @staticmethod
    def send(terminal, user_data_c):
        # TODO: user_data needs formal structure for send and for error
        send = ffi.from_handle(user_data_c) if user_data_c != ffi.NULL else None
        return send(terminal) if callable(send) else 0

# class decorator
# include a namedtuple (derived from the cls name, an ffi struct) in cls's bases
def octv_struct(cls):
    struct_name = cls.__name__
    struct_fields = tuple(map(operator.itemgetter(0), ffi.typeof(struct_name).fields))
    debug and log(f'octv_struct: struct_name: {struct_name}, struct_fields: {struct_fields}')

    struct_tuple = collections.namedtuple(struct_name+'_namedtuple', struct_fields)

    field_getters = tuple(operator.attrgetter(field) for field in struct_tuple._fields)

    def __new__(cls, obj_c, *, field_getters=field_getters):
        debug and log(f'octv_struct: {struct_name}.__new__: obj_c: {obj_c}')
        return struct_tuple.__new__(cls, *(getter(obj_c) for getter in field_getters))

    log(f'octv_struct: cls.__bases__: {cls.__bases__}')
    #bases = (struct_tuple, ) + cls.__bases__
    bases = (struct_tuple, OctvBase) + cls.__bases__
    log(f'octv_struct: bases: {bases}')

    class_dict = cls.__dict__.copy()
    class_dict.pop('__dict__', None)
    class_dict['__slots__'] = ()
    class_dict['__new__'] = staticmethod(__new__)

    return type(struct_name, bases, class_dict)

@octv_struct
#class OctvFlatFeature_2(OctvBase):
class OctvFlatFeature_2:
    __slots__ = ()
    pass

zz = OctvFlatFeature_2(of_c)
log(f'zz.audio_sample: {repr(zz.audio_sample)}')
log(f'zz: {zz}')
#log(f'zz.hello(): {zz.hello()}')
log(f'dir(zz): {dir(zz)}')
log(f'zz._fields: {zz._fields}')
log(f'zz._asdict(): {zz._asdict()}')
log(f'zz._as_json: {zz._as_json}')

log(f'dir(collections.namedtuple("footuple", ("foo", "bar", "baz"))): {dir(collections.namedtuple("footuple", ("foo", "bar", "baz")))}')

sys.stdout.flush()
time.sleep(0.0625)

#1/0


@ffi.def_extern()
def octv_flat_feature_cb(flat_feature_c, user_data_c):
    send = ffi.from_handle(user_data_c) if user_data_c != ffi.NULL else None
    flat_feature = OctvFlatFeature(flat_feature_c)
    log(f'octv_flat_feature_cb: flat_feature_c {flat_feature_c}, user_data_c: {user_data_c}, send: {send}, flat_feature: {flat_feature}')
    return send(flat_feature) if send is not None else 0


class OctvX(object):

    @ffi.def_extern()
    @staticmethod
    def octv_class_cb(payload, user_data):
        #log(f'OctvX.octv_class_cb: payload: {payload}, user_data: {user_data}')
        try:
            octv = OctvX.new_octv(payload)
            return ffi.from_handle(user_data)(octv) if user_data != ffi.NULL else 0
        except Exception as error:
            log(f'OctvX.octv_class_cb: {type(error).__name__}: error: {error}')
            return 0

    @staticmethod
    def new_octv(payload):
        match struct.pack('<BBBBBBBB', *payload.bytes):
            case payload_bytes if payload_bytes[0] in OctvXFeature.type_c:
                return OctvXFeature(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvXTick.type_c):
                return OctvXTick(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvXMoment.type_c):
                return OctvXMoment(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvXSentinel.type_c):
                return OctvXSentinel(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvXConfig.type_c):
                return OctvXConfig(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvXEnd.type_c):
                return OctvXEnd(payload_bytes)
            case _:
                return payload_bytes

    if False:
        payload_bytes = struct.pack('<BBBBBBBB', *payload.bytes)
        match payload_bytes[0]:
        #match payload.type:
            case type_c if payload_bytes.startswith(OctvSentinel.type_c):
            #case type_c if type_c == OctvSentinel.type_c[0]:
                res = OctvSentinel(payload_bytes)
                log(f'Octv.new_octv: OctvSentinel: {res}')
            case type_c if type_c == OctvEnd.type_c[0]:
                res = OctvEnd(payload_bytes)
                log(f'Octv.new_octv: OctvEnd: {res}')
            case type_c if type_c == OctvConfig.type_c[0]:
                res = OctvConfig(payload_bytes)
                log(f'Octv.new_octv: OctvConfig: {res}')
            case type_c if type_c == OctvMoment.type_c[0]:
                res = OctvMoment(payload_bytes)
                log(f'Octv.new_octv: OctvMoment: {res}')
            case type_c if type_c == OctvTick.type_c[0]:
                res = OctvTick(payload_bytes)
                log(f'Octv.new_octv: OctvTick: {res}')
            case type_c if type_c in OctvFeature.type_c:
                res = OctvFeature(payload_bytes)
                log(f'Octv.new_octv: OctvFeature: {res}')
            case _:
                res = payload_bytes
        #return res


class OctvXBase(object):
    @property
    def type(self):
        return self._payload[0]

    @property
    def payload(self):
        return self._payload

    @property
    def as_dict(self):
        return dict(
            type_name = type(self).__name__,
            type = hex(self.type),
            payload = '_'.join(f'{x:02x}' for x in self.payload),
            )

    @property
    def unpacked(self):
        return struct.unpack(self.struct_format, self.payload)

    def validate_payload(self):
        # called from super().__init__ after self.payload and self.type are usable
        if not self.payload.startswith(self.type_c):
            raise ValueError(f'{type(self).__name__} expected payload to start with {self.type_c}, got {self.payload}')

    def __init__(self, payload):
        if not isinstance(payload, bytes):
            raise TypeError(f'{type(self).__name__} expected payload to be bytes, got {type(payload).__name__}')
        if len(payload) != 8:
            raise ValueError(f'{type(self).__name__} expected payload length to be 8 bytes, got {len(payload)}')

        self._payload = payload
        self.validate_payload()

    def __str__(self):
        return json.dumps(self.as_dict)

    def __repr__(self):
        return f'{type(self).__name__}({self.payload})'

class OctvXSentinel(OctvXBase):
    r"""
    >>> o = OctvXSentinel(b'Octv\xa4\x6d\xae\xb6')
    >>> o
    OctvXSentinel(b'Octv\xa4m\xae\xb6')
    >>> hex(o.type)
    '0x4f'
    >>> str(o)
    '{"type_name": "OctvXSentinel", "type": "0x4f", "payload": "4f_63_74_76_a4_6d_ae_b6"}'
    """

    type_c = b'Octv\xa4\x6d\xae\xb6'

class OctvXEnd(OctvXBase):
    r"""
    >>> o = OctvXEnd(b'End \xa4\x6d\xae\xb6')
    >>> o
    OctvXEnd(b'End \xa4m\xae\xb6')
    >>> hex(o.type)
    '0x45'
    >>> str(o)
    '{"type_name": "OctvXEnd", "type": "0x45", "payload": "45_6e_64_20_a4_6d_ae_b6"}'
    """

    type_c = b'End \xa4\x6d\xae\xb6'


class OctvXConfig(OctvXBase):
    r"""
    >>> o = OctvXConfig(b'\x50\x01\x02\x80\xbb\x00\x58\x02')
    >>> o
    OctvXConfig(b'P\x01\x02\x80\xbb\x00X\x02')
    >>> hex(o.type)
    '0x50'
    >>> str(o)
    '{"type_name": "OctvXConfig", "type": "0x50", "payload": "50_01_02_80_bb_00_58_02", "octv_version": 1, "audio_sample_rate": 48000, "num_detectors": 600}'
    """

    # includes octv_version
    type_c = b'\x50\x01'
    struct_format = '<x B B BBB H'

    @property
    def octv_version(self):
        return self._octv_version

    @property
    def num_audio_channels(self):
        return self._num_audio_channels

    @property
    def audio_sample_rate(self):
        return self._audio_sample_rate

    @property
    def num_detectors(self):
        return self._num_detectors

    @property
    def as_dict(self):
        as_dict = super().as_dict
        as_dict.update(
            octv_version=self.octv_version,
            audio_sample_rate=self.audio_sample_rate,
            num_detectors=self.num_detectors,
        )
        return as_dict

    def __init__(self, payload):
        super().__init__(payload)
        self._octv_version, self._num_audio_channels, rate0, rate1, rate2, self._num_detectors = self.unpacked
        self._audio_sample_rate = rate0 | (rate1 << 8) | (rate2 << 16)


class OctvXMoment(OctvXBase):
    r"""
    >>> o = OctvXMoment(b'\x60\x00\x00\x00\x02\x00\x00\x00')
    >>> o
    OctvXMoment(b'`\x00\x00\x00\x02\x00\x00\x00')
    >>> hex(o.type)
    '0x60'
    >>> str(o)
    '{"type_name": "OctvXMoment", "type": "0x60", "payload": "60_00_00_00_02_00_00_00", "audio_frame_index_hi_bytes": 131072}'
    """

    type_c = b'\x60'
    struct_format = '<x xxx I'

    @property
    def audio_frame_index_hi_bytes(self):
        return self._audio_frame_index_hi_bytes

    @property
    def as_dict(self):
        as_dict = super().as_dict
        as_dict.update(
            audio_frame_index_hi_bytes=self.audio_frame_index_hi_bytes,
        )
        return as_dict

    def __init__(self, payload):
        super().__init__(payload)
        self._audio_frame_index_hi_bytes, = self.unpacked
        self._audio_frame_index_hi_bytes <<= 16


class OctvXTick(OctvXBase):
    r"""
    >>> o = OctvXTick(b'\x70\x01\x01\x02\x00\x00\x40\x3f')
    >>> o
    OctvXTick(b'p\x01\x01\x02\x00\x00@?')
    >>> hex(o.type)
    '0x70'
    >>> str(o)
    '{"type_name": "OctvXTick", "type": "0x70", "payload": "70_01_01_02_00_00_40_3f", "audio_channel": 1, "audio_frame_index_lo_bytes": 513, "audio_sample": 0.75}'
    """

    type_c = b'\x70'
    struct_format = '<x B H f'

    @property
    def audio_channel(self):
        return self._audio_channel

    @property
    def audio_frame_index_lo_bytes(self):
        return self._audio_frame_index_lo_bytes

    @property
    def audio_sample(self):
        return self._audio_sample

    @property
    def as_dict(self):
        as_dict = super().as_dict
        as_dict.update(
            audio_channel=self._audio_channel,
            audio_frame_index_lo_bytes=self._audio_frame_index_lo_bytes,
            audio_sample=self._audio_sample,
        )
        return as_dict

    def __init__(self, payload):
        super().__init__(payload)
        self._audio_channel, self._audio_frame_index_lo_bytes, self._audio_sample = self.unpacked

class OctvXFeature(OctvXBase):
    r"""
    >>> o = OctvXFeature(b'\x03\x0f\x01\x02\x01\x02\x04\x08')
    >>> o
    OctvXFeature(b'\x03\x0f\x01\x02\x01\x02\x04\x08')
    >>> hex(o.type)
    '0x3'
    >>> str(o)
    '{"type_name": "OctvXFeature", "type": "0x3", "payload": "03_0f_01_02_01_02_04_08", "frame_offset": 15, "detector_index": 513, "level_0_int8_0": 1, "level_0_int8_1": 2, "level_0_int8_2": 4, "level_0_int8_3": 8}'

    >>> str(OctvXFeature(b'\x23\x0f\x01\x02\x01\x02\x04\x08'))
    '{"type_name": "OctvXFeature", "type": "0x23", "payload": "23_0f_01_02_01_02_04_08", "frame_offset": 15, "detector_index": 513, "level_2_int8_0": 1, "level_2_int8_1": 2, "level_2_int16_0": 2052}'
    >>> str(OctvXFeature(b'\x33\x0f\x01\x02\x01\x02\x04\x08'))
    '{"type_name": "OctvXFeature", "type": "0x33", "payload": "33_0f_01_02_01_02_04_08", "frame_offset": 15, "detector_index": 513, "level_3_int16_0": 513, "level_3_int16_1": 2052}'
    """

    type_c = range(lib.OCTV_FEATURE_0_LOWER, lib.OCTV_FEATURE_3_UPPER)
    struct_format = '<x B H xxxx'

    level_0 = range(lib.OCTV_FEATURE_0_LOWER, lib.OCTV_FEATURE_0_UPPER)
    level_2 = range(lib.OCTV_FEATURE_2_LOWER, lib.OCTV_FEATURE_2_UPPER)
    level_3 = range(lib.OCTV_FEATURE_3_LOWER, lib.OCTV_FEATURE_3_UPPER)

    @property
    def frame_offset(self):
        return self._frame_offset

    @property
    def detector_index(self):
        return self._detector_index

    @property
    def as_dict(self):
        as_dict = super().as_dict
        as_dict.update(
            frame_offset=self._frame_offset,
            detector_index=self._detector_index,
        )
        match self.type:
            case level_0 if level_0 in self.level_0:
                int8s = struct.unpack('<BBBB', self.payload[4:])
                as_dict.update(
                    level_0_int8_0 = int8s[0],
                    level_0_int8_1 = int8s[1],
                    level_0_int8_2 = int8s[2],
                    level_0_int8_3 = int8s[3],
                    )
            case level_2 if level_2 in self.level_2:
                int8sint16 = struct.unpack('<BBH', self.payload[4:])
                as_dict.update(
                    level_2_int8_0 = int8sint16[0],
                    level_2_int8_1 = int8sint16[1],
                    level_2_int16_0 = int8sint16[2],
                    )
            case level_3 if level_3 in self.level_3:
                int16s = struct.unpack('<HH', self.payload[4:])
                as_dict.update(
                    level_3_int16_0 = int16s[0],
                    level_3_int16_1 = int16s[1],
                    )
            case _:
                raise AssertionError(f'should never happen, got {self.type}')
        return as_dict

    def validate_payload(self):
        # called from super().__init__ after self.payload and self.type are usable
        if not self.type in self.type_c:
            raise ValueError(f'{type(self).__name__} expected type to be in {self.type_c}, got {self.type}')

    def __init__(self, payload):
        super().__init__(payload)
        self._frame_offset, self._detector_index = self.unpacked


@ffi.def_extern()
def octv_flat_feature_cb0(flat_feature, user_data):
    cb = ffi.from_handle(user_data) if user_data != ffi.NULL else None
    log(f'octv_flat_feature_cb0: flat_feature {flat_feature}, user_data: {user_data}, cb: {cb}')
    return cb(flat_feature) if cb is not None else 0


@ffi.def_extern()
def octv_sentinelX_cb(sentinel):
    #log(f'octv_sentinelX_cb: sentinel {octv_struct_str(sentinel)}')
    log_terminal('octv_sentinelX_cb', sentinel)
    return 0

@ffi.def_extern()
def octv_endX_cb(end):
    #log(f'octv_endX_cb: end {end}')
    log_terminal('octv_endX_cb', end)
    return 0

@ffi.def_extern()
def octv_configX_cb(config):
    #log(f'octv_configX_cb: config {config}')
    log_terminal('octv_configX_cb', config)
    return 0

@ffi.def_extern()
def octv_momentX_cb(moment):
    #log(f'octv_momentX_cb: moment {moment}')
    log_terminal('octv_momentX_cb', moment)
    return 0

@ffi.def_extern()
def octv_tickX_cb(tick):
    #log(f'octv_tickX_cb: tick {tick}')
    log_terminal('octv_tickX_cb', tick)
    return 0

@ffi.def_extern()
def octv_featureX_cb(feature):
    #log(f'octv_featureX_cb: feature: type: {hex(feature.type)} : {octv_struct_str(feature)}')
    log_terminal('octv_featureX_cb', feature)
    return 0

@ffi.def_extern()
def octv_errorX_cb(code, payload):
    #log(f'octv_errorX_cb: code: {code}, payload: {payload}')
    log_terminal('octv_errorX_cb', payload)

    #return code
    return 0


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

def parse_flat0(file_c, flat_feature_cb):
    assert callable(flat_feature_cb), str((file_c, flat_feature_cb))
    sys.stdout.flush()
    lib.octv_parse_flat0(file_c, lib.octv_flat_feature_cb0, ffi.NULL)
    res = lib.octv_parse_flat0(file_c, lib.octv_flat_feature_cb0, ffi_new_handle(flat_feature_cb))

    return res

def make_octv_parse_class_callbacks(send):
    debug and log(f'make_octv_parse_class_callbacks: send: {send}')
    assert callable(send) or send is None, str((send))

    callbacks = ffi_new('OctvParseClass *')

    callbacks.user_data = ffi_new_handle(send)
    if False:
        # Yow! structs, (callbacks) only hold the pointer value, not the full handle object
        referents.append(ffi.new_handle(send))
        callbacks.user_data = referents[-1]

    if False:
        log(f'user_data: {callbacks.user_data}')

        blah = ffi.from_handle(callbacks.user_data)
        log(f'blah: {blah}')

        blah('fake make_octv_parse_class_callbacks')

        #callbacks.user_data = ffi.NULL

    callbacks.sentinel_cb = lib.octv_sentinel_cb
    callbacks.end_cb = lib.octv_end_cb
    callbacks.config_cb = lib.octv_config_cb
    callbacks.moment_cb = lib.octv_moment_cb
    callbacks.tick_cb = lib.octv_tick_cb
    callbacks.feature_cb = lib.octv_feature_cb
    callbacks.error_cb = lib.octv_error_cb

    return callbacks

def make_octv_parse_flat_callbacks(send):
    debug and log(f'make_octv_parse_flat_callbacks: send: {send}')
    assert callable(send) or send is None, str((send))

    callbacks = ffi_new('OctvParseFlat *')

    callbacks.user_data = ffi_new_handle(send)
    callbacks.flat_feature_cb = lib.octv_flat_feature_cb

    return callbacks

def octv_parse_class(file_c, send):
    callbacks = make_octv_parse_class_callbacks(send)

    sys.stdout.flush()
    res = lib.octv_parse_class(file_c, callbacks)
    #res = lib.octv_parse_class(file_c, ffi.NULL)
    #res = lib.octv_parse_class(file_c, lib.octv_class_cb, ffi.new_handle(send))

    return res

def octv_parse_flat(file_c, send):
    callbacks = make_octv_parse_flat_callbacks(send)

    sys.stdout.flush()
    res = lib.octv_parse_flat(file_c, callbacks)

    return res

def octv_parse_class0(file_c, send):
    sys.stdout.flush()
    res = lib.octv_parse_class0(file_c, lib.octv_class_cb, ffi_new_handle(send))
    return res

def new_parser():
    parser = ffi_new('OctvParseCallbacks *')

    parser.sentinel_cb = lib.octv_sentinelX_cb
    parser.end_cb = lib.octv_endX_cb
    parser.config_cb = lib.octv_configX_cb
    parser.moment_cb = lib.octv_momentX_cb
    parser.tick_cb = lib.octv_tickX_cb
    parser.feature_cb = lib.octv_featureX_cb

    parser.error_cb = lib.octv_errorX_cb

    return parser

def octv_parse_full(file_c, parser):
    log(f'octv_parse_full: file_c: {file_c}, parser: {parser}')
    sys.stdout.flush()
    res = lib.octv_parse_full(file_c, parser)

    return res
