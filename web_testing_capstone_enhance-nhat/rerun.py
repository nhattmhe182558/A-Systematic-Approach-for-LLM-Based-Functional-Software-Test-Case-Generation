import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

class TestCaseRunner:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
        self.driver = None
    
    def inspect_json_structure(self, file_path):
        """Inspect the structure of a JSON file for debugging"""
        print(f"\n{'='*80}")
        print(f"Inspecting JSON file: {file_path}")
        print(f"{'='*80}")
        
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                content = f.read()
                print(f"File size: {len(content)} characters")
                print(f"First 200 characters:\n{content[:200]}")
                
                # Try to parse
                f.seek(0)
                data = json.load(f)
                
                print(f"\nParsed type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"Number of items: {len(data)}")
                    if len(data) > 0:
                        print(f"First item type: {type(data[0])}")
                        if isinstance(data[0], dict):
                            print(f"First item keys: {list(data[0].keys())}")
                        elif isinstance(data[0], str):
                            print(f"First item is a string (first 100 chars): {data[0][:100]}")
                elif isinstance(data, dict):
                    print(f"Dictionary keys: {list(data.keys())}")
                elif isinstance(data, str):
                    print(f"String content (first 100 chars): {data[:100]}")
                
                print(f"{'='*80}\n")
                return data
                
        except Exception as e:
            print(f"Error inspecting file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def setup_driver(self):
        """Initialize the Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # Uncomment for headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--allow-insecure-localhost")
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        return self.driver
    
    def trigger_events_on_element(self, driver, elem):
        """Trigger events on element after input"""
        try:
            driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, elem)
        except Exception as e:
            print(f"Warning: Could not trigger events: {e}")
    
    def execute_action(self, driver, action, selector_type=None, selector_value=None, input_value=None):
        """Execute a single action from the test case"""
        log_entry = {
            "action": action,
            "selector_type": selector_type,
            "selector_value": selector_value,
            "input_value": input_value,
            "success": False,
            "error": None,
        }
        
        if not action:
            log_entry["error"] = "No action specified."
            return log_entry

        try:
            if action == "done":
                log_entry["success"] = True
                return log_entry

            selector_map = {
                "id": By.ID,
                "name": By.NAME,
                "class": By.CLASS_NAME,
                "xpath": By.XPATH,
                "text": By.XPATH,
            }

            if selector_type not in selector_map:
                raise ValueError(f"Unsupported selector type: {selector_type}")

            if selector_type == "text":
                selector_value = f"//*[text()='{selector_value}']"

            if action == "upload" and not input_value:
                raise ValueError("Input value (file path) is required for 'upload' action.")

            elem = driver.find_element(selector_map[selector_type], selector_value)

            if action == "click":
                elem.click()
                log_entry["success"] = True

            elif action == "input":
                elem.clear()
                elem.send_keys(input_value or "")
                self.trigger_events_on_element(driver=driver, elem=elem)
                log_entry["success"] = True

            elif action == "upload":
                absolute_file_path = os.path.abspath(input_value)
                if not os.path.exists(absolute_file_path):
                    raise FileNotFoundError(f"Local file not found at path: {absolute_file_path}")
                elem.send_keys(absolute_file_path)
                log_entry["success"] = True

            else:
                raise ValueError(f"Unknown action type: {action}")

        except Exception as e:
            log_entry["error"] = str(e)
            return log_entry

        return log_entry
    
    def rerun_testcase(self, testcase_data, delay=1):
        """Rerun a single test case"""
        # Validate testcase_data structure
        if not isinstance(testcase_data, dict):
            raise TypeError(f"testcase_data must be a dictionary, got {type(testcase_data)}")
        
        if "test_case_info" not in testcase_data:
            raise KeyError("testcase_data missing 'test_case_info' field")
        
        if "execute_log" not in testcase_data:
            raise KeyError("testcase_data missing 'execute_log' field")
        
        test_case_id = testcase_data["test_case_info"].get("test_case_id", "UNKNOWN")
        test_case_title = testcase_data["test_case_info"].get("test_case_title", "UNKNOWN")
        
        print(f"\n{'='*80}")
        print(f"Rerunning Test Case: {test_case_id}")
        print(f"Title: {test_case_title}")
        print(f"{'='*80}")
        
        execute_log = testcase_data["execute_log"]
        new_execute_log = []
        
        # Setup driver and navigate to base URL
        if not self.driver:
            self.setup_driver()
        
        self.driver.get(self.base_url)
        time.sleep(delay)
        
        # Execute each action in the log
        for idx, step in enumerate(execute_log):
            print(f"\nStep {idx + 1}/{len(execute_log)}: {step['action']}")
            if step['selector_type']:
                print(f"  Selector: {step['selector_type']}='{step['selector_value']}'")
            if step['input_value']:
                print(f"  Input: {step['input_value']}")
            
            log_entry = self.execute_action(
                driver=self.driver,
                action=step["action"],
                selector_type=step["selector_type"],
                selector_value=step["selector_value"],
                input_value=step["input_value"]
            )
            
            new_execute_log.append(log_entry)
            
            if log_entry["success"]:
                print(f"  ✓ Success")
            else:
                print(f"  ✗ Failed: {log_entry['error']}")
            
            time.sleep(delay)
        
        # Update testcase data with new execution log
        testcase_data["execute_log"] = new_execute_log
        
        return testcase_data
    
    def rerun_all_testcases(self, result_dict="generated_testcase_action", output_dict="rerun_results", delay=1):
        """Rerun all test cases in the directory structure"""
        os.makedirs(output_dict, exist_ok=True)
        
        total_testcases = 0
        successful_testcases = 0
        failed_testcases = 0
        
        for bp in os.listdir(result_dict):
            bp_path = os.path.join(result_dict, bp)
            if not os.path.isdir(bp_path):
                continue
            
            output_bp_path = os.path.join(output_dict, bp)
            os.makedirs(output_bp_path, exist_ok=True)
            
            for us in os.listdir(bp_path):
                us_path = os.path.join(bp_path, us)
                if not us_path.endswith('.json'):
                    continue
                
                print(f"\n{'#'*80}")
                print(f"Processing file: {us_path}")
                print(f"{'#'*80}")
                
                with open(us_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, str):
                    print(f"Warning: Data is a string, attempting to parse again")
                    data = json.loads(data)
                
                if not isinstance(data, list):
                    print(f"Error: Expected list of test cases, got {type(data)}")
                    continue
                
                rerun_results = []
                
                for idx, testcase in enumerate(data):
                    # Validate testcase structure
                    if isinstance(testcase, str):
                        print(f"Warning: Test case {idx} is a string, attempting to parse")
                        try:
                            testcase = json.loads(testcase)
                        except:
                            print(f"Error: Could not parse test case {idx}")
                            continue
                    
                    if not isinstance(testcase, dict):
                        print(f"Error: Test case {idx} is not a dictionary, got {type(testcase)}")
                        continue
                    
                    if "test_case_info" not in testcase or "execute_log" not in testcase:
                        print(f"Error: Test case {idx} missing required fields")
                        continue
                    total_testcases += 1
                    
                    try:
                        # Rerun the test case
                        updated_testcase = self.rerun_testcase(testcase, delay=delay)
                        rerun_results.append(updated_testcase)
                        
                        # Check if all steps succeeded
                        all_success = all(step["success"] for step in updated_testcase["execute_log"])
                        if all_success:
                            successful_testcases += 1
                        else:
                            failed_testcases += 1
                        
                    except Exception as e:
                        print(f"\n✗ Exception during test case execution: {e}")
                        testcase["rerun_error"] = str(e)
                        rerun_results.append(testcase)
                        failed_testcases += 1
                    
                    # Reset for next test case
                    if self.driver:
                        self.driver.quit()
                        self.driver = None
                
                # Save rerun results
                output_path = os.path.join(output_bp_path, us)
                with open(output_path, "w") as f:
                    json.dump(rerun_results, f, indent=2)
                
                print(f"\nSaved rerun results to: {output_path}")
        
        print(f"\n{'='*80}")
        print(f"RERUN SUMMARY")
        print(f"{'='*80}")
        print(f"Total test cases rerun: {total_testcases}")
        print(f"Successful: {successful_testcases}")
        print(f"Failed: {failed_testcases}")
        print(f"{'='*80}")
        
        if self.driver:
            self.driver.quit()
    
    def rerun_specific_testcase(self, file_path, test_case_index=0, delay=1):
        """Rerun a specific test case from a file"""
        with open(file_path, "r", encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, str):
            print(f"Warning: Data is a string, attempting to parse again")
            data = json.loads(data)
        
        if not isinstance(data, list):
            print(f"Error: Expected list of test cases, got {type(data)}")
            return None
        
        if test_case_index >= len(data):
            print(f"Error: Test case index {test_case_index} out of range. File has {len(data)} test cases.")
            return None
        
        testcase = data[test_case_index]
        
        # Validate testcase structure
        if isinstance(testcase, str):
            print(f"Warning: Test case is a string, attempting to parse")
            try:
                testcase = json.loads(testcase)
            except:
                print(f"Error: Could not parse test case")
                return None
        
        try:
            updated_testcase = self.rerun_testcase(testcase, delay=delay)
            return updated_testcase
        finally:
            if self.driver:
                self.driver.quit()


# Example usage
if __name__ == "__main__":
    runner = TestCaseRunner(base_url="https://localhost:5000/#/")
    
    # Debug: Inspect a specific file first
    print("Inspecting JSON structure...")
    sample_file = "generated_testcase_action/BP1/UC-COM-01.json"  # Update with your actual file path
    # Uncomment the line below to inspect file structure
    # runner.inspect_json_structure(sample_file)
    
    # Option 1: Rerun all test cases
    runner.rerun_all_testcases(
        result_dict="generated_testcase_action",
        output_dict="rerun_results",
        delay=1  # Wait 1 second between actions
    )
    
    # Option 2: Rerun a specific test case
    # runner.setup_driver()
    # result = runner.rerun_specific_testcase(
    #     file_path="generated_testcase_action/BP1/UC-COM-01.json",
    #     test_case_index=0,
    #     delay=1
    # )
    # print("\nRerun result:", json.dumps(result, indent=2))