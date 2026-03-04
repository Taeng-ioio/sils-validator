from core.data_loader import ADTFLoader
import sys

if len(sys.argv) < 2:
    print("Provide dat path")
    sys.exit(1)

path = sys.argv[1]
loader = ADTFLoader()
res = loader.load_file(path)
print("load_file:", res)
print("total_frames:", loader.get_total_frames())
print("frame(0):", loader.get_frame(0) is not None)
