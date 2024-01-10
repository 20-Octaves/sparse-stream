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


int octv_parse_class(FILE * file,  octv_parse_class_cb_t parse_class_cb, void * user_data) {
  //int octv_parse_class(FILE * file, int(*parse_class_cb)(OctvPayload *, void *), void * user_data) {
  printf("octv.c:: octv_parse_class():\n");
  fflush(stdout);

  while( 1 ) {
    OctvPayload payload;
    const int got = fread(&payload, sizeof(payload), 1, file);
    if( got != 1 ) return OCTV_ERROR_EOF;

    const int code = parse_class_cb(&payload, user_data);
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
      code = callbacks->error_cb(OCTV_ERROR_NULL, &payload);
      if( code != 0 ) return code;
    }
  }
}

int octv_parse_flat(FILE * file, octv_flat_feature_cb_t flat_feature_cb, void * user_data) {
  printf("octv.c:: octv_parse_flat():\n");

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
