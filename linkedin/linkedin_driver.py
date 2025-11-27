import os
import platform

import parameters
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

WAIT_TIME_SHORT = 3
WAIT_TIME_LONG = 5

class LinkedInDriver:
    def __init__(self):
        self.driver = None

    def initialize_driver(self):
        options = self._build_chrome_options()
        print("INFO: Initializing ChromeDriver with options:", options.arguments)

        starters = self._build_startup_strategy()
        last_error = None

        for starter in starters:
            try:
                starter(options)
                self.driver.maximize_window()
                print("INFO: ChromeDriver started successfully.")
                return
            except Exception as exc:
                last_error = exc
                print(f"WARN: {starter.__name__} failed: {exc}")

        raise RuntimeError(
            "Unable to start Google Chrome even after trying Selenium Manager "
            "and webdriver-manager strategies. Original error: "
            f"{last_error}"
        )

    def get_search_results(self, page):
        query_url = self._build_query_url(page)
        self.driver.get(query_url)
        WebDriverWait(self.driver, WAIT_TIME_LONG).until(EC.presence_of_element_located((By.CLASS_NAME, 'reusable-search__result-container')))
        return self.driver.find_elements(By.CLASS_NAME, 'reusable-search__result-container')

    def _build_query_url(self, page):
        return f'https://www.linkedin.com/search/results/people/?keywords={parameters.keywords}&origin=GLOBAL_SEARCH_HEADER&page={page}'

    def close_driver(self):
        self.driver.quit()

    def _build_chrome_options(self):
        options = Options()
        binary_path = self._locate_chrome_binary()

        if binary_path:
            options.binary_location = binary_path
            print(f"INFO: Using Chrome binary at '{binary_path}'.")
        else:
            print("WARN: Chrome binary path not set; relying on system defaults.")

        if getattr(parameters, 'headless', False):
            options.add_argument("--headless=new")
            print("INFO: Headless mode enabled.")
        else:
            print("INFO: Running with visible browser window.")

        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--remote-allow-origins=*")

        return options

    def _build_startup_strategy(self):
        prefer_selenium_manager = getattr(parameters, 'prefer_selenium_manager', False)

        if prefer_selenium_manager:
            print("INFO: Prefering Selenium Manager for ChromeDriver resolution.")
            return (
                self._start_with_selenium_manager,
                self._start_with_webdriver_manager,
            )

        print("INFO: Skipping Selenium Manager (prefer_selenium_manager=False).")
        return (self._start_with_webdriver_manager, self._start_with_selenium_manager)

    def _start_with_selenium_manager(self, options):
        print("INFO: Trying Selenium Manager to resolve the ChromeDriver.")
        self.driver = webdriver.Chrome(options=options)

    def _start_with_webdriver_manager(self, options):
        print("INFO: Trying webdriver-manager to resolve the ChromeDriver.")
        driver_path = ChromeDriverManager().install()
        print(f"INFO: Using ChromeDriver binary at '{driver_path}'.")
        self.driver = webdriver.Chrome(service=Service(driver_path), options=options)

    def _locate_chrome_binary(self):
        explicit_path = getattr(parameters, 'chrome_binary_path', '').strip() if hasattr(parameters, 'chrome_binary_path') else ''

        if explicit_path:
            if os.path.exists(explicit_path):
                return explicit_path
            raise FileNotFoundError(f"Chrome binary not found at '{explicit_path}'.")

        if platform.system() == 'Darwin':
            mac_candidates = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
            for candidate in mac_candidates:
                if os.path.exists(candidate):
                    return candidate

        return None
