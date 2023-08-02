from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from linkedin.linkedin_driver import LinkedInDriver
from linkedin.linkedin_login import LinkedInLogin
from linkedin.linkedin_scraper import LinkedInScraper
import parameters

if __name__ == "__main__":
    try:
        driver = LinkedInDriver()
        driver.initialize_driver()

        login_handler = LinkedInLogin(driver.driver)
        login_handler.login()

        scraper = LinkedInScraper(driver)

        ignore_list = parameters.ignore_list.split(',') if parameters.ignore_list else []
        scraper.initialize_csv_writer()

        for page in range(1, parameters.till_page + 1):
            print(f'\nINFO: Checking on page {page}')
            linkedin_urls = scraper.linkedinDriver.get_search_results(page)
            print(f'INFO: {len(linkedin_urls)} connections found on page {page}')
            scraper.process_results(linkedin_urls, ignore_list)

    except KeyboardInterrupt:
        print("\n\nINFO: User Canceled\n")
    except Exception as e:
        print('ERROR: Unable to run, error - %s' % (e))
    finally:
        driver.close_driver()
