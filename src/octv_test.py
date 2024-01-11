print()

import sys, os

import octv
from octv import ffi, lib


debug = False
debug = True

main = __name__ == '__main__'

_, FILE = os.path.split(__file__)

def log(*args):
    print(f'{FILE}:', *args)


def octv_test(args):

    assert not args, str((args,))

    # single-value terminals
    print(f'octv_test: OCTV_SENTINEL_TYPE: {hex(lib.OCTV_SENTINEL_TYPE)} {repr(chr(lib.OCTV_SENTINEL_TYPE))}')
    print(f'octv_test: OCTV_END_TYPE: {hex(lib.OCTV_END_TYPE)} {repr(chr(lib.OCTV_END_TYPE))}')
    print(f'octv_test: OCTV_CONFIG_TYPE: {hex(lib.OCTV_CONFIG_TYPE)}')
    print(f'octv_test: OCTV_MOMENT_TYPE: {hex(lib.OCTV_MOMENT_TYPE)}')
    print(f'octv_test: OCTV_TICK_TYPE: {hex(lib.OCTV_TICK_TYPE)}')

    # FEATURE masks, mutually exclusive bits
    print(f'octv_test: OCTV_FEATURE_MASK: {hex(lib.OCTV_FEATURE_MASK)}')
    print(f'octv_test: OCTV_NON_FEATURE_MASK: {hex(lib.OCTV_NON_FEATURE_MASK)}')
    print(f'octv_test: OCTV_FEATURE_MASK & OCTV_NON_FEATURE_MASK: {hex(lib.OCTV_FEATURE_MASK & lib.OCTV_NON_FEATURE_MASK)}')
    assert (lib.OCTV_FEATURE_MASK & lib.OCTV_NON_FEATURE_MASK) == 0x00, str((hex(lib.OCTV_FEATURE_MASK & lib.OCTV_NON_FEATURE_MASK), hex(lib.OCTV_FEATURE_MASK), hex(lib.OCTV_NON_FEATURE_MASK)))
    print(f'octv_test: OCTV_FEATURE_MASK | OCTV_NON_FEATURE_MASK: {hex(lib.OCTV_FEATURE_MASK | lib.OCTV_NON_FEATURE_MASK)}')
    assert (lib.OCTV_FEATURE_MASK | lib.OCTV_NON_FEATURE_MASK) == 0xff, str((hex(lib.OCTV_FEATURE_MASK | lib.OCTV_NON_FEATURE_MASK), hex(lib.OCTV_FEATURE_MASK), hex(lib.OCTV_NON_FEATURE_MASK)))

    # FEATURE supports up to 63 values
    print(f'octv_test: OCTV_FEATURE_0_LOWER: {hex(lib.OCTV_FEATURE_0_LOWER)}')
    print(f'octv_test: OCTV_FEATURE_3_UPPER: {hex(lib.OCTV_FEATURE_3_UPPER)}')
    print(f'octv_test: OCTV_FEATURE_3_UPPER - OCTV_FEATURE_0_LOWER: {lib.OCTV_FEATURE_3_UPPER-lib.OCTV_FEATURE_0_LOWER}')

    print()
    print(f'octv_test: _octv_prevent_warnings(): {lib._octv_prevent_warnings()}')

    print()
    print(f'label: ffi.sizeof("OctvDelimiter"): {ffi.sizeof("OctvDelimiter")}')
    print(f'label: ffi.sizeof("OctvConfig"): {ffi.sizeof("OctvConfig")}')
    print(f'label: ffi.sizeof("OctvMoment"): {ffi.sizeof("OctvMoment")}')
    print(f'label: ffi.sizeof("OctvTick"): {ffi.sizeof("OctvTick")}')
    print(f'label: ffi.sizeof("OctvFeature"): {ffi.sizeof("OctvFeature")}')

    print()
    print(f'label: ffi.sizeof("OctvPayload"): {ffi.sizeof("OctvPayload")}')

    print()
    print(f'label: ffi.sizeof("OctvFullFeature"): {ffi.sizeof("OctvFullFeature")}')
    print(f'label: ffi.sizeof("OctvFlatFeature"): {ffi.sizeof("OctvFlatFeature")}')
    print()
    print(f'label: ffi.sizeof("OctvParseCallbacks"): {ffi.sizeof("OctvParseCallbacks")}')

    print()

    parser = octv.new_parser()

    print(f'octv_test: parser: {parser}')

    with octv.open_file_c('octv_test.py') as file_c:
        print(f'octv_test: octv_parse_file(): {octv.octv_parse_full(file_c, parser)}')


    def send_obj(obj):
        log(f'send_obj: obj: {obj}')
        return 0

    with octv.open_file_c('test2.octv') as file_c:
        res = octv.octv_parse_class0(file_c, send_obj)

    with octv.open_file_c('test1.octv') as file_c:
        res = octv.octv_parse_class0(file_c, send_obj)


    # called with each full feature
    def flat_feature_cb(feature):
        log(f'flat_feature_cb: feature: {feature}')
        feature_o = octv.flat_feature_object(feature)
        log(f'flat_feature_cb: feature_o: {feature_o}')

        return 0

    with octv.open_file_c('octv_test.py') as file_c:
        print(f'octv_test: octv_parse_flat0(): {octv.parse_flat0(file_c, flat_feature_cb)}')


    with octv.open_file_c('test1.octv') as file_c:
        while True:
            res = octv.octv_parse_full(file_c, parser)
            print(f'octv_test: octv_parse_full(): {res}')
            if res != 0: break


    print()

    # Exercise octv_parse_class()

    # NULL file, OCTV_ERROR_NULL
    res = octv.octv_parse_class(ffi.NULL, send_obj)
    log(f'octv_test: octv_parse_class: res: {res}')
    print()

    # bogus data, invalid type, OCTV_ERROR_TYPE
    with octv.open_file_c('test1.octv') as file_c:
        res = octv.octv_parse_class(file_c, send_obj)
    log(f'octv_test: octv_parse_class: res: {res}')
    print()

    # bad version value, OCTV_ERROR_VALUE
    with octv.open_file_c('test4.octv') as file_c:
        res = octv.octv_parse_class(file_c, send_obj)
    log(f'octv_test: octv_parse_class: res: {res}')
    print()

    # truncated Octv, OCTV_ERROR_EOF
    with octv.open_file_c('test3.octv') as file_c:
        res = octv.octv_parse_class(file_c, send_obj)
    log(f'octv_test: octv_parse_class: res: {res}')
    print()

    # valid Octv, no callback
    with octv.open_file_c('test2.octv') as file_c:
        res = octv.octv_parse_class(file_c, None)
    log(f'octv_test: octv_parse_class: res: {res}')
    print()

    # valid Octv, with callback
    with octv.open_file_c('test2.octv') as file_c:
        res = octv.octv_parse_class(file_c, send_obj)
    log(f'octv_test: octv_parse_class: res: {res}')
    print()


    print('OK')

if main:
    sys.exit(octv_test(sys.argv[1:]))
