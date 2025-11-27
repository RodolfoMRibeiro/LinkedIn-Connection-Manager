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

    def scrape_profile(self, profile_url: str) -> Dict:
        print(f"INFO: Loading profile {profile_url}")
        self.driver.get(profile_url)
        self._wait_for_profile_header()
        self._progressive_scroll()
        self._expand_all_show_more_buttons()

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
        about = self._extract_section_text("about")
        location_full = self._safe_text(By.CSS_SELECTOR, "div.ph5.pb5 span.text-body-small.inline.t-black--light.break-words")
        first_name, last_name = self._split_name(fullname)
        location_data = self._parse_location(location_full)
        profile_picture_url = self._safe_attr(By.CSS_SELECTOR, "img.pv-top-card-profile-picture__image", "src")
        background_picture_url = self._safe_attr(By.CSS_SELECTOR, "img.profile-background-image__image", "src")
        follower_count = self._extract_stat_number("followers")
        connection_count = self._extract_stat_number("connections")
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
            title = self._safe_text(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']", parent=item)
            company = self._safe_text(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']", parent=item)
            meta = self._safe_text(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']", parent=item)
            location = self._extract_location_from_item(item)
            description = self._safe_text(By.CSS_SELECTOR, "div.inline-show-more-text span[aria-hidden='true']", parent=item)
            logo_url = self._safe_attr(By.CSS_SELECTOR, "img.pvs-entity__image", "src", parent=item)
            company_url = self._safe_attr(By.CSS_SELECTOR, "a.pvs-entity__path-node", "href", parent=item)
            skills_url = self._safe_attr(By.CSS_SELECTOR, "a[href*='skill-associations']", "href", parent=item)

            date_range = self._parse_date_range(meta)
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
                "employment_type": self._infer_employment_type(title),
                "location_type": None,
                "skills": self._extract_skills_from_item(item),
                "company_id": self._extract_company_id_from_url(company_url),
                "skills_url": skills_url,
            }
            entries.append(entry)

        return entries

    def _extract_education(self) -> List[Dict]:
        section = self._find_section("education")
        if not section:
            return []

        entries = []
        for item in self._list_items(section):
            school = self._safe_text(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']", parent=item)
            degree = self._safe_text(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']", parent=item)
            description = self._safe_text(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']", parent=item)
            logo_url = self._safe_attr(By.CSS_SELECTOR, "img.pvs-entity__image", "src", parent=item)
            school_url = self._safe_attr(By.CSS_SELECTOR, "a.pvs-entity__path-node", "href", parent=item)

            date_range = self._parse_date_range(description)

            entry = {
                "school": school,
                "degree": degree,
                "degree_name": degree,
                "field_of_study": None,
                "duration": description if date_range.duration is None else date_range.duration,
                "school_linkedin_url": school_url,
                "school_logo_url": logo_url,
                "start_date": date_range.start,
                "end_date": date_range.end,
                "school_id": self._extract_company_id_from_url(school_url),
                "description": description,
            }
            entries.append(entry)

        return entries

    def _extract_certifications(self) -> List[Dict]:
        section = self._find_section("licenses_and_certifications")
        if not section:
            return []

        entries = []
        for item in self._list_items(section):
            name = self._safe_text(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']", parent=item)
            issuer = self._safe_text(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']", parent=item)
            issued = self._safe_text(By.CSS_SELECTOR, "span.t-14.t-normal.t-black--light span[aria-hidden='true']", parent=item)

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
            language = self._safe_text(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']", parent=item)
            proficiency = self._safe_text(By.CSS_SELECTOR, "span.t-14.t-normal span[aria-hidden='true']", parent=item)
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
    
    def _save_debug_html(self):
        """Save current page HTML for debugging purposes."""
        try:
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print("DEBUG: Page HTML saved to 'debug_page.html'")
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
        selectors = [
            f"section[id='{section_id}']",
            f"section[data-section='{section_id}']",
            f"section[data-view-name*='{section_id}']",
        ]
        for selector in selectors:
            elements = self._find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements[0]
        return None

    def _list_items(self, section: WebElement) -> List[WebElement]:
        return section.find_elements(By.CSS_SELECTOR, "li.pvs-list__item--line-separated")

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

    def _extract_section_text(self, section_id: str) -> str:
        section = self._find_section(section_id)
        if not section:
            return ""
        return self._safe_text(By.CSS_SELECTOR, "div.inline-show-more-text span[aria-hidden='true']", parent=section)

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

    def _extract_stat_number(self, label: str) -> Optional[int]:
        items = self.driver.find_elements(By.CSS_SELECTOR, "li.inline.t-16.t-black.t-normal")
        for item in items:
            text = item.text.lower()
            if label in text:
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
            skill = self._safe_text(By.CSS_SELECTOR, "span.mr1.t-bold span[aria-hidden='true']", parent=item)
            if skill:
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
        is_current = end_raw is None or end_raw.lower() in ("present", "atual")
        end = None if is_current else self._build_date_dict(end_raw)

        return DateRange(start=start, end=end, is_current=is_current, duration=duration_part)

    def _build_date_dict(self, value: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
        if not value:
            return None
        tokens = value.split()
        if len(tokens) == 2:
            return {"year": int(tokens[1]) if tokens[1].isdigit() else None, "month": tokens[0]}
        if tokens and tokens[0].isdigit():
            return {"year": int(tokens[0]), "month": None}
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