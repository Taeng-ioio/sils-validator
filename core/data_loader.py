import pandas as pd
import adtf_file
import numpy as np
from pathlib import Path

class ExcelLoader:
    def __init__(self):
        self.df = None
        self.time_step = 0.033
        self.topics = []

    def load_file(self, file_path):
        """
        Loads the Excel file. 
        Assumes Row 1 (header=0) contains Topic names.
        """
        try:
            # Load with pandas
            if file_path.lower().endswith('.csv'):
                 self.df = pd.read_csv(file_path, header=0)
            else:
                 # Using header=0 to treat the first row as columns (Topic names)
                 self.df = pd.read_excel(file_path, header=0)
            
            # Generate Time Column if not exists (assuming data is contiguous 0.033s steps)
            # Create a new index based time column for internal usage
            num_rows = len(self.df)
            self.df['_internal_time'] = [i * self.time_step for i in range(num_rows)]
            
            # Extract topics (columns)
            # Exclude internal columns if any
            self.topics = [col for col in self.df.columns if col != '_internal_time']
            
            return True
        except Exception as e:
            raise e

    def get_topics(self):
        return self.topics

    def get_data_for_topic(self, topic):
        if self.df is not None and topic in self.df.columns:
            return self.df[topic].values
        return []
    
    def get_time_axis(self):
        if self.df is not None:
            return self.df['_internal_time'].values
        return []

    def get_value_at_time_index(self, topic, index):
        """
        Returns the value of a topic at a specific integer index (frame).
        """
        if self.df is not None and topic in self.df.columns:
            if 0 <= index < len(self.df):
                return self.df.iloc[index][topic]
        return None

class ADTFLoader:
    def __init__(self):
        self.reader = None
        self.image_stream_id = None
        self.current_frame_index = 0
        self.image_shape = (1985, 2560)
        
    def load_file(self, file_path):
        """
        Loads the ADTF .dat file and finds the image stream.
        """
        try:
            dat_name = str(Path(file_path))
            self.reader = adtf_file.create_seekablereader(dat_name)
            
            # Find image stream ID
            self.image_stream_id = None
            for stream in self.reader.streams:
                if stream.name in ['Image0', 'DTSImage0']:
                    self.image_stream_id = stream.stream_id
                    break
            
            if self.image_stream_id is None:
                raise ValueError("이미지 스트림을 찾을 수 없습니다. (Image0 또는 DTSImage0)")
            
            self.current_frame_index = 0
            
            return True
        except Exception as e:
            raise e
    
    def get_frame(self, frame_index):
        """
        Gets the image at the specified frame index.
        Returns: numpy array of the image
        """
        if self.reader is None or self.image_stream_id is None:
            return None
        
        try:
            # Get item index for the frame
            item_idx = self.reader.get_item_index_for_stream_item_index(
                self.image_stream_id, frame_index
            )
            
            # Seek to the item
            self.reader.seek_to(item_idx)
            item = self.reader.get_next_item()
            
            if not item or item.stream_id != self.image_stream_id:
                return None
            
            buffer = item.sample.buffer
            buffer_len = len(buffer)
            
            target_size_8bit = self.image_shape[0] * self.image_shape[1]
            
            # 1. Check exact size match for user's legacy 8-bit shape
            if buffer_len == target_size_8bit:
                img = np.frombuffer(buffer, dtype=np.uint8)
                img = np.reshape(img, self.image_shape)
                return img
                
            # 2. Check 16-bit 1984x2560 case (10,158,080 bytes)
            # This handles the specific DAT file the user is currently struggling with
            if buffer_len == 10158080:
                # Based on the ADTF analysis, this is 10-bit Raw Grayscale (LSB-aligned) data
                # where the maximum value is 1023 (0x03FF) in a 16-bit container.
                img16 = np.frombuffer(buffer, dtype=np.uint16).reshape((1984, 2560))
                
                # Shift right by 2 to convert 10-bit (0-1023) to 8-bit (0-255) safely 
                img8 = (img16 >> 2).astype(np.uint8)
                
                return img8
            else:
                # Log unexpected buffer sizes to diagnose the black screen
                with open("/Volumes/T7/Project/LGE/sils-validator/ui_error.txt", "a") as f:
                    f.write(f"WARNING: Unexpected buffer_len: {buffer_len}. Expected 10158080 or {target_size_8bit}.\n")
            
            # 3. Fallback: try raw reshape with user's original logic as a last resort
            img = np.frombuffer(buffer, dtype=np.uint8)
            img = np.reshape(img, self.image_shape)
            return img
            
        except Exception as e:
            import traceback
            with open("/Volumes/T7/Project/LGE/sils-validator/ui_error.txt", "a") as f:
                f.write(f"ERROR in get_frame: {e}\n{traceback.format_exc()}\n")
            return None
    
    def get_next_frame(self):
        """
        Gets the next frame and increments the index.
        Returns: numpy array of the image, or None if at the end
        """
        if self.current_frame_index < 10000:  # Safety limit
            self.current_frame_index += 1
            return self.get_frame(self.current_frame_index)
        return None
    
    def get_previous_frame(self):
        """
        Gets the previous frame and decrements the index.
        Returns: numpy array of the image, or None if at the beginning
        """
        if self.current_frame_index > 0:
            self.current_frame_index -= 1
            return self.get_frame(self.current_frame_index)
        return None
    
    def get_current_frame_index(self):
        return self.current_frame_index
    
    def get_total_frames(self):
        """Get total number of frames by counting stream items"""
        if self.reader is None or self.image_stream_id is None:
            return 0
        
        try:
            # Count items by iterating through the stream
            count = 0
            for stream in self.reader.streams:
                if stream.stream_id == self.image_stream_id:
                    # Get item count for this stream
                    count = stream.item_count
                    break
            return count
        except Exception as e:
            print(f"Error getting total frames: {e}")
            return 0
    
    def close(self):
        """Closes the ADTF reader"""
        if self.reader:
            self.reader.close()
            self.reader = None
