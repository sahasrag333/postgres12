from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from capital_group.Utils.ce_logger import get_logger
from contextlib import contextmanager
from capital_group.configs import config
from sqlalchemy import create_engine
import pandas as pd
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text,text, Boolean
import json
# module-level logger
logger = get_logger(__name__)

# Initialize SQLAlchemy without an app context yet
# It will be bound to the app in factory.py via db.init_app(app)
db = SQLAlchemy()

class DBManager:
    """
    Utility class for database operations.
    Provides context managers for safe session handling.
    """

    @staticmethod
    @contextmanager
    def session_scope():
        """
        Provide a transactional scope around a series of operations.
        Ensures the session is committed if successful, or rolled back on error.
        """
        session = db.session
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Database Transaction Error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def bulk_insert(model_class, data_list):
        """
        Optimized bulk insertion for high-performance data loading.
        """
        if not data_list:
            return

        try:
            db.session.bulk_insert_mappings(model_class, data_list)
            db.session.commit()
            logger.info(f"Successfully bulk inserted {len(data_list)} records into {model_class.__tablename__}.")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Bulk Insert Failed: {str(e)}")
            raise

# Singleton-like access
db_manager = DBManager()


def dataframe_to_postgres(df: pd.DataFrame, table_name: str, if_exists: str = 'append', chunksize: int = 300):
    """
    Insert a pandas DataFrame into a Postgres table using SQLAlchemy engine.

    - df: pandas DataFrame to insert
    - table_name: target table name in the database
    - if_exists: passed to pandas.DataFrame.to_sql (append/replace/fail)
    - chunksize: number of rows per chunk to write
    """
    if df is None or df.empty:
        logger.info("No data to write to Postgres (empty DataFrame).")
        return 0
    total_written = 0
    # Build engine from central config so Celery tasks can use it without Flask app context
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
        # Ensure basic types are handled; let pandas infer dtypes
        
        with engine.begin() as conn:
            for start in range(0, len(df), chunksize):
                chunk = df.iloc[start:start + chunksize]

                chunk.to_sql(
                    name=table_name,
                    con=conn,
                    if_exists=if_exists,
                    index=False,
                    dtype={
                            "reference_id": Text(),
                            "data_payload": JSONB(),          
                            "is_validated": Boolean(),
                            "validation_errors": JSONB()
                        }
                )

                total_written += len(chunk)

        logger.info(f"Wrote {total_written} rows to {table_name} (Postgres)")
        return total_written

    except Exception as e:
        logger.error(f"Failed to write DataFrame to Postgres table {table_name}: {e}")
        raise

def fetch_all_payloads(table_name: str):
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

    query = text(f"""
        SELECT data_payload
        FROM {table_name}
        WHERE data_payload IS NOT NULL
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    # Convert JSONB → dict
    return [dict(r.data_payload) for r in rows]