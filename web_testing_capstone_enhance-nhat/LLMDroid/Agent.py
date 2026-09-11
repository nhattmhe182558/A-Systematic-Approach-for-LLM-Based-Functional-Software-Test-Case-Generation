import json
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urljoin, urlparse
import google.generativeai as genai

# Selenium imports for REAL browser automation
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INFO = "info"


@dataclass
class TestStep:
    step_number: int
    action: str
    status: str
    details: str
    timestamp: str


@dataclass
class TestCase:
    id: str
    functionality: str
    description: str
    timestamp: str
    page_url: str = ""
    status: str = "pending"
    steps: List[TestStep] = field(default_factory=list)
    error: Optional[str] = None
    coverage: Optional[Dict] = None


@dataclass
class PageNode:
    """Represents a discovered page in the application"""
    url: str
    title: str
    visited: bool = False
    test_count: int = 0
    elements_count: int = 0
    links_to: List[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RealBrowserLLMTester:
    """
    Multi-Page Dynamic Test Generation with Real Browser Testing
    
    Enhanced features:
    - Explores multiple pages automatically
    - Discovers application sitemap
    - Generates tests for each discovered page
    - Tracks visited pages and prevents loops
    - Prioritizes unexplored pages
    """
    
    def __init__(self, website_url: str, gemini_api_key: str, test_duration: int = 300, 
                 headless: bool = False, max_pages: int = 10, max_depth: int = 3):
        self.website_url = website_url
        self.base_domain = urlparse(website_url).netloc
        self.test_duration = test_duration
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.test_results: List[TestCase] = []
        self.current_test: Optional[TestCase] = None
        self.headless = headless
        
        # Initialize Gemini AI
        genai.configure(api_key=gemini_api_key)
        self.llm_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Initialize Selenium WebDriver
        self.driver = None
        self.wait = None
        self.init_browser()
        
        # Load input context (credentials, test data, etc.)
        self.input_data = self.load_input_data()
        
        # Multi-page exploration state
        self.page_map: Dict[str, PageNode] = {}  # URL -> PageNode
        self.visited_urls: Set[str] = set()
        self.pending_urls: List[tuple] = []  # List of (url, depth)
        self.tested_functionalities: Set[str] = set()
        
        print("="*80)
        print("🌐 MULTI-PAGE DYNAMIC TEST GENERATION with Real Browser")
        print("="*80)
        print(f"Website: {self.website_url}")
        print(f"Browser: Chrome {'(Headless)' if headless else '(Visible)'}")
        print(f"AI Model: Gemini Flash")
        print(f"Test Duration: {self.test_duration}s")
        print(f"Max Pages to Explore: {self.max_pages}")
        print(f"Max Exploration Depth: {self.max_depth}")
        print(f"Available Test Data: {len(self.input_data)} entries")
        print("="*80)
        print()
    
    def init_browser(self):
        """Initialize Selenium WebDriver with Chrome"""
        try:
            options = webdriver.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--allow-insecure-localhost')
            
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 10)
            
            print("✅ Browser initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}")
            print("\n💡 Make sure you have Chrome and ChromeDriver installed:")
            print("   pip install selenium")
            print("   Download ChromeDriver: https://chromedriver.chromium.org/")
            raise
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL to prevent duplicates"""
        if not url:
            return ""
        
        # Handle relative URLs
        if url.startswith('/'):
            url = urljoin(self.website_url, url)
        elif not url.startswith('http'):
            return ""
        
        # Remove fragment and trailing slash
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        
        # Add query string if present
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be explored"""
        if not url:
            return False
        
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != self.base_domain:
            return False
        
        # Skip common non-page URLs
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.zip', '.exe', '.css', '.js']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
        
        # Skip logout, delete, etc.
        skip_keywords = ['logout', 'signout', 'delete', 'remove']
        if any(keyword in url.lower() for keyword in skip_keywords):
            return False
        
        return True
    
    def discover_links_on_page(self) -> List[str]:
        """Discover all valid links on current page"""
        discovered_links = []
        
        try:
            # Find all links
            link_elements = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link_elem in link_elements:
                try:
                    href = link_elem.get_attribute("href")
                    if href:
                        normalized = self.normalize_url(href)
                        if self.is_valid_url(normalized):
                            discovered_links.append(normalized)
                except:
                    continue
            
            # Remove duplicates
            discovered_links = list(set(discovered_links))
            
        except Exception as e:
            print(f"    ⚠️  Error discovering links: {e}")
        
        return discovered_links
    
    def add_page_to_map(self, url: str, depth: int = 0) -> PageNode:
        """Add or update page in the site map"""
        normalized_url = self.normalize_url(url)
        
        if normalized_url in self.page_map:
            return self.page_map[normalized_url]
        
        page_node = PageNode(
            url=normalized_url,
            title=self.driver.title if normalized_url == self.driver.current_url else "Unknown"
        )
        
        self.page_map[normalized_url] = page_node
        
        return page_node
    
    def navigate_to_page(self, url: str) -> bool:
        """Navigate to a specific page"""
        try:
            print(f"\n🔗 Navigating to: {url}")
            self.driver.get(url)
            time.sleep(2)  # Wait for page load
            
            # Check if page loaded successfully
            if "error" in self.driver.title.lower() or len(self.driver.page_source) < 100:
                print(f"    ⚠️  Page failed to load properly")
                return False
            
            print(f"    ✅ Page loaded: {self.driver.title}")
            return True
            
        except Exception as e:
            print(f"    ❌ Navigation failed: {e}")
            return False
    
    def explore_page(self, url: str, depth: int) -> PageNode:
        """Explore a single page and discover its elements and links"""
        print(f"\n{'='*80}")
        print(f"🔍 EXPLORING PAGE (Depth {depth})")
        print(f"{'='*80}")
        
        # Navigate to page
        if not self.navigate_to_page(url):
            return None
        
        # Add to map
        current_page = self.add_page_to_map(url, depth)
        current_page.visited = True
        current_page.title = self.driver.title
        self.visited_urls.add(url)
        
        # Discover page elements
        page_info = self.discover_page_elements()
        current_page.elements_count = len(page_info.get('elements', []))
        
        print(f"📊 Page Analysis:")
        print(f"    URL: {url}")
        print(f"    Title: {current_page.title}")
        print(f"    Elements found: {current_page.elements_count}")
        
        # Discover links on this page
        if depth < self.max_depth:
            discovered_links = self.discover_links_on_page()
            current_page.links_to = discovered_links
            
            print(f"    Links discovered: {len(discovered_links)}")
            
            # Add new links to pending queue
            new_links = 0
            for link in discovered_links:
                if link not in self.visited_urls and link not in [url for url, _ in self.pending_urls]:
                    self.pending_urls.append((link, depth + 1))
                    new_links += 1
            
            if new_links > 0:
                print(f"    ➕ Added {new_links} new pages to explore")
        
        return current_page
    
    def check_website_available(self) -> bool:
        """Check if the website is actually running"""
        try:
            print(f"🔎 Checking if website is available at: {self.website_url}")
            self.driver.get(self.website_url)
            time.sleep(2)
            
            if "error" in self.driver.title.lower() or len(self.driver.page_source) < 100:
                return False
            
            print(f"✅ Website is accessible! Page title: {self.driver.title}")
            return True
            
        except Exception as e:
            print(f"❌ Cannot access website: {e}")
            return False
    
    def load_input_data(self, filepath: str = "input_context.json") -> Dict:
        """Load test data (credentials, files, etc.) from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data_list = json.load(f)
                
            # Convert list to dictionary organized by role/function
            organized_data = {
                "credentials": {},
                "files": {},
                "other": {}
            }
            
            for item in data_list:
                role = item.get("Role", "").lower()
                func = item.get("Function", "").lower()
                input_val = item.get("Input", "")
                
                # Organize credentials
                if "login" in func or "signin" in func:
                    if role not in organized_data["credentials"]:
                        organized_data["credentials"][role] = {}
                    
                    if "username" in input_val.lower() or "email" in input_val.lower():
                        organized_data["credentials"][role]["username"] = input_val.split(":")[-1].strip()
                    elif "password" in input_val.lower():
                        organized_data["credentials"][role]["password"] = input_val.split(":")[-1].strip()
                
                # Organize file uploads
                elif "upload" in func or "file" in input_val.lower():
                    organized_data["files"][role] = input_val
                
                else:
                    organized_data["other"][func] = input_val
            
            print(f"📋 Loaded test data:")
            print(f"   - Credentials: {list(organized_data['credentials'].keys())}")
            print(f"   - Files: {list(organized_data['files'].keys())}")
            
            return organized_data
            
        except FileNotFoundError:
            print("⚠️  No input_context.json found, using defaults")
            return {
                "credentials": {
                    "teacher": {
                        "username": "teacher@gmail.com",
                        "password": "pass"
                    }
                },
                "files": {},
                "other": {}
            }
    
    def call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini LLM with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.llm_model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"⚠️  LLM call failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return f"Error: Unable to get LLM response"
        return ""
    
    def log_test_step(self, step: str, status: str, details: str):
        """Log a test step with timestamp"""
        if not self.current_test:
            return
        
        step_number = len(self.current_test.steps) + 1
        timestamp = datetime.now().isoformat()
        
        test_step = TestStep(
            step_number=step_number,
            action=step,
            status=status,
            details=details,
            timestamp=timestamp
        )
        
        self.current_test.steps.append(test_step)
        
        status_symbol = {
            "success": "✓",
            "failed": "✗",
            "running": "⟳",
            "info": "ℹ"
        }.get(status, "•")
        
        print(f"  [{status_symbol}] Step {step_number}: {step}")
        print(f"      {details}")
        print()
    
    def discover_page_elements(self) -> Dict:
        """Discover actual elements on the current page"""
        try:
            page_info = {
                "url": self.driver.current_url,
                "title": self.driver.title,
                "elements": []
            }
            
            element_types = [
                (By.TAG_NAME, "input"),
                (By.TAG_NAME, "button"),
                (By.TAG_NAME, "a"),
                (By.TAG_NAME, "select"),
                (By.TAG_NAME, "textarea"),
                (By.TAG_NAME, "form")
            ]
            
            for by, tag in element_types:
                try:
                    elements = self.driver.find_elements(by, tag)
                    for idx, elem in enumerate(elements[:30]):
                        try:
                            if elem.is_displayed():
                                elem_info = {
                                    "type": tag,
                                    "id": elem.get_attribute("id") or f"{tag}_{idx}",
                                    "name": elem.get_attribute("name") or "",
                                    "class": elem.get_attribute("class") or "",
                                    "text": elem.text[:50] if elem.text else "",
                                    "placeholder": elem.get_attribute("placeholder") or "",
                                    "value": elem.get_attribute("value") or "",
                                    "href": elem.get_attribute("href") if tag == "a" else "",
                                    "type_attr": elem.get_attribute("type") or ""
                                }
                                page_info["elements"].append(elem_info)
                        except:
                            continue
                except:
                    continue
            
            return page_info
            
        except Exception as e:
            print(f"⚠️  Error discovering elements: {e}")
            return {"url": "unknown", "title": "unknown", "elements": []}
    
    def llm_generate_test_cases(self, page_info: Dict) -> List[Dict]:
        """Use LLM to generate test cases based on discovered page elements"""
        
        # Create concise element summary
        elements_summary = []
        for elem in page_info.get('elements', [])[:25]:
            elem_desc = f"- {elem['type']}"
            if elem.get('id'):
                elem_desc += f" id='{elem['id']}'"
            if elem.get('name'):
                elem_desc += f" name='{elem['name']}'"
            if elem.get('text'):
                elem_desc += f" text='{elem['text'][:30]}'"
            if elem.get('placeholder'):
                elem_desc += f" placeholder='{elem['placeholder'][:30]}'"
            if elem.get('type_attr'):
                elem_desc += f" type='{elem['type_attr']}'"
            elements_summary.append(elem_desc)
        
        if not elements_summary:
            print("    ⚠️  No elements found to generate tests")
            return self.get_fallback_test_cases()
        
        prompt = f"""You are an expert QA engineer analyzing a web page to generate test cases.

Page Title: {page_info.get('title', 'Unknown')}
URL: {page_info.get('url', 'Unknown')}

Available Elements:
{chr(10).join(elements_summary)}

Based on these REAL elements, generate 2-3 test cases that should be executed for THIS PAGE ONLY.

For each test case, provide:
1. Test name (concise)
2. Description (what functionality to test)
3. Steps to execute
4. Priority (high/medium/low)
5. Required data (if needs login, specify role; if needs file, specify type)

Return as JSON array:
[
  {{
    "name": "Test Login Functionality",
    "description": "Verify user can login with valid credentials",
    "steps": ["Navigate to login", "Enter username", "Enter password", "Click submit"],
    "priority": "high",
    "requires_data": {{"type": "credentials", "role": "teacher"}}
  }}
]

Focus on:
- Forms (login, registration, data entry)
- Navigation (links, buttons)
- Interactive elements (dropdowns, checkboxes)
- File uploads
- Search functionality

Return ONLY valid JSON array, no markdown or explanation."""

        llm_response = self.call_llm(prompt)
        
        if not llm_response or "Error" in llm_response:
            print(f"    ⚠️  LLM returned no valid response")
            return self.get_fallback_test_cases()
        
        try:
            # Extract JSON from response
            json_start = llm_response.find('[')
            json_end = llm_response.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                test_cases = json.loads(json_str)
                
                # Validate test cases structure
                if not isinstance(test_cases, list) or len(test_cases) == 0:
                    print(f"    ⚠️  Invalid test cases format")
                    return self.get_fallback_test_cases()
                
                # Ensure all required fields exist
                validated_tests = []
                for tc in test_cases:
                    if isinstance(tc, dict) and 'name' in tc and 'description' in tc:
                        # Set defaults for missing fields
                        tc.setdefault('steps', ['Execute test'])
                        tc.setdefault('priority', 'medium')
                        tc.setdefault('requires_data', None)
                        validated_tests.append(tc)
                
                if validated_tests:
                    return validated_tests
                else:
                    return self.get_fallback_test_cases()
                    
        except json.JSONDecodeError as e:
            print(f"    ⚠️  Failed to parse JSON: {e}")
            return self.get_fallback_test_cases()
        except Exception as e:
            print(f"    ⚠️  Error processing test cases: {e}")
            return self.get_fallback_test_cases()
    
    def get_fallback_test_cases(self) -> List[Dict]:
        """Return basic fallback test cases when LLM fails"""
        print("    💡 Using fallback test cases")
        return [
            {
                "name": "Test Page Navigation",
                "description": "Verify page loads and basic navigation works",
                "steps": ["Check title", "Verify elements visible"],
                "priority": "high",
                "requires_data": None
            }
        ]
    
    # [Previous helper methods: create_smart_strategy, llm_create_test_strategy, 
    # get_fallback_strategy, find_element_flexible, execute_test_action remain the same]
    
    def create_smart_strategy(self, test_case: Dict, page_info: Dict) -> Dict:
        """Create test strategy using element analysis"""
        elements = page_info.get('elements', [])
        test_name = test_case.get('name', '').lower()
        
        # Get test data if needed
        test_data = {}
        requires_data = test_case.get('requires_data')
        if requires_data and isinstance(requires_data, dict):
            req_type = requires_data.get('type', '')
            if req_type == 'credentials':
                role = requires_data.get('role', '')
                credentials = self.input_data.get('credentials', {})
                if role in credentials:
                    test_data = credentials[role]
        
        actions = []
        
        # Login test strategy
        if 'login' in test_name or 'signin' in test_name:
            print("    🎯 Detected LOGIN test")
            
            username_field = next((e for e in elements if e.get('type') == 'input' and 
                                  any(term in (e.get('id', '') + e.get('name', '') + e.get('placeholder', '')).lower() 
                                      for term in ['user', 'email', 'login'])), None)
            
            password_field = next((e for e in elements if e.get('type') == 'input' and 
                                  e.get('type_attr') == 'password'), None)
            
            submit_button = next((e for e in elements if e.get('type') in ['button', 'input'] and 
                                 any(term in (e.get('text', '') + e.get('value', '') + e.get('id', '')).lower() 
                                     for term in ['login', 'signin', 'submit'])), None)
            
            if username_field:
                actions.append({
                    "step": "Enter username",
                    "element_selector": {"type": "id" if username_field.get('id') else "name", 
                                       "value": username_field.get('id') or username_field.get('name')},
                    "action_type": "input",
                    "input_value": test_data.get('username', 'test@example.com'),
                    "wait_after": 0.5
                })
            
            if password_field:
                actions.append({
                    "step": "Enter password",
                    "element_selector": {"type": "id" if password_field.get('id') else "name",
                                       "value": password_field.get('id') or password_field.get('name')},
                    "action_type": "input",
                    "input_value": test_data.get('password', 'password123'),
                    "wait_after": 0.5
                })
            
            if submit_button:
                actions.append({
                    "step": "Click login button",
                    "element_selector": {"type": "id" if submit_button.get('id') else "name",
                                       "value": submit_button.get('id') or submit_button.get('name') or 'login-btn'},
                    "action_type": "click",
                    "wait_after": 2
                })
        
        if actions:
            return {
                "actions": actions,
                "expected_outcome": f"{test_name} should complete successfully",
                "validation": "Check for expected page changes"
            }
        
        return self.get_fallback_strategy(page_info)
    
    def llm_create_test_strategy(self, test_case: Dict, page_info: Dict) -> Dict:
        """Create detailed test execution strategy"""
        strategy = self.create_smart_strategy(test_case, page_info)
        if strategy and strategy.get('actions'):
            return strategy
        return self.get_fallback_strategy(page_info)
    
    def get_fallback_strategy(self, page_info: Dict = None) -> Dict:
        """Return basic fallback strategy"""
        return {
            "actions": [{
                "step": "Observe page",
                "element_selector": {"type": "xpath", "value": "//body"},
                "action_type": "click",
                "wait_after": 1
            }],
            "expected_outcome": "Page remains stable",
            "validation": "No errors"
        }
    
    def find_element_flexible(self, selector: Dict) -> Optional[any]:
        """Find element using flexible selectors"""
        try:
            sel_type = selector.get("type", "id")
            sel_value = selector.get("value", "")
            
            if not sel_value:
                return None
            
            strategies = []
            if sel_type == "id":
                strategies = [(By.ID, sel_value), (By.XPATH, f"//*[contains(@id, '{sel_value}')]")]
            elif sel_type == "name":
                strategies = [(By.NAME, sel_value), (By.XPATH, f"//*[contains(@name, '{sel_value}')]")]
            elif sel_type == "text":
                strategies = [(By.XPATH, f"//*[contains(text(), '{sel_value}')]")]
            
            for by, value in strategies:
                try:
                    element = self.wait.until(EC.presence_of_element_located((by, value)))
                    if element.is_displayed():
                        return element
                except:
                    continue
            
            return None
        except:
            return None
    
    def execute_test_action(self, action: Dict) -> bool:
        """Execute a single test action"""
        try:
            step = action.get("step", "Unknown step")
            element_selector = action.get("element_selector", {})
            action_type = action.get("action_type", "click")
            input_value = action.get("input_value", "")
            wait_after = action.get("wait_after", 1)
            
            self.log_test_step(step, "running", f"Action: {action_type}")
            
            element = self.find_element_flexible(element_selector)
            if not element:
                self.log_test_step(step, "failed", "Element not found")
                return False
            
            if action_type == "input":
                element.clear()
                element.send_keys(input_value)
                self.log_test_step(step, "success", f"Entered: {input_value}")
            elif action_type == "click":
                element.click()
                self.log_test_step(step, "success", "Clicked successfully")
            
            time.sleep(wait_after)
            return True
        except Exception as e:
            self.log_test_step(action.get("step", "Unknown"), "failed", f"Error: {str(e)}")
            return False
    
    def execute_generated_test(self, test_case_def: Dict, page_info: Dict) -> TestCase:
        """Execute a generated test case"""
        test_id = f"TC_{int(time.time())}_{random.randint(1000, 9999)}"
        
        test_case = TestCase(
            id=test_id,
            functionality=test_case_def.get('name', 'Unknown Test'),
            description=test_case_def.get('description', 'No description'),
            page_url=self.driver.current_url,
            timestamp=datetime.now().isoformat()
        )
        
        self.current_test = test_case
        self.test_results.append(test_case)
        
        print("\n" + "="*80)
        print(f"🧪 EXECUTING TEST: {test_case_def.get('name')}")
        print(f"📄 Page: {test_case.page_url}")
        print("="*80)
        
        try:
            strategy = self.llm_create_test_strategy(test_case_def, page_info)
            actions = strategy.get('actions', [])
            
            if not actions:
                raise Exception("No actions in strategy")
            
            all_success = all(self.execute_test_action(action) for action in actions)
            
            test_case.status = "success" if all_success else "failed"
            if not all_success:
                test_case.error = "Action execution failed"
            
            print(f"\n{'✅ TEST PASSED' if all_success else '❌ TEST FAILED'}")
            
        except Exception as e:
            test_case.status = "failed"
            test_case.error = str(e)
            print(f"\n❌ TEST FAILED: {e}")
        
        return test_case
    
    def run_all_tests(self):
        """Main multi-page exploration and testing loop"""
        
        if not self.check_website_available():
            print("\n⚠️  WEBSITE NOT ACCESSIBLE")
            self.cleanup()
            return
        
        start_time = time.time()
        
        print("\n🚀 " * 40)
        print("MULTI-PAGE TEST DISCOVERY & EXECUTION")
        print("🚀 " * 40)
        
        # Initialize exploration with home page
        self.pending_urls.append((self.website_url, 0))
        
        pages_explored = 0
        
        # Main exploration loop
        while self.pending_urls and pages_explored < self.max_pages:
            if time.time() - start_time > self.test_duration:
                print(f"\n⏰ Time limit reached ({self.test_duration}s)")
                break
            
            # Get next page to explore
            current_url, depth = self.pending_urls.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            pages_explored += 1
            
            print(f"\n{'#'*80}")
            print(f"📍 PAGE {pages_explored}/{self.max_pages}")
            print(f"{'#'*80}")
            
            # Explore the page
            page_node = self.explore_page(current_url, depth)
            
            if not page_node:
                print("⚠️  Failed to explore page, skipping...")
                continue
            
            # Generate tests for this page
            print(f"\n🤖 Generating test cases for: {page_node.title}")
            page_info = self.discover_page_elements()
            test_cases = self.llm_generate_test_cases(page_info)
            
            if not test_cases:
                print("⚠️  No test cases generated for this page")
                continue
            
            print(f"✅ Generated {len(test_cases)} test cases")
            
            # Execute tests for this page
            for idx, test_def in enumerate(test_cases, 1):
                print(f"\n{'>'*80}")
                print(f"Test {idx}/{len(test_cases)} on page: {page_node.title}")
                print(f"{'>'*80}")
                
                result = self.execute_generated_test(test_def, page_info)
                page_node.test_count += 1
                
                # Check time limit
                if time.time() - start_time > self.test_duration:
                    print(f"\n⏰ Time limit reached during testing")
                    break
            
            # Show exploration progress
            print(f"\n📊 Exploration Progress:")
            print(f"    Pages explored: {pages_explored}/{self.max_pages}")
            print(f"    Pages pending: {len(self.pending_urls)}")
            print(f"    Tests executed: {len(self.test_results)}")
            print(f"    Time elapsed: {int(time.time() - start_time)}s / {self.test_duration}s")
        
        # Final summary
        self.print_exploration_summary()
        self.print_test_summary()
        self.cleanup()
    
    def print_exploration_summary(self):
        """Print page exploration summary"""
        print("\n" + "="*80)
        print("🗺️  SITE MAP - DISCOVERED PAGES")
        print("="*80)
        
        for idx, (url, page) in enumerate(self.page_map.items(), 1):
            status = "✅" if page.visited else "⏳"
            print(f"{status} {idx}. {page.title}")
            print(f"    URL: {url}")
            print(f"    Elements: {page.elements_count} | Tests: {page.test_count} | Links: {len(page.links_to)}")
            
            if page.links_to and len(page.links_to) <= 3:
                print(f"    Links to: {', '.join([urlparse(l).path for l in page.links_to[:3]])}")
            elif page.links_to:
                print(f"    Links to: {len(page.links_to)} other pages")
            print()
        
        print(f"Total pages discovered: {len(self.page_map)}")
        print(f"Pages fully explored: {sum(1 for p in self.page_map.values() if p.visited)}")
        print("="*80)
    
    def print_test_summary(self):
        """Print test execution summary"""
        total = len(self.test_results)
        if total == 0:
            return
            
        success = sum(1 for t in self.test_results if t.status == "success")
        failed = total - success
        
        # Group tests by page
        tests_by_page = {}
        for test in self.test_results:
            page_url = test.page_url
            if page_url not in tests_by_page:
                tests_by_page[page_url] = []
            tests_by_page[page_url].append(test)
        
        print("\n" + "="*80)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*80)
        print(f"Total Tests Executed: {total}")
        print(f"✅ Passed: {success} ({success/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Pages Tested: {len(tests_by_page)}")
        print("="*80)
        
        # Show tests by page
        print("\n📄 Tests by Page:")
        for page_url, tests in tests_by_page.items():
            page_title = next((p.title for p in self.page_map.values() if p.url == page_url), "Unknown")
            page_success = sum(1 for t in tests if t.status == "success")
            page_total = len(tests)
            
            print(f"\n  {page_title}")
            print(f"  URL: {page_url}")
            print(f"  Tests: {page_success}/{page_total} passed")
            
            for test in tests:
                status_icon = "✅" if test.status == "success" else "❌"
                print(f"    {status_icon} {test.functionality}")
                if test.status == "failed" and test.error:
                    print(f"       Error: {test.error}")
        
        print("\n" + "="*80)
        
        if failed > 0:
            print("\n❌ Failed Tests Summary:")
            for test in self.test_results:
                if test.status == "failed":
                    print(f"  - [{urlparse(test.page_url).path}] {test.functionality}")
                    print(f"    Error: {test.error}")
    
    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            print("\n🧹 Cleaning up browser...")
            self.driver.quit()
            print("✅ Browser closed")
    
    def export_results(self, filename: str = None):
        """Export test results and site map to JSON"""
        if filename is None:
            filename = f"multi_page_test_results_{int(time.time())}.json"
        
        export_data = {
            "test_config": {
                "website_url": self.website_url,
                "timestamp": datetime.now().isoformat(),
                "browser": "Chrome",
                "test_mode": "Multi-Page Dynamic Generation",
                "max_pages": self.max_pages,
                "max_depth": self.max_depth
            },
            "site_map": {
                "total_pages": len(self.page_map),
                "pages_explored": sum(1 for p in self.page_map.values() if p.visited),
                "pages": [
                    {
                        "url": url,
                        "title": page.title,
                        "visited": page.visited,
                        "elements_count": page.elements_count,
                        "test_count": page.test_count,
                        "links_to": page.links_to,
                        "discovered_at": page.discovered_at
                    }
                    for url, page in self.page_map.items()
                ]
            },
            "test_summary": {
                "total": len(self.test_results),
                "success": sum(1 for t in self.test_results if t.status == "success"),
                "failed": sum(1 for t in self.test_results if t.status == "failed"),
                "pages_tested": len(set(t.page_url for t in self.test_results))
            },
            "test_results": [
                {
                    "id": t.id,
                    "page_url": t.page_url,
                    "functionality": t.functionality,
                    "description": t.description,
                    "status": t.status,
                    "timestamp": t.timestamp,
                    "steps": [
                        {
                            "step_number": s.step_number,
                            "action": s.action,
                            "status": s.status,
                            "details": s.details,
                            "timestamp": s.timestamp
                        }
                        for s in t.steps
                    ],
                    "error": t.error
                }
                for t in self.test_results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n💾 Results exported to: {filename}")
        
        # Also export a simplified site map
        sitemap_file = f"sitemap_{int(time.time())}.json"
        sitemap_data = {
            "discovered_at": datetime.now().isoformat(),
            "base_url": self.website_url,
            "pages": [
                {
                    "url": url,
                    "title": page.title,
                    "elements": page.elements_count,
                    "links": len(page.links_to)
                }
                for url, page in self.page_map.items() if page.visited
            ]
        }
        
        with open(sitemap_file, 'w') as f:
            json.dump(sitemap_data, f, indent=2)
        
        print(f"💾 Site map exported to: {sitemap_file}")


# Main execution
if __name__ == "__main__":
    import sys
    
    print("="*80)
    print("🌐 MULTI-PAGE DYNAMIC WEB TESTING SYSTEM")
    print("="*80)
    print()
    print("This system will:")
    print("1. 🔍 Crawl your web application (multiple pages)")
    print("2. 🗺️  Build a site map of discovered pages")
    print("3. 🤖 Generate test cases for each page using AI")
    print("4. 🧪 Execute tests on all discovered pages")
    print("5. 📊 Provide comprehensive coverage report")
    print()
    print("="*80)
    print()
    
    # Configuration
    WEBSITE_URL = "https://localhost:5000/#/"
    GEMINI_API_KEY = "AIzaSyBiBThJO9Dvk3WLUujP5zj7xBJDTzylvzM"
    TEST_DURATION = 600  # 10 minutes for multi-page exploration
    MAX_PAGES = 10  # Maximum pages to explore
    MAX_DEPTH = 3  # Maximum depth for link following
    
    if len(sys.argv) > 1:
        WEBSITE_URL = sys.argv[1]
    if len(sys.argv) > 2:
        MAX_PAGES = int(sys.argv[2])
    
    print(f"🎯 Target Website: {WEBSITE_URL}")
    print(f"📄 Max Pages: {MAX_PAGES}")
    print(f"🔗 Max Depth: {MAX_DEPTH}")
    print(f"⏱️  Test Duration: {TEST_DURATION}s")
    print()
    print("⚠️  IMPORTANT: Make sure your web application is running!")
    print()
    print("💡 Usage: python Agent.py [website_url] [max_pages]")
    print("   Example: python Agent.py http://localhost:3000 15")
    print()
    
    try:
        tester = RealBrowserLLMTester(
            website_url=WEBSITE_URL,
            gemini_api_key=GEMINI_API_KEY,
            test_duration=TEST_DURATION,
            headless=False,
            max_pages=MAX_PAGES,
            max_depth=MAX_DEPTH
        )
        
        tester.run_all_tests()
        tester.export_results()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        if 'tester' in locals():
            tester.cleanup()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        if 'tester' in locals():
            tester.cleanup()