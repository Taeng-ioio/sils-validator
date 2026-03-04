import sys
import os
import numpy as np

sys.path.append(os.path.dirname(__file__))

# Import the loader
from core.data_loader import ADTFLoader

def log_image_stats():
    loader = ADTFLoader()
    
    # User's recent DAT file paths
    import glob
    dats = glob.glob("/Volumes/T7/Project/LGE/sils-validator/**/*.dat", recursive=True)
    if not dats:
        print("No dat files found")
        return

    # Find the specific 10MB dat file the user is testing
    target_dat = None
    for dat in dats:
        if "dummy.dat" in dat: continue
        # use the first real dat file
        target_dat = dat
        break

    if not target_dat:
        print("No valid target dat")
        return
        
    print(f"Loading {target_dat}")
    if not loader.load_file(target_dat):
        print("Failed to load dat")
        return
        
    total = loader.get_total_frames()
    print(f"Total frames: {total}")
    if total == 0:
        return
        
    for i in range(min(5, total)):
        frame = loader.get_frame(i)
        if frame is None:
            print(f"Frame {i}: None")
            continue
            
        # frame is RGB (2560, 1984, 3) because of our current data_loader.py
        h, w, c = frame.shape
        print(f"Frame {i}: Shape {frame.shape}, Dtype {frame.dtype}")
        
        # calculate max, min, mean
        f_max = np.max(frame)
        f_min = np.min(frame)
        f_mean = np.mean(frame)
        print(f"  -> Min: {f_min}, Max: {f_max}, Mean: {f_mean:.2f}")

        # Check if literally black
        if f_max == 0:
            print("  -> WARNING: FRAME IS 100% PITCH BLACK (ALL ZEROS).")
        
        # Check standard deviation to see if it's solid color
        print(f"  -> Std Dev: {np.std(frame):.2f}")
        
if __name__ == "__main__":
    log_image_stats()
