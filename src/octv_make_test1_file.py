#!/usr/bin/env python3

import struct

values = range(1, 8)
with open('test1.octv', 'wb') as testfile:
    for typ in range(1<<8):
        payload = struct.pack('BBBBBBBB', typ, *values)
        testfile.write(payload)
