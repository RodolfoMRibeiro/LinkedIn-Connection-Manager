from linkedin.csv_writer import CSVWriter
from linkedin.linkedin_driver import LinkedInDriver
from linkedin.linkedin_login import LinkedInLogin
from linkedin.linkedin_scraper import LinkedInScraper
import parameters

def main():
    try:
        linkedin_driver = LinkedInDriver()
        linkedin_driver.initialize_driver()
        
        csv_writer = CSVWriter(parameters.file_name)

        login_handler = LinkedInLogin(linkedin_driver.driver)
        login_handler.login()

        scraper = LinkedInScraper(linkedin_driver, csv_writer)

        ignore_list = parameters.ignore_list.split(',') if parameters.ignore_list else []

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
        linkedin_driver.close_driver()

if __name__ == "__main__":
    main()
