from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import parameters

WAIT_TIME_SHORT = 3
WAIT_TIME_LONG = 5

class LinkedInDriver:
    def __init__(self):
        self.driver = None

    def initialize_driver(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    def scroll_to_end(self):
        html = self.driver.find_element(By.TAG_NAME, 'html')
        html.send_keys(Keys.END)
        WebDriverWait(self.driver, WAIT_TIME_LONG).until(EC.presence_of_element_located((By.TAG_NAME, 'footer')))
        time.sleep(WAIT_TIME_SHORT)

    def get_search_results(self, page):
        query_url = self._build_query_url(page)
        self.driver.get(query_url)
        WebDriverWait(self.driver, WAIT_TIME_LONG).until(EC.presence_of_element_located((By.CLASS_NAME, 'reusable-search__result-container')))
        return self.driver.find_elements(By.CLASS_NAME, 'reusable-search__result-container')

    def _build_query_url(self, page):
        return f'https://www.linkedin.com/search/results/people/?keywords={parameters.keywords}&origin=GLOBAL_SEARCH_HEADER&page={page}'

    def close_driver(self):
        self.driver.quit()
