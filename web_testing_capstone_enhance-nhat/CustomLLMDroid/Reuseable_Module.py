import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-insecure-localhost")


class ReusableTestRunner:
    """
    Test runner that executes saved test cases without requiring LLM.
    Uses saved steps and assertions to verify test outcomes.
    """
    
    def __init__(self, web_url: str):
        self.web_url = web_url
        self.test_results = []
        
    def load_test_cases(self, test_file_path: str):
        """Load test cases from JSON file"""
        with open(test_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def execute_action(self, driver, action, selector_type, selector_value, input_value=None):
        """Execute a single test action"""
        try:
            if action == "done":
                return True, "Test completed"
            
            # Map selector types to Selenium locators
            selector_map = {
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME,
                "xpath": By.XPATH,
                "text": By.XPATH
            }
            
            if selector_type not in selector_map:
                return False, f"Unsupported selector type: {selector_type}"
            
            # Convert text selector to xpath
            if selector_type == "text":
                selector_value = f"//*[text()='{selector_value}']"
                by_type = By.XPATH
            else:
                by_type = selector_map[selector_type]
            
            # Wait for element to be present
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((by_type, selector_value))
            )
            
            # Perform action
            if action == "click":
                element.click()
                time.sleep(0.5)  # Small delay after click
                return True, f"Clicked element: {selector_type}={selector_value}"
                
            elif action == "input":
                element.clear()
                element.send_keys(input_value or "")
                return True, f"Input '{input_value}' into {selector_type}={selector_value}"
            
            else:
                return False, f"Unknown action: {action}"
                
        except TimeoutException:
            return False, f"Element not found: {selector_type}={selector_value}"
        except Exception as e:
            return False, f"Error executing action: {str(e)}"
    
    def verify_assertion(self, driver, assertion):
        """Verify a single assertion"""
        try:
            assertion_type = assertion.get("type")
            selector_type = assertion.get("selector_type")
            selector_value = assertion.get("selector_value")
            expected_value = assertion.get("expected_value", "")
            attribute_name = assertion.get("attribute_name", "")
            description = assertion.get("description", "")
            
            # Map selector types
            selector_map = {
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME,
                "xpath": By.XPATH,
                "text": By.XPATH
            }
            
            if selector_type == "text":
                selector_value = f"//*[text()='{selector_value}']"
                by_type = By.XPATH
            elif selector_type in selector_map:
                by_type = selector_map[selector_type]
            else:
                return False, f"Invalid selector type: {selector_type}"
            
            # Execute assertion based on type
            if assertion_type == "element_exists":
                try:
                    driver.find_element(by_type, selector_value)
                    return True, f"✓ {description}"
                except NoSuchElementException:
                    return False, f"✗ {description} - Element not found"
            
            elif assertion_type == "element_not_exists":
                try:
                    driver.find_element(by_type, selector_value)
                    return False, f"✗ {description} - Element should not exist but was found"
                except NoSuchElementException:
                    return True, f"✓ {description}"
            
            elif assertion_type == "text_contains":
                element = driver.find_element(by_type, selector_value)
                actual_text = element.text
                if expected_value in actual_text:
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Expected '{expected_value}' in '{actual_text}'"
            
            elif assertion_type == "text_equals":
                element = driver.find_element(by_type, selector_value)
                actual_text = element.text.strip()
                if actual_text == expected_value:
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Expected '{expected_value}', got '{actual_text}'"
            
            elif assertion_type == "url_contains":
                current_url = driver.current_url
                if expected_value in current_url:
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Expected URL to contain '{expected_value}', got '{current_url}'"
            
            elif assertion_type == "url_equals":
                current_url = driver.current_url
                if current_url == expected_value:
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Expected URL '{expected_value}', got '{current_url}'"
            
            elif assertion_type == "element_visible":
                element = driver.find_element(by_type, selector_value)
                if element.is_displayed():
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Element is not visible"
            
            elif assertion_type == "element_not_visible":
                try:
                    element = driver.find_element(by_type, selector_value)
                    if not element.is_displayed():
                        return True, f"✓ {description}"
                    else:
                        return False, f"✗ {description} - Element should not be visible"
                except NoSuchElementException:
                    return True, f"✓ {description}"
            
            elif assertion_type == "element_enabled":
                element = driver.find_element(by_type, selector_value)
                if element.is_enabled():
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Element is disabled"
            
            elif assertion_type == "element_disabled":
                element = driver.find_element(by_type, selector_value)
                if not element.is_enabled():
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Element should be disabled"
            
            elif assertion_type == "attribute_equals":
                element = driver.find_element(by_type, selector_value)
                actual_value = element.get_attribute(attribute_name)
                if actual_value == expected_value:
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Expected {attribute_name}='{expected_value}', got '{actual_value}'"
            
            elif assertion_type == "attribute_contains":
                element = driver.find_element(by_type, selector_value)
                actual_value = element.get_attribute(attribute_name) or ""
                if expected_value in actual_value:
                    return True, f"✓ {description}"
                else:
                    return False, f"✗ {description} - Expected {attribute_name} to contain '{expected_value}', got '{actual_value}'"
            
            else:
                return False, f"Unknown assertion type: {assertion_type}"
                
        except NoSuchElementException:
            return False, f"✗ {description} - Element not found"
        except Exception as e:
            return False, f"✗ {description} - Error: {str(e)}"
    
    def run_test_case(self, test_case):
        """Run a single test case"""
        test_case_id = test_case.get("test_case_id", "Unknown")
        test_case_title = test_case.get("test_case_title", "Untitled")
        expected_outcome = test_case.get("expected_outcome", "True")
        steps = test_case.get("test_step", test_case.get("steps", []))
        assertions = test_case.get("assertions", [])
        
        print(f"\n{'='*80}")
        print(f"Running Test Case: {test_case_id}")
        print(f"Title: {test_case_title}")
        print(f"Expected Outcome: {expected_outcome}")
        print(f"{'='*80}\n")
        
        driver = webdriver.Chrome(options=options)
        test_result = {
            "test_case_id": test_case_id,
            "test_case_title": test_case_title,
            "expected_outcome": expected_outcome,
            "steps_executed": 0,
            "steps_failed": 0,
            "assertions_passed": 0,
            "assertions_failed": 0,
            "test_passed": False,
            "execution_log": [],
            "assertion_log": []
        }
        
        try:
            # Navigate to the web application
            driver.get(self.web_url)
            time.sleep(1)
            
            # Execute all steps
            print("Executing steps:")
            for i, step in enumerate(steps, 1):
                action = step.get("action")
                selector_type = step.get("selector_type")
                selector_value = step.get("selector_value")
                input_value = step.get("input_value")
                
                success, message = self.execute_action(
                    driver, action, selector_type, selector_value, input_value
                )
                
                test_result["steps_executed"] += 1
                if success:
                    print(f"  Step {i}: ✓ {message}")
                    test_result["execution_log"].append({
                        "step": i,
                        "status": "passed",
                        "message": message
                    })
                else:
                    print(f"  Step {i}: ✗ {message}")
                    test_result["steps_failed"] += 1
                    test_result["execution_log"].append({
                        "step": i,
                        "status": "failed",
                        "message": message
                    })
                    # Don't stop on step failure, continue to see what happens
            
            # Small delay before assertions
            time.sleep(1)
            
            # Verify all assertions
            if assertions:
                print(f"\nVerifying assertions:")
                for i, assertion in enumerate(assertions, 1):
                    passed, message = self.verify_assertion(driver, assertion)
                    
                    if passed:
                        print(f"  Assertion {i}: {message}")
                        test_result["assertions_passed"] += 1
                        test_result["assertion_log"].append({
                            "assertion": i,
                            "status": "passed",
                            "message": message
                        })
                    else:
                        print(f"  Assertion {i}: {message}")
                        test_result["assertions_failed"] += 1
                        test_result["assertion_log"].append({
                            "assertion": i,
                            "status": "failed",
                            "message": message
                        })
            
            # Determine if test passed
            # For success test cases (expected_outcome="True"), all assertions should pass
            # For failure test cases (expected_outcome="False"), we expect specific assertions to pass
            if expected_outcome == "True":
                test_result["test_passed"] = (
                    test_result["steps_failed"] == 0 and
                    test_result["assertions_failed"] == 0 and
                    test_result["assertions_passed"] == len(assertions)
                )
            else:
                # For fail cases, test passes if assertions verify the expected failure
                test_result["test_passed"] = (
                    test_result["assertions_passed"] > 0
                )
            
            # Print summary
            print(f"\n{'='*80}")
            print(f"Test Case: {test_case_id} - {'PASSED' if test_result['test_passed'] else 'FAILED'}")
            print(f"Steps: {test_result['steps_executed']} executed, {test_result['steps_failed']} failed")
            print(f"Assertions: {test_result['assertions_passed']} passed, {test_result['assertions_failed']} failed")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"\n✗ Test execution error: {str(e)}")
            test_result["test_passed"] = False
            test_result["execution_log"].append({
                "step": "error",
                "status": "failed",
                "message": str(e)
            })
        finally:
            driver.quit()
        
        return test_result
    
    def run_all_tests(self, test_file_path: str):
        """Run all test cases from a file"""
        print(f"\n{'#'*80}")
        print(f"Loading test cases from: {test_file_path}")
        print(f"{'#'*80}\n")
        
        test_cases = self.load_test_cases(test_file_path)
        
        if isinstance(test_cases, dict):
            test_cases = [test_cases]
        
        for test_case in test_cases:
            result = self.run_test_case(test_case)
            self.test_results.append(result)
        
        # Print final summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary of all test results"""
        print(f"\n{'#'*80}")
        print(f"TEST EXECUTION SUMMARY")
        print(f"{'#'*80}\n")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["test_passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.2f}%\n")
        
        if failed_tests > 0:
            print("Failed Tests:")
            for result in self.test_results:
                if not result["test_passed"]:
                    print(f"  - {result['test_case_id']}: {result['test_case_title']}")
        
        print(f"\n{'#'*80}\n")
        
        # Save detailed results
        with open("test_execution_report.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        print("Detailed report saved to: test_execution_report.json")


if __name__ == "__main__":
    # Example usage
    web_url = "https://localhost:5000/#/"
    test_file = "TC_LOGIN_001.json"  # Your generated test case file
    
    runner = ReusableTestRunner(web_url)
    runner.run_all_tests(test_file)