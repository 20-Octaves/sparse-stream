#include <stdint.h>
#include <stdio.h>

#include "octv.h"

// "Octv"
#define OCTV_SENTINEL_CHARS  OCTV_SENTINEL_TYPE, 'c', 't', 'v'
// "End "
#define OCTV_END_CHARS  OCTV_END_TYPE, 'n', 'd', ' '
// random, but not in -2 .. 2
#define OCTV_DELIMITER_SIGNATURE  0xa4, 0x6d, 0xae, 0xb6


static const char sentinel_chars[4] = { OCTV_SENTINEL_CHARS };
static const char end_chars[4] = { OCTV_END_CHARS };
static const uint8_t delimiter_signature[4] = { OCTV_END_CHARS };


// Delimiters are fully populated singletons
static const OctvDelimiter octv_sentinel = { { OCTV_SENTINEL_CHARS }, { OCTV_DELIMITER_SIGNATURE } };
static const OctvDelimiter octv_end = {  { OCTV_END_CHARS }, { OCTV_DELIMITER_SIGNATURE } };

// Fill in fixed fields
static const OctvConfig octv_config = { OCTV_CONFIG_TYPE, OCTV_VERSION, 0 };
static const OctvMoment octv_moment = { OCTV_MOMENT_TYPE, { 0 } };
static const OctvTick octv_tick = { OCTV_TICK_TYPE, 0 };


// check OctvPayload.delimiter.chars for sentinel_chars
static
int octv_check_sentinel_chars(const OctvDelimiter * delimiter) {
  return delimiter->chars[0] == sentinel_chars[0] && delimiter->chars[1] == sentinel_chars[1] && delimiter->chars[2] == sentinel_chars[2] && delimiter->chars[3] == sentinel_chars[3];
}
// check OctvPayload.delimiter.chars for end_chars
static
int octv_check_end_chars(const OctvDelimiter * delimiter) {
  return delimiter->chars[0] == end_chars[0] && delimiter->chars[1] == end_chars[1] && delimiter->chars[2] == end_chars[2] && delimiter->chars[3] == end_chars[3];
}

// check OctvPayload.delimiter.signature
static
int octv_check_signature(const OctvDelimiter * delimiter) {
  return delimiter->signature[0] == delimiter_signature[0] && delimiter->signature[1] == delimiter_signature[1] && delimiter->signature[2] == delimiter_signature[2] && delimiter->signature[3] == delimiter_signature[3];
  //return delimiter->signature[0] == 0xa4 && delimiter->signature[1] == 0x6d && delimiter->signature[2] == 0xae && delimiter->signature[3] == 0xb6;
}


// error condition, see what client wants to do
static
int octv_error(int code, OctvPayload * payload, const OctvParseClass * parse_class_cbs) {
  return parse_class_cbs != NULL && parse_class_cbs->error_cb != NULL
    ? parse_class_cbs->error_cb(code, payload, parse_class_cbs->user_data)
    : code;
}


// parse a FILE * stream, dispatching to each terminal type, stateless
int octv_parse_class(FILE * file, const OctvParseClass * parse_class_cbs) {
  printf("octv.c:: octv_parse_class(): file: %p, parse_class_cbs: %p, user_data: %p\n", file, parse_class_cbs, parse_class_cbs != NULL ? parse_class_cbs->user_data : NULL);
  fflush(stdout);

  if( file == NULL ||  parse_class_cbs == NULL ) return OCTV_ERROR_NULL;

  while( 1 ) {
    OctvPayload payload;
    //char * chars;

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
      //chars = payload.delimiter.chars;
      if( octv_check_end_chars(&payload.delimiter) && octv_check_signature(&payload.delimiter) ) {
        //if( chars[0] == 'n' && chars[1] == 'd' && chars[2] == ' ' && octv_check_signature(&payload.delimiter) ) {
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
      //chars = payload.delimiter.chars;
      if( octv_check_sentinel_chars(&payload.delimiter) && octv_check_signature(&payload.delimiter) ) {
        //if( chars[0] == 'c' && chars[1] == 't' && chars[2] == 'v' && octv_check_signature(&payload.delimiter) ) {
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
      if( parse_class_cbs != NULL && parse_class_cbs->feature_cb != NULL ) {
        code = parse_class_cbs->feature_cb(&payload.feature, parse_class_cbs->user_data);
      }
      break;
    }

    if( code != 0 ) return code;
  }
}



// TODO: check on state machine transitions
static
int config_flat_cb(OctvConfig * config, void * user_data) {
  OctvFlatFeatureState * flat_feature_state = user_data;
  *flat_feature_state->config = *config;
  return 0;
}
static
int moment_flat_cb(OctvMoment * moment, void * user_data) {
  OctvFlatFeatureState * flat_feature_state = user_data;
  *flat_feature_state->moment = *moment;
  return 0;
}
static
int tick_flat_cb(OctvTick * tick, void * user_data) {
  OctvFlatFeatureState * flat_feature_state = user_data;
  *flat_feature_state->tick = *tick;
  return 0;
}

static
int feature_flat_cb(OctvFeature * feature, void * user_data) {
  OctvFlatFeatureState * flat_feature_state = user_data;
  *flat_feature_state->feature = *feature;

  // build the flat_feature
  OctvFlatFeature flat_feature = {
    // CONFIG
    .octv_version = flat_feature_state->config->octv_version,
    .num_audio_channels = flat_feature_state->config->num_audio_channels,
    .audio_sample_rate = -1,
    /*
    .audio_sample_rate_0 = flat_feature_state->config->audio_sample_rate_0,
    .audio_sample_rate_1 = flat_feature_state->config->audio_sample_rate_1,
    .audio_sample_rate_2 = flat_feature_state->config->audio_sample_rate_2,
    */
    /*
    .num_detectors = flat_feature_state->config->num_detectors,
    .max_level = 63,
    .min_level = -63,
    */
    // MOMENT + TICK
    .audio_frame_index = -1,
    //.audio_frame_index_hi_bytes = flat_feature_state->moment->audio_frame_index_hi_bytes,
    // TICK + FEATURE
    .audio_channel = flat_feature_state->tick->audio_channel,
    .frame_index_offset = (float)flat_feature_state->feature->frame_offset * 1.0f,  // config-based recip
    //.audio_frame_index_lo_bytes = flat_feature_state->tick->audio_frame_index_lo_bytes,
    .audio_sample = flat_feature_state->tick->audio_sample,
    // FEATURE
    .detector_type = flat_feature_state->feature->type,
    .detector_index = flat_feature_state->feature->detector_index,
  };

  return flat_feature_state->parse_flat_cbs->flat_feature_cb(&flat_feature, flat_feature_state->parse_flat_cbs->user_data);
}

static
int error_flat_cb(int error_code, OctvPayload * payload, void * user_data) {
  //OctvFlatFeatureState * flat_feature_state = user_data;
  return error_code;
}



// stateful parsing, emit each feature
int octv_parse_flat(FILE * file, const OctvParseFlat * parse_flat_cbs) {
  printf("octv.c:: octv_parse_flat(): file: %p, parse_flat_cbs: %p, user_data: %p\n", file, parse_flat_cbs, parse_flat_cbs != NULL ? parse_flat_cbs->user_data : NULL);
  fflush(stdout);

  if( file == NULL || parse_flat_cbs == NULL ) return OCTV_ERROR_NULL;

  // state for flat feature work
  OctvConfig config;
  OctvMoment moment;
  OctvTick tick;
  OctvFeature feature;
  OctvFlatFeatureState flat_feature_state = {
    .config = &config,
    .moment = &moment,
    .tick = &tick,
    .feature = &feature,
    .parse_flat_cbs = parse_flat_cbs
  };

  // callbacks for low-level class parser
  OctvParseClass parse_class_cbs = {
    .sentinel_cb = NULL,
    .end_cb = NULL,
    .config_cb = config_flat_cb,
    .moment_cb = moment_flat_cb,
    .tick_cb = tick_flat_cb,
    .feature_cb = feature_flat_cb,
    .error_cb = error_flat_cb,
    .user_data = &flat_feature_state
  };


  int code = octv_parse_class(file,  &parse_class_cbs);
  return code;


  OctvFlatFeature flat_feature_c;
  flat_feature_c.detector_type = 'H';
  return parse_flat_cbs->flat_feature_cb(&flat_feature_c, parse_flat_cbs->user_data);

  return 0;
}


int _octv_prevent_warnings() {
  // prevent warnings by doing stuff with what's been declared
  int result = 0;

  result += octv_sentinel.chars[0];
  result += octv_end.chars[0];
  result += octv_config.type + octv_config.octv_version;
  result += octv_moment.type;
  result += octv_tick.type;

  for( int feature_type = OCTV_FEATURE_0_LOWER; feature_type <= OCTV_FEATURE_3_UPPER; ++feature_type ) {
    const OctvFeature feature = { feature_type };
    result += feature.type;
  }
  return result;
}
