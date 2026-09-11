import json
import pandas as pd
import os
import re

# ==========================================
# 1. HELPER: ID NORMALIZATION
# ==========================================

def normalize_tc_id(tc_id):
    """
    Converts various ID formats into a standard TC-XXX format.
    Input: "tc_004", "TC4", "MTC-1", "TC-004_batch"
    Output: "TC-004", "TC-004", "MTC-001", "TC-004"
    """
    if not tc_id:
        return ""
    
    # Uppercase and basic cleanup
    clean_id = tc_id.strip().upper()
    
    # Flexible Regex: Matches TC or MTC, followed by optional separator (- or _ or space), followed by digits
    match = re.search(r"(TC|MTC)[-_\s]?(\d+)", clean_id)
    
    if match:
        prefix = match.group(1) # TC or MTC
        number = match.group(2) # e.g. 4 or 004
        # Standardize to TC-004 (3 digits padded)
        return f"{prefix}-{number.zfill(3)}"
    
    return clean_id # Return original if pattern not found

# ==========================================
# 2. DATA MAPPING
# ==========================================

use_cases = [
    "UC-COM-01", "UC-COM-01", "UC-COM-01", "UC-COM-01", "UC-COM-01", "UC-COM-01", "UC-COM-01", "UC-COM-01", 
    "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", 
    "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", 
    "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-02", "UC-COM-03", "UC-COM-03", "UC-COM-03", 
    "UC-COM-03", "UC-COM-03", "UC-COM-03", "UC-COM-04", "UC-COM-04", "UC-COM-05", "UC-COM-05", "UC-COM-05", 
    "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", 
    "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-05", "UC-COM-06", 
    "UC-COM-06", "UC-COM-06", "UC-COM-06", "UC-COM-06", "UC-COM-06", "UC-COM-06", "UC-COM-06", "UC-COM-07", 
    "UC-COM-07", "UC-COM-07", "UC-COM-07", "UC-COM-07", "UC-COM-07", "UC-COM-08", "UC-COM-08", "UC-COM-08", 
    "UC-COM-08", "UC-COM-08", "UC-COM-08", "UC-COM-08", "UC-COM-08"
]

screens = [
    "Login Modal", "Login Modal", "Login Modal", "Login Modal", "Login Modal", "Login Modal", "Login Modal", "Login Modal", 
    "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", 
    "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", 
    "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Registration Modal", "Add New Course Modal", "Add New Course Modal", "Add New Course Modal", 
    "Add New Course Modal", "Add New Course Modal", "Add New Course Modal", "Info Tab", "Info Tab", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", 
    "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", 
    "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", "Add New Attenders Modal", 
    "Add New Attenders Modal", "New/Modify Session Modal", "New/Modify Session Modal", "New/Modify Session Modal", "New/Modify Session Modal", "New/Modify Session Modal", "New/Modify Session Modal", 
    "New/Modify Session Modal", "New/Modify Session Modal", "New Entry Modal", "New Entry Modal", "New Entry Modal", "New Entry Modal", "New Entry Modal", "New Entry Modal", 
    "Add files Modal", "Add files Modal", "New File Group Modal", "New File Group Modal", "Add files Modal", "Add files Modal", "Add files Modal", "Add files Modal"
]

relevant_tcs = [
    "TC-004, TC-007, TC-014, TC-017",
    "TC-001, TC-097, TC-105, TC-121, TC-123, TC-132, TC-136, TC-139, TC-140, TC-146, MTC-001, MTC-002, MTC-003, MTC-004, MTC-005",
    "TC-006, TC-007, TC-008, TC-009, TC-010, TC-011, TC-012, TC-013, TC-014, TC-016, TC-017, TC-018, TC-019, TC-020, MTC-004",
    "TC-001, TC-097, TC-105, TC-121, TC-123, TC-132, TC-139, TC-140, TC-146, MTC-001, MTC-002, MTC-003, MTC-005",
    "TC-005, TC-006, TC-015, TC-016, MTC-045",
    "TC-001, TC-097, TC-105, TC-121, TC-123, TC-132, TC-136, TC-139, TC-140, TC-146, MTC-001, MTC-002, MTC-003, MTC-004, MTC-005",
    "TC-006, TC-007, TC-008, TC-009, TC-010, TC-011, TC-012, TC-013, TC-014, TC-016, TC-017, TC-018, TC-019, TC-020, MTC-004",
    "TC-001, TC-097, TC-105, TC-121, TC-123, TC-132, TC-139, TC-140, TC-146, MTC-001, MTC-002, MTC-003, MTC-005",
    "TC-049, TC-050, TC-051, TC-057, TC-062, TC-063, TC-065, TC-066, TC-067, TC-068, TC-069, TC-071, TC-072, TC-073, TC-074, TC-075, TC-076, TC-079, TC-081, TC-082, TC-084, TC-085, TC-086, TC-087, TC-088, TC-089, TC-090, TC-091, TC-092, TC-093, TC-094, TC-095",
    "TC-046, MTC-021",
    "TC-056, TC-075, TC-078, TC-088, TC-093",
    "TC-046, MTC-021",
    "TC-046, MTC-022",
    "TC-046, MTC-023",
    "TC-046, MTC-024",
    "TC-051, TC-056, TC-067, TC-076, TC-084, TC-085, TC-088",
    "TC-052, TC-055, TC-074, TC-075",
    "TC-053, TC-054, TC-071, TC-082, TC-086",
    "TC-046",
    "TC-049, TC-060, TC-061, TC-064, TC-089, TC-095",
    "TC-050, TC-068, TC-069, TC-078, TC-083, TC-092",
    "TC-049, TC-052, TC-058, TC-063, TC-067, TC-071, TC-082, TC-083, TC-085, TC-086, TC-087, TC-088, TC-091, TC-092, TC-093, TC-094, TC-095",
    "TC-046",
    "TC-046, TC-047, TC-048, TC-049, TC-051, TC-055, TC-057, TC-065",
    "TC-050, TC-052, TC-053, TC-054, TC-056, TC-058, TC-059, TC-060, TC-061, TC-062, TC-063, TC-064, TC-066, TC-067, TC-069, TC-070, TC-071, TC-072, TC-073, TC-074, TC-075, TC-076, TC-077, TC-078, TC-079, TC-080, TC-081, TC-082, TC-083, TC-084, TC-085, TC-086, TC-087, TC-088, TC-089, TC-090, TC-091, TC-092, TC-093, TC-094, TC-095",
    "TC-050, TC-051, TC-052, TC-055, TC-061, TC-064, TC-066, TC-071, TC-074, TC-080, TC-081, TC-085, TC-086, TC-093, TC-094",
    "TC-046, TC-053, TC-054, TC-060, TC-067, TC-079, TC-087",
    "TC-047, TC-053, TC-054, TC-058, TC-061, TC-062, TC-068, TC-072, TC-074, TC-076, TC-077, TC-078, TC-079, TC-089, TC-090",
    "TC-046, TC-049, TC-050, TC-051, TC-052, TC-055, TC-056, TC-060, TC-063, TC-064, TC-065, TC-066, TC-067, TC-069, TC-070, TC-071, TC-073, TC-075, TC-080, TC-081, TC-082, TC-083, TC-084, TC-085, TC-086, TC-087, TC-088, TC-089, TC-091, TC-092, TC-093, TC-094, TC-095",
    "TC-023, TC-024",
    "TC-021, TC-162",
    "TC-022, TC-023",
    "TC-021, TC-024, TC-162",
    "-",
    "TC-021, TC-162",
    "TC-026, TC-027",
    "TC-025",
    "TC-101",
    "TC-098, TC-099, TC-102, TC-103",
    "TC-149, MTC-022",
    "TC-153, MTC-022, MTC-025",
    "MTC-023",
    "TC-150",
    "TC-102",
    "TC-098, TC-099",
    "TC-103",
    "TC-098, TC-099",
    "MTC-022",
    "TC-149",
    "TC-153",
    "TC-149",
    "MTC-023",
    "TC-150",
    "MTC-023",
    "TC-150",
    "TC-028, TC-032, TC-034, TC-036, TC-037, TC-040, TC-042",
    "TC-031, TC-035, TC-041",
    "TC-030, TC-031, TC-032, TC-035, TC-036, TC-037, TC-038, TC-041, TC-042",
    "TC-028, TC-033, TC-034, TC-039, TC-040",
    "TC-028, TC-031, TC-035, TC-040",
    "TC-030, TC-032, TC-033, TC-034, TC-036, TC-037, TC-038, TC-039, TC-041, TC-042",
    "-",
    "TC-028, TC-040",
    "TC-106, TC-108, TC-109, TC-112, TC-113",
    "TC-107, TC-110, TC-111, TC-114",
    "TC-106, TC-108, TC-109, TC-110, TC-113, TC-114",
    "TC-107, TC-111, TC-112",
    "-",
    "TC-107",
    "TC-043, TC-119",
    "TC-044",
    "-",
    "TC-156",
    "TC-043, TC-119, TC-150",
    "-",
    "TC-043, TC-119, TC-150",
    "-"
]

descriptions = [
    "These test cases cover invalid email formats by using the input value invalid_format_username_or_email.",
    "Covered by all successful login test cases using valid emails like GiangGiangteacher@gmail.com and student_newuser@example.com.",
    "Covers a wide range of invalid passwords including null, empty string (\"\"), whitespace (\" \"), and incorrect_password.",
    "Covered by all successful login test cases using valid passwords like ValidPassword123!Giangteacher and NewStudent123!.",
    "These test cases use non-existent or unregistered emails like unregistered_username_or_email and unregistered_user@example.com.",
    "This is the positive case for a valid login, covered by test cases using existing, registered emails.",
    "Covered by test cases using incorrect, null, empty, or whitespace passwords against a valid user.",
    "This is the positive case for a valid login, covered by test cases using correct, matching passwords.",
    "Extensive coverage using pairs like (short1, no_match2), (password_more_than_20_chars_example_123, non_matching_password_example), etc.",
    "Covered by the successful registration test case where Password and Confirm Password are both NewStudent123!.",
    "These test cases use emails known to already exist, such as student.existing@example.com and existing_email@example.com.",
    "Covered by the successful registration case using the unique email student_newuser@example.com.",
    "The successful registration password NewStudent123! contains digits.",
    "The successful registration password NewStudent123! contains lowercase letters.",
    "The successful registration password NewStudent123! contains an uppercase letter.",
    "These test cases use passwords like password_no_digit, NoDigitPass, and passwordnodigit.",
    "These test cases use passwords like PASSWORD123! and WEAKPASS123! which lack lowercase letters.",
    "These test cases use passwords like password_no_uppercase and password which lack uppercase letters.",
    "The successful registration password NewStudent123! has a length of 14, which is within the valid range.",
    "These test cases cover short passwords with values like short1 (length 6) and short (length 5).",
    "These test cases cover long passwords with values like password_more_than_20_chars_example_123 and ThisIsAVeryLongPasswordThatExceedsTwentyCharacters.",
    "Extensively covered with the input value existing_username.",
    "Covered by the successful registration test case using the unique username student_newuser.",
    "All successful and many failed registration attempts cover a completed reCAPTCHA.",
    "Extensive coverage of failed registration due to reCAPTCHA field value being false.",
    "Extensive coverage with values like invalid_email_no_at_sign and invalid_email_no_domain.",
    "Covered by successful registration and various failed attempts that still used a valid email format.",
    "Extensive coverage with Username field value being an empty string (\"\").",
    "Covered by all test cases that use a non-empty username, including the successful registration.",
    "These test cases explicitly test with a null value for the course image.",
    "Covered by successful course creation cases using software_eng_image.jpg and temp_course_image.jpg.",
    "These test cases explicitly test with a null value for the course name.",
    "Covered by successful course creation cases using valid, non-empty course names.",
    "No test case attempts to create a new course with a name that is identical to an existing course.",
    "This is the positive case, implicitly covered by all successful course creation test cases.",
    "Covers both null and whitespace-only (\" \") inputs for the course information field.",
    "Covered by the successful update of course information with a non-empty string.",
    "Test case TC-101 explicitly tests enrolling a student with the invalid email format invalid_email_format.",
    "Covered by all single-student enrollment test cases that use a structurally valid email.",
    "Test case TC-149 covers this by attempting to enroll multiple students with a list of valid emails: student_valid_1@example.com, student_valid_2@example.com.",
    "Test case TC-153 provides a mixed list including the invalid format email invalid-email.",
    "The test file content includes an improperly formatted email (\"invalid-file-email\").",
    "Test case TC-150 tests uploading a file named valid_file_with_emails_not_enrolled.txt.",
    "Test case TC-102 explicitly tests enrolling a student with an unregistered email: unregistered@example.com.",
    "This is the positive case for single enrollment, covered by test cases using existing, registered student emails.",
    "Test case TC-103 explicitly tests enrolling a student who is already in the course using the email already_enrolled_email.",
    "This is the positive case for single enrollment, covered by test cases adding a new, valid student.",
    "Test data includes \"student_nonexistent@example.com\" to verify the system handles users not found in the database.",
    "This is the positive case for bulk enrollment, covered by TC-149 where all provided emails belong to existing students.",
    "Test case TC-153 provides a mixed list that includes the email student_already_enrolled@example.com.",
    "This is the positive case for bulk enrollment, covered by TC-149 where all provided emails are for students not yet in the course.",
    "The test file includes \"student_nonexistent_from_file@example.com\".",
    "This is the positive case for file enrollment, covered by TC-150 which uses a file of valid, existing students.",
    "The test file includes \"student_already_enrolled@example.com\".",
    "This is the positive case for file enrollment, covered by TC-150 which uses a file of students not yet in the course.",
    "All successful session creations and many failed ones cover a selected date, e.g., 2024-06-15.",
    "These test cases explicitly use null or whitespace values for the date picker.",
    "Extensive coverage of empty titles using null, \"\", and whitespace  .",
    "All successful session creation test cases cover this with valid titles.",
    "All successful session creations and some failed ones cover a selected time, e.g., 10:00 AM.",
    "Extensive coverage of empty time pickers using null, \"\", and whitespace  .",
    "No test case attempts to create a new session with a title that is identical to an existing session within the same course.",
    "This is the positive case, implicitly covered by all successful session creation test cases.",
    "Covers null, \"\", and whitespace   inputs for the entry comment field.",
    "Covered by successful entry creations and some failed attempts that used valid content.",
    "Covers null and whitespace   inputs for the entry title field.",
    "Covered by successful entry creations and some failed attempts that used a valid title.",
    "No test case attempts to create a new forum entry with a title that is identical to an existing entry.",
    "This is the positive case, implicitly covered by the successful forum entry creation test case.",
    "These test cases cover uploading syllabus.pdf and reference_document.pdf.",
    "Test case TC-044 explicitly tests attempting an upload with a null file selection.",
    "No test case attempts to create a new file group with an empty or whitespace-only title.",
    "Covered by the successful creation of a file group with the title Reference Materials.",
    "All successful file upload test cases implicitly cover this by using allowed file types like .pdf and .txt.",
    "No test case attempts to upload a file with a disallowed extension (e.g., .exe, .zip).",
    "All successful file upload test cases implicitly cover this by using files that are presumably within the size limit.",
    "No test case attempts to upload a file that is explicitly stated to be larger than the maximum allowed size."
]

df = pd.DataFrame({
    'Use Case': use_cases,
    'Screen': screens,
    'Relevant Test Case(s)': relevant_tcs,
    'Description': descriptions
})

# ==========================================
# 3. FILE PARSING WITH ROBUST MATCHING
# ==========================================

def get_test_metrics_from_file(file_path):
    """
    Reads a JSON file and tries to extract ID, Total Actions, and Success count.
    Prioritizes extraction from the FILENAME using flexible regex.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Normalize structure
        if isinstance(data, list):
            if not data: return None
            tc_data = data[0]
        elif isinstance(data, dict):
            tc_data = data
        else:
            return None

        # 1. Aggressive Filename Extraction
        filename = os.path.basename(file_path)
        # Regex to catch TC-046, TC_046, MTC 01, etc.
        match = re.search(r"(TC|MTC)[-_\s]?(\d+)", filename, re.IGNORECASE)
        
        raw_id = ""
        if match:
            # Reconstruct standard ID from filename parts
            raw_id = f"{match.group(1)}-{match.group(2)}" 
        else:
            # Fallback to internal ID if filename is weird (e.g. "output.json")
            tc_info = tc_data.get('test_case_info', {})
            raw_id = tc_info.get('test_case_id', '').strip()
        
        # 2. Normalize whatever we found
        tc_id = normalize_tc_id(raw_id)
        
        # 3. Calculate metrics
        execute_log = tc_data.get('execute_log', [])
        total = len(execute_log)
        success = sum(1 for step in execute_log if step.get('success') is True)
        
        if tc_id:
            return tc_id, total, success
            
    except Exception as e:
        # Silent fail or print if needed
        pass 
    
    return None

def calculate_metrics_from_folder(root_folder_path, output_excel_path):
    print(f"Scanning folder: {root_folder_path}")
    
    tc_metrics = {}
    file_count = 0
    
    # 1. Scan Files
    for root, dirs, files in os.walk(root_folder_path):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                result = get_test_metrics_from_file(full_path)
                
                if result:
                    tc_id, total, success = result
                    file_count += 1
                    tc_metrics[tc_id] = {
                        'total': total,
                        'success': success
                    }

    print(f"Processed {file_count} JSON files.")
    print(f"Extracted {len(tc_metrics)} unique Test Case IDs.")

    # 2. Map to DataFrame
    total_col = []
    success_col = []
    rate_col = []
    
    all_required_tcs = set()

    for index, row in df.iterrows():
        relevant_str = str(row['Relevant Test Case(s)'])

        if relevant_str == "-" or not relevant_str.strip():
            tcs_in_row = []
        else:
            tcs_in_row = [
                normalize_tc_id(x.strip())
                for x in relevant_str.split(',')
                if x.strip()
            ]

        # Deduplicate and track required
        tcs_in_row = list(set(tcs_in_row))
        all_required_tcs.update(tcs_in_row)

        row_total = sum(tc_metrics[tc]['total'] for tc in tcs_in_row if tc in tc_metrics)
        row_success = sum(tc_metrics[tc]['success'] for tc in tcs_in_row if tc in tc_metrics)

        total_col.append(row_total)
        success_col.append(row_success)
        
        if row_total > 0:
            rate_col.append(f"{(row_success/row_total)*100:.2f}%")
        else:
            rate_col.append("0.00%")

    df['Total Actions'] = total_col
    df['Successful Actions'] = success_col
    df['Success Rate (%)'] = rate_col

    # 3. Export
    try:
        final_columns = [
            'Use Case', 'Screen', 'Relevant Test Case(s)', 'Description', 
            'Total Actions', 'Successful Actions', 'Success Rate (%)'
        ]
        df[final_columns].to_excel(output_excel_path, index=False)
        print(f"\nSuccess! File generated at: {output_excel_path}")
    except Exception as e:
        print(f"Error writing Excel: {e}")

    # ==========================================
    # 4. DIAGNOSTIC REPORT (Crucial Step)
    # ==========================================
    print("\n--- DIAGNOSTIC REPORT ---")
    found_tcs = set(tc_metrics.keys())
    missing_tcs = all_required_tcs - found_tcs
    
    if len(missing_tcs) == 0:
        print("PERFECT: All Test Cases mentioned in the list were found in the folder.")
    else:
        print(f"WARNING: The following {len(missing_tcs)} Test Cases are mentioned in the Excel list but were NOT found in the folder:")
        # Print first 20 missing IDs to give a hint
        sorted_missing = sorted(list(missing_tcs))
        print(f"Sample Missing: {sorted_missing[:20]}")
        print("Possible reasons: Files do not exist, or filenames do not match expected pattern 'TC-XXX'.")

# ==========================================
# 5. EXECUTION
# ==========================================

target_folder = 'generated_testcase_action'

if not os.path.exists(target_folder):
    print(f"Error: Folder '{target_folder}' not found.")
else:
    calculate_metrics_from_folder(target_folder, 'Test_Case_Report_v2.xlsx')