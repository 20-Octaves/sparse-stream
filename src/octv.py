import sys, os
import contextlib
import struct
import json

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


@contextlib.contextmanager
def open_file_c(filename):
    # create and manage a FILE *
    file_c = None
    try:
        fd = os.open(filename, os.O_RDONLY)
        file_c = lib.fdopen(fd, 'r'.encode())
        debug and log(f'open_file_c: filename: {filename}, fd: {fd}, file_c: {file_c}')
        yield file_c
    finally:
        if file_c is not None:
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


class Octv(object):

    @ffi.def_extern()
    @staticmethod
    def octv_class_cb(payload, user_data):
        #log(f'Octv.octv_class_cb: payload: {payload}, user_data: {user_data}')
        try:
            octv = Octv.new_octv(payload)
            return ffi.from_handle(user_data)(octv) if user_data != ffi.NULL else 0
        except Exception as error:
            log(f'Octv.octv_class_cb: {type(error).__name__}: error: {error}')
            return 0

    @staticmethod
    def new_octv(payload):
        match struct.pack('<BBBBBBBB', *payload.bytes):
            case payload_bytes if payload_bytes[0] in OctvFeature.type_c:
                return OctvFeature(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvTick.type_c):
                return OctvTick(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvMoment.type_c):
                return OctvMoment(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvSentinel.type_c):
                return OctvSentinel(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvConfig.type_c):
                return OctvConfig(payload_bytes)
            case payload_bytes if payload_bytes.startswith(OctvEnd.type_c):
                return OctvEnd(payload_bytes)
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


class OctvBase(object):
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

class OctvSentinel(OctvBase):
    r"""
    >>> o = OctvSentinel(b'Octv\xa4\x6d\xae\xb6')
    >>> o
    OctvSentinel(b'Octv\xa4m\xae\xb6')
    >>> hex(o.type)
    '0x4f'
    >>> str(o)
    '{"type_name": "OctvSentinel", "type": "0x4f", "payload": "4f_63_74_76_a4_6d_ae_b6"}'
    """

    type_c = b'Octv\xa4\x6d\xae\xb6'

class OctvEnd(OctvBase):
    r"""
    >>> o = OctvEnd(b'End \xa4\x6d\xae\xb6')
    >>> o
    OctvEnd(b'End \xa4m\xae\xb6')
    >>> hex(o.type)
    '0x45'
    >>> str(o)
    '{"type_name": "OctvEnd", "type": "0x45", "payload": "45_6e_64_20_a4_6d_ae_b6"}'
    """

    type_c = b'End \xa4\x6d\xae\xb6'


class OctvConfig(OctvBase):
    r"""
    >>> o = OctvConfig(b'\x50\x01\x02\x80\xbb\x00\x58\x02')
    >>> o
    OctvConfig(b'P\x01\x02\x80\xbb\x00X\x02')
    >>> hex(o.type)
    '0x50'
    >>> str(o)
    '{"type_name": "OctvConfig", "type": "0x50", "payload": "50_01_02_80_bb_00_58_02", "octv_version": 1, "audio_sample_rate": 48000, "num_detectors": 600}'
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


class OctvMoment(OctvBase):
    r"""
    >>> o = OctvMoment(b'\x60\x00\x00\x00\x02\x00\x00\x00')
    >>> o
    OctvMoment(b'`\x00\x00\x00\x02\x00\x00\x00')
    >>> hex(o.type)
    '0x60'
    >>> str(o)
    '{"type_name": "OctvMoment", "type": "0x60", "payload": "60_00_00_00_02_00_00_00", "audio_frame_index_hi_bytes": 131072}'
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


class OctvTick(OctvBase):
    r"""
    >>> o = OctvTick(b'\x70\x01\x01\x02\x00\x00\x40\x3f')
    >>> o
    OctvTick(b'p\x01\x01\x02\x00\x00@?')
    >>> hex(o.type)
    '0x70'
    >>> str(o)
    '{"type_name": "OctvTick", "type": "0x70", "payload": "70_01_01_02_00_00_40_3f", "audio_channel": 1, "audio_frame_index_lo_bytes": 513, "audio_sample": 0.75}'
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

class OctvFeature(OctvBase):
    r"""
    >>> o = OctvFeature(b'\x03\x0f\x01\x02\x01\x02\x04\x08')
    >>> o
    OctvFeature(b'\x03\x0f\x01\x02\x01\x02\x04\x08')
    >>> hex(o.type)
    '0x3'
    >>> str(o)
    '{"type_name": "OctvFeature", "type": "0x3", "payload": "03_0f_01_02_01_02_04_08", "frame_offset": 15, "detector_index": 513, "level_0_int8_0": 1, "level_0_int8_1": 2, "level_0_int8_2": 4, "level_0_int8_3": 8}'

    >>> str(OctvFeature(b'\x23\x0f\x01\x02\x01\x02\x04\x08'))
    '{"type_name": "OctvFeature", "type": "0x23", "payload": "23_0f_01_02_01_02_04_08", "frame_offset": 15, "detector_index": 513, "level_2_int8_0": 1, "level_2_int8_1": 2, "level_2_int16_0": 2052}'
    >>> str(OctvFeature(b'\x33\x0f\x01\x02\x01\x02\x04\x08'))
    '{"type_name": "OctvFeature", "type": "0x33", "payload": "33_0f_01_02_01_02_04_08", "frame_offset": 15, "detector_index": 513, "level_3_int16_0": 513, "level_3_int16_1": 2052}'
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
def octv_flat_feature_cb(flat_feature, user_data):
    cb = ffi.from_handle(user_data) if user_data != ffi.NULL else None
    log(f'octv_flat_feature_cb: flat_feature {flat_feature}, user_data: {user_data}, cb: {cb}')
    return cb(flat_feature) if cb is not None else 0


@ffi.def_extern()
def octv_sentinel_cb(sentinel):
    #log(f'octv_sentinel_cb: sentinel {octv_struct_str(sentinel)}')
    log_terminal('octv_sentinel_cb', sentinel)
    return 0

@ffi.def_extern()
def octv_end_cb(end):
    #log(f'octv_end_cb: end {end}')
    log_terminal('octv_end_cb', end)
    return 0

@ffi.def_extern()
def octv_config_cb(config):
    #log(f'octv_config_cb: config {config}')
    log_terminal('octv_config_cb', config)
    return 0

@ffi.def_extern()
def octv_moment_cb(moment):
    #log(f'octv_moment_cb: moment {moment}')
    log_terminal('octv_moment_cb', moment)
    return 0

@ffi.def_extern()
def octv_tick_cb(tick):
    #log(f'octv_tick_cb: tick {tick}')
    log_terminal('octv_tick_cb', tick)
    return 0

@ffi.def_extern()
def octv_feature_cb(feature):
    #log(f'octv_feature_cb: feature: type: {hex(feature.type)} : {octv_struct_str(feature)}')
    log_terminal('octv_feature_cb', feature)
    return 0

@ffi.def_extern()
def octv_error_cb(code, payload):
    #log(f'octv_error_cb: code: {code}, payload: {payload}')
    log_terminal('octv_error_cb', payload)

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

def parse_flat(file_c, flat_feature_cb):
    assert callable(flat_feature_cb), str((file_c, flat_feature_cb))
    sys.stdout.flush()
    lib.octv_parse_flat(file_c, lib.octv_flat_feature_cb, ffi.NULL)
    res = lib.octv_parse_flat(file_c, lib.octv_flat_feature_cb, ffi.new_handle(flat_feature_cb))
    #res = lib.octv_parse_flat(file_c, lib.octv_flat_feature_cb, ffi.NULL)

    return res

def octv_parse_class(file_c, send):
    res = lib.octv_parse_class(file_c, lib.octv_class_cb, ffi.new_handle(send))
    return res

# referents holds onto cdata objects until this module goes away, needed because pointers in cdata
# structs don't hold onto the underlying cdata

referents = list()
def new(c_type):
    referents.append(ffi.new(c_type))
    return referents[-1]

def new_parser():
    parser = new('OctvParseCallbacks *')

    parser.sentinel_cb = lib.octv_sentinel_cb
    parser.end_cb = lib.octv_end_cb
    parser.config_cb = lib.octv_config_cb
    parser.moment_cb = lib.octv_moment_cb
    parser.tick_cb = lib.octv_tick_cb
    parser.feature_cb = lib.octv_feature_cb

    parser.error_cb = lib.octv_error_cb

    return parser

def octv_parse_full(file_c, parser):
    log(f'octv_parse_full: file_c: {file_c}, parser: {parser}')
    sys.stdout.flush()
    res = lib.octv_parse_full(file_c, parser)

    return res
