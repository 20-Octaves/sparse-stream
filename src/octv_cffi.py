from cffi import FFI
ffibuilder = FFI()


header_filename = 'octv.h'

with open(header_filename, 'rt') as header_file:
    header_str = header_file.read()

stdlib_str = """
     FILE * fdopen(int fildes, const char *mode);
     int fclose(FILE *stream);
"""

extern_python_str = """
  extern "Python" int octv_flat_feature_cb(OctvFlatFeature * flat_feature, void * user_data);

  extern "Python" int octv_sentinel_cb(OctvDelimiter * sentinel);
  extern "Python" int octv_end_cb(OctvDelimiter * end);

  extern "Python" int octv_config_cb(OctvConfig * config);
  extern "Python" int octv_moment_cb(OctvMoment * moment);
  extern "Python" int octv_tick_cb(OctvTick * tick);
  extern "Python" int octv_feature_cb(OctvFeature * feature);

  extern "Python" int octv_error_cb(int code, OctvPayload * payload);
"""

# cdef() expects a single string declaring the C types, functions and
# globals needed to use the shared object. It must be in valid C syntax.
ffibuilder.cdef(header_str + stdlib_str + extern_python_str)
#ffibuilder.cdef(header_str + stdlib_str)
#ffibuilder.cdef(header_str)

# set_source() gives the name of the python extension module to
# produce, and some C source code as a string.  This C code needs
# to make the declarated functions, types and globals available,
# so it is often just the "#include".
# see also: https://setuptools.pypa.io/en/stable/userguide/ext_modules.html#building-extension-modules
ffibuilder.set_source("octv_cffi",
                      f"""
     #include "{header_filename}"
""",
                      library_dirs=['.'],  # library search path, for the linker
                      libraries=['octv'],  # library name, for the linker
                      # extra_link_args hasn't worked, so we cp liboctv.o to /usr/lib
                      #runtime_library_dirs=['/octv'],
                      #extra_link_args=['-Wl,-rpath=/octv'],
                      #library_dirs=['/octv'],
                      )

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
