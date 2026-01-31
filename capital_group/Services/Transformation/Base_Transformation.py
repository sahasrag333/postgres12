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
    Aggregation-focused transformer for Postgres JSONB data.
    """

    def clean(self):
        df = pd.DataFrame(self.raw_data)

        # Normalize column names
        df.columns = [c.lower().strip() for c in df.columns]

        # Type casting
        df["purchase_amount"] = df["purchase_amount"].astype(float)
        df["purchase_date"] = pd.to_datetime(df["purchase_date"])

        self.transformed_data = df

    def format_schema(self):
        df = self.transformed_data

        # Example transformation: total purchase per city
        grouped = (
            df.groupby("source", as_index=False)
              .agg(
                  total_purchase_amount=("purchase_amount", "sum"),
                  avg_purchase_amount=("purchase_amount", "mean"),
                  total_customers=("id", "count")
              )
        )

        return grouped
