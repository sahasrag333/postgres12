import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError
from capital_group.configs import config
from capital_group.Utils.ce_logger import get_logger

# module-level logger
logger = get_logger(__name__)

class S3Client:
    """
    Utility class for interacting with AWS S3.
    Uses singleton-like pattern for the boto3 client to reuse connections.
    """

    def __init__(self):
        self.bucket_name = config.S3_BUCKET_NAME
        try:
            self.s3 = boto3.client(
                's3',
                aws_access_key_id=config.AWS_ACCESS_KEY,
                aws_secret_access_key=config.AWS_SECRET_KEY,
                region_name=config.S3_REGION
            )
            logger.info("S3 Client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize S3 Client: {e}")
            self.s3 = None

    def upload_file(self, local_path, s3_key):
        """
        Uploads a local file to the configured S3 bucket.
        """
        if not self.s3:
            logger.error("S3 client not available.")
            return False

        try:
            self.s3.upload_file(local_path, self.bucket_name, s3_key)
            logger.info(f"Successfully uploaded {local_path} to s3://{self.bucket_name}/{s3_key}")
            return True
        except FileNotFoundError:
            logger.error(f"The file {local_path} was not found.")
        except NoCredentialsError:
            logger.error("AWS credentials not provided.")
        except ClientError as e:
            logger.error(f"S3 Upload error: {e}")
        return False

    def download_file(self, s3_key, local_path):
        """
        Downloads a file from S3 to a local destination.
        """
        if not self.s3:
            return False

        try:
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading from S3: {e}")
            return False

    def get_signed_url(self, s3_key, expires_in=3600):
        """
        Generates a temporary URL for viewing/downloading a private S3 object.
        Useful for providing links in the API.
        """
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

# Global instance for app-wide use
s3_utility = S3Client()