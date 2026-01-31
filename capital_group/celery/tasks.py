import time
import json
import os
from datetime import datetime

import pandas as pd
from celery import chain

from capital_group.celery.celery_app import celery_app
from capital_group.Utils.ce_logger import get_logger
from capital_group.Utils.selenium_web_extraction import download_file_from_url

# module-level logger
logger = get_logger(__name__)


# -----------------------------
# Helper: normalize JSON values
# -----------------------------
def normalize_value(value):
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

        downloaded = download_file_from_url(
            source_url,
            download_dir=dest_path,
            chromedriver_path=chromedriver_path,
        )

        self.update_state(state="PROGRESS", meta={"current": 80, "total": 100})

        # ✅ FULL PIPELINE CHAIN
        job = chain(
            extraction_task.s(downloaded),
            transformation_to_csv_task.s(),
            upload_csv_to_s3_task.s()
        ).apply_async()

        logger.info(f"Queued full ETL → S3 pipeline {job.id}")

        return {
            "status": "pipeline_started",
            "url": source_url,
            "path": downloaded,
            "pipeline_task_id": job.id,
        }

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


# -----------------------------
# Extraction Task
# -----------------------------
@celery_app.task(name="tasks.extraction_task")
def extraction_task(file_path: str):
    logger.info(f"Starting extraction for file: {file_path}")

    from capital_group.Services.Validation.data_validation import validator
    from capital_group.Utils.db_utils import dataframe_to_postgres

    sheets = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")

    total_rows = total_written = invalid_rows = 0

    for sheet_name, df in sheets.items():
        df = df.dropna(how="all")
        total_rows += len(df)

        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        records = df.to_dict(orient="records")
        valid, invalid = validator.process_batch(records)
        invalid_rows += len(invalid)

        rows_to_insert = []
        for rec in valid:
            clean_payload = {k: normalize_value(v) for k, v in rec.items()}
            rows_to_insert.append({
                "reference_id": str(clean_payload.get("customer_id")),
                "data_payload": clean_payload,
                "is_validated": True,
                "validation_errors": None,
            })

        if rows_to_insert:
            valid_df = pd.DataFrame(rows_to_insert)
            written = dataframe_to_postgres(
                valid_df,
                os.getenv("EXTRACTION_TARGET_TABLE", "processed_records"),
                chunksize=50
            )
            total_written += written

    return {
        "status": "extracted",
        "rows": total_rows,
        "written": total_written,
        "invalid": invalid_rows
    }


# -----------------------------
# Transformation → CSV Task
# -----------------------------
@celery_app.task(name="tasks.transformation_to_csv_task")
def transformation_to_csv_task(_previous_result=None):
    logger.info("Starting transformation → CSV task")

    from capital_group.Utils.db_utils import fetch_all_payloads
    from capital_group.Services.Transformation.Base_Transformation import StandardTransformer

    table_name = os.getenv("EXTRACTION_TARGET_TABLE", "processed_records")
    raw_data = fetch_all_payloads(table_name)

    transformer = StandardTransformer(raw_data)
    result_df = transformer.execute()

    output_dir = os.path.join(os.getcwd(), "transformed_output")
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(
        output_dir,
        f"purchase_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    result_df.to_csv(csv_path, index=False)

    logger.info(f"CSV generated at {csv_path}")

    # ✅ IMPORTANT: return CSV path for next task
    return {
        "csv_path": csv_path
    }


# -----------------------------
# Upload CSV to S3 Task (NEW)
# -----------------------------
@celery_app.task(name="tasks.upload_csv_to_s3_task")
def upload_csv_to_s3_task(prev_result):
    """
    Upload generated CSV file to S3.
    """
    from capital_group.Utils.S3_utilities import s3_utility

    csv_path = prev_result.get("csv_path")

    if not csv_path or not os.path.exists(csv_path):
        logger.error("CSV file not found for S3 upload")
        return {"status": "failed", "reason": "csv_missing"}

    s3_key = f"transformed_outputs/{os.path.basename(csv_path)}"

    success = s3_utility.upload_file(csv_path, s3_key)

    if not success:
        return {"status": "failed", "s3_key": s3_key}

    logger.info(f"CSV uploaded to S3: {s3_key}")

    return {
        "status": "uploaded",
        "s3_key": s3_key,
        "bucket": s3_utility.bucket_name
    }