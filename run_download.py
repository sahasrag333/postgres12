from capital_group.Utils.selenium_web_extraction import download_file_from_url

path = download_file_from_url(
    'https://www.exceldemy.com/learn-excel/sample-data/',
    download_dir=r'C:\Users\RAVI KUMAR\OneDrive\Desktop\capiq2',
    wait_timeout=60,
    headless=False
)
print("Downloaded:", path)
