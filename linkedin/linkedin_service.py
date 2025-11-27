"""
LinkedIn Service - Singleton that manages browser session with auto-recovery.
"""
import threading
import time
from typing import Dict, Optional

from selenium.common.exceptions import WebDriverException, TimeoutException

from linkedin.linkedin_driver import LinkedInDriver
from linkedin.linkedin_login import LinkedInLogin
from linkedin.linkedin_scraper import LinkedInScraper


class LinkedInService:
    """
    Singleton service that manages the LinkedIn browser session.
    Handles login, session recovery, and scraping operations.
    """
    _instance: Optional['LinkedInService'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._driver: Optional[LinkedInDriver] = None
        self._scraper: Optional[LinkedInScraper] = None
        self._session_active = False
        self._scrape_lock = threading.Lock()
        self._last_activity = 0
        self._session_timeout = 30 * 60  # 30 minutes of inactivity
    
    @property
    def is_ready(self) -> bool:
        """Check if the service is ready to scrape."""
        return self._session_active and self._driver is not None
    
    def initialize(self) -> bool:
        """
        Initialize the browser and login to LinkedIn.
        Should be called once when the API starts.
        """
        try:
            print("INFO: Initializing LinkedIn service...")
            self._driver = LinkedInDriver()
            self._driver.initialize_driver()
            
            login_handler = LinkedInLogin(self._driver.driver)
            login_handler.login()
            
            self._scraper = LinkedInScraper(self._driver)
            self._session_active = True
            self._last_activity = time.time()
            
            print("INFO: LinkedIn service initialized successfully!")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to initialize LinkedIn service: {e}")
            self._session_active = False
            return False
    
    def _check_session_valid(self) -> bool:
        """Check if the current session is still valid."""
        if not self._driver or not self._driver.driver:
            return False
        
        try:
            # Try to access LinkedIn to check if session is valid
            current_url = self._driver.driver.current_url
            
            # If we're on the login page, session expired
            if "login" in current_url.lower() or "checkpoint" in current_url.lower():
                print("WARNING: Session expired - detected login/checkpoint page")
                return False
            
            # Check for session timeout based on inactivity
            if time.time() - self._last_activity > self._session_timeout:
                print("WARNING: Session timeout due to inactivity")
                # Navigate to feed to check if still logged in
                self._driver.driver.get("https://www.linkedin.com/feed/")
                time.sleep(2)
                
                if "login" in self._driver.driver.current_url.lower():
                    return False
            
            return True
            
        except WebDriverException:
            print("WARNING: Browser session is invalid")
            return False
    
    def _recover_session(self) -> bool:
        """Attempt to recover an expired session."""
        print("INFO: Attempting to recover session...")
        
        try:
            # Close existing driver if any
            if self._driver:
                try:
                    self._driver.close_driver()
                except Exception:
                    pass
            
            # Re-initialize
            return self.initialize()
            
        except Exception as e:
            print(f"ERROR: Failed to recover session: {e}")
            return False
    
    def scrape_profile(self, profile_url: str) -> Dict:
        """
        Scrape a LinkedIn profile.
        Handles session validation and auto-recovery.
        
        Args:
            profile_url: The LinkedIn profile URL to scrape
            
        Returns:
            Dict with profile data
            
        Raises:
            Exception if scraping fails
        """
        with self._scrape_lock:
            # Check if session is valid
            if not self._check_session_valid():
                print("INFO: Session invalid, attempting recovery...")
                if not self._recover_session():
                    raise Exception("Failed to recover LinkedIn session")
            
            try:
                # Perform the scrape
                result = self._scraper.scrape_profile(profile_url)
                self._last_activity = time.time()
                return result
                
            except TimeoutException as e:
                print(f"WARNING: Timeout during scrape, checking session...")
                # Session might have expired during scrape
                if not self._check_session_valid():
                    if self._recover_session():
                        # Retry once after recovery
                        result = self._scraper.scrape_profile(profile_url)
                        self._last_activity = time.time()
                        return result
                raise e
                
            except Exception as e:
                print(f"ERROR: Scrape failed: {e}")
                raise
    
    def shutdown(self):
        """Gracefully shutdown the service."""
        print("INFO: Shutting down LinkedIn service...")
        self._session_active = False
        
        if self._driver:
            try:
                self._driver.close_driver()
            except Exception as e:
                print(f"WARNING: Error closing driver: {e}")
        
        self._driver = None
        self._scraper = None
        print("INFO: LinkedIn service shutdown complete.")
    
    def get_status(self) -> Dict:
        """Get the current status of the service."""
        return {
            "initialized": self._initialized,
            "session_active": self._session_active,
            "is_ready": self.is_ready,
            "last_activity": self._last_activity,
            "seconds_since_activity": int(time.time() - self._last_activity) if self._last_activity else None,
        }


# Global instance
linkedin_service = LinkedInService()

