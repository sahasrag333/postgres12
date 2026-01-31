from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from capital_group.configs import config
from capital_group.Utils.ce_logger import get_logger

import os
import time
import requests
import pandas as pd
import datetime
from typing import Optional

logger = get_logger(__name__)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from capital_group.configs import config
from capital_group.Utils.ce_logger import get_logger

import os
import time
from typing import Optional

logger = get_logger(__name__)

def _wait_for_new_download(download_dir: str, timeout: int = 60) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            files = os.listdir(download_dir)
            for fname in files:
                # Look for completed xlsx files and ignore temp/crdownload files
                if fname.lower().endswith('.xlsx') and not (fname.endswith('.crdownload') or fname.endswith('.tmp')):
                    full_path = os.path.join(download_dir, fname)
                    if os.path.getsize(full_path) > 0:
                        return full_path
        except Exception:
            pass
        time.sleep(2)
    return None

def download_file_from_url(url: str, download_dir: Optional[str] = None, wait_timeout: int = 60, chromedriver_path: Optional[str] = None) -> Optional[str]:
    if not download_dir:
        download_dir = os.path.join(str(config.BASE_DIR), "downloads")
    
    # Ensure absolute path for Chrome preferences
    download_dir = os.path.abspath(download_dir)
    os.makedirs(download_dir, exist_ok=True)

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    
    # Bypasses security bubbles/warnings for local downloads
    options.add_argument("--disable-features=InsecureDownloadWarnings,DownloadBubble,DownloadBubbleV2")
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False, 
        "profile.default_content_settings.popups": 0,
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(chromedriver_path) if chromedriver_path else Service()
    driver = None
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        # Explicitly allow downloads via Chrome DevTools Protocol
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow", 
            "downloadPath": download_dir
        })
        
        logger.info(f"Accessing direct download URL: {url}")
        # Direct URL to .xlsx triggers download automatically
        driver.get(url)

        # Wait for file to appear in the folder
        return _wait_for_new_download(download_dir, timeout=wait_timeout)

    except Exception as e:
        logger.error(f"ChromeDriver failure: {e}")
        return None
    finally:
        if driver:
            # Short buffer to allow file system to finalize the file
            time.sleep(2)
            driver.quit()


def _download_via_requests(url: str, download_dir: str, timeout: int = 30) -> Optional[str]:
    """Download a file via HTTP (requests) into download_dir and return the full path.

    This is a fast, reliable path for direct static files (for example http://localhost:8000/file.xlsx).
    """
    try:
        local_name = url.split('/')[-1] or 'download.xlsx'
        out_path = os.path.join(download_dir, local_name)
        with requests.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            with open(out_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return out_path
    except Exception as e:
        logger.error(f"HTTP download failed for {url}: {e}")
        return None


def download_and_modify_excel(url: str, download_dir: Optional[str] = None, wait_timeout: int = 60,
                              chromedriver_path: Optional[str] = None) -> Optional[str]:
    """Download an Excel file from `url`, add a 'Processed' column with a UTC timestamp to every sheet,
    and save a new file named `modified_<original>` in the same download directory.

    - If the URL points directly to an .xlsx file this function will use requests (faster and reliable).
    - Returns the full path to the modified file or None on failure.
    """
    if not download_dir:
        download_dir = os.path.join(str(config.BASE_DIR), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Prefer direct HTTP download for static .xlsx files (common for local dev servers on port 8000)
    downloaded = None
    try:
        if url.lower().endswith('.xlsx'):
            downloaded = _download_via_requests(url, download_dir, timeout=wait_timeout)
        else:
            # Fallback: try a HEAD to inspect content-type
            try:
                head = requests.head(url, timeout=10)
                ctype = head.headers.get('content-type', '')
                if 'spreadsheet' in ctype or 'excel' in ctype or 'vnd.openxmlformats-officedocument' in ctype:
                    downloaded = _download_via_requests(url, download_dir, timeout=wait_timeout)
            except Exception:
                downloaded = None

        # If direct download didn't work, fall back to Selenium-based download
        if not downloaded:
            logger.info("Direct HTTP download path failed or not applicable; falling back to Selenium.")
            downloaded = download_file_from_url(url, download_dir=download_dir, wait_timeout=wait_timeout,
                                                chromedriver_path=chromedriver_path)

        if not downloaded:
            logger.error("Unable to download the file using either HTTP or Selenium.")
            return None

        # Modify the Excel file: add a 'Processed' column with current UTC timestamp to every sheet
        try:
            sheets = pd.read_excel(downloaded, sheet_name=None, engine='openpyxl')
        except Exception as e:
            logger.error(f"Failed to read downloaded Excel file {downloaded}: {e}")
            return None

        ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
        for name, df in sheets.items():
            # Ensure we operate on a DataFrame
            try:
                df['Processed'] = ts
                sheets[name] = df
            except Exception:
                # If sheet is empty or cannot be modified, create a minimal frame
                sheets[name] = pd.DataFrame({'Processed': [ts]})

        out_name = f"modified_{os.path.basename(downloaded)}"
        out_path = os.path.join(os.path.dirname(downloaded), out_name)
        try:
            with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
                for sheet, df in sheets.items():
                    # pandas will create sheets; avoid overly long sheet names
                    safe_name = (sheet[:30] if isinstance(sheet, str) else 'Sheet')
                    df.to_excel(writer, sheet_name=safe_name, index=False)
            logger.info(f"Modified file written to: {out_path}")
            return out_path
        except Exception as e:
            logger.error(f"Failed to write modified Excel file {out_path}: {e}")
            return None

    except Exception as e:
        logger.error(f"Unexpected error in download_and_modify_excel: {e}")
        return None