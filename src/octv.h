/*
 * octv.h
 *
 * Headers for Octv stream objects, implementing the Sparse Stream protocol
 *
 */


#define OCTV_VERSION  1

// Except for FEATURE, Octv expects a small set of hard-wired types for each terminal

// Delimiter type start as 0x4x
// 'O'
#define OCTV_SENTINEL_TYPE  0x4f
// 'E'
#define OCTV_END_TYPE  0x45

// Config type start with 0x50
#define OCTV_CONFIG_TYPE  0x50

// MOMENT type start with 0x60
#define OCTV_MOMENT_TYPE  0x60

// TICK type start with 0x70
#define OCTV_TICK_TYPE  0x70

// FEATURE is everything less than 0x40 except 0x00
// use a range of type, non-zero, with 6-bit mask 0x3f, so 0x21 thru 0x3f
// This allows library clients work with up to 63 distinct FEATURE values without recompiling
// low-level parsing and dispatch code

// FEATURE type are zero in the top-two bits, 6 bits for type, but not using 0x00, so 63 types
#define OCTV_FEATURE_MASK  0x3f
#define OCTV_NOT_FEATURE_MASK  0xc0

// these are half-open ranges (UPPER is not in the range)
// 31 use level_0* anonymous struct fields
#define OCTV_FEATURE_0_LOWER  0x01
#define OCTV_FEATURE_0_UPPER  0x20
// 16 use level_2* anonymous struct fields
#define OCTV_FEATURE_2_LOWER  0x20
#define OCTV_FEATURE_2_UPPER  0x30
// 16 use level_3* anonymous struct fields
#define OCTV_FEATURE_3_LOWER  0x30
#define OCTV_FEATURE_3_UPPER  0x40


// SENTINEL and END
typedef struct {
  char type;
  char chars[3];
  uint8_t signature[4];
} OctvDelimiter;


// CONFIG
typedef struct {
  uint8_t type;
  uint8_t octv_version;

  uint8_t num_audio_channels;
  // 24-bit sample rate in Hz, little endian
  uint8_t audio_sample_rate_0;
  uint8_t audio_sample_rate_1;
  uint8_t audio_sample_rate_2;
  //uint8_t audio_sample_rate[3];

  uint16_t num_detectors;
} OctvConfig;


// MOMENT
typedef struct {
  uint8_t type;
  uint8_t _reserved[3];

  uint32_t audio_frame_index_hi_bytes;
} OctvMoment;


// TICK
typedef struct {
  uint8_t type;

  uint8_t audio_channel;
  uint16_t audio_frame_index_lo_bytes;
  float audio_sample;
} OctvTick;


typedef union {
  struct {
    // type: range(OCTV_FEATURE_0_LOWER, OCTV_FEATURE_0_UPPER)
    int8_t level_0_int8_0;
    int8_t level_0_int8_1;
    int8_t level_0_int8_2;
    int8_t level_0_int8_3;
  };
  struct {
    // type: range(OCTV_FEATURE_2_LOWER, OCTV_FEATURE_2_UPPER)
    int8_t level_2_int8_0;
    int8_t level_2_int8_1;
    int16_t level_2_int16_0;
  };
  struct {
    // type: range(OCTV_FEATURE_3_LOWER, OCTV_FEATURE_3_UPPER)
    int16_t level_3_int16_0;
    int16_t level_3_int16_1;
  };
} OctvFeatureLevels;

// FEATURE terminal has multiple "values" based on the value in type which has top two bits 0 and
// at least one non-zero bit in low 6 bits
typedef struct {
  uint8_t type;

  uint8_t frame_offset;
  uint16_t detector_index;

  // Support for type-specific data classes
  // Cannot use a typedef, as per https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1549.pdf
  // So, this union declaration is repeated in OctvFlatFeature
  union {
    struct {
      // type: range(OCTV_FEATURE_0_LOWER, OCTV_FEATURE_0_UPPER)
      int8_t level_0_int8_0;
      int8_t level_0_int8_1;
      int8_t level_0_int8_2;
      int8_t level_0_int8_3;
    };
    struct {
      // type: range(OCTV_FEATURE_2_LOWER, OCTV_FEATURE_2_UPPER)
      int8_t level_2_int8_0;
      int8_t level_2_int8_1;
      int16_t level_2_int16_0;
    };
    struct {
      // type: range(OCTV_FEATURE_3_LOWER, OCTV_FEATURE_3_UPPER)
      int16_t level_3_int16_0;
      int16_t level_3_int16_1;
    };
  };
  //OctvFeatureLevels levels;
} OctvFeature;


// OctvPayload holds any terminal and has the terminal's type field in the anonymous struct
typedef union {
  struct {
    uint8_t type;
    uint8_t _reserved[7];
  };
  OctvDelimiter delimiter;
  OctvConfig config;
  OctvMoment moment;
  OctvTick tick;
  OctvFeature feature;
} OctvPayload;


typedef struct {
  OctvConfig * config;
  OctvMoment * moment;
  OctvTick * tick;
  OctvFeature * feature;
} OctvFullFeature;

typedef struct {
  // CONFIG
  uint8_t octv_version;
  uint8_t num_audio_channels;
  // 24-bit sample rate in Hz, little endian
  uint8_t audio_sample_rate_0;
  uint8_t audio_sample_rate_1;
  uint8_t audio_sample_rate_2;
  uint16_t num_detectors;

  // MOMENT
  uint32_t audio_frame_index_hi_bytes;

  // TICK
  uint8_t audio_channel;
  uint16_t audio_frame_index_lo_bytes;
  float audio_sample;

  // FEATURE
  // support for type-specific data classes
  uint8_t type;

  uint8_t frame_offset;
  uint16_t detector_index;
  union {
    struct {
      // type: range(OCTV_FEATURE_0_LOWER, OCTV_FEATURE_0_UPPER)
      int8_t level_0_int8_0;
      int8_t level_0_int8_1;
      int8_t level_0_int8_2;
      int8_t level_0_int8_3;
    };
    struct {
      // type: range(OCTV_FEATURE_2_LOWER, OCTV_FEATURE_2_UPPER)
      int8_t level_2_int8_0;
      int8_t level_2_int8_1;
      int16_t level_2_int16_0;
    };
    struct {
      // type: range(OCTV_FEATURE_3_LOWER, OCTV_FEATURE_3_UPPER)
      int16_t level_3_int16_0;
      int16_t level_3_int16_1;
    };
  };
} OctvFlatFeature;

typedef int (*octv_flat_feature_cb_t)(OctvFlatFeature * flat_feature, void * user_data);

typedef struct {
  int (*config_cb)(OctvConfig * config);
  int (*moment_cb)(OctvMoment * moment);
  int (*tick_cb)(OctvTick * tick);
  int (*feature_cb)(OctvFeature * feature);

  int (*error_cb)(int code);
} OctvParseCallbacks;



int octv_parse_flat(FILE * file, octv_flat_feature_cb_t flat_feature_cb, void * user_data);
int octv_parse_full(FILE * file, OctvParseCallbacks * callbacks);

int _octv_prevent_warnings();
