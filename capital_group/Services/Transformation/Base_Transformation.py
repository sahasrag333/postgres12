import pandas as pd
from abc import ABC, abstractmethod
from capital_group.Utils.ce_logger import get_logger

# module-level logger
logger = get_logger(__name__)

class BaseTransformer(ABC):
    """
    Abstract Base Class for Data Transformation.
    Standardizes how raw data is cleaned and formatted.
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.transformed_data = None

    @abstractmethod
    def clean(self):
        """Method to handle nulls, whitespace, and duplicates."""
        pass

    @abstractmethod
    def format_schema(self):
        """Method to map raw fields to the final database schema."""
        pass

    def execute(self):
        """
        Orchestrates the transformation steps.
        """
        try:
            logger.info("Starting data transformation...")
            if not self.raw_data:
                logger.warning("No data provided for transformation.")
                return []
            
            self.clean()
            result = self.format_schema()
            
            logger.info(f"Transformation complete. {len(result)} records processed.")
            return result
        except Exception as e:
            logger.error(f"Transformation failed: {str(e)}")
            raise

class StandardTransformer(BaseTransformer):
    """
    A concrete implementation for general data cleaning.
    """

    def clean(self):
        """
        Uses Pandas for high-performance cleaning.
        """
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(self.raw_data)

        # 1. Remove complete duplicates
        df.drop_duplicates(inplace=True)

        # 2. Standardize string columns (strip whitespace)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        # 3. Fill NaN with empty strings or standard nulls
        df = df.where(pd.notnull(df), None)

        self.transformed_data = df

    def format_schema(self):
        """
        Maps internal data to the JSONB structure expected by 'processed_records'.
        """
        records = self.transformed_data.to_dict(orient='records')
        
        final_output = []
        for item in records:
            # We wrap the data in a structure compatible with our SQL schema
            final_output.append({
                "reference_id": str(item.get('id', 'N/A')),
                "data_payload": item,  # This goes into the JSONB column
                "is_validated": False  # To be updated by the Validation Service
            })
        
        return final_output