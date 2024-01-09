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


int octv_parse_flat(FILE * file, octv_flat_feature_cb_t flat_feature_cb, void * user_data) {
//int octv_parse_flat(FILE * file, int (*flat_feature_cb)(OctvFlatFeature * flat_feature, void * user_data), void * user_data) {
  OctvFlatFeature flat_feature = { 0 };

  OctvPayload payload;

  while( 1 ) {
    int got = fread(&payload, sizeof(payload), 1, file);
    if( got != 1 ) break;
    //printf("octv.c: payload.type: %c 0x%2x\n", payload.type, payload.type);
  }
  fflush(stdout);

  int code = 0;
  if( flat_feature_cb != NULL ) {
    code = flat_feature_cb(&flat_feature, user_data);
  }
  return code + flat_feature.type;
}

int octv_parse_full(FILE * file, OctvParseCallbacks * callbacks) {
  OctvConfig config = octv_config;
  OctvMoment moment = octv_moment;
  OctvTick tick = octv_tick;
  OctvFeature feature = { 0 };

  OctvFullFeature full_feature = {
    .config = &config,
    .moment = &moment,
    .tick = &tick,
    .feature = &feature
  };
  return 0 + full_feature.feature->type;
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
