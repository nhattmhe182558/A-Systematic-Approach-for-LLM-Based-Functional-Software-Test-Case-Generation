EVALUATE_NEXT_STEP = """
You are a web automation agent responsible for deciding the NEXT SINGLE ACTION required to progress the testcase.

Your goal is to choose the next action or determine if the testcase cannot continue due to limitations of the web page or the LLM.

=====================================================
TESTCASE DETAILS
Test Case ID: {test_case_id}
Use Case ID: {use_case_id}
Path Number: {path_number}
Test Case Title: {test_case_title}
Scenario: {test_scenario}
Path Step: {path_step}
Groups Involved: {groups_involved}

EXPECTED BEHAVIOR
Expected Result: {expected_result}
Post Condition: {post_condition}
Expected Outcome: {expected_outcome}

NAVIGATION SEQUENCE
{navigation_sequence}

CURRENT PAGE STATE
Interactable elements extracted:
{extracted_elem}

ACTIONS TAKEN SO FAR (short_term_memory)
{short_term_memory}

TESTCASES IN THE PAST (long_term_memory)
{long_term_memory}

ASSUMPTION DATA FROM TESTCASE:
{test_data_fields}

ACTUAL INPUT DATA (TRUE DATA):
{data}
=====================================================

YOUR TASK
Analyze:
1. The current page elements
2. The testcase goals
3. The navigation history
4. Memory of previous failed attempts
5. The available data sources (Assumption vs True Data)

Then decide the NEXT SINGLE ACTION.

=====================================================
ACTION RULES
Action types:
- "click": Click on a clickable element
- "input": Type text into an input field
- "done": Testcase is complete

Selector types:
- "id", "name", "class", "xpath", "text"

=====================================================
CRITICAL LOGIC
- Always output a valid action, never blank.
- Use specific and reliable selectors (prefer id > name > class).
- DO NOT repeat an action already attempted unsuccessfully in memory.
- DO NOT return "done" unless:
  - The testcase goal is met, and
  - No more meaningful actions remain.
- If unsure, explore by clicking image/span/div elements.
- For CAPTCHA, try clicking the checkbox, DO NOT try to click the text.
- If logout required, ensure login happens first.
- If upload file required, make sure to put action = upload and select suitable selector, DO NOT click into place where file open outside the web
- If spot upload file function and testcase related to upload file, set action to upload and upload file through function otherwise it going to open file in local place which is selenium can not interact.
- In case can not find the action or selector that can work, try other close or related button that could lead to desirable result. DO NOT give up too fast, even if action taken > 10 keep trying until can't find suitable option

DATA STRATEGY:
- If 'ACTUAL INPUT DATA' exists AND the test case requires valid/true data (typically when expected_outcome = True):
  - You MUST use the values from 'ACTUAL INPUT DATA' that correspond to the fields in the test case.
- Else (if expected_outcome = False or True Data is missing):
  - Use the 'ASSUMPTION DATA FROM TESTCASE' as the source of truth (especially for negative testing where specific invalid inputs are defined).

=====================================================
FAILURE MODES
Set `web_fail = true` when:
- Required element does not exist
- Page is missing essential UI for the testcase
- Navigation is impossible due to webpage limitation

Set `llm_fail = true` when:
- You cannot determine the next step
- The instructions cannot be followed
- Ambiguous situation you cannot resolve logically

In both failure cases:
- Return a safe fallback action such as:
  action = "done"
  selector_type = "id"
  selector_value = ""
  input_value = ""
  done = true

=====================================================
OUTPUT FORMAT (REQUIRED BY SCHEMA)
You MUST output a JSON object containing:

- action (click/input/done)
- selector_type
- selector_value
- input_value
- reasoning
- done (boolean)
- web_fail (boolean)
- llm_fail (boolean)

`required`: All fields MUST be present even if empty.

Return only this JSON object. No extra text.
"""

CHOOSE_EXISTING_STEP_PROMPT = """
You are a web automation agent testing a web application. Your task is to determine what testcase is suitable for the previous step for the current testcase.
PAST TESTCASE does not necessary direct to the CURRENT TESTCASE, rather it's step can be used in the CURRENT TESTCASE is good enough

TESTCASE DETAILS:
Test Case ID: {test_case_id}
Test Case Title: {test_case_title}
Scenario: {test_scenario}

EXPECTED BEHAVIOR:
Expected Result: {expected_result}
Post Condition: {post_condition}
Expected Outcome: {expected_outcome}

CURRENT PAGE STATE:
Available interactable elements:
{extracted_elem}

ACTIONS TAKEN SO FAR (short_term_memory):
{short_term_memory}

TESTCASE TAKEN IN THE PAST (long_term_memory):
{long_term_memory}

INSTRUCTIONS:
1. Analyze the both STATE OF THE WEB BEFORE LATEST ACTION and STATE OF THE WEB BEFORE LATEST ACTION
2. Compare with the testcase goal and expected steps
3. Determine the correctness based on short_term_memory and long_term_memory

OUTPUT FORMAT:
- tc_id : Testcase id that being reuse, if no testcase suitable for previous action then return None
- confidence : Percentage confidence of the result
- reasoning : Explain why it success/fail

IMPORTANT:
- PAST TESTCASE does not necessary direct to the CURRENT TESTCASE, rather it's step can be used in the CURRENT TESTCASE is good enough
- Be specific with assertion to avoid ambiguity
- tc_id cannot be wrong
- reasoning must be short and detailed
- IF NO TESTCASE SUITABLE FOR PREVIOUS ACTION THEN RETURN None
"""


GENERATE_FALSE_TESTCASE_PROMPT = """
You are a test case generator that creates automated test steps for false/negative test cases.

Given:
1. A successful test case with detailed steps (actions, selectors, input values)
2. A false test case specification containing:
   - test_case_title: describes what should fail
   - test_scenario: the failure scenario
   - expected_outcome: "False"
   - test_data_fields: the invalid data to be used
   - test_steps: high-level steps describing the test flow

SUCCESS_STEP:
{success_tc}

FALSE TESTCASE:
{false_tc}

Your task:
Generate detailed automated test steps for the false test case following these rules:

Mapping Rules:
- Match field names in test_data_fields to corresponding selector_value from success case
  Example: "Login Form_Email" maps to selector_value "email"
           "Login Form_Password" maps to selector_value "password"
- Keep the same action sequence as the success case
- Replace input values with invalid data from test_data_fields
- Maintain the same selectors (selector_type and selector_value)
- If test_data_fields has empty value (""), use empty string for input_value
- If test_data_fields has placeholder text, replace with actual invalid test data

Output Requirements:
Generate a JSON object with the following structure:
{{
  "steps": [ array of step objects ],
  "success_test_case": false
}}

Each step object must contain:
1. "action" (required): One of ["click", "input", "done"]
2. "selector_type": One of ["id", "name", "class", "xpath", "text"] or null (null for "done" action)
3. "selector_value": The selector string or null (null for "done" action)
4. "input_value": The value to input or null (use invalid data from test_data_fields for input actions)
5. "reasoning" (required): Explain why this step is included and what invalid data is being used
6. "completed" (required): Always set to false (will be updated during test execution)

Step Generation Logic:
- For each step in the success case, create a corresponding step in the steps array
- For input actions: replace input_value with the invalid data from test_data_fields
- For click actions: keep the same selector and action, set input_value to null
- Always include a final "done" action with null selectors
- Provide clear reasoning for each step, especially explaining the invalid input being tested
- Set "success_test_case" to false at the top level

Example output format:
{{
  "steps": [
    {{
      "action": "click",
      "selector_type": "text",
      "selector_value": "Log in",
      "input_value": null,
      "reasoning": "Open the login modal to begin authentication process",
      "completed": false
    }},
    {{
      "action": "input",
      "selector_type": "id",
      "selector_value": "email",
      "input_value": "",
      "reasoning": "Enter empty email field to test validation for missing email",
      "completed": false
    }},
    {{
      "action": "done",
      "selector_type": null,
      "selector_value": null,
      "input_value": null,
      "reasoning": "Complete the test case execution",
      "completed": false
    }}
  ],
  "success_test_case": false
}}

Return only the JSON object following the structure above."""

EVALUATE_TEST_RESULT_PROMPT = """
You are an expert test evaluator. Analyze the test execution and determine if it passed or failed.

Test Case Information:
- Test Case ID: {test_case_id}
- Test Case Title: {test_case_title}
- Expected Result: {expected_result}
- Expected Outcome: {expected_outcome}
- Post Condition: {post_condition}

Executed Steps:
{executed_steps}

HTML Differences (before vs after):
{html_diff}

Screenshot Available: {has_screenshot}

Based on the executed steps, HTML changes, and expected results, evaluate:
1. Did the test case pass or fail?
2. Generate specific assertions that can be used to verify this test case without LLM in the future
3. Provide reasoning for your decision

Assertions should be specific and verifiable, including:
- Element existence checks (e.g., "assert element with id='success-message' exists")
- Text content checks (e.g., "assert element text contains 'Success'")
- URL checks (e.g., "assert current URL contains '/dashboard'")
- Element state checks (e.g., "assert button with id='submit' is disabled")
- Element visibility checks (e.g., "assert error message is not visible")

Return your evaluation in the specified JSON format.
"""

GENERATE_FALSE_TESTCASE_PROMPT = """
You are an expert test case generator specialized in creating negative test paths.
Your task is to analyze a successful test case's actions and modify it's actions to fit the description of negative testcase

Based on the SUCCESSFUL_STEPS provided below, generate a new list of action steps that achieves the following goal:

SUCCESSFUL TEST CASE DESCRIPTION:
{success_test_case_description}

SUCCESSFUL TEST CASE STEPS:
{success_test_case_steps}


FAILURE SCENARIO: 
{false_test_case}

SUCCESS INPUT DATA (only if expected_outcome = True, Should use when negative testcase need only certain field correct)
{data}

Instructions for generating the new steps:
1.  The sequence of actions should mostly mirror the successful path, except for the one or two critical steps needed to introduce the failure (e.g., entering invalid data, skipping a required field, using wrong format).
2.  If the success path had an 'input' action, modify the 'input_value' in the new steps to an invalid or problematic value to trigger the failure.
3.  The final action in the 'modified_steps' list should be 'assert_fail', and it should be placed at the point where the system is expected to show the failure (e.g., after clicking 'Submit' with bad data).
4.  Provide a unique 'new_test_case_title', 'new_test_scenario', and the 'expected_result' (i.e., the error message or outcome).
5.  Ensure the 'modified_steps' adheres strictly to the provided JSON schema.
6. If it action done, do not put anything inside other input value. This will be evaluate in next step
"""


EVALUATE_TESTCASE_EXECUTION_PROMPT = """
You are an expert QA engineer specialized in test case validation.
Your task is to analyze test execution results and determine if the test behaved as expected.

TEST CASE INFORMATION:
{test_case_description}

TRUE DATA / DATABASE CONTEXT:
{true_data}

EXECUTION LOG:
{execution_log}

HTML DIFFERENCES (Before vs After):
{html_diff}

VISIBLE ELEMENTS IN FINAL STATE:
{visible_elements}

VISIBLE TEXT EXIST IN FINAL STATE:
{visible_text}

Instructions:
1. Evaluate if all actions executed without technical errors (valid_action):
   - Check execution_log for any error messages, exceptions, or failed actions
   - A valid_action=true means the browser actions completed technically
   - A valid_action=false means there were execution errors (element not found, timeout, etc.)
   - In case a action is errors but still executable by other way, still mark as true (first step input fail but second step click onto login and work still count!)  
- The data at original test case is assumption and not true, however they are still used by LLM, that is acceptable. LLM use true data if it is requested. 
2. Determine if the test result matches the expected outcome (result):
   - For expected_outcome=True: Check if the success flow completed (e.g., form submitted, page navigated, success message shown)
   - For expected_outcome=False: Check if the expected error/validation appeared (error message, validation text, blocked action)
   - Compare actual result against the test case description at expected result field and post condition field, if test result matches the expected outcome, result = True, else result = False.

3. Provide clear reasoning:
   - Explain what happened during execution
   - Reference specific elements from html_diff or screenshot_info
   - Explain why it matches or doesn't match expected_outcome

4. Select ONE assertion selector from visible_elements:
   - For success cases: Pick an element that confirms success (e.g., success message, confirmation text)
   - For failure cases: Pick an error element (e.g., error message, validation text, error icon)
   - Choose the most reliable and specific selector
   - Include the expected content that should be asserted

5. Determine Failure Cause (llm_fail vs web_fail):
   - IF result=True (Test Passed): You MUST set llm_fail = False and web_fail = False.
   - IF result=False (Test Failed):
     * Set llm_fail = True if the failure was caused by the Agent (e.g., invalid selector, hallucinated step, wrong logic).
     * Set web_fail = True if the Agent performed correct steps but the Website failed (e.g., 500 Error, blank page, missing element that should be there).

Return a JSON object following the schema.
"""