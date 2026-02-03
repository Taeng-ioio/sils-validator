import pandas as pd

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
