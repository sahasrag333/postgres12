import re
from capital_group.Utils.ce_logger import get_logger

# module-level logger
logger = get_logger(__name__)

class DataValidator:
    """
    Service to validate extracted data against business rules.
    """

    @staticmethod
    def is_valid_url(url):
        """Simple regex check for URL format."""
        regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
            r'localhost|' # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return re.match(regex, url) is not None

    def validate_record(self, record):
        """
        Validates an individual record.
        Returns (is_valid, error_list)
        """
        errors = []
        
        # Rule 1: Check for required fields (Example: 'id' and 'source')
        required_fields = ['id', 'source']
        for field in required_fields:
            if field not in record or not record[field]:
                errors.append(f"Missing required field: {field}")

        # Rule 2: Validate Data Types (Example: 'price' should be numeric)
        if 'price' in record:
            try:
                float(record['price'])
            except (ValueError, TypeError):
                errors.append("Field 'price' must be a numeric value")

        # Rule 3: Business Logic (Example: check URL validity)
        if 'url' in record and not self.is_valid_url(record['url']):
            errors.append("Invalid URL format")

        is_valid = len(errors) == 0
        return is_valid, errors

    def process_batch(self, data_list):
        """
        Validates a list of records and separates valid from invalid.
        """
        valid_records = []
        invalid_records = []

        logger.info(f"Starting validation for {len(data_list)} records.")

        for item in data_list:
            is_valid, errors = self.validate_record(item)
            if is_valid:
                valid_records.append(item)
            else:
                item['validation_errors'] = errors
                invalid_records.append(item)

        logger.info(f"Validation complete: {len(valid_records)} passed, {len(invalid_records)} failed.")
        return valid_records, invalid_records

# Singleton instance
validator = DataValidator()