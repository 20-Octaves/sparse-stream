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

// FEATURE are values less than 0x40 except 0x00
// This allows library clients work with up to 63 distinct FEATURE values without recompiling
// low-level parsing and dispatch code

// FEATURE type are zero in the top-two bits, 6 bits for type, but not using 0x00, so 63 types
#define OCTV_FEATURE_MASK  0x3f
#define OCTV_NON_FEATURE_MASK  0xc0

// These are half-open ranges (UPPER is not in the range)
// 31 use level_0* anonymous struct fields (4 1-byte feature values)
#define OCTV_FEATURE_0_LOWER  0x01
#define OCTV_FEATURE_0_UPPER  0x20
// 16 use level_2* anonymous struct fields (2 1-byte and 1 2-byte feature values)
#define OCTV_FEATURE_2_LOWER  0x20
#define OCTV_FEATURE_2_UPPER  0x30
// 16 use level_3* anonymous struct fields (2 2-bytefeature values)
#define OCTV_FEATURE_3_LOWER  0x30
#define OCTV_FEATURE_3_UPPER  0x40

// Parser error semantics:
// pointer argument is null
#define OCTV_ERROR_NULL  0x01
// payload.type is not handled
#define OCTV_ERROR_TYPE  0x02
// value inconsistent with type
#define OCTV_ERROR_VALUE  0x03
// incomplete read (eof or error...)
#define OCTV_ERROR_EOF  0x04
// incomplete read (eof or error...)
#define OCTV_ERROR_FREAD  0x05
// error from client callback
#define OCTV_ERROR_CLIENT  0x06


// SENTINEL and END
typedef struct {
  //uint8_t type;
  char chars[4];
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

// FEATURE terminal has multiple "values" based on the value in type which has top two bits 0 and
// at least one non-zero bit in low 6 bits
typedef struct {
  uint8_t type;

  int8_t frame_offset;
  uint16_t detector_index;

  // Support for type-specific data classes
  // Half-open rnages, the OCTV_FEATURE_*_UPPER is not in the range
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

// info about fread failure
typedef struct {
  uint8_t type;
  uint8_t feof;
  uint8_t ferror;

  uint8_t _reserved[5];
} OctvError;


// OctvPayload holds any terminal, and it the terminal's type field in an anonymous struct, and also the bytes[8] array
typedef union {
  struct {
    uint8_t type;
    uint8_t _reserved[7];
  };
  struct {
    uint8_t bytes[8];
  };

  OctvDelimiter delimiter;
  OctvConfig config;
  OctvMoment moment;
  OctvTick tick;
  OctvFeature feature;

  OctvError error;
} OctvPayload;


typedef struct {
  // CONFIG
  uint8_t octv_version;
  uint8_t num_audio_channels;
  int audio_sample_rate;

  // MOMENT + TICK
  int audio_frame_index;

  // TICK + FEATURE
  uint8_t audio_channel;
  float frame_index_offset;
  float audio_sample;

  // FEATURE
  uint16_t detector_index;

  uint8_t detector_type;

  // half-open ranges of the values of detector_type for which set of the level_* fields are valid

  // detector_type: range(OCTV_FEATURE_0_LOWER, OCTV_FEATURE_0_UPPER)
  int8_t level_0_int8_0;
  int8_t level_0_int8_1;
  int8_t level_0_int8_2;
  int8_t level_0_int8_3;

  // detector_type: range(OCTV_FEATURE_2_LOWER, OCTV_FEATURE_2_UPPER)
  int8_t level_2_int8_0;
  int8_t level_2_int8_1;
  int16_t level_2_int16_0;

  // detector_type: range(OCTV_FEATURE_3_LOWER, OCTV_FEATURE_3_UPPER)
  int16_t level_3_int16_0;
  int16_t level_3_int16_1;

} OctvFlatFeature;



typedef int (*octv_error_cb_t)(int error_code, OctvPayload * payload, void * user_data);
typedef int (*octv_flat_feature_cb_t)(OctvFlatFeature * flat_feature, void * user_data);


// parsing that emits each terminal
typedef struct {
  int (*sentinel_cb)(OctvDelimiter * sentinel, void * user_data);
  int (*end_cb)(OctvDelimiter * end, void * user_data);
  int (*config_cb)(OctvConfig * config, void * user_data);
  int (*moment_cb)(OctvMoment * moment, void * user_data);
  int (*tick_cb)(OctvTick * tick, void * user_data);
  int (*feature_cb)(OctvFeature * feature, void * user_data);

  octv_error_cb_t error_cb;

  void * user_data;
} OctvParseClass;

// parsing that emits features with fields derived from all tiers
typedef struct {
  octv_flat_feature_cb_t flat_feature_cb;
  octv_error_cb_t error_cb;
  void * user_data;
} OctvParseFlat;

// TODO: add support for Sparse Stream state machine checks
typedef struct {
  OctvConfig * config;
  OctvMoment * moment;
  OctvTick * tick;
  OctvFeature * feature;

  // Note: const may affect the struct's field ordering
  const OctvParseFlat * parse_flat_cbs;
} OctvFlatFeatureState;


int octv_parse_class(FILE * file, const OctvParseClass * parse_class_cbs);
int octv_parse_flat(FILE * file, const OctvParseFlat * parse_flat_cbs);

int _octv_prevent_warnings();
