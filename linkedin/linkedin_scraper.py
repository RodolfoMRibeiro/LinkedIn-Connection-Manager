import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from linkedin.linkedin_driver import LinkedInDriver

WAIT_TIME_SHORT = 3
WAIT_TIME_LONG = 10  # Increased to allow JS rendering


@dataclass
class DateRange:
    start: Optional[Dict[str, Optional[str]]] = None
    end: Optional[Dict[str, Optional[str]]] = None
    is_current: bool = False
    duration: Optional[str] = None


class LinkedInScraper:
    linkedinDriver: LinkedInDriver
    
    def __init__(self, linkedinDriver: LinkedInDriver):
        self.linkedinDriver = linkedinDriver
        self.driver = linkedinDriver.driver
        self.wait = WebDriverWait(self.driver, WAIT_TIME_LONG * 2)

    def scrape_profile(self, profile_url: str, debug: bool = False) -> Dict:
        print(f"INFO: Loading profile {profile_url}")
        self.driver.get(profile_url)
        self._wait_for_profile_header()
        self._progressive_scroll()
        self._expand_all_show_more_buttons()
        
        if debug:
            self._save_debug_html("debug_after_scroll.html")

        experience = self._extract_experience()

        profile_payload = {
            "basic_info": self._extract_basic_info(profile_url, experience),
            "experience": experience,
            "education": self._extract_education(),
            "certifications": self._extract_certifications(),
            "languages": self._extract_languages(),
        }

        print(f"INFO: Finished scraping {profile_url}")
        return profile_payload

    # --- extraction helpers -------------------------------------------------
    def _extract_basic_info(self, profile_url: str, experience: List[Dict]) -> Dict:
        fullname = self._safe_text_with_fallbacks([
            "h1.text-heading-xlarge",
            "h1[data-generated-suggestion-target]",
            "section.artdeco-card h1",
            "div.ph5 h1",
        ])
        headline = self._safe_text(By.CSS_SELECTOR, "div.text-body-medium.break-words")
        about = self._extract_about_section()
        location_full = self._safe_text_with_fallbacks([
            "span.text-body-small.inline.t-black--light.break-words",
            "div.ph5 span.text-body-small.t-black--light",
        ])
        first_name, last_name = self._split_name(fullname)
        location_data = self._parse_location(location_full)
        profile_picture_url = self._safe_attr_with_fallbacks([
            "img.pv-top-card-profile-picture__image--show",
            "img.pv-top-card-profile-picture__image",
            "button.pv-top-card__photo img",
            "img.EntityPhoto-circle-9",
        ], "src")
        background_picture_url = self._safe_attr_with_fallbacks([
            "img.profile-background-image__image",
            "div.profile-background-image img",
        ], "src")
        follower_count = self._extract_stat_number(["followers", "seguidores"])
        connection_count = self._extract_connection_count()
        top_skills = self._extract_top_skills()
        public_identifier = self._extract_public_identifier(profile_url)

        current_company = None
        current_company_url = None
        current_company_urn = None
        if experience:
            current = next((exp for exp in experience if exp.get("is_current")), None)
            if current:
                current_company = current.get("company")
                current_company_url = current.get("company_linkedin_url")
                current_company_urn = current.get("company_id")

        return {
            "fullname": fullname,
            "first_name": first_name,
            "last_name": last_name,
            "headline": headline,
            "public_identifier": public_identifier,
            "profile_url": profile_url,
            "profile_picture_url": profile_picture_url,
            "about": about,
            "location": location_data,
            "creator_hashtags": [],
            "is_creator": False,
            "is_influencer": False,
            "is_premium": bool(self._find_elements(By.CSS_SELECTOR, "li.pv-top-card--list-bullet span.premium-icon")),
            "open_to_work": "open to work" in self.driver.page_source.lower(),
            "created_timestamp": None,
            "show_follower_count": follower_count is not None,
            "background_picture_url": background_picture_url,
            "urn": None,
            "follower_count": follower_count,
            "connection_count": connection_count,
            "current_company": current_company,
            "current_company_urn": current_company_urn,
            "current_company_url": current_company_url,
            "top_skills": top_skills,
            "email": None,
        }

    def _extract_experience(self) -> List[Dict]:
        section = self._find_section("experience")
        if not section:
            return []

        entries = []
        for item in self._list_items(section):
            # Title: look for bold text in the first heading area
            title = self._safe_text_with_fallbacks([
                "div.display-flex.align-items-center.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "div.t-bold span[aria-hidden='true']",
                "span.mr1.t-bold span[aria-hidden='true']",
                "span.t-bold span[aria-hidden='true']",
            ], parent=item)
            
            # Company: in span.t-14.t-normal (first one, contains company · employment type)
            company_full = self._safe_text_with_fallbacks([
                "span.t-14.t-normal span[aria-hidden='true']",
                "span.t-14.t-normal:not(.t-black--light) span[aria-hidden='true']",
            ], parent=item)
            # Extract just the company name (before the ·)
            company = company_full.split("·")[0].strip() if company_full else ""
            
            # Date/duration: in span.pvs-entity__caption-wrapper or span.t-14.t-normal.t-black--light
            meta = self._safe_text_with_fallbacks([
                "span.pvs-entity__caption-wrapper[aria-hidden='true']",
                "span.t-14.t-normal.t-black--light span.pvs-entity__caption-wrapper",
                "span.t-14.t-normal.t-black--light span[aria-hidden='true']",
            ], parent=item)
            
            # Location: second span.t-14.t-normal.t-black--light
            location = self._extract_location_from_experience_item(item)
            
            # Description: in inline-show-more-text div
            description = self._safe_text_with_fallbacks([
                "div.inline-show-more-text span[aria-hidden='true']",
                "div[class*='inline-show-more-text'] span[aria-hidden='true']",
            ], parent=item)
            
            # Logo URL
            logo_url = self._safe_attr_with_fallbacks([
                "img.ivm-view-attr__img--centered",
                "img.EntityPhoto-square-3",
                "img[alt*='Logo']",
            ], "src", parent=item)
            
            # Company URL
            company_url = self._safe_attr_with_fallbacks([
                "a[data-field='experience_company_logo']",
                "a[href*='/company/']",
            ], "href", parent=item)
            
            skills_url = self._safe_attr(By.CSS_SELECTOR, "a[href*='skill-associations']", "href", parent=item)

            # Skip if we couldn't extract the essential info
            if not title and not company:
                continue

            date_range = self._parse_date_range(meta)
            
            # Extract employment type from company_full if present
            employment_type = None
            if "·" in company_full:
                emp_type_raw = company_full.split("·")[1].strip() if len(company_full.split("·")) > 1 else ""
                employment_type = self._normalize_employment_type(emp_type_raw) or self._infer_employment_type(title)
            else:
                employment_type = self._infer_employment_type(title)
            
            entry = {
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "duration": date_range.duration,
                "start_date": date_range.start,
                "end_date": date_range.end,
                "is_current": date_range.is_current,
                "company_linkedin_url": company_url,
                "company_logo_url": logo_url,
                "employment_type": employment_type,
                "location_type": None,
                "skills": self._extract_skills_from_item(item),
                "company_id": self._extract_company_id_from_url(company_url),
                "skills_url": skills_url,
            }
            entries.append(entry)

        return entries
    
    def _extract_location_from_experience_item(self, item: WebElement) -> Optional[str]:
        """Extract location from experience item (usually the second t-black--light span)."""
        try:
            spans = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']")
            # First span is usually date, second is location
            for span in spans:
                text = span.text.strip()
                # Location typically contains city/country names, not dates
                if text and not self._looks_like_date(text):
                    return text
            return None
        except Exception:
            return None
    
    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date string."""
        # Month names and date-related keywords
        date_keywords = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez",
                        "feb", "apr", "may", "aug", "sep", "oct", "dec",
                        "momento", "present", "atual", "ano ", "year", "mês", "month", "meses", "months"]
        text_lower = text.lower()
        
        # Check for date keywords
        has_date_keyword = any(keyword in text_lower for keyword in date_keywords)
        
        # Also check for year pattern (4 digits between 1900-2100)
        has_year = bool(re.search(r'\b(19|20)\d{2}\b', text))
        
        # Check for date range pattern (contains " - ")
        has_date_range = " - " in text
        
        return has_date_keyword or (has_year and has_date_range)
    
    def _normalize_employment_type(self, raw: str) -> Optional[str]:
        """Normalize employment type to standard format."""
        if not raw:
            return None
        raw_lower = raw.lower().strip()
        mapping = {
            "tempo integral": "Full-time",
            "full-time": "Full-time",
            "meio período": "Part-time",
            "part-time": "Part-time",
            "autônomo": "Freelance",
            "freelance": "Freelance",
            "contrato": "Contract",
            "contract": "Contract",
            "estágio": "Internship",
            "internship": "Internship",
            "temporário": "Temporary",
            "temporary": "Temporary",
        }
        for key, value in mapping.items():
            if key in raw_lower:
                return value
        return raw.strip() if raw.strip() else None

    def _extract_education(self) -> List[Dict]:
        section = self._find_section("education")
        if not section:
            return []

        entries = []
        for item in self._list_items(section):
            # School name - first bold text
            school = self._safe_text_with_fallbacks([
                "div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "div.mr1.t-bold span[aria-hidden='true']",
                "span.mr1.t-bold span[aria-hidden='true']",
                "div.t-bold span[aria-hidden='true']",
            ], parent=item)
            
            # Degree - second line, normal text
            degree = self._safe_text_with_fallbacks([
                "span.t-14.t-normal:not(.t-black--light) span[aria-hidden='true']",
                "span.t-14.t-normal span[aria-hidden='true']",
            ], parent=item)
            
            # Date/duration - in t-black--light span
            date_text = self._safe_text_with_fallbacks([
                "span.pvs-entity__caption-wrapper[aria-hidden='true']",
                "span.t-14.t-normal.t-black--light span[aria-hidden='true']",
            ], parent=item)
            
            # Logo and URL
            logo_url = self._safe_attr_with_fallbacks([
                "img.ivm-view-attr__img--centered",
                "img.EntityPhoto-square-3",
                "img[alt*='Logo']",
            ], "src", parent=item)
            
            school_url = self._safe_attr_with_fallbacks([
                "a[data-field='education_school_logo']",
                "a[href*='/school/']",
                "a[href*='/company/']",
            ], "href", parent=item)

            date_range = self._parse_date_range(date_text)
            
            # Skip empty entries
            if not school and not degree:
                continue

            entry = {
                "school": school,
                "degree": degree,
                "degree_name": degree,
                "field_of_study": None,
                "duration": date_text if date_range.duration is None else date_range.duration,
                "school_linkedin_url": school_url,
                "school_logo_url": logo_url,
                "start_date": date_range.start,
                "end_date": date_range.end,
                "school_id": self._extract_company_id_from_url(school_url),
                "description": date_text,
            }
            entries.append(entry)

        return entries

    def _extract_certifications(self) -> List[Dict]:
        section = self._find_section("licenses_and_certifications")
        if not section:
            return []

        entries = []
        for item in self._list_items(section):
            # Certification name - bold text
            name = self._safe_text_with_fallbacks([
                "div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "div.mr1.t-bold span[aria-hidden='true']",
                "span.mr1.t-bold span[aria-hidden='true']",
                "div.t-bold span[aria-hidden='true']",
            ], parent=item)
            
            # Issuer - normal text
            issuer = self._safe_text_with_fallbacks([
                "span.t-14.t-normal:not(.t-black--light) span[aria-hidden='true']",
                "span.t-14.t-normal span[aria-hidden='true']",
            ], parent=item)
            
            # Issue date - light text
            issued = self._safe_text_with_fallbacks([
                "span.pvs-entity__caption-wrapper[aria-hidden='true']",
                "span.t-14.t-normal.t-black--light span[aria-hidden='true']",
            ], parent=item)
            
            # Skip empty entries
            if not name and not issuer:
                continue

            entries.append({
                "name": name,
                "issuer": issuer,
                "issued_date": issued,
            })

        return entries

    def _extract_languages(self) -> List[Dict]:
        section = self._find_section("languages")
        if not section:
            return []

        entries = []
        for item in self._list_items(section):
            # Language name - bold text
            language = self._safe_text_with_fallbacks([
                "div.mr1.t-bold span[aria-hidden='true']",
                "span.mr1.t-bold span[aria-hidden='true']",
                "div.t-bold span[aria-hidden='true']",
            ], parent=item)
            
            # Proficiency - in caption wrapper or normal text
            proficiency = self._safe_text_with_fallbacks([
                "span.pvs-entity__caption-wrapper[aria-hidden='true']",
                "span.t-14.t-normal.t-black--light span[aria-hidden='true']",
                "span.t-14.t-normal span[aria-hidden='true']",
            ], parent=item)
            
            # Skip empty entries
            if not language:
                continue
            
            entries.append({
                "language": language,
                "proficiency": proficiency,
            })

        return entries

    # --- selenium helpers ---------------------------------------------------
    def _wait_for_profile_header(self):
        """Wait for profile header with multiple fallback selectors."""
        selectors = [
            "h1.text-heading-xlarge",  # Standard profile name
            "h1[data-generated-suggestion-target]",  # Alternative selector
            "section.artdeco-card h1",  # Profile card header
            "div.ph5 h1",  # Profile header container
        ]
        
        for selector in selectors:
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"DEBUG: Profile header found with selector: {selector}")
                return
            except TimeoutException:
                continue
        
        # If none worked, save HTML for debugging and raise error
        self._save_debug_html()
        raise TimeoutException(
            f"Profile header did not load. Tried selectors: {selectors}. "
            "Check 'debug_page.html' for the actual page content."
        )
    
    def _save_debug_html(self, filename: str = "debug_page.html"):
        """Save current page HTML for debugging purposes."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"DEBUG: Page HTML saved to '{filename}'")
        except Exception as e:
            print(f"DEBUG: Could not save debug HTML: {e}")

    def _progressive_scroll(self):
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, document.body.scrollHeight / 5);")
            time.sleep(0.7)

    def _expand_all_show_more_buttons(self):
        buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-expanded='false']")
        for button in buttons:
            label = (button.get_attribute("aria-label") or button.text or "").lower()
            if "show more" in label or "ver mais" in label:
                try:
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.2)
                except Exception:
                    continue

    def _find_section(self, section_id: str) -> Optional[WebElement]:
        """Find profile section by various possible identifiers."""
        # Map section names to possible identifiers
        section_map = {
            "experience": ["experience", "experiência"],
            "education": ["education", "educação", "formação"],
            "licenses_and_certifications": ["licenses", "certifications", "licenças", "certificações"],
            "languages": ["languages", "idiomas"],
            "skills": ["skills", "competências", "habilidades"],
            "about": ["about", "sobre"],
        }
        
        identifiers = section_map.get(section_id, [section_id])
        
        # Try to find div anchor and get parent section
        for identifier in identifiers:
            # First try: find div anchor and navigate to parent section
            anchor_selectors = [
                f"div[id='{identifier}']",
                f"div#'{identifier}'",
            ]
            for selector in anchor_selectors:
                elements = self._find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Navigate up to find the section container
                    try:
                        parent = elements[0].find_element(By.XPATH, "./ancestor::section[contains(@class, 'artdeco-card')]")
                        print(f"DEBUG: Found section '{section_id}' via anchor div and parent section")
                        return parent
                    except Exception:
                        # Try to find the closest parent with artdeco-card class
                        try:
                            parent = elements[0].find_element(By.XPATH, "./ancestor::*[contains(@class, 'artdeco-card')]")
                            print(f"DEBUG: Found section '{section_id}' via anchor div and artdeco-card parent")
                            return parent
                        except Exception:
                            pass
        
        # Second try: direct section selectors
        for identifier in identifiers:
            selectors = [
                f"section[id='{identifier}']",
                f"section[data-section='{identifier}']",
                f"section[data-view-name*='{identifier}']",
            ]
            for selector in selectors:
                elements = self._find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"DEBUG: Found section '{section_id}' with selector: {selector}")
                    return elements[0]
        
        # Third try: find by section header text
        sections = self._find_elements(By.CSS_SELECTOR, "section.artdeco-card")
        for section in sections:
            try:
                header_selectors = [
                    "h2 span[aria-hidden='true']",
                    "h2 span",
                    ".pvs-header__title span",
                    "span.pvs-header__title-text",
                ]
                for header_selector in header_selectors:
                    headers = section.find_elements(By.CSS_SELECTOR, header_selector)
                    for header in headers:
                        header_text = header.text.strip().lower()
                        for identifier in identifiers:
                            if identifier.lower() in header_text:
                                print(f"DEBUG: Found section '{section_id}' by header text: '{header_text}'")
                                return section
            except Exception:
                continue
        
        print(f"DEBUG: Section '{section_id}' not found")
        return None

    def _list_items(self, section: WebElement) -> List[WebElement]:
        """Find list items within a section using multiple fallback selectors."""
        selectors = [
            # Direct children of the section's list - most specific
            "ul > li.artdeco-list__item",
            "li.artdeco-list__item",
            "li.pvs-list__item--line-separated",
            "li.pvs-list__paged-list-item",
            # Fallback to any li in a list container
            "ul li[class*='list__item']",
            "div.pvs-list__outer-container > ul > li",
        ]
        for selector in selectors:
            items = section.find_elements(By.CSS_SELECTOR, selector)
            if items:
                print(f"DEBUG: Found {len(items)} items with selector: {selector}")
                return items
        return []

    def _find_elements(self, by, value) -> List[WebElement]:
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def _safe_text(self, by, value, parent: Optional[WebElement] = None) -> str:
        try:
            element = parent.find_element(by, value) if parent else self.driver.find_element(by, value)
            return element.text.strip()
        except Exception:
            return ""

    def _safe_text_with_fallbacks(self, selectors: List[str], parent: Optional[WebElement] = None) -> str:
        """Try multiple CSS selectors and return text from the first match."""
        for selector in selectors:
            text = self._safe_text(By.CSS_SELECTOR, selector, parent)
            if text:
                return text
        return ""

    def _safe_attr(self, by, value, attr: str, parent: Optional[WebElement] = None) -> Optional[str]:
        try:
            element = parent.find_element(by, value) if parent else self.driver.find_element(by, value)
            return element.get_attribute(attr)
        except Exception:
            return None

    def _safe_attr_with_fallbacks(self, selectors: List[str], attr: str, parent: Optional[WebElement] = None) -> Optional[str]:
        """Try multiple CSS selectors and return attribute from the first match."""
        for selector in selectors:
            value = self._safe_attr(By.CSS_SELECTOR, selector, attr, parent)
            if value:
                return value
        return None

    def _extract_section_text(self, section_id: str) -> str:
        section = self._find_section(section_id)
        if not section:
            return ""
        return self._safe_text(By.CSS_SELECTOR, "div.inline-show-more-text span[aria-hidden='true']", parent=section)
    
    def _extract_about_section(self) -> str:
        """Extract about section text with multiple fallback selectors."""
        # Try to find the about section
        section = self._find_section("about")
        if section:
            text = self._safe_text_with_fallbacks([
                "div.inline-show-more-text span[aria-hidden='true']",
                "div[class*='inline-show-more-text'] span[aria-hidden='true']",
                "span[aria-hidden='true']",
            ], parent=section)
            if text:
                return text
        
        # Fallback: search for the about text directly in the page
        about_selectors = [
            "section.pv-about-section div.inline-show-more-text span",
            "div[data-generated-suggestion-target] div.inline-show-more-text span[aria-hidden='true']",
        ]
        for selector in about_selectors:
            text = self._safe_text(By.CSS_SELECTOR, selector)
            if text:
                return text
        
        return ""
    
    def _extract_connection_count(self) -> Optional[int]:
        """Extract connection count from profile."""
        # Try to find connection count in various formats
        selectors = [
            "span.t-bold",  # "+ de 500 conexões"
            "li.text-body-small span",
        ]
        for selector in selectors:
            elements = self._find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                text = elem.text.lower()
                if "conexões" in text or "connections" in text:
                    # Handle "500+" or "500" or "+ de 500"
                    match = re.search(r"(\d[\d,\.]*)", text.replace(".", "").replace(",", ""))
                    if match:
                        try:
                            return int(match.group(1))
                        except ValueError:
                            pass
                    # Handle "500+" format
                    if "500" in text:
                        return 500
        return None

    def _split_name(self, fullname: str):
        if not fullname:
            return ("", "")
        parts = fullname.split()
        if len(parts) == 1:
            return (parts[0], "")
        return (parts[0], " ".join(parts[1:]))

    def _parse_location(self, location_full: str) -> Dict:
        if not location_full:
            return {
                "country": None,
                "city": None,
                "full": None,
                "country_code": None,
            }
        parts = [part.strip() for part in location_full.split(",")]
        city = parts[0] if parts else None
        country = parts[-1] if parts else None
        return {
            "country": country,
            "city": city,
            "full": location_full,
            "country_code": None,
        }

    def _extract_stat_number(self, labels: List[str]) -> Optional[int]:
        """Extract a stat number by searching for labels in stat elements."""
        if isinstance(labels, str):
            labels = [labels]
        
        items = self.driver.find_elements(By.CSS_SELECTOR, "li.inline.t-16.t-black.t-normal")
        for item in items:
            text = item.text.lower()
            for label in labels:
                if label.lower() in text:
                    match = re.search(r"(\d[\d,\.+]*)", item.text)
                    if match:
                        number = match.group(1).replace(",", "").replace(".", "")
                        if "+" in number:
                            number = number.replace("+", "")
                        try:
                            return int(number)
                        except ValueError:
                            return None
        return None

    def _extract_top_skills(self) -> List[str]:
        section = self._find_section("skills")
        if not section:
            return []
        skills = []
        for item in self._list_items(section):
            skill = self._safe_text_with_fallbacks([
                "div.mr1.hoverable-link-text.t-bold span[aria-hidden='true']",
                "div.mr1.t-bold span[aria-hidden='true']",
                "span.mr1.t-bold span[aria-hidden='true']",
                "div.t-bold span[aria-hidden='true']",
            ], parent=item)
            if skill and skill not in skills:
                skills.append(skill)
        return skills[:10]

    def _extract_public_identifier(self, profile_url: str) -> Optional[str]:
        parsed = urlparse(profile_url)
        identifier = parsed.path.rstrip("/").split("/")[-1]
        return identifier or None

    def _extract_location_from_item(self, item: WebElement) -> Optional[str]:
        candidates = item.find_elements(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']")
        if len(candidates) >= 2:
            return candidates[-1].text.strip()
        return None

    def _parse_date_range(self, text: str) -> DateRange:
        if not text:
            return DateRange()

        parts = [part.strip() for part in text.split("·")]
        date_part = parts[0] if parts else ""
        duration_part = parts[1] if len(parts) > 1 else None

        dates = [segment.strip() for segment in date_part.split(" - ")]
        start = self._build_date_dict(dates[0]) if dates else None
        end_raw = dates[1] if len(dates) > 1 else None
        
        # Check if current position - handle multiple languages
        current_keywords = ["present", "atual", "o momento", "momento", "now", "currently"]
        is_current = end_raw is None or any(kw in end_raw.lower() for kw in current_keywords)
        end = None if is_current else self._build_date_dict(end_raw)

        return DateRange(start=start, end=end, is_current=is_current, duration=duration_part)

    def _build_date_dict(self, value: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
        if not value:
            return None
        
        # Month name mapping (Portuguese and English)
        month_map = {
            "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
            "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
            "feb": 2, "apr": 4, "may": 5, "aug": 8, "sep": 9, "oct": 10, "dec": 12,
            "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
            "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
        }
        
        # Clean the value - remove "de" which is common in Portuguese dates
        cleaned = value.lower().replace(" de ", " ").strip()
        tokens = cleaned.split()
        
        year = None
        month = None
        month_name = None
        
        for token in tokens:
            # Check if it's a year (4 digits)
            if token.isdigit() and len(token) == 4:
                year = int(token)
            # Check if it's a month abbreviation
            elif token[:3] in month_map:
                month = month_map[token[:3]]
                month_name = token.capitalize()
        
        if year or month:
            return {"year": year, "month": month_name or (month if month else None)}
        
        return {"year": None, "month": value}

    def _infer_employment_type(self, title: str) -> Optional[str]:
        if not title:
            return None
        mapping = {
            "intern": "Internship",
            "estagi": "Internship",
            "freelance": "Freelance",
            "part-time": "Part-time",
            "full-time": "Full-time",
            "contract": "Contract",
        }
        lower_title = title.lower()
        for key, value in mapping.items():
            if key in lower_title:
                return value
        return None

    def _extract_skills_from_item(self, item: WebElement) -> List[str]:
        badges = item.find_elements(By.CSS_SELECTOR, "li.pvs-list__item span[aria-hidden='true']")
        skills = []
        for badge in badges:
            text = badge.text.strip()
            if text and text not in skills:
                skills.append(text)
        return skills

    def _extract_company_id_from_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        match = re.search(r"/company/([^/?]+)/?", url)
        if match:
            return match.group(1)
        match_numeric = re.search(r"/company/(\d+)", url)
        if match_numeric:
            return match_numeric.group(1)
        return None