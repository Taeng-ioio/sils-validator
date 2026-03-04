import sys
import os
import adtf_file
from glob import glob

try:
    folder = "/Volumes/T7/Project/LGE/sils-validator"
    dat_files = glob(os.path.join(folder, "**", "*.dat"), recursive=True)
    if not dat_files:
        print("No dat files found.")
        sys.exit()
    dat_file = dat_files[0]
    print(f"Reading {dat_file}...")
    reader = adtf_file.create_seekablereader(dat_file)
    print("Streams:")
    for s in reader.streams:
        print(f" - {s.name} (id: {s.stream_id}), item_count: {getattr(s, 'item_count', 'N/A')}")
        
    # See if we can manually count items
    print("Manual counting via get_next_item():")
    for s in reader.streams:
        if s.name in ['Image0', 'DTSImage0']:
            count = 0
            try:
                reader.seek_to(0)
                while True:
                    item = reader.get_next_item()
                    if not item:
                        break
                    if item.stream_id == s.stream_id:
                        count += 1
                        if count == 1:
                            print(f" First frame len: {len(item.sample.buffer)}")
            except Exception as e:
                print(f" Stopped due to error: {e}")
            print(f" Manually counted frames for {s.name}: {count}")
            
except Exception as e:
    import traceback
    traceback.print_exc()
