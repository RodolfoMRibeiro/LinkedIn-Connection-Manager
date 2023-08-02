import csv
import os.path
import time
import parameters
from linkedin_driver import LinkedInDriver 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

WAIT_TIME_SHORT = 10
WAIT_TIME_LONG = 20

class LinkedInScraper:
    linkedinDriver: LinkedInDriver
    
    def __init__(self, linkedinDriver: LinkedInDriver):
        self.linkedinDriver = linkedinDriver
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
                self.print_ignored(index, text)
            else:
                self.process_connection_action(result, index, text)

    def process_connection_action(self, result, index, text):
        connection_action = result.find_elements(By.CLASS_NAME, 'artdeco-button__text')
        if not connection_action:
            self.print_cant(index, text)
            return

        connection = connection_action[0]
        if connection.text == 'Connect':
            self.send_connection_request(connection, index, text)
        elif connection.text == 'Pending':
            self.print_pending(index, text)
        else:
            if text:
                self.print_cant(index, text)
            else:
                self.print_error(index)

    def send_connection_request(self, connection, index, text):
        try:
            connection.click()
            sendButton = self.linkedinDriver.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send')]")
            sendButton.click()
            self.print_sent(index, text)
        except Exception as e:
            self.print_error(index, text)
        time.sleep(WAIT_TIME_SHORT)

    def print_ignored(self, index, text):
        print("%s) IGNORED: %s" % (index, text))

    def print_cant(self, index, text):
        print("%s) CANT: %s" % (index, text))

    def print_sent(self, index, text):
        print("%s) SENT: %s" % (index, text))

    def print_pending(self, index, text):
        print("%s) PENDING: %s" % (index, text))

    def print_error(self, index):
        print("%s) ERROR: You might have reached the limit" % index)
