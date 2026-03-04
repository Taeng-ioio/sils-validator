import sys
import os
import adtf_file
import numpy as np
from glob import glob

try:
    folder = "/Volumes/T7/Project/LGE/sils-validator"
    dat_files = glob(os.path.join(folder, "**", "*.dat"), recursive=True)
    if not dat_files:
        sys.exit(0)
    dat_file = dat_files[0]
    
    reader = adtf_file.create_seekablereader(dat_file)
    stream_id = None
    for s in reader.streams:
        if s.name in ['Image0']:
            stream_id = s.stream_id
            break
            
    if stream_id is not None:
        reader.seek_to(0)
        item = reader.get_next_item()
        buf = item.sample.buffer
        if len(buf) == 10158080:
            arr = np.frombuffer(buf, dtype=np.uint16)
            print("16-bit stats:")
            print("min:", arr.min(), "max:", arr.max(), "mean:", arr.mean())
            arr_masked = arr & 0x03FF
            print("10-bit LSB masked stats:")
            print("min:", arr_masked.min(), "max:", arr_masked.max(), "mean:", arr_masked.mean())
            arr_msb = arr >> 6
            print("10-bit MSB shifted stats:")
            print("min:", arr_msb.min(), "max:", arr_msb.max(), "mean:", arr_msb.mean())
except Exception as e:
    pass
