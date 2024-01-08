print()

import sys, os

from octv_cffi import ffi, lib
import octv


debug = True
debug = False

main = __name__ == '__main__'

_, FILE = os.path.split(__file__)

def log(*args):
    print(f'{FILE}:', *args)


def octv_test(args):

    assert not args, str((args,))

    # single-value terminals
    print(f'octv_test: OCTV_SENTINEL_TYPE: {hex(lib.OCTV_SENTINEL_TYPE)}')
    print(f'octv_test: OCTV_END_TYPE: {hex(lib.OCTV_END_TYPE)}')
    print(f'octv_test: OCTV_CONFIG_TYPE: {hex(lib.OCTV_CONFIG_TYPE)}')
    print(f'octv_test: OCTV_MOMENT_TYPE: {hex(lib.OCTV_MOMENT_TYPE)}')
    print(f'octv_test: OCTV_TICK_TYPE: {hex(lib.OCTV_TICK_TYPE)}')

    # FEATURE supports up to 63 values
    print(f'octv_test: OCTV_FEATURE_MASK: {hex(lib.OCTV_FEATURE_MASK)}')
    print(f'octv_test: OCTV_FEATURE_LOWER: {hex(lib.OCTV_FEATURE_LOWER)}')
    print(f'octv_test: OCTV_FEATURE_UPPER: {hex(lib.OCTV_FEATURE_UPPER)}')
    print(f'octv_test: OCTV_NOT_FEATURE_MASK: {hex(lib.OCTV_NOT_FEATURE_MASK)}')

    print()
    print(f'octv_test: _octv_prevent_warnings(): {lib._octv_prevent_warnings()}')

    print()
    print(f'label: ffi.sizeof("OctvDelimiter"): {ffi.sizeof("OctvDelimiter")}')
    print(f'label: ffi.sizeof("OctvConfig"): {ffi.sizeof("OctvConfig")}')
    print(f'label: ffi.sizeof("OctvMoment"): {ffi.sizeof("OctvMoment")}')
    print(f'label: ffi.sizeof("OctvTick"): {ffi.sizeof("OctvTick")}')
    print(f'label: ffi.sizeof("OctvFeature"): {ffi.sizeof("OctvFeature")}')

    print(f'label: ffi.sizeof("OctvPayload"): {ffi.sizeof("OctvPayload")}')

    print()

    fd = os.open('octv_test.py', os.O_RDONLY)
    print(f'fd: {fd}')

    file_c = lib.fdopen(fd, 'r'.encode())
    print(f'file_c: {file_c}')

    parser = octv.new_parser()

    print(f'octv_test: parser: {parser}')

    print(f'octv_test: octv_parse_file(): {lib.octv_parse_full(file_c, parser)}')

    def flat_feature_cb(feature):
        log(f'flat_feature_cb: feature: {feature}')
        feature_o = octv.flat_feature_object(feature)
        log(f'flat_feature_cb: feature_o: {feature_o}')

        return 0

    print(f'octv_test: octv_parse_flat(): {octv.parse_flat(file_c, flat_feature_cb)}')


if main:
    sys.exit(octv_test(sys.argv[1:]))
