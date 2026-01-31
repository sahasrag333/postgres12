import time
import json
import os
from datetime import datetime

import pandas as pd
from capital_group.celery.celery_app import celery_app
from capital_group.Utils.ce_logger import get_logger
from capital_group.Utils.selenium_web_extraction import download_file_from_url

# module-level logger
logger = get_logger(__name__)


# -----------------------------
# Helper: normalize JSON values
# -----------------------------
def normalize_value(value):
    """
    Convert Pandas Timestamp / datetime to string for JSONB safety.
    """
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


# -----------------------------
# Scraping Task
# -----------------------------
@celery_app.task(bind=True, name="tasks.scraping_task")
def scraping_task(self, source_url: str, dest_path: str = None, chromedriver_path: str = None):
    logger.info(f"Starting scraping task for: {source_url}")

    try:
        self.update_state(state="PROGRESS", meta={"current": 10, "total": 100})

        if dest_path:
            downloaded = download_file_from_url(
                source_url,
                download_dir=dest_path,
                chromedriver_path=chromedriver_path,
            )

            self.update_state(state="PROGRESS", meta={"current": 80, "total": 100})

            try:
                extraction_job = extraction_task.delay(downloaded)
                logger.info(f"Queued extraction task {extraction_job.id}")
                extraction_id = extraction_job.id
            except Exception as e:
                logger.error(f"Failed to queue extraction task: {e}")
                extraction_id = None

            return {
                "status": "downloaded",
                "url": source_url,
                "path": downloaded,
                "extraction_task_id": extraction_id,
            }

        time.sleep(2)
        return {"status": "success", "url": source_url}

    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


# -----------------------------
# Extraction Task
# -----------------------------
@celery_app.task(name="tasks.extraction_task")
def extraction_task(file_path: str):
    logger.info(f"Starting extraction for file: {file_path}")

    try:
        from capital_group.Services.Validation.data_validation import validator
        from capital_group.Utils.db_utils import dataframe_to_postgres

        if not file_path or not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return {"status": "failed", "reason": "file_missing"}

        try:
            sheets = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")
        except Exception as e:
            logger.error(f"Failed to read Excel file: {e}")
            return {"status": "failed", "reason": "read_error"}

        total_rows = 0
        total_written = 0
        invalid_rows = 0

        for sheet_name, df in sheets.items():
            logger.info(f"Processing sheet1: {sheet_name}")

            df = df.dropna(how="all")
            total_rows += len(df)

            # Normalize column names
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

            records = df.to_dict(orient="records")
            valid, invalid = validator.process_batch(records)
            invalid_rows += len(invalid)
            print(records)
            print(valid)
            print(invalid)
            if not valid:
                continue

            rows_to_insert = []

            for rec in valid:
                clean_payload = {
                    k: normalize_value(v) for k, v in rec.items()
                }

                rows_to_insert.append({
                    "reference_id": str(clean_payload.get("Customer_ID")),
                    "data_payload": json.dumps(clean_payload),
                    "is_validated": True,
                    "validation_errors": None,
                })

            valid_df = pd.DataFrame(rows_to_insert)

            table_name = os.getenv("EXTRACTION_TARGET_TABLE", "processed_records")

            try:
                written = dataframe_to_postgres(
                    valid_df,
                    table_name,
                    chunksize=50  # SAFE for JSONB
                )
                total_written += written
            except Exception as e:
                logger.error(f"DB insert failed for sheet {sheet_name}: {e}")

        logger.info(
            f"Extraction complete. Rows read={total_rows}, "
            f"written={total_written}, invalid={invalid_rows}"
        )

        return {
            "status": "extracted",
            "path": file_path,
            "rows": total_rows,
            "written": total_written,
            "invalid": invalid_rows,
        }

    except Exception as e:
        logger.error(f"Unexpected extraction error: {e}")
        raise


# -----------------------------
# Validation Task (placeholder)
# -----------------------------
@celery_app.task(name="tasks.validation_task")
def validation_task(data):
    logger.info("Starting data validation...")
    return {"status": "validated", "valid": True}