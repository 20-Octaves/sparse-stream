#include <stdint.h>
#include <stdio.h>

#include "octv.h"

#define OCTV_DELIMITER_SIGNATURE  0x00, 0x00, 0x00, 0x00

#define OCTV_SENTINEL_INITIALIZER  OCTV_SENTINEL_TYPE, { 'c', 't', 'v', }, { OCTV_DELIMITER_SIGNATURE }

#define OCTV_END_INITIALIZER OCTV_END_TYPE, { 'n', 'd', '_', }, { OCTV_DELIMITER_SIGNATURE }


// Delimiters are fully populated singletons
static const OctvDelimiter octv_sentinel = { OCTV_SENTINEL_INITIALIZER };
static const OctvDelimiter octv_end = { OCTV_END_INITIALIZER };

// Fill in fixed fields
static const OctvConfig octv_config = { OCTV_CONFIG_TYPE, OCTV_VERSION, 0 };
static const OctvMoment octv_moment = { OCTV_MOMENT_TYPE, { 0, 0, 0 }, 0 };
static const OctvTick octv_tick = { OCTV_TICK_TYPE, 0 };


// error condition, see what client wants to do
static
int octv_error(int code, OctvPayload * payload, const OctvParseClass * parse_class_cbs) {
  return parse_class_cbs != NULL && parse_class_cbs->error_cb != NULL
    ? parse_class_cbs->error_cb(code, payload, parse_class_cbs->user_data)
    : code;
}

// check OctvPayload.delimiter.signature
static
int octv_check_signature(const OctvDelimiter * delimiter) {
  return delimiter->signature[0] == 0xa4 && delimiter->signature[1] == 0x6d && delimiter->signature[2] == 0xae && delimiter->signature[3] == 0xb6;
}

int octv_parse_class(FILE * file, const OctvParseClass * parse_class_cbs) {
  printf("octv.c:: octv_parse_class(): file: %p, parse_class_cbs: %p, user_data: %p\n", file, parse_class_cbs, parse_class_cbs != NULL ? parse_class_cbs->user_data : NULL);
  fflush(stdout);

  if( file == NULL ||  parse_class_cbs == NULL ) return OCTV_ERROR_NULL;

  while( 1 ) {
    OctvPayload payload;
    char * chars;

    const int num_items = fread(&payload, sizeof(payload), 1, file);
    if( num_items != 1 ) {
      // TODO: fread manpage says eof and error cannot be distinguished without further work...
      // we ignore the code from octv_error (from parse_class_cbs->error_cb)
      octv_error(OCTV_ERROR_EOF, &payload, parse_class_cbs);
      return OCTV_ERROR_EOF;
    }

    // switch statement cases can set code to non-zero, which is then returned
    int code = 0;
    switch (payload.type) {
    default:
      // invalid type, client can return 0 to allow parsing to continue
      // TODO: implement code to find next valid terminal or sentinel
      code = octv_error(OCTV_ERROR_TYPE, &payload, parse_class_cbs);
      break;

    case OCTV_END_TYPE:
      chars = payload.delimiter.chars;
      //OctvDelimiter end = payload.delimiter;
      if( chars[0] == 'n' && chars[1] == 'd' && chars[2] == ' ' && octv_check_signature(&payload.delimiter) ) {
        //if( end.chars[0] == 'n' && end.chars[1] == 'd' && end.chars[2] == ' ' && octv_check_signature(&payload.delimiter) ) {
        //&& end.signature[0] == 0xa4 && end.signature[1] == 0x6d && end.signature[2] == 0xae && end.signature[3] == 0xb6 ) {
        // always return on valid OCTV_END_TYPE
        return parse_class_cbs != NULL && parse_class_cbs->end_cb != NULL
          ? parse_class_cbs->end_cb(&payload.delimiter, parse_class_cbs->user_data)
          : 0;
      }
      else {
        code = octv_error(OCTV_ERROR_VALUE, &payload, parse_class_cbs);
      }
      break;

    case OCTV_SENTINEL_TYPE:
      chars = payload.delimiter.chars;
      //OctvDelimiter sentinel = payload.delimiter;
      if( chars[0] == 'c' && chars[1] == 't' && chars[2] == 'v' && octv_check_signature(&payload.delimiter) ) {
        //if( sentinel.chars[0] == 'c' && sentinel.chars[1] == 't' && sentinel.chars[2] == 'v' && octv_check_signature(&payload.delimiter) ) {
        //&& sentinel.signature[0] == 0xa4 && sentinel.signature[1] == 0x6d && sentinel.signature[2] == 0xae && sentinel.signature[3] == 0xb6 ) {
        if( parse_class_cbs != NULL && parse_class_cbs->sentinel_cb != NULL ) {
          code = parse_class_cbs->sentinel_cb(&payload.delimiter, parse_class_cbs->user_data);
        }
      }
      else {
        code = octv_error(OCTV_ERROR_VALUE, &payload, parse_class_cbs);
      }
      break;

    case OCTV_CONFIG_TYPE:
      // TODO: plan for older versions...
      if( payload.config.octv_version == OCTV_VERSION ) {
        if( parse_class_cbs != NULL && parse_class_cbs->config_cb != NULL ) {
          code = parse_class_cbs->config_cb(&payload.config, parse_class_cbs->user_data);
        }
      }
      else {
        code = octv_error(OCTV_ERROR_VALUE, &payload, parse_class_cbs);
      }
      break;


    case OCTV_MOMENT_TYPE:
      if( parse_class_cbs != NULL && parse_class_cbs->moment_cb != NULL ) {
        code = parse_class_cbs->moment_cb(&payload.moment, parse_class_cbs->user_data);
      }
      break;

    case OCTV_TICK_TYPE:
      if( parse_class_cbs != NULL && parse_class_cbs->tick_cb != NULL ) {
        code = parse_class_cbs->tick_cb(&payload.tick, parse_class_cbs->user_data);
      }
      break;

    case OCTV_FEATURE_0_LOWER ... OCTV_FEATURE_3_UPPER:
      // OCTV_FEATURE_0_LOWER thru OCTV_FEATURE_0_UPPER
      /*   */
        /*
  case 0x01: case 0x02: case 0x03: case 0x04: case 0x05: case 0x06: case 0x07:
    case 0x08: case 0x09: case 0x0a: case 0x0b: case 0x0c: case 0x0d: case 0x0e: case 0x0f:
    case 0x10: case 0x11: case 0x12: case 0x13: case 0x14: case 0x15: case 0x16: case 0x17:
    case 0x18: case 0x19: case 0x1a: case 0x1b: case 0x1c: case 0x1d: case 0x1e: case 0x1f:

      // OCTV_FEATURE_2_LOWER thru OCTV_FEATURE_2_UPPER
    case 0x20: case 0x21: case 0x22: case 0x23: case 0x24: case 0x25: case 0x26: case 0x27:
    case 0x28: case 0x29: case 0x2a: case 0x2b: case 0x2c: case 0x2d: case 0x2e: case 0x2f:

      // OCTV_FEATURE_3_LOWER thru OCTV_FEATURE_3_UPPER
    case 0x30: case 0x31: case 0x32: case 0x33: case 0x34: case 0x35: case 0x36: case 0x37:
    case 0x38: case 0x39: case 0x3a: case 0x3b: case 0x3c: case 0x3d: case 0x3e: case 0x3f:
        */
      if( parse_class_cbs != NULL && parse_class_cbs->feature_cb != NULL ) {
        code = parse_class_cbs->feature_cb(&payload.feature, parse_class_cbs->user_data);
      }
      break;
    }

    if( code != 0 ) return code;
  }
}


int octv_parse_flat(FILE * file, const OctvParseFlat * parse_flat_cbs) {
  printf("octv.c:: octv_parse_flat(): file: %p, parse_flat_cbs: %p, user_data: %p\n", file, parse_flat_cbs, parse_flat_cbs != NULL ? parse_flat_cbs->user_data : NULL);
  fflush(stdout);

  if( file == NULL || parse_flat_cbs == NULL ) return OCTV_ERROR_NULL;

  OctvFlatFeature flat_feature_c;
  flat_feature_c.type = 'H';
  return parse_flat_cbs->flat_feature_cb(&flat_feature_c, parse_flat_cbs->user_data);

  return 0;
}

int octv_parse_class0(FILE * file,  octv_parse_class0_cb_t parse_class0_cb, void * user_data) {
  //int octv_parse_class(FILE * file, int(*parse_class_cb)(OctvPayload *, void *), void * user_data) {
  printf("octv.c:: octv_parse_class0():\n");
  fflush(stdout);

  while( 1 ) {
    OctvPayload payload;
    const int got = fread(&payload, sizeof(payload), 1, file);
    if( got != 1 ) return OCTV_ERROR_EOF;

    const int code = parse_class0_cb(&payload, user_data);
    if( code != 0 ) return code;
  }
}


int octv_parse_full(FILE * file, OctvParseCallbacks * callbacks) {
  printf("octv.c:: octv_parse_full():\n");
  fflush(stdout);

  OctvPayload payload;
  int code;

  while( 1 ) {
    const int got = fread(&payload, sizeof(payload), 1, file);
    if( got != 1 ) {
      callbacks->error_cb(OCTV_ERROR_EOF, NULL);
      return OCTV_ERROR_EOF;
    }

    //printf("octv.c:: octv_parse_full: payload.type: 0x%02x\n", payload.type);
    //fflush(stdout);

    if( payload.type & OCTV_NON_FEATURE_MASK ) {
      // terminals other than FEATURE
      switch (payload.type) {
      default:
        // type is not handled
        code = callbacks->error_cb(OCTV_ERROR_TYPE, &payload);
        if( code != 0 ) return code;
        break;

      case OCTV_END_TYPE:
        OctvDelimiter end = payload.delimiter;
        code = callbacks->end_cb(&end);
        // end of what we consume from stream, regardless of value of code
        return code;


      case OCTV_SENTINEL_TYPE:
        OctvDelimiter sentinel = payload.delimiter;
        code = callbacks->sentinel_cb(&sentinel);
        if( code != 0 ) return code;
        break;

      case OCTV_CONFIG_TYPE:
        OctvConfig config = payload.config;
        code = callbacks->config_cb(&config);
        if( code != 0 ) return code;
        break;

      case OCTV_MOMENT_TYPE:
        OctvMoment moment = payload.moment;
        code = callbacks->moment_cb(&moment);
        if( code != 0 ) return code;
        break;

      case OCTV_TICK_TYPE:
        OctvTick tick = payload.tick;
        code = callbacks->tick_cb(&tick);
        if( code != 0 ) return code;
        break;
      }
    }
    else if( payload.type & OCTV_FEATURE_MASK ) {
      // FEATURE
      OctvFeature feature = payload.feature;
      code = callbacks->feature_cb(&feature);
      if( code != 0 ) return code;
    }
    else {
      // payload.type field is 0x00
      code = callbacks->error_cb(OCTV_ERROR_TYPE, &payload);
      if( code != 0 ) return code;
    }
  }
}

int octv_parse_flat0(FILE * file, octv_flat_feature_cb_t flat_feature_cb, void * user_data) {
  printf("octv.c:: octv_parse_flat0():\n");

  OctvFlatFeature flat_feature = { 0 };

  OctvPayload payload;

  while( 1 ) {
    int got = fread(&payload, sizeof(payload), 1, file);
    if( got != 1 ) break;
  }
  fflush(stdout);

  int code = 0;
  if( flat_feature_cb != NULL ) {
    code = flat_feature_cb(&flat_feature, user_data);
  }

  fflush(stdout);
  return code + flat_feature.type;
}


int _octv_prevent_warnings() {
  // prevent warnings by doing stuff with what's been declared
  int result = 0;

  result += octv_sentinel.type;
  result += octv_end.type;
  result += octv_config.type + octv_config.octv_version;
  result += octv_moment.type;
  result += octv_tick.type;

  for( int feature_type = OCTV_FEATURE_0_LOWER; feature_type <= OCTV_FEATURE_3_UPPER; ++feature_type ) {
    const OctvFeature feature = { feature_type };
    result += feature.type;
  }
  return result;
}
