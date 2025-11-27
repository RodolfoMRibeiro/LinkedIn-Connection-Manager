"""
Parameters configuration for LinkedIn Scraper.
Reads from environment variables (for Docker) or uses defaults.
"""
import os


def get_env(key: str, default: str = '') -> str:
    """Get environment variable or return default."""
    return os.environ.get(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.environ.get(key, '').lower()
    if value in ('true', '1', 'yes'):
        return True
    if value in ('false', '0', 'no'):
        return False
    return default


# LinkedIn credentials - REQUIRED
linkedin_username = get_env('LINKEDIN_USERNAME', '')
linkedin_password = get_env('LINKEDIN_PASSWORD', '')

# Search settings
file_name = get_env('FILE_NAME', 'csv')
keywords = get_env('KEYWORDS', '')
ignore_list = get_env('IGNORE_LIST', '')
till_page = get_env('TILL_PAGE', '2')

# Profile scraping
profile_urls = [url.strip() for url in get_env('PROFILE_URLS', '').split(',') if url.strip()]
output_json_path = get_env('OUTPUT_JSON_PATH', 'profiles.json')

# Chrome/Chromium/Selenium settings
chrome_binary_path = get_env('CHROME_BIN', '/usr/bin/chromium')
chromedriver_path = get_env('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
headless = get_env_bool('HEADLESS', True)  # Default True for Docker
prefer_selenium_manager = get_env_bool('PREFER_SELENIUM_MANAGER', False)  # Use system chromedriver

# Validate required settings
if not linkedin_username or not linkedin_password:
    print("WARNING: LinkedIn credentials not set!")
    print("Set LINKEDIN_USERNAME and LINKEDIN_PASSWORD environment variables.")

