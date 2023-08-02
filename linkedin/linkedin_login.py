from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os.path
import time
import parameters

WAIT_TIME_SHORT = 3
WAIT_TIME_LONG = 5
LINKEDIN_LOGIN_URL = 'https://www.linkedin.com/login'

class LinkedInLogin:
    def __init__(self, driver):
        self.driver = driver

    def login(self):
        self.driver.get(LINKEDIN_LOGIN_URL)
        WebDriverWait(self.driver, WAIT_TIME_LONG).until(EC.presence_of_element_located((By.ID, 'username')))
        self.driver.find_element(By.ID, 'username').send_keys(parameters.linkedin_username)
        time.sleep(WAIT_TIME_SHORT)
        self.driver.find_element(By.ID, 'password').send_keys(parameters.linkedin_password)
        self.driver.find_element(By.XPATH, '//*[@type="submit"]').click()

    def _wait_for_user_confirmation(self):
        if input("Can we proceed (yes / no)? ").lower() not in "yes":
            os._exit(1)
