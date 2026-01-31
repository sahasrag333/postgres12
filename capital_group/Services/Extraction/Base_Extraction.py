import pandas as pd
import os
from abc import ABC, abstractmethod
from capital_group.Utils.ce_logger import get_logger

# module-level logger
logger = get_logger(__name__)
from capital_group.Utils.S3_utilities import s3_client  # We will build this next

class BaseExtractor(ABC):
    """
    Abstract Base Class for all Extraction Services.
    Ensures a consistent interface for different data sources.
    """

    def __init__(self, source_path):
        self.source_path = source_path
        self.raw_data = None
        self.processed_data = None

    @abstractmethod
    def load_source(self):
        """Method to load data from S3 or local path."""
        pass

    @abstractmethod
    def extract_logic(self):
        """Main logic to parse the raw data."""
        pass

    def run(self):
        """
        Orchestration method to execute the extraction pipeline.
        """
        try:
            logger.info(f"Starting extraction pipeline for: {self.source_path}")
            self.load_source()
            result = self.extract_logic()
            logger.info("Extraction completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Error in extraction pipeline: {str(e)}")
            raise e

class CSVExtractor(BaseExtractor):
    """
    Example implementation for CSV Extraction.
    """

    def load_source(self):
        # Logic to handle local vs S3 pathing
        if self.source_path.startswith("s3://"):
            logger.info("Downloading file from S3...")
            # s3_client logic will go here
            pass
        else:
            if not os.path.exists(self.source_path):
                raise FileNotFoundError(f"File not found: {self.source_path}")
            self.raw_data = pd.read_csv(self.source_path)

    def extract_logic(self):
        """
        Cleans and parses the CSV data.
        """
        if self.raw_data is not None:
            # Example logic: Remove empty rows and trim whitespace
            df = self.raw_data.dropna(how='all')
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            self.processed_data = df.to_dict(orient='records')
            return self.processed_data
        return None