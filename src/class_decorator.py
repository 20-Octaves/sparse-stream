
# add getter properties for each of struct_fields, proxy-ing through self.self_c
def octv_terminal(cls):
    for attr_name in cls.struct_fields:
        #print(f'yow: {attr_name}')
        def get_attr(self, attr_name=attr_name):
            return getattr(self.self_c, attr_name)
        setattr(cls, attr_name, property(get_attr))
    return cls

class foon(object):
    pass

@octv_terminal
class OctvFlatFeature(object):
    struct_fields = 'octv_version', 'num_audio_channels', 'audio_sample_rate_0', 'audio_sample_rate_1', 'audio_sample_rate_2', 'num_detectors', 'audio_frame_index_hi_bytes', 'audio_channel', 'audio_frame_index_lo_bytes', 'audio_sample', 'type', 'frame_offset', 'detector_index',

    def __init__(self):
        self.self_c = foon()
        self.self_c.octv_version = 23
        self.self_c.num_audio_channels = 4

f = OctvFlatFeature()
print(f'f.octv_version: {f.octv_version}')
print(f'f.num_audio_channels: {f.num_audio_channels}')

def addAttrs(attr_names):
  def deco(cls):
    for attr_name in attr_names:
      def getAttr(self, attr_name=attr_name):
        return getattr(self, "_" + attr_name)
      def setAttr(self, value, attr_name=attr_name):
        setattr(self, "_" + attr_name, value)
      prop = property(getAttr, setAttr)
      setattr(cls, attr_name, prop)
      setattr(cls, "_" + attr_name, None) # Default value for that attribute
    return cls
  return deco

@addAttrs(['x', 'y'])
class MyClass(object):
  pass
