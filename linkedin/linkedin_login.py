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
        self._navigate_to_login_page()
        self._enter_credentials_and_submit()

    def _navigate_to_login_page(self):
        self.driver.get(LINKEDIN_LOGIN_URL)
        WebDriverWait(self.driver, WAIT_TIME_LONG).until(EC.presence_of_element_located((By.ID, 'username')))

    def _enter_credentials_and_submit(self):
        username_input = self.driver.find_element(By.ID, 'username')
        username_input.send_keys(parameters.linkedin_username)
        time.sleep(WAIT_TIME_SHORT)
        password_input = self.driver.find_element(By.ID, 'password')
        password_input.send_keys(parameters.linkedin_password)
        submit_button = self.driver.find_element(By.XPATH, '//*[@type="submit"]')
        submit_button.click()

    def confirm_user_action(self):
        if input("Can we proceed (yes / no)? ").lower() != "yes":
            os._exit(1)
