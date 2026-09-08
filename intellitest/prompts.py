from typing import List

gen_business_process_prompt = """
Task: Identify and extract distinct business processes sections performed by human actors. A business process is a complete end-to-end sequence of actions to achieve a business goal. Each business process must be a complete, continuous flow from start to finish.

**AVAILABLE SCREENS LIST:**
This is the definitive list of all valid screens in the system. You MUST use these exact screen names.
{screens_list}

EXTRACTION STRATEGY - Follow this exact priority order:

**PRIORITY 1: Target Dedicated Business Process Sections**
First, scan the RDS Documentation for sections with these specific names or similar variations:
- "Business Process" / "Business Processes"
- "Business Process Flow" / "Business Process Flows"
- "Business Workflow" / "Business Workflows"
- "End-to-End Process" / "End-to-End Flow"
- "System Workflow" / "System Process"
- "Business Logic Flow"
- "Process Flow" (when in a dedicated section)

**BUSINESS PROCESS REQUIREMENTS:**
- Each business process must be COMPLETE and CONTINUOUS from start to finish
- Each process must have a clear business objective/goal
- Steps must follow logical sequence and be connected
- Each process should represent a meaningful business scenario
- Group related steps into cohesive business processes

**NEW: STEP DESCRIPTION RULES**
- **Complete Flow Description**: The `description` MUST provide a comprehensive narrative of WHO does WHAT, with WHICH DATA, for WHAT PURPOSE, following the exact flow in the business process.
- **Extract Actor from Document**: You MUST identify and extract the actor/role from the use case or business process description in the document (e.g., if document mentions "seller registration", actor is "A seller"; if "customer checkout", actor is "A customer"). Extract the exact role terminology used in the document.
- **Detailed Action Breakdown**: Describe the complete sequence of user interactions on the `current_screen`:
  1. **WHO**: Identify the actor/role performing the action (extract from document)
  2. **WHAT**: Describe the specific actions taken (e.g., "provides", "enters", "selects", "clicks", "uploads", "confirms")
  3. **WHICH DATA**: Explicitly list ALL key data fields/parameters involved (extract field names from the use case specification or screen description)
  4. **PURPOSE**: Include the business goal or outcome (e.g., "to create a seller account", "to complete the order")
- **Field Extraction Priority**: 
  1. First, look for explicit field lists in use case descriptions or screen specifications
  2. Second, look for data requirements in business rules or validation sections
  3. Always prefer specific field names over generic terms
- **Exclude Navigation/Preparatory Steps**: Do NOT include actions like "navigates to the page" or "opens the modal". The description should start from the point where the user is already on the correct screen.
- **Focus on Action** (for the `step` field): Each `step` description MUST be a concise, role-agnostic summary of the action (e.g., "Register seller account", "Update profile information", "Place an order").

**STRICT EXCLUSION RULES - DO NOT INCLUDE:**
- System validations (e.g., "System validates user data")
- Data processing steps (e.g., "System processes payment")
- Database operations (e.g., "System stores information")
- Backend calculations or logic
- Email sending or receiving (unless specifically viewing emails in the UI)
- Any action not directly visible to and performable by a user
- Any step containing "System" as the actor
- Individual use case normal flows or alternative flows

**DESCRIPTION FORMAT EXAMPLES:**
(Note: Extract actor roles from the document - examples below are illustrative only)

**Example 1 - Account Registration:**
- ✅ GOOD: "[Actor] creates a new account by providing personal details including [list specific fields like first name, last name, email, password], and [domain-specific information like shop name, company details], then agrees to [specific terms/policies] to complete the registration."
- ❌ BAD: "User fills out the registration form and submits."

**Example 2 - Authentication:**
- ✅ GOOD: "[Actor] accesses their existing account by entering the registered [specific credential fields like email address, username] and password."
- ❌ BAD: "User logs in."

**Example 3 - Data Entry:**
- ✅ GOOD: "[Actor] creates a new [entity/item] by providing [entity] details including [list all key fields like name, identifier, description, price, quantity], and uploads [specific files like images, documents]."
- ❌ BAD: "[Actor] adds information."

**Example 4 - Data Update:**
- ✅ GOOD: "[Actor] updates their [profile/record] information by modifying the [list specific fields being updated like name, contact details, preferences]."
- ❌ BAD: "User updates profile."

**Key Pattern**: "[Actor/Role] + [Action Verb] + [Object] + by + [Detailed Method with Specific Field Names] + [Optional Purpose]"

**IMPORTANT**: 
- If a use case appears multiple times with sub-actions, combine them into ONE step that captures the main use case action
- However, if the same use case appears for different actors, these are separate independent steps and both should be included
- The key is distinguishing between sub-actions of the same use case vs independent use case executions by different actors

**SCREEN NAVIGATION REQUIREMENTS:**
- **CRITICAL CONSTRAINT**: The `current_screen` and `next_screen` values MUST exactly match one of the names from the "AVAILABLE SCREENS LIST" provided above.
- **PROHIBITION**: Do NOT invent, create, or hallucinate screen names. Do not confuse other UI elements like modals or tabs for screens unless they are in the provided list. Any deviation from the provided list is strictly forbidden.
- **current_screen**: The screen where this use case is actually performed.
- **next_screen**: The screen the user navigates to after successfully completing this use case.
- **element**: The specific UI element (button, link, menu item, icon, etc.) that the user interacts with to perform this action or navigate to the next screen. Extract the exact element name as described in the document (e.g., "Logout button", "Submit button", "Login link", "Profile icon", "Save changes button"). If the element name is not explicitly mentioned in the document, infer it based on the action and common UI patterns (e.g., for "Log out" action, use "Logout button").

**KEYWORDS REQUIREMENTS:**
- **keywords**: A list of exactly 8 relevant keywords that describe the purpose and context of this use case
- Each keyword must be a SINGLE WORD only (no phrases, no spaces)
- Keywords must NOT contain special characters (only letters, numbers, underscores allowed)
- Keywords should capture the business intent, user actions, system functionality, and domain concepts

**ROLE EXTRACTION REQUIREMENTS:**
- **role**: Extract the user role/persona that performs this business process step from the requirement document
- Analyze actor mentions in use case descriptions, business process flows, or user type specifications
- Use role names exactly as they appear in the document (e.g., "Customer" → "customer", "Seller" → "seller", "Admin" → "admin")
- Convert to lowercase for consistency
- Common patterns to look for:
  * Explicit role mentions: "A customer creates...", "The seller updates...", "An admin manages..."
  * Actor sections: "Actor: Customer", "User Type: Seller"
  * Use case actors: "Primary Actor: Administrator"
- If no explicit role is mentioned, infer from context:
  * Registration/Login flows → typically "customer" or "user"
  * Product/Order management → "seller" or "admin"
  * Public browsing → "guest" or "visitor"
- Default to "user" only if role cannot be determined from context
- This role will be used for role-based path filtering in screen navigation

**CRITICAL REQUIREMENTS:**
- Each business process must be complete and continuous
- Steps must be logically connected and follow a natural flow
- Extract UC IDs exactly as they appear in the document
- Ensure each business process has a clear start and end point
- **STEP FOCUS**: Each step should describe the PRIMARY action of the use case, not sub-actions or detailed steps within the use case
- **SUB-ACTION EXCLUSION**: If multiple steps share the same UC ID but represent sub-actions of the same use case, combine them into ONE step that captures the main use case action
- **INDEPENDENT USE CASES**: Different actors performing the same use case are considered separate, independent steps and should both be included
"""

extract_all_screens_prompt = """
TASK: Extract all unique, formally defined screens from the RDS document.

OBJECTIVE: Identify and list only the items that are explicitly defined as primary screens or pages.

**STRICT EXTRACTION RULES:**
1. **EXACT TEXT MATCH**: Use the EXACT screen name as it appears in the document - preserve all capitalization, spacing, and formatting
2. **PRIMARY SCREENS ONLY**: Only extract main functional screens, NOT UI components like modals, dialogs, tabs, or popups

**WHAT TO IGNORE - EXAMPLES:**
❌ "Login Modal" (Modal dialog, not a primary screen)
❌ "Confirmation Popup" (Popup, lacks formal identifier)
❌ "Navigation Menu" (UI component, not a screen)
❌ "Product Details Tab" (Tab within a screen)
❌ "Error Message" (System message, not a screen)
❌ "Header Section" (Part of UI, not a screen)

**VALIDATION CHECKLIST:**
Before including any item, verify:
1. ✓ Represents a distinct functional screen/page
2. ✓ Is NOT a modal, dialog, tab, or UI component
3. ✓ Text matches document exactly (no modifications)

**OUTPUT REQUIREMENT:**
Extract ONLY screens that meet ALL the above criteria. Each screen name MUST be exactly as written in the document, including the full identifier and title.
"""

gen_screen_graph_prompt= """
TASK: Extract navigation flow of screens from specific elements of screens which is used for navigation.

**CHAIN OF THOUGHT: ELEMENT EXTRACTION STRATEGY**
1.  **Focus on Current Screen**: Target one screen at a time from the 'SCREEN LIST TO PROCESS'.
2.  **Scan for Navigation Elements**: Systematically scan all elements on the screen.
3.  **Filter by Navigation Capability**: Identify and filter for elements that can trigger navigation. Look for clues in the element's description, type, or name (e.g., "button", "link", "menu item").
4.  **Comprehensive Extraction**: Ensure you extract ALL navigation elements, even if they appear to be duplicates or common UI components (e.g., header/footer links). Do not omit any.
5.  **Recursive Scanning**: If a screen contains components or sections with their own elements, apply this scanning and filtering process recursively to ensure no nested navigation elements are missed.

OBJECTIVE: From the provided 'SCREEN LIST TO PROCESS', identify ALL navigation actions (edges) that originate from the single screen in the list.

STRICT REQUIREMENTS THAT YOU MUST OBEY: MUST EXTRACT ALL NAVIGATION ELEMENTS: Include every button, link, menu, tab, anything that navigates to another screen. Each screens have separate elements so that you must list all of them regardless of duplication.

SCREEN LIST TO PROCESS:
{screens_list}

NODE ATTRIBUTES:
-   `name`: The descriptive name of the screen (use exact names from the screen list above).

EDGE ATTRIBUTES:
-   `source`: The `name` of the screen where the action originates.
-   `target`: The `name` of the screen the action leads to (must be from the screen list above).
-   `action`: A description of the action (e.g., "Navigate to Product Details").
-   `element`: The UI element the user interacts with (e.g., "Product Image").
-   `keywords`: A list of exactly 8 relevant keywords that describe the PURPOSE and INTENT of the action. Each keyword must be a SINGLE WORD only (no phrases, no spaces, no special characters). Focus on what the action accomplishes, not just what it is.
-   `important_key`: The single most critical keyword that best represents the PURPOSE of the action. Must be a SINGLE WORD only.
-   `roles`: (OPTIONAL) A list of user roles that can access this navigation element. Extract this from the document if the element has role-based access restrictions. Examples:
    * "Admin Dashboard button" → `["admin"]` (only admins can see/use this)
    * "Seller Dashboard link" → `["seller"]` (only sellers)
    * "My Orders" → `["customer"]` or `null` if available to all logged-in users
    * "Product Details" → `null` (public access, no restrictions)
    * Convert role names to lowercase (e.g., "Admin" → "admin", "Seller" → "seller")
    * If multiple roles can access, list all (e.g., `["admin", "seller"]`)
    * If no explicit role restriction is mentioned and the element seems generally accessible, leave as `null` or omit this field

OUTPUT FORMAT:
Your output must be a single JSON object representing the `ScreenFlowGraph`.
"""

gen_screen_variables_prompt = """
TASK: From the business process step provided below, identify ONLY THE INTERACTABLE UI elements for the specified `current_screen`. Organize them in a HIERARCHICAL LAYER STRUCTURE and define their valid/invalid test values. You MUST exclude all non-interactable, static elements.

**BUSINESS PROCESS STEP CONTEXTS:**
- **Current Screen**: {current_screen}
{contexts}

**CRITICAL EXTRACTION RULE:**
- You MUST ONLY extract elements that are **explicitly mentioned** in the `Step Descriptions` across all provided contexts.
- Do NOT infer or assume the existence of any elements not described in the context. If one step description says "user enters credentials" and another says "user clicks forgot password", you can extract "username", "password", "login button", and "forgot password link".
- Your primary task is to model ONLY the elements relevant to the described steps.

**CHAIN OF THOUGHT: ELEMENT EXTRACTION STRATEGY**
1.  **Analyze Step Descriptions**: Read the `Step Descriptions` provided in the context. This is your ONLY source of truth for which elements to extract.
2.  **Identify Mentioned Elements**: Identify every interactable element that is explicitly mentioned or directly required to perform the actions in the descriptions.
3.  **Strict Filtering**: Ignore any other elements on the `{current_screen}` that are not relevant to the described steps.
4.  **Group Functionally**: Group the identified elements based on the business function they support, as described in the context.
5.  **Assign Business Process**: For each `element_group`, you MUST set the `belong_to` field to the name of the business process that the source step description came from (e.g., "business_process_1"). This is critical for traceability.
- **Recursive Scanning for Mentioned Elements**: If a mentioned element (like a button) reveals other elements (like in a modal), apply this same strict filtering process to the newly revealed elements. Only extract them if they are also mentioned or directly implied by the business process steps.

HIERARCHICAL LAYER STRUCTURE:
- **LAYER 0**: Base screen elements (always visible)
- **LAYER 1**: Elements that appear when Layer 0 elements are activated (modals, dropdowns, popups)
- **LAYER 2**: Elements that appear when Layer 1 elements are activated (nested modals, sub-forms)
- **LAYER N**: Continue for deeper nesting levels

**CRITICAL CONSTRAINT:** You MUST ONLY generate variables for the screen specified in `Current Screen`. Do NOT extract variables for any other screen.

**NEW TRIGGER ELEMENT CONSTRAINT:**
- For every layer greater than 0 (e.g., Layer 1, 2, etc.), you MUST specify the `trigger_element`.
- The `trigger_element`'s value MUST EXACTLY MATCH one of the `valid_values` of the element from the PREVIOUS layer that makes the current layer visible.
- For Layer 0, `trigger_element` must be `null`.

**NEW CONSTRAINT: Business Process-Aware Extraction**
- You MUST analyze the business processes associated with each screen.
- Prioritize extracting elements that are DIRECTLY mentioned or implied in the business process steps.
- This ensures that the extracted variables are relevant to the actual user workflows to be tested.

TESTING METHODOLOGY:
- **Source of Truth**: Your primary source for generating test data is the **business rules** described in the requirement document.
- **Apply Techniques**: You MUST apply the following testing techniques to those business rules to derive the abstract `valid_values` and `invalid_values`.
- **USE ABSTRACT VALUES**: All `valid_values` and `invalid_values` MUST be abstract representations of data categories, not concrete examples.

1. **Boundary Value Analysis (BVA)**: For numeric ranges or constraints, you MUST extract test values at and around boundaries.
   
   **CRITICAL BVA RULE**: For each boundary, extract THREE values:
   - One value BELOW the boundary (invalid)
   - One value AT the boundary (valid)
   - One value ABOVE the boundary (valid for lower bound, or use for context)
   
   **Example: Password length 8-20 characters**
   - For LOWER boundary (8):
     * "=7" (below lower boundary - INVALID)
     * "=8" (at lower boundary - VALID)
     * "=9" (just above lower boundary - VALID)
   - For UPPER boundary (20):
     * "=19" (just below upper boundary - VALID)
     * "=20" (at upper boundary - VALID)
     * "=21" (above upper boundary - INVALID)
   - Additional invalid values:
     * "null" (empty/null input)
     * " " (whitespace only)
   
   **MUST EXTRACT ALL SIX BOUNDARY VALUES**: =7, =8, =9, =19, =20, =21 for range 8-20
   
   **Pattern for any range [MIN, MAX]**:
   - Valid values: "=MIN", "=(MIN+1)", "=(MAX-1)", "=MAX"
   - Invalid values: "=(MIN-1)", "=(MAX+1)", "null", " "

2. **Equivalence Partitioning**: Group values into valid/invalid equivalence classes based on business rules

3. **Business Rule Testing**: Extract constraints from document (format requirements, mandatory fields, etc.)

**CRITICAL: USE CASE-SPECIFIC BUSINESS RULE CONSTRAINT**
- **Strict Scope Enforcement**: You MUST ONLY use business rules that are explicitly mentioned or directly referenced in the use case(s) associated with the current screen.
- **Step-by-Step Process**:
  1. **Identify Current Use Case**: Review the "Step Descriptions" in the context to identify which use case(s) are being performed on this screen
  2. **Extract Use Case Rules**: For each identified use case, extract ONLY the business rules explicitly stated in that use case's description, requirements, or alternative flows
  3. **Verify Rule Ownership**: Before using any business rule, verify it belongs to the current use case, NOT other use cases
  4. **Generate Test Values**: Only generate test values from rules that belong to the current use case
  5. **Document Only Used Rules**: Only include rules in `used_business_rules` if you generated at least one test value from them

**DO NOT Borrow Rules from Other Use Cases**:
- ❌ **BAD**: Using password complexity rules from a registration use case when processing an authentication screen
- ✅ **GOOD**: Using only authentication-specific rules (invalid credentials, account lockout) for authentication screen
- ❌ **BAD**: Using account creation rules when processing an account update screen
- ✅ **GOOD**: Using only update-specific rules for account update screen

**Double Constraint - A business rule must satisfy BOTH**:
1. ✅ Belongs to the use case associated with this screen
2. ✅ You have generated at least one test value from it

**Traceability Requirement**:
- Each business rule in `used_business_rules` MUST:
  - Be explicitly mentioned in the current screen's use case
  - Directly map to at least one specific test value you generated

**Generic Examples** (adapt to your document):
- ✅ **GOOD**: Authentication screen + Password field → Use authentication use case's "Invalid Credentials" alternative flow to generate "incorrect_password" value
- ❌ **BAD**: Authentication screen + Password field → Using password complexity rules that belong to registration use case
- ✅ **GOOD**: Account creation screen + Password field → Use registration use case's password complexity rules to generate "password_too_short", "password_missing_uppercase", etc.

**Fallback**: If you cannot find a specific rule from the current use case, state the common practice or assumption (e.g., "Common practice: Email format validation").

**Critical Requirement**: This ensures traceability and prevents mixing rules from different use cases.

**NEW: STRICT ABSTRACT VALUE CONSTRAINT**
- **No Concrete Data**: Generated values MUST be abstract descriptions of the data type, not actual data. The goal is to define the *category* of the test data.
- **Example - GOOD**: "valid_email_format", "invalid_email_no_at_sign", "name_exactly_50_chars", "name_over_50_chars", "password_8_mixed_chars", "password_less_than_8_chars", "numeric_string_10_digits", "non_numeric_string", "valid_shop_name", "shop_name_with_special_chars".
- **Example - BAD**: "johndoe@email.com", "johndoe", "MyValidP@ss1", "1234567890", "John's Shop".
- **Enforcement**: You must strictly adhere to this rule. Do not use any real-world names, emails, addresses, numbers, or specific content as values.

**NEW: EMPTY VALUE CONSTRAINT**
- For any test case that represents an empty input (e.g., a mandatory field left blank), you MUST use the string "null" instead of an empty string (""). This ensures that empty inputs are explicitly represented.
- **Example - GOOD**: `"invalid_values": ["null", " " (whitespace only)]`
- **Example - BAD**: `"invalid_values": ["", " " (whitespace only)]`

**STRICT ELEMENT INTERACTION RULE:**
- **INCLUDE ONLY INTERACTABLE ELEMENTS**: You MUST ONLY extract UI elements that a user can directly interact with to input data, make a selection, or trigger an operation.
- **INTERACTIVE ELEMENT EXAMPLES**:
  - Input fields (text, password, email, number)
  - Textareas
  - Buttons (submit, reset, cancel)
  - Links that trigger actions or navigation
  - Checkboxes
  - Radio buttons
  - Dropdowns (select menus)
  - Toggles / Switches
- **EXCLUDE NON-INTERACTIVE ELEMENTS**: You MUST IGNORE all static, non-interactable elements.
- **NON-INTERACTIVE ELEMENT EXAMPLES TO EXCLUDE**:
  - Static text labels
  - Headings and titles
  - Descriptive text or paragraphs
  - Non-clickable images or icons
  - Banners
  - Any element of type "Content"

**CRITICAL GROUPING AND NAMING RULES:**
- **Group by Function**: Elements that work together to perform a single business function MUST be in the same `element_group`.
- **Forms and Actions Together**: All fields of a form (inputs, dropdowns, etc.) and its action buttons ("Submit", "Save", "Cancel") MUST be in the same group.
- **Assign Business Function**: For each `element_group`, you MUST provide a `business_function`.
- **Assign Use Case ID**: For each `element_group`, you MUST extract and set the `use_case_id` field from the business process step context. The `use_case_id` should match the use case identifier mentioned in the step description (e.g., "UC-101", "UC-102", "UC-301"). This is CRITICAL for mapping groups to specific use cases.
  - **Focus on Action, Not Role**: The description MUST focus on the core action or use case.
  - **Be Detailed and Data-Specific**: The description must be a full sentence detailing the user actions and explicitly mentioning the key data fields involved (e.g., "first name, last name, email"). Instead of a high-level summary, describe what the user *does* and what data they provide.
  - **BE ROLE-AGNOSTIC**: Do NOT include user roles like "seller," "customer," or "admin".
  - **Example 1 - GOOD**: "Authenticate and access an existing account by entering a username and password."
  - **Example 1 - BAD**: "Authenticate an account."
  - **Example 2 - GOOD**: "Create a new account by filling in personal details like first name, last name, email and shop information like shop name, shop address."
  - **Example 2 - BAD**: "Allows new sellers to register an account."

**NEW: ELEMENT SEMANTIC RULES**
- **Distinguish Parameters from Actions**: You must analyze each interactive element and classify it into one of two categories:
  - **Parameters**: Elements that accept user data or input (e.g., text fields, search bars, checkboxes, dropdowns). These elements require test data.
  - **Actions**: Elements that trigger an operation or navigation (e.g., submit buttons, navigation links, icons). These elements do not require test data.
- **Individual Actions**: Each distinct action element (like a 'Login' button or a 'View Cart' link) must be treated as a separate, individual item. Do not group them.

**CRITICAL: USE CASE ID EXTRACTION**:
- For each `element_group`, you MUST extract the `use_case_id` from the business process step context provided.
- The `use_case_id` should be extracted EXACTLY as it appears in the context - preserve the exact format, casing, and structure from the document.
- Look for use case identifiers in the step descriptions, requirements section, or any explicitly stated use case reference in the context.
- Do NOT invent, modify, or assume any use case ID format. Extract it verbatim from the source document.

OUTPUT FORMAT:
The output structure will be strictly validated by the system. Focus on correctly identifying the business functions, parameters, actions, and use_case_id based on the rules above.

**CRITICAL SCREEN NAME RULE**: The "screen_name" MUST be extracted exactly as it appears in the document. Do NOT modify, abbreviate, or change the screen name in any way. Use the exact name from the document.
"""

gen_test_case_prompt = """
TASK: Generate comprehensive test cases that combine business process context with specific test scenarios from CSV data.

INPUTS PROVIDED:
- Business Process Step: {step_info} [CONTEXT - Provides workflow and purpose]
- Navigation Path: {path_info} [REQUIRED - Navigation Flow]
- CSV Test Data Row: {screen_csv_data} [TEST SCENARIOS - Defines specific test data and expected outcome]
- Matched Group Information: {matched_group}
- Input Data: {input_data}
- Previous Test Case Context: {test_case_context}

**CRITICAL UNDERSTANDING - THE BALANCE:**

1. **Business Process Step = CONTEXT**
   - Provides the workflow and user journey
   - Defines which screen and which fields are involved
   - Describes the business purpose and user intent
   - Sets the overall test scenario context

2. **CSV Test Data Row = TEST SCENARIO**
   - Provides specific test data values (positive AND negative)
   - Defines the expected outcome (success or failure)
   - Specifies which validation rules to test
   - Determines whether to test happy path or error cases

3. **The Combination**
   - Business Process tells you WHAT to test (e.g., "user login")
   - CSV Data tells you HOW to test it (e.g., "with invalid password" → outcome=false)
   - Together they create complete test cases covering all scenarios

OBJECTIVE: Create a detailed test case that:
1. **Uses Business Process Step for CONTEXT** - Understand the workflow and purpose
2. **Uses CSV Data for TEST SCENARIO** - Apply specific data values and expected outcome
3. **Uses Navigation Path** - To establish how the user reaches the screen
4. **Maintains Continuity** - Uses previous test case context for data consistency

**CONTEXT + SCENARIO TEST GENERATION:**

**STEP 1: Understand Business Process Context**
1. **Read Business Process Step**:
   - Understand the `step`, `description`, and `keywords`
   - Identify the workflow: which screen, which action, which fields
   - Understand the business purpose (e.g., "authenticate user", "register account")
   - This gives you the CONTEXT and STRUCTURE of the test

**STEP 2: Apply CSV Test Scenario**
2. **Use CSV Data Row for Test Scenario**:
   - CSV provides the SPECIFIC TEST CASE to generate
   - Check `outcome` field in CSV:
     * `outcome=true` → Generate POSITIVE test case (success scenario)
     * `outcome=false` → Generate NEGATIVE test case (validation failure scenario)
   - Use CSV field values to populate test data
   - Use CSV field combinations to create realistic test scenarios
   - CSV determines whether you test happy path or error handling

**STEP 3: Generate Complete Test Case**
3. **Combine Context + Scenario**:
   - Business Process context tells you: "Test user login functionality"
   - CSV scenario tells you: "with invalid password" (outcome=false)
   - Result: Test case for "User login with incorrect password should fail"
   
4. **Test Steps Generation**:
   - Extract test steps from Business Process workflow
   - Apply CSV data values to those steps
   - Set expected_result based on CSV outcome:
     * outcome=true → Success message, navigation to next screen
     * outcome=false → Error message, stay on same screen

5. **Test Data Fields**:
   - Extract field names from Business Process description
   - Use CSV row values for concrete data
   - Each CSV column becomes a test data field
   - Ensure test data matches the CSV scenario (valid/invalid)

**CRITICAL HIERARCHY:**
```
Business Process Step (provides CONTEXT: which screen, which fields, which workflow)
    ↓
CSV Test Data Row (provides SCENARIO: specific test data + expected outcome)
    ↓
Navigation Path (provides NAVIGATION: how to reach the screen)
    ↓
Combined Result: Context-aware test case with specific scenario
```

**EXAMPLES:**

**Example 1: Login Test Cases**
- Business Process: "User authenticates by entering username and password"
- CSV Row 1: username="valid_user", password="valid_password", outcome="true"
  → Test Case: "User successfully logs in with correct credentials" ✅
- CSV Row 2: username="valid_user", password="incorrect_password", outcome="false"
  → Test Case: "User login fails with incorrect password" ✅
- CSV Row 3: username="null", password="valid_password", outcome="false"
  → Test Case: "User login fails with empty username" ✅

**Example 2: Registration Test Cases**
- Business Process: "User creates account by providing email, password, name"
- CSV Row 1: email="valid@example.com", password="=8_chars", outcome="true"
  → Test Case: "User successfully registers with valid data" ✅
- CSV Row 2: email="invalid_format", password="=8_chars", outcome="false"
  → Test Case: "Registration fails with invalid email format" ✅
- CSV Row 3: email="valid@example.com", password="=7_chars", outcome="false"
  → Test Case: "Registration fails with password too short" ✅

**CRITICAL INPUT DATA USAGE RULES:**
- **Context-Aware Data Selection**: You MUST analyze the current business process step and screen context before using Input Data.
- **Role/Context Matching**: Only use Input Data that matches the current test scenario context:
  - Match the user role/persona from Input Data with the functionality being tested
  - Ensure data permissions and access levels align with the test scenario
  - Use data that is appropriate for the specific workflow or business function
- **Contextual Validation**: Before using any Input Data value, verify that the data description and context align with the current test case scenario.
- **Fallback Strategy**: If Input Data doesn't match the current context or is inappropriate, generate contextually appropriate data instead.
- **Priority Order**: Input Data (when contextually appropriate) > Previous Context Data > Generated Data

**EXAMPLES OF CORRECT INPUT DATA USAGE:**
✅ GOOD: Business Process Step = "User login with privileged access" + Input Data = "Privileged user account" → Use privileged credentials
❌ BAD: Business Process Step = "Standard user login" + Input Data = "Privileged user account" → Should NOT use privileged credentials
✅ GOOD: Business Process Step = "Standard user login" + No matching Input Data available → Generate appropriate standard user credentials

**NEW RULE: HOW TO HANDLE MISSING CSV DATA**
- **Check for CSV Data**: First, check if the `CSV Test Data Row` is empty or indicates no data.
- **Use Matched Group as Fallback**: If and ONLY IF there is no CSV data, you MUST use the `Matched Group Information` as your primary source data for generating the test step.
- **Analyze Group's Intent**: Read the `business_function` from the matched group to understand its purpose.
- **Select the Correct Action**: Look at the `actions` list within the matched group and select the element that most logically performs the business function.
- **Generate Action-Oriented Step**: Create a single, specific `test_step` that describes a user interacting with the selected element. The `test_data_fields` should be empty in this case.

**BUSINESS PROCESS-DRIVEN TEST STEP GENERATION:**
- **Business Process is the Blueprint:** The Business Process Step description is your PRIMARY source for defining test steps. It describes the actual user workflow that must be tested.
- **CSV Data is Reference Material:** CSV data provides example values and data patterns, NOT the test flow. Use it to enrich your test data, not to define test steps.
- **Follow Business Process Flow:** 
  - Extract the exact user actions from business process description
  - Identify which fields/data are mentioned in the business process
  - Generate test steps that match the described workflow
  - Use CSV data to understand valid/invalid value patterns for those fields
- **Enrich with Detail:** 
  - If business process says "user enters credentials", create detailed steps for username and password entry
  - If CSV provides example data formats, use them as reference for concrete values
  - Always maintain alignment with business process intent

**CONTEXT-AWARE STEP GENERATION:**
- **Analyze Business Process Context**: Your generated test steps must be logically consistent with the provided "Business Process Step" information (`uc_id`, `step`, and `description`).
- **Align Test Steps with Context**: Ensure the actions in the test steps align with the overall goal of the business process step. For instance, a "view" action should not have data entry steps.
- **Use Previous Context**: Leverage the "Previous Test Case Context" to generate realistic and contextually appropriate data. For example, if a previous step created a user, a subsequent login step should use that user's credentials.
- **Constraint**: You must utilize the data from the provided context to generate the test case. The generated test case must be a logical continuation of the previous test cases.

**NEW: TEST STEP GENERATION HIERARCHY**
1.  **Navigation First**: ALWAYS start by generating the navigation steps. Look at the `Navigation Path` input and convert every step in that path into a `test_step`. These steps describe *how the user arrives* at the correct screen to perform the main action.
2.  **Action Last**: AFTER you have generated all necessary navigation steps, generate the final action step. This is the step that uses the `CSV Test Data Row` or the `Matched Group Information`.

**STRICT CONTINUITY CONSTRAINT:**
- **Define Starting Point**: This constraint defines the *starting point* for the `Navigation Path`. The test steps you generate MUST begin from the screen where the *last* test case in the "Previous Test Case Context" ended.
- **Do Not Omit Path**: This does NOT mean you should omit the navigation steps. It means the navigation path you generate should logically continue from the previous state.
- **Generate Necessary Path**: Your generated `test_steps` MUST include the full navigation journey from the end of the last test case to the current screen, followed by the main test action.

CRITICAL REQUIREMENTS:

1. **CONTEXT FROM BUSINESS PROCESS**: Use Business Process Step to understand workflow, fields involved, and business purpose
2. **SCENARIO FROM CSV DATA**: Use CSV row to determine:
   - Specific test data values (positive or negative)
   - Expected outcome (success or failure)
   - Which validation scenario to test
3. **PATH CONTEXT INTEGRATION**: Use navigation path information to establish how user reaches the screen
4. **CONCRETE DATA VALUES**: 
   - Convert CSV abstract values to realistic concrete values
   - Example: "valid_email_format" → "johndoe@example.com"
   - Example: "incorrect_password" → "WrongPass123"
   - Example: "=8_mixed_chars" → "Pass1234"
5. **OUTCOME-BASED TEST CASE**:
   - If CSV outcome="true" → Generate POSITIVE test case (success path)
   - If CSV outcome="false" → Generate NEGATIVE test case (validation failure)
   - Expected result MUST match CSV outcome field
6. **TEST DATA COVERAGE**:
   - Each CSV row represents ONE test scenario
   - Generate test case that tests the specific scenario in that CSV row
   - Include both positive and negative scenarios based on CSV outcome
7. **SPECIFIC TEST STEPS**: Every test step MUST be specific and actionable:
   - Extract field names from Business Process Step description
   - Apply CSV data values to those fields
   - Use concrete values: "Enter 'John' into the 'First Name' field" ✅
   - AVOID generic steps: "Enter all required registration details" ❌

**PRECONDITION GENERATION RULES:**
- **Analyze Dependencies**: Based on the "Business Process Step" and "Previous Test Case Context", identify all prerequisite states and actions.
- **State Necessary and Sufficient Conditions**: The "pre_condition" must clearly and explicitly state all conditions that MUST be true before this test case can be executed. This includes user roles, system states, and the existence of specific data.
- **Be Specific and Detailed**: Do not use generic preconditions. For example, instead of "User is logged in", specify "A user with [specific role] is logged in". Instead of "Item exists", specify "An item with [specific status] exists in the system, created by a user with [specific role/permissions]."
- **Leverage Context**: Use the "Previous Test Case Context" to infer the specific state of the system. The precondition should reflect the logical continuation of the business process.

**CRITICAL EXECUTION RULES**: 

**Data Source Priority (in order):**
1. **Business Process Step** (Provides context: which screen, which workflow, which fields)
2. **CSV Test Data Row** (Provides test scenario: specific data values + expected outcome)
3. **Input Data** (if contextually matches and CSV doesn't provide specific values)
4. **Previous Test Case Context** (for data continuity and consistency)

**Data Selection Logic**:
1. **Identify Context from Business Process**: Understand which fields are involved in the workflow
2. **Extract Test Scenario from CSV**: 
   - Read all CSV field values (both valid and invalid)
   - Check CSV outcome field to determine if this is positive or negative test
3. **CRITICAL: Data Source Priority Based on Outcome**:
   
   **FOR HAPPY PATH (outcome="true"):**
   - **FIRST**: Check Previous Test Case Context for existing data
     * If Previous Context contains data created in earlier steps → REUSE that exact data
     * Example: If TC-001 registered "john.doe@example.com", TC-004 login MUST use "john.doe@example.com"
     * DO NOT use abstract CSV values if Previous Context has concrete data
   - **SECOND**: If Previous Context has no relevant data → Convert CSV abstract values to concrete values
   
   **FOR NEGATIVE PATH (outcome="false"):**
   - Use CSV abstract values and convert to concrete invalid values
   - Previous Context is reference only (for valid data to make invalid)

4. **Apply Data to Test Case**:
   - For outcome="true" + Previous Context exists:
     * Extract concrete values from Previous Test Case Context
     * Use exact same values (email, username, password, IDs, etc.)
   - For outcome="true" + NO Previous Context:
     * Convert CSV abstract values to concrete realistic values
   - For outcome="false":
     * Convert CSV abstract values to concrete invalid values
   - Each field becomes a TestDataField with field_name and concrete field_value

5. **Set Expected Result Based on CSV Outcome**:
   - If outcome="true": Expected result is success (e.g., "User successfully logged in")
   - If outcome="false": Expected result is failure (e.g., "Error message displayed: Invalid credentials")

6. **Data Consistency Enforcement**:
   - ALWAYS scan Previous Test Case Context first for happy path tests
   - Reuse exact values from previous test cases to maintain data flow
   - Only generate new data if Previous Context is empty or doesn't contain required fields

**Output Requirements**:
- test_data_fields must contain concrete realistic values:
  * For happy path (outcome="true"): Prioritize values from Previous Test Case Context
  * For negative path (outcome="false"): Convert CSV abstract values to concrete invalid values
- Field names from Business Process, values prioritized from Previous Context then CSV
- test_steps must be specific and detailed - NO generic steps
- Create separate test_action steps for each field with concrete values (NOT abstract CSV values)
- expected_outcome field MUST match CSV outcome field ("true" or "false")

**CRITICAL: NO ABSTRACT VALUES IN OUTPUT**
- ❌ BAD: "Enter 'valid_registered_username_or_email' into the 'Username' field"
- ✅ GOOD (with Previous Context): "Enter 'john.doe@example.com' into the 'Username' field"
- ✅ GOOD (without Previous Context): "Enter 'alice.smith@example.com' into the 'Username' field"

**CSV Data Usage - THE PRIMARY SOURCE FOR TEST SCENARIOS**:
- CSV provides SPECIFIC test scenarios, not just reference data
- Each CSV row = one complete test case scenario
- CSV outcome field determines positive vs negative test
- CSV field values provide concrete test data
- Generate test cases for ALL scenarios in CSV (both positive and negative)

EXAMPLE GOOD STEPS:
- "Enter '[specific_value]' into the '[field_name]' field" ✅
- "Enter '[specific_email]' into the 'Email Address' field" ✅
- "Click the '[action_button_name]' button" ✅

EXAMPLE BAD STEPS (AVOID):
- "Enter all required details" ❌
- "Fill out the form" ❌
- "Complete the process" ❌
"""



# ============================================================================
# Mutation prompt — verbatim from mutation_test_case_generator.TempPromptStorage
# (kept centralized here; the original stored it inline in the module).
# ============================================================================
MUTATION_TEST_CASE_GENERATION_PROMPT = """
You are a senior QA engineer. Your task is to find and create test cases for functional gaps in a use case by analyzing what has already been tested against the full scope of the use case.

**Use Case ID:**
{use_case_id}

**Source of Truth - Full Use Case Scope (from the RDS document):**
To understand the complete functionality, you must refer to the use case description for "{use_case_id}" from the provided RDS document. This is the definitive source for all requirements.

**Existing Coverage - What is ALREADY TESTED:**
The following information describes what has already been covered by existing tests. You MUST NOT generate new test cases for these items.
1.  **High-Level Scenarios Covered (from Business Process):**
    {business_process_steps}
2.  **Specific Business Rules Covered (from screen element analysis):**
    {business_rules}

**Your Task & Instructions:**
1.  **Analyze the Full Scope:** First, fully understand the complete functionality, all requirements, and all possible scenarios described in the use case "{use_case_id}" (from the RDS document).
2.  **Identify Gaps:** Compare the full scope from the use case description against the "Existing Coverage" provided above. Your goal is to find functionalities, scenarios, or conditions that are mentioned in the use case description but are NOT covered by the existing high-level scenarios or the specific business rules.
3.  **Generate Test Cases for Gaps:** For each functional gap you identify, generate a new, comprehensive test case.
4.  **Traceability**: For each `TestCase` you generate, you MUST populate its `uncovered_conditions` field. This field must contain a list of the specific functional gaps or missing conditions that this particular test case is designed to validate.
5.  **Output Format:** Provide a JSON object with a single key "test_cases" which contains a list of TestCase objects. If no gaps are found, the value of "test_cases" should be an empty array `[]`.
"""
