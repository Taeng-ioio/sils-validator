import sys
import os
import numpy as np
import cv2
os.environ["QT_QPA_PLATFORM"] = "offscreen" # prevent qt conflicts if imported

sys.path.append("/Volumes/T7/Project/LGE/sils-validator")
from core.data_loader import ADTFLoader

loader = ADTFLoader()
dat_path = "/Volumes/T7/Project/LGE/sils-validator/dummy.dat" # we need real dat
