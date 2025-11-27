from linkedin.linkedin_driver import LinkedInDriver
from linkedin.linkedin_login import LinkedInLogin
from linkedin.linkedin_scraper import LinkedInScraper
from linkedin.json_writer import ProfileJSONWriter
import parameters

def main():
    try:
        linkedin_driver = LinkedInDriver()
        linkedin_driver.initialize_driver()

        login_handler = LinkedInLogin(linkedin_driver.driver)
        login_handler.login()

        scraper = LinkedInScraper(linkedin_driver)
        json_writer = ProfileJSONWriter(parameters.output_json_path)

        profile_urls = [url.strip() for url in getattr(parameters, "profile_urls", []) if url.strip()]
        if not profile_urls:
            raise ValueError("No profile URLs provided in parameters.profile_urls")

        scraped_profiles = []
        for url in profile_urls:
            try:
                profile_data = scraper.scrape_profile(url, debug=True)
                scraped_profiles.append(profile_data)
            except Exception as scrape_error:
                print(f"ERROR: Failed to scrape {url}: {scrape_error}")

        json_writer.write(scraped_profiles)
        print(f"INFO: Saved {len(scraped_profiles)} profiles to {parameters.output_json_path}")

    except KeyboardInterrupt:
        print("\n\nINFO: User Canceled\n")
    except Exception as e:
        print('ERROR: Unable to run, error - %s' % (e))
        raise
    finally:
        linkedin_driver.close_driver()

if __name__ == "__main__":
    main()
