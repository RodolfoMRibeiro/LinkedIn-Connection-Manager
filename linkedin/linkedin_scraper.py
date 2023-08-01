import csv
import os.path
import time
import parameters
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

WAIT_TIME_SHORT = 10
WAIT_TIME_LONG = 20

class LinkedInScraper:
    def __init__(self, driver):
        self.driver = driver
        self.writer = None

    def initialize_csv_writer(self):
        file_name = parameters.file_name
        file_exists = os.path.isfile(file_name)
        with open(file_name, 'a', newline='') as file:
            self.writer = csv.writer(file)
            if not file_exists:
                self.writer.writerow(['Connection Summary'])

    def process_results(self, linkedin_urls, ignore_list):
        for index, result in enumerate(linkedin_urls, start=1):
            text = result.text.split('\n')[0]
            if text in ignore_list or text.strip() in ignore_list:
                print("%s) IGNORED: %s" % (index, text))
                continue
            connection_action = result.find_elements(By.CLASS_NAME, 'artdeco-button__text')
            if not connection_action:
                print("%s) CANT: %s" % (index, text))
                continue

            connection = connection_action[0]
            self.send_connection_request(connection, index, text)

    def send_connection_request(self, connection, index, text):
        if connection.text == 'Connect':
            try:
                coordinates = connection.location_once_scrolled_into_view
                self.driver.execute_script("window.scrollTo(%s, %s);" % (coordinates['x'], coordinates['y']))
                time.sleep(WAIT_TIME_SHORT)
                connection.click()
                WebDriverWait(self.driver, WAIT_TIME_LONG).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'artdeco-button--primary'))
                )
                if self.driver.find_elements(By.CLASS_NAME, 'artdeco-button--primary')[0].is_enabled():
                    self.driver.find_elements(By.CLASS_NAME, 'artdeco-button--primary')[0].click()
                    self.writer.writerow([text])
                    print("%s) SENT: %s" % (index, text))
                else:
                    self.driver.find_elements(By.CLASS_NAME, 'artdeco-modal__dismiss')[0].click()
                    print("%s) CANT: %s" % (index, text))
            except Exception as e:
                print('%s) ERROR: %s' % (index, text))
            time.sleep(WAIT_TIME_SHORT)
        elif connection.text == 'Pending':
            print("%s) PENDING: %s" % (index, text))
        else:
            if text:
                print("%s) CANT: %s" % (index, text))
            else:
                print("%s) ERROR: You might have reached the limit" % (index))
