import time
import json
import base64
from bs4 import BeautifulSoup
from LLMCaller import LLMCaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from Prompt import *
import re
import os
from Schemas import *
from pprint import pprint
from difflib import unified_diff
from tqdm import tqdm
options = Options()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-insecure-localhost")

class TestAgent:
    def __init__(self, web_url:str, api_keys:list[str], input_context:str, success_tc : str, output_success_step: str = "success_step.json", output_full_log: str = "full_log.json"):
        self.web_url = web_url
        self.model = LLMCaller(api_keys=api_keys)
        self.input_context = self.load_json(input_context)
        self.output_success_step = output_success_step
        self.output_full_log = output_full_log
        self.object_log = []
        try:
            self.long_term_mem = self.load_json(success_tc)
        except:
            self.long_term_mem = []
        
        # Create screenshot directory
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

    def load_json(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def extract_testcase(self,tcs_path = "mutation_test_case"):
        bussiness_process_dict = {}
        for business_process in os.listdir(tcs_path):
            business_process_path = os.path.join(tcs_path, business_process)

            bussiness_process_dict[business_process] = {}

            for tc in os.listdir(business_process_path):
                tc_path = os.path.join(business_process_path, tc)
                with open(tc_path, "r", encoding="utf-8") as f:
                    bussiness_process_dict[business_process][tc] = json.load(f)
        return bussiness_process_dict
    
    def trigger_events_on_element(self, driver, elem):
        """Trigger native DOM events on a single element"""
        try:
            driver.execute_script("""
                var element = arguments[0];
                var events = ['input', 'change', 'blur'];
                events.forEach(function(eventType) {
                    var event = new Event(eventType, { bubbles: true });
                    element.dispatchEvent(event);
                });
            """, elem)
        except:
            pass

    def capture_screenshot(self, driver, test_case_id, step_number):
        """Capture screenshot and return base64 encoded image"""
        try:
            screenshot_path = f"screenshots/{test_case_id}_step_{step_number}.png"
            driver.save_screenshot(screenshot_path)
            
            with open(screenshot_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None

    def get_html_diff(self, html_before, html_after):
        """Get the difference between two HTML strings"""
        try:
            diff = list(unified_diff(
                html_before.splitlines(keepends=True),
                html_after.splitlines(keepends=True),
                fromfile='before',
                tofile='after',
                lineterm=''
            ))
            return ''.join(diff)
        except Exception as e:
            print(f"Error generating HTML diff: {e}")
            return ""

    def execute_action(self, driver, action, selector_type=None, selector_value=None, input_value=None):
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
                "id": "id",
                "name": "name",
                "class": "class name",
                "xpath": "xpath",
                "text": "xpath",
            }

            if selector_type not in selector_map:
                raise ValueError(f"Unsupported selector type: {selector_type}")

            if selector_type == "text":
                selector_value = f"//*[text()='{selector_value}']"

            # Special case: 'upload' action requires input_value to be the file path
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
                # 1. Ensure the path is absolute, as required by Selenium.
                absolute_file_path = os.path.abspath(input_value)

                # 2. Check if the file exists locally.
                if not os.path.exists(absolute_file_path):
                    raise FileNotFoundError(f"Local file not found at path: {absolute_file_path}")

                # 3. Use send_keys on the file input element to upload the file.
                elem.send_keys(absolute_file_path)
                log_entry["success"] = True

            else:
                raise ValueError(f"Unknown action type: {action}")

        except Exception as e:
            log_entry["error"] = str(e)
            return log_entry

        return log_entry

    def extract_interactable_elements(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        interactable = []
        
        def is_visible(elem):
            style = elem.get('style', '')
            if style:
                style_lower = style.lower()
                if 'display:none' in style_lower.replace(' ', '') or 'display: none' in style_lower:
                    return False
                if 'visibility:hidden' in style_lower.replace(' ', '') or 'visibility: hidden' in style_lower:
                    return False
                if 'opacity:0' in style_lower.replace(' ', '') or 'opacity: 0' in style_lower:
                    return False
            
            if elem.has_attr('hidden'):
                return False
            
            if elem.get('aria-hidden') == 'true':
                return False
            
            classes = elem.get('class', [])
            if isinstance(classes, list):
                hidden_classes = {'hidden', 'd-none', 'hide', 'invisible', 'sr-only', 'screen-reader-only'}
                if any(cls in hidden_classes for cls in classes):
                    return False
            
            parent = elem.parent
            while parent and parent.name != '[document]':
                parent_style = parent.get('style', '')
                if parent_style:
                    parent_style_lower = parent_style.lower()
                    if ('display:none' in parent_style_lower.replace(' ', '') or 
                        'display: none' in parent_style_lower):
                        return False
                
                if parent.has_attr('hidden'):
                    return False
                    
                parent = parent.parent
            
            return True
        
        clickable_tags = ['a', 'button', 'i', 'span', 'div']
        input_tags = ['input', 'textarea', 'select']
        potential_clickable = ['div', 'span', 'img', 'li', 'td', 'th']
        
        for tag in clickable_tags:
            for elem in soup.find_all(tag):
                if not is_visible(elem):
                    continue
                    
                interactable.append({
                    'tag': tag,
                    'type': 'clickable',
                    'text': elem.get_text(strip=True),
                    'attributes': {
                        'id': elem.get('id'),
                        'class': elem.get('class'),
                        'href': elem.get('href'),
                        'name': elem.get('name'),
                    }
                })
        
        for tag in input_tags:
            for elem in soup.find_all(tag):
                if not is_visible(elem):
                    continue
                    
                input_type = elem.get('type', 'text') if tag == 'input' else tag
                interactable.append({
                    'tag': tag,
                    'type': f'input_{input_type}',
                    'text': elem.get_text(strip=True) if tag != 'input' else '',
                    'attributes': {
                        'id': elem.get('id'),
                        'class': elem.get('class'),
                        'name': elem.get('name'),
                        'placeholder': elem.get('placeholder'),
                        'value': elem.get('value'),
                        'type': input_type,
                    }
                })
        
        for tag in potential_clickable:
            for elem in soup.find_all(tag):
                if not is_visible(elem):
                    continue
                    
                has_event = any(attr.startswith('on') for attr in elem.attrs)
                has_role = elem.get('role') in ['button', 'link', 'menuitem']
                has_tabindex = elem.get('tabindex') is not None
                
                if has_event or has_role or has_tabindex:
                    interactable.append({
                        'tag': tag,
                        'type': 'clickable',
                        'text': elem.get_text(strip=True),
                        'attributes': {
                            'id': elem.get('id'),
                            'class': elem.get('class'),
                            'role': elem.get('role'),
                            'onclick': elem.get('onclick'),
                        }
                    })
        
        for form in soup.find_all('form'):
            if not is_visible(form):
                continue
                
            interactable.append({
                'tag': 'form',
                'type': 'form',
                'text': '',
                'attributes': {
                    'id': form.get('id'),
                    'class': form.get('class'),
                    'action': form.get('action'),
                    'method': form.get('method'),
                }
            })
        
        return interactable
    
    def evaluate_next_step(self, extracted_elem : dict, current_tc : dict):
        extracted_elem_str = json.dumps(extracted_elem)
        input_context_str = json.dumps(self.input_context)
        navigation_sequence_str = json.dumps(current_tc.get("navigation_sequence", []), indent=2, ensure_ascii=False)
        test_data_fields = json.dumps(current_tc.get("test_data_fields", []), indent=2, ensure_ascii=False)
        print(test_data_fields)

        prompt = EVALUATE_NEXT_STEP.format(
            test_case_id=current_tc.get("test_case_id", "Unknown"),
            use_case_id=current_tc.get("use_case_id", "Unknown"),
            path_number=current_tc.get("path_number", "N/A"),
            test_case_title=current_tc.get("test_case_title", "Untitled"),
            test_scenario=current_tc.get("test_scenario", "N/A"),
            path_step=current_tc.get("path_step", "N/A"),
            groups_involved=current_tc.get("groups_involved", "N/A"),
            expected_result=current_tc.get("expected_result", "N/A"),
            post_condition=current_tc.get("post_condition", "N/A"),
            expected_outcome=current_tc.get("expected_outcome", "N/A"),
            data=input_context_str,
            navigation_sequence=navigation_sequence_str,
            extracted_elem=extracted_elem_str,
            test_data_fields=test_data_fields,
            short_term_memory = json.dumps(self.short_term_mem),
            long_term_memory = json.dumps(self.long_term_mem),
        )
        self.object_log.append(prompt)
        result = self.model.generate_json(prompt=prompt, schema=EVALUATE_NEXT_STEP_SCHEMA)
        return result
    
    def evaluate_past_success_tc(self, extracted_elem: dict, current_tc : dict):
        extracted_elem_str = json.dumps(extracted_elem)

        prompt = CHOOSE_EXISTING_STEP_PROMPT.format(
            test_case_id=current_tc.get("test_case_id", "Unknown"),
            test_case_title=current_tc.get("test_case_title", "Untitled"),
            test_scenario=current_tc.get("test_scenario", "N/A"),
            expected_result=current_tc.get("expected_result", "N/A"),
            post_condition=current_tc.get("post_condition", "N/A"),
            expected_outcome=current_tc.get("expected_outcome", "N/A"),
            extracted_elem=extracted_elem_str,
            short_term_memory = json.dumps(self.short_term_mem),
            long_term_memory = json.dumps(self.long_term_mem),
        )
        result = self.model.generate_json(prompt=prompt, schema=CHOOSE_EXISTING_STEP_SCHEMA)
        return result
    
    def generate_false_testcase(self, success_test_case: dict, success_actions : dict, false_test_case : dict):
        success_actions = json.dumps(success_actions)
        success_test_case_string_descrips = json.dumps(success_test_case)
        false_test_case_string_descrips = json.dumps(false_test_case)
        input_context_str = json.dumps(self.input_context)

        prompt = GENERATE_FALSE_TESTCASE_PROMPT.format(
            success_test_case_description = success_test_case_string_descrips,
            success_test_case_steps = success_actions,
            false_test_case = false_test_case_string_descrips,
            data = input_context_str,
        )
        result = self.model.generate_json(prompt=prompt, schema=GENERATE_FALSE_TESTCASE_SCHEMA)
        return result
    
    def evaluate_test_execution(self, test_case_description,  execution_log, html_before, html_after, screenshot_before, screenshot_after, visible_element):
        html_diff = self.get_html_diff(html_before, html_after)
        input_context_str = json.dumps(self.input_context)
        visible_text = self.html_text_with_paths(html_after)
        prompt = EVALUATE_TESTCASE_EXECUTION_PROMPT.format(
            test_case_description = test_case_description,
            execution_log = execution_log,
            html_diff=html_diff[:5000],
            visible_elements = visible_element,
            true_data = input_context_str,
            visible_text = visible_text
        )
        
        if screenshot_before and screenshot_after:
            result = self.model.generate_json_with_images(
                prompt=prompt,
                images=[screenshot_before, screenshot_after],
                schema=VALIDATION_RESULT_SCHEMA,
            )
        elif screenshot_after:
            # Fallback with only after screenshot
            result = self.model.generate_json_with_images(
                prompt=prompt,
                image_base64=screenshot_after,
                schema=VALIDATION_RESULT_SCHEMA
            )
        else:
            # Fallback without images
            result = self.model.generate_json(
                prompt=prompt,
                schema=VALIDATION_RESULT_SCHEMA
            )
        return result
    
    def _remove_failed_element(self, extracted_elem: list, selector_type: str, selector_value: str):
        if not selector_type or not selector_value or not extracted_elem:
            return extracted_elem

        new_list = []
        removed = []

        for elem in extracted_elem:
            attrs = elem.get("attributes", {}) or {}
            match = False

            if selector_type == "id":
                match = attrs.get("id") == selector_value
            elif selector_type == "name":
                match = attrs.get("name") == selector_value
            elif selector_type == "class":
                classes = attrs.get("class") or []
                if isinstance(classes, str):
                    classes = [classes]
                match = selector_value in classes
            elif selector_type == "tag":
                match = elem.get("tag") == selector_value
            elif selector_type == "text":
                match = elem.get("text", "").strip() == selector_value.strip()
            elif selector_type == "href":
                match = attrs.get("href") == selector_value
            elif selector_type == "role":
                match = attrs.get("role") == selector_value

            if not match:
                new_list.append(elem)
            else:
                removed.append({
                    "tag": elem.get("tag"),
                    "type": elem.get("type"),
                    "attributes": attrs
                })

        if removed:
            print(f"🧹 Removed {len(removed)} element(s): {removed}")

        return new_list
    def html_text_with_paths(self, html_content):
        """
        Extracts text from HTML and prepends the structural path (breadcrumbs) 
        to each line of text.
        
        Format: [tag > parent > child]: Text Content
        """
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Clean up technical junk (scripts, styles, metadata)
        unwanted_tags = ['script', 'style', 'head', 'meta', 'title', 'noscript']
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()

        output_lines = []

        # 2. Iterate over every specific text node in the tree
        # text=True finds all text strings inside tags
        for text_node in soup.find_all(text=True):
            
            # Remove whitespace-only nodes (indentation/newlines in code)
            clean_text = text_node.strip()
            
            if clean_text:
                # 3. Build the path hierarchy for this specific text node
                path_elements = []
                
                # .parents traverses up the tree from the text to [document]
                for parent in text_node.parents:
                    if parent.name == '[document]':
                        continue
                    
                    # Build a readable tag label (e.g., "div#main" or "p.text-bold")
                    tag_label = parent.name
                    
                    # Add ID if it exists (makes it very easy to locate)
                    if parent.get('id'):
                        tag_label += f"#{parent.get('id')}"
                    # Add Class if it exists (and no ID)
                    elif parent.get('class'):
                        # Classes in BS4 are lists, join them with dots
                        tag_label += f".{'.'.join(parent.get('class'))}"
                    
                    path_elements.append(tag_label)

                # Reverse list because we climbed UP the tree, but we want to read DOWN
                full_path = " > ".join(reversed(path_elements))
                
                # 4. Append to results
                output_lines.append(f"[{full_path}]: {clean_text}")

        return "\n".join(output_lines)
    def save_log(self, output_file, save_dict):
        if not os.path.exists(output_file):
            data = [save_dict]
        else:
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = []
            except (json.JSONDecodeError, FileNotFoundError):
                existing = []

            existing.append(save_dict)
            data = existing

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def init_agent_status(self):
        self.short_term_mem = {"execute_log" : []}
        done = False
        start_time = time.time()
        execution_status = True
        driver = webdriver.Chrome(options=options)
        driver.get(url=self.web_url)
        boosting = True
        return done, start_time, execution_status, driver, boosting
    
    def walkthrough(self, timeout_seconds = 600):
        bussiness_process_dict = self.extract_testcase()
        skip_bp=11
        skip_uc=0
        bp_count = 0
        uc_count = 0
        for bussiness_process in bussiness_process_dict.keys():
            if bp_count < skip_bp:
                bp_count += 1
                continue

            for use_case in bussiness_process_dict[bussiness_process]:
                if uc_count < skip_uc:
                    uc_count += 1
                    continue
                current_use_case = bussiness_process_dict[bussiness_process][use_case]
                print(f"Start running {bussiness_process}")

                success_tc = current_use_case
                
                # Trying to get golden path from success path
                done, start_time, execution_status, driver, boosting = self.init_agent_status()
                
                while not done:
                    # Setting for reset in case model stuck in a loop
                    elapsed_time = time.time() - start_time
                    if elapsed_time > timeout_seconds:
                        print(f"Timeout reached ({timeout_seconds/60} minutes). Resetting...")
                        driver.quit()
                        done, start_time, execution_status, driver, boosting = self.init_agent_status()
                    
                    # Extract interactable element from the current page
                    html = driver.page_source
                    if execution_status:
                        extracted_elem = self.extract_interactable_elements(html)
                    else:
                        extracted_elem = self._remove_failed_element(extracted_elem, selector_type, selector_value)
                    
                    # Agent check if the current testcase can leverage past success testcase
                    if boosting:
                        selected_tc = self.evaluate_past_success_tc(extracted_elem=extracted_elem, current_tc=success_tc)
                        if selected_tc["tc_id"] != "None":
                            for past_tc in self.long_term_mem:
                                if past_tc["test_case_info"]["test_case_id"] == selected_tc["tc_id"]:
                                    for step in past_tc["execute_log"]:
                                        if not step["error"] or step["action"] != "done":
                                            log_entry = self.execute_action(
                                                driver=driver,
                                                action=step.get("action"),
                                                selector_type=step.get("selector_type"),
                                                selector_value=step.get("selector_value"),
                                                input_value=step.get("input_value"),
                                            )
                                            self.short_term_mem["execute_log"].append(log_entry)
                                    time.sleep(0.5)
                                    html = driver.page_source
                                    extracted_elem = self.extract_interactable_elements(html)
                        boosting = False
                        
                    # Evaluate next step for agent in current page
                    response = self.evaluate_next_step(extracted_elem=extracted_elem, current_tc=success_tc)
                    print(response["reasoning"])

                    selector_type = response.get("selector_type", None)
                    selector_value = response.get("selector_value", None)

                    #NOTE(nhat): get HTML before and screenshot to evaluate later on
                    html_before = driver.page_source
                    screenshot_before = driver.get_screenshot_as_base64()
                    
                    #NOTE(nhat): execute selected action
                    log_entry = self.execute_action(
                        driver=driver,
                        action=response.get("action"),
                        selector_type=response.get("selector_type"),
                        selector_value=response.get("selector_value"),
                        input_value=response.get("input_value"),
                    )

                    time.sleep(0.5)
                    #NOTE(nhat): get HTML after and screenshot to compare with html_before later on
                    html_after = driver.page_source
                    screenshot_after = driver.get_screenshot_as_base64()

                    #NOTE(nhat): If current action getting error, subtract the element and retry
                    if not log_entry["error"]:
                        execution_status = True
                    else: execution_status = False

                    #NOTE(nhat): save log (even error) so agent have knowledge about error and execution progress
                    self.short_term_mem["execute_log"].append(log_entry)
                    done = response.get("done")

                # Close web
                driver.quit()

                # Evaluation part of success path
                visible_elements = self.extract_interactable_elements(html_after)
                execute_log = self.short_term_mem["execute_log"]
                test_case_description = success_tc

                result = self.evaluate_test_execution(test_case_description=test_case_description, 
                                            execution_log=execute_log,
                                            html_before=html_before,
                                            html_after=html_after,
                                            screenshot_before=screenshot_before,
                                            screenshot_after=screenshot_after,
                                            visible_element=visible_elements)

                # Construct reuseable selenium testcase step
                success_reuseable_testcase_object = {"execute_log" : self.short_term_mem["execute_log"],
                                                                "test_case_info" : success_tc,
                                                                "evaluation" : result}
                # This save success case first
                reuseable_testcase_list = [success_reuseable_testcase_object]

                # Append success happy path to long term memory to reuse in fail case gen and future reuse
                # NOTE(nhat): Exclude done part
                long_term_mem_obj = {"execute_log" :[], "test_case_info" : success_tc}
                for step in self.short_term_mem["execute_log"]:
                    if not step["error"] or step["action"] == "done":

                        long_term_mem_obj["execute_log"].append(step)
                self.long_term_mem.append(long_term_mem_obj)
                                
                folder_path = f"generated_mutation_testcase_action/{bussiness_process}"
                os.makedirs(folder_path, exist_ok=True)
                file_path = f"{folder_path}/{use_case}"

                with open(file_path, "w", encoding='utf-8') as f:
                    json.dump(reuseable_testcase_list, f, indent=2, ensure_ascii=False)
                with open("success_mutation_path.json", "w", encoding='utf-8') as f:
                    json.dump(self.long_term_mem, f, indent=2, ensure_ascii=False)
                with open(self.output_full_log, "w", encoding='utf-8') as f:
                    json.dump(self.object_log, f, indent=2, ensure_ascii=False)

from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    web_url = "https://localhost:5000/#/"
    api_keys = os.getenv("GEMINI_API_KEY").split(",")
    input_context = "input_context.json"
    success_tc = "success_happy_path.json"
    test_model = TestAgent(
        web_url=web_url, 
        api_keys=api_keys, 
        input_context=input_context,
        success_tc=success_tc,
        output_success_step="mutation_path.json",
        output_full_log="mutation_log.json"
    )

    test_model.walkthrough()