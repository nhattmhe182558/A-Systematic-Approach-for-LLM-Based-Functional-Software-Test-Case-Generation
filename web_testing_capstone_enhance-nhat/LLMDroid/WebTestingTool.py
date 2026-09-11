from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from LLMDroid.dataObject import WebPage, WebElement
import time
from selenium.webdriver.common.by import By

class WebTestingTool:    
    def __init__(self, start_url: str, headless: bool = False):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.start_url = start_url
        self.driver.get(start_url)
        self.wait = WebDriverWait(self.driver, 10)
    
    def get_current_page(self, page_id: int) -> WebPage:
        time.sleep(1)  # Wait for page to stabilize
        
        elements = []
        
        # Find all interactive elements
        try:
            all_elements = self.driver.find_elements(By.XPATH, 
                "//*[@href or @onclick or self::button or self::input or self::a]")
            
            for idx, elem in enumerate(all_elements[:50]):  # Limit to 50 elements
                try:
                    element_data = WebElement(
                        id=f"elem_{idx}",
                        tag_name=elem.tag_name,
                        element_id=elem.get_attribute('id') or '',
                        classes=elem.get_attribute('class') or '',
                        text=elem.text[:100] if elem.text else '',
                        clickable=elem.is_enabled() and elem.is_displayed(),
                        href=elem.get_attribute('href') or '',
                        input_type=elem.get_attribute('type') or '',
                        xpath=f"//*[@id='{elem.get_attribute('id')}']" if elem.get_attribute('id') else ''
                    )
                    elements.append(element_data)
                except:
                    continue
        except Exception as e:
            print(f"Error Getting elements: {e}")
        
        return WebPage(
            page_id=page_id,
            url=self.driver.current_url,
            title=self.driver.title,
            elements=elements
        )
    
    def execute_random_action(self) -> bool:
        try:
            clickable = self.driver.find_elements(By.XPATH, 
                "//*[self::button or self::a or @onclick]")
            
            if clickable:
                import random
                elem = random.choice(clickable[:20])
                if elem.is_displayed() and elem.is_enabled():
                    elem.click()
                    time.sleep(2)
                    return True
        except Exception as e:
            print(f"Error Random action: {e}")
        
        return False
    
    def execute_action_by_id(self, element_id: str, action_type: str, input_text: str = ""):
        try:
            if element_id:
                elem = self.driver.find_element(By.ID, element_id)
            else:
                return False
            
            if action_type == "click":
                elem.click()
            elif action_type == "input" and input_text:
                elem.clear()
                elem.send_keys(input_text)
            
            time.sleep(2)
            return True
        except Exception as e:
            print(f"[Error] Executing action: {e}")
            return False
    
    def navigate_to_url(self, url: str):
        try:
            self.driver.get(url)
            time.sleep(2)
        except Exception as e:
            print(f"[Error] Navigation: {e}")
    
    def restart(self):
        self.driver.get(self.start_url)
        time.sleep(2)
    
    def close(self):
        self.driver.quit()
