import time
import parameters
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

WAIT_TIME_SHORT = 3
WAIT_TIME_LONG = 10
LINKEDIN_LOGIN_URL = 'https://www.linkedin.com/login'


class LinkedInLogin:
    def __init__(self, driver):
        self.driver = driver

    def login(self) -> bool:
        """
        Perform LinkedIn login.
        
        Returns:
            True if login was successful, False otherwise
        """
        try:
            self._navigate_to_login_page()
            self._enter_credentials_and_submit()
            return self._verify_login_success()
        except Exception as e:
            print(f"ERROR: Login failed: {e}")
            return False

    def _navigate_to_login_page(self):
        print("INFO: Navigating to LinkedIn login page...")
        self.driver.get(LINKEDIN_LOGIN_URL)
        WebDriverWait(self.driver, WAIT_TIME_LONG).until(
            EC.presence_of_element_located((By.ID, 'username'))
        )

    def _enter_credentials_and_submit(self):
        print("INFO: Entering credentials...")
        username_input = self.driver.find_element(By.ID, 'username')
        username_input.send_keys(parameters.linkedin_username)
        time.sleep(WAIT_TIME_SHORT)
        
        password_input = self.driver.find_element(By.ID, 'password')
        password_input.send_keys(parameters.linkedin_password)
        
        submit_button = self.driver.find_element(By.XPATH, '//*[@type="submit"]')
        submit_button.click()
        
    def _verify_login_success(self) -> bool:
        """
        Verify that login was successful.
        Waits for the feed page or handles verification challenges.
        """
        print("INFO: Verifying login... (waiting up to 30 seconds)")
        
        # Wait for login to complete - could be feed, checkpoint, or error
        max_wait = 30
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            current_url = self.driver.current_url.lower()
            
            # Success - redirected to feed or main page
            if "/feed" in current_url or "linkedin.com/in/" in current_url:
                print("INFO: Login successful!")
                return True
            
            # Checkpoint/verification required - need manual intervention
            if "checkpoint" in current_url or "challenge" in current_url:
                print("\n" + "=" * 50)
                print("⚠️  VERIFICATION REQUIRED!")
                print("Please complete the verification in the browser.")
                print("Waiting up to 60 seconds...")
                print("=" * 50 + "\n")
                
                # Wait longer for manual verification
                verification_start = time.time()
                while time.time() - verification_start < 60:
                    time.sleep(2)
                    current_url = self.driver.current_url.lower()
                    if "/feed" in current_url or "linkedin.com/in/" in current_url:
                        print("INFO: Verification completed, login successful!")
                        return True
                
                print("ERROR: Verification timeout")
                return False
            
            # Still on login page - might be an error
            if "login" in current_url:
                # Check for error messages
                try:
                    error = self.driver.find_element(By.CSS_SELECTOR, ".form__label--error, #error-for-password")
                    if error:
                        print(f"ERROR: Login error - {error.text}")
                        return False
                except Exception:
                    pass
            
            time.sleep(1)
        
        print("ERROR: Login verification timeout")
        return False
    
    def is_logged_in(self) -> bool:
        """Check if currently logged in to LinkedIn."""
        try:
            current_url = self.driver.current_url.lower()
            return "/feed" in current_url or (
                "linkedin.com" in current_url and 
                "login" not in current_url and 
                "checkpoint" not in current_url
            )
        except Exception:
            return False