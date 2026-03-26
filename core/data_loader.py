import pandas as pd
import adtf_file
import numpy as np
from pathlib import Path


class ExcelLoader:
    def __init__(self):
        self.df = None
        self.time_step = 1 / 30
        self.topics = []

    def load_file(self, file_path):
        """
        Load an Excel/CSV file.
        Assumes the first row contains topic names.
        """
        if file_path.lower().endswith('.csv'):
            self.df = pd.read_csv(file_path, header=0)
        else:
            self.df = pd.read_excel(file_path, header=0)

        num_rows = len(self.df)
        self.df['_internal_time'] = [round(i * self.time_step, 3) for i in range(num_rows)]
        self.topics = [col for col in self.df.columns if col != '_internal_time']
        return True

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
        """Return the value of a topic at a specific frame index."""
        if self.df is not None and topic in self.df.columns and 0 <= index < len(self.df):
            return self.df.iloc[index][topic]
        return None


class ADTFLoader:
    def __init__(self):
        self.reader = None
        self.image_stream_id = None
        self.current_frame_index = 0
        self.image_shape = (1985, 2560)

    def load_file(self, file_path):
        """Load the ADTF .dat file and find the image stream."""
        dat_name = str(Path(file_path))
        self.reader = adtf_file.create_seekablereader(dat_name)

        self.image_stream_id = None
        for stream in self.reader.streams:
            if stream.name in ['Image0', 'DTSImage0']:
                self.image_stream_id = stream.stream_id
                break

        if self.image_stream_id is None:
            raise ValueError("이미지 스트림을 찾을 수 없습니다. (Image0 또는 DTSImage0)")

        self.current_frame_index = 0
        return True

    def get_frame(self, frame_index):
        """Get the image at the specified frame index."""
        if self.reader is None or self.image_stream_id is None:
            return None

        try:
            item_idx = self.reader.get_item_index_for_stream_item_index(
                self.image_stream_id, frame_index
            )
            self.reader.seek_to(item_idx)
            item = self.reader.get_next_item()

            if not item or item.stream_id != self.image_stream_id:
                return None

            buffer = item.sample.buffer
            img_bytes = np.frombuffer(buffer, dtype=np.uint8)
            buffer_len = img_bytes.size

            target_size_8bit = self.image_shape[0] * self.image_shape[1]
            if buffer_len == target_size_8bit:
                return np.reshape(img_bytes, self.image_shape)

            if buffer_len == 10158080:
                img16 = img_bytes.view(np.uint16).reshape((1984, 2560))
                return (img16 >> 2).astype(np.uint8)

            return np.reshape(img_bytes, self.image_shape)
        except Exception:
            return None

    def get_next_frame(self):
        """Get the next frame and increment the index."""
        if self.current_frame_index < 10000:
            self.current_frame_index += 1
            return self.get_frame(self.current_frame_index)
        return None

    def get_previous_frame(self):
        """Get the previous frame and decrement the index."""
        if self.current_frame_index > 0:
            self.current_frame_index -= 1
            return self.get_frame(self.current_frame_index)
        return None

    def get_current_frame_index(self):
        return self.current_frame_index

    def get_total_frames(self):
        """Get total number of frames by counting stream items."""
        if self.reader is None or self.image_stream_id is None:
            return 0

        try:
            for stream in self.reader.streams:
                if stream.stream_id == self.image_stream_id:
                    return stream.item_count
        except Exception:
            return 0

        return 0

    def close(self):
        """Close the ADTF reader."""
        if self.reader:
            self.reader.close()
            self.reader = None
