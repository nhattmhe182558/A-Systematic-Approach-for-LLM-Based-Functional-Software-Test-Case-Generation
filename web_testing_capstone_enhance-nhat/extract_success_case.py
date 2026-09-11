import os
import json
import shutil

# Configuration
SOURCE_DIR = "generated_testcase_action_forth_attempt"
DEST_DIR = "extract_success_llm"

def extract_successful_cases():
    count = 0
    
    # Check if source exists
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory '{SOURCE_DIR}' not found.")
        return

    print(f"Scanning '{SOURCE_DIR}' for cases where llm_fail is false...")

    # Walk through the directory tree
    total_success = []
    total_tc = []
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Logic to find llm_fail = false
                # Based on your structure: List -> Object -> evaluation -> llm_fail
                is_success = False
                
                if isinstance(data, list):
                    for item in data:
                        if item["evaluation"]["result"]:
                            total_success.append(item["test_case_info"]["test_case_id"])

                        total_tc.append(item)

    return total_success
                

if __name__ == "__main__":
    success_list = extract_successful_cases()
    success_set = set(success_list)
    tc_list = [
    "TC-004, TC-007, TC-014, TC-017",
    "TC-001, TC-097, TC-105, TC-121, TC-123, TC-132, TC-136, TC-139, TC-140, TC-146, MTC-001, MTC-002, MTC-003, MTC-004, MTC-005",
    "TC-006, TC-007, TC-008, TC-009, TC-010, TC-011, TC-012, TC-013, TC-014, TC-016, TC-017, TC-018, TC-019, TC-020, MTC-004",
    "TC-001, TC-097, TC-105, TC-121, TC-123, TC-132, TC-139, TC-140, TC-146, MTC-001, MTC-002, MTC-003, MTC-005",
    "TC-005, TC-006, TC-015, TC-016, MTC-045",
    "TC-001, TC-097, TC-105, TC-121, TC-123, TC-132, TC-136, TC-139, TC-140, TC-146, MTC-001, MTC-002, MTC-003, MTC-004, MTC-005",
    'TC-006, TC-007, TC-008, TC-009, TC-010, TC-011, TC-012, TC-013, TC-014, TC-016, TC-017, TC-018, TC-019, TC-020, MTC-004',
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
    "-",]

    result = []

    for group in tc_list:
        # Split group into individual test IDs and strip spaces
        items = [x.strip() for x in group.split(",")]
        
        # Keep only items present in success_list
        matched = [tc for tc in items if tc in success_set]
        
        print(matched)
        print(len(matched))