import json


def create_prompt_for_test_design(requirements: list, technique: str):
    """Tạo prompt để sinh Test Design (Hình 9 & 10)."""
    reqs_block = "\n".join(f"- {r}" for r in requirements)
    system_prompt = f"""You are an AI test developer in the automotive industry. Your task is to create a high-quality '{technique}' for the given system-level requirements.
Your output must be a single, complete, and accurate markdown table. The table should cover all conditions and outcomes mentioned in the requirements.
"""
    user_prompt = f"""Create a {technique} for the following requirements:

Input Requirements:
{reqs_block}

Generate the markdown table now.
"""
    return system_prompt + user_prompt

def create_prompt_for_test_purposes(requirements: list, scenarios: list):
    """Tạo prompt để sinh Test Purposes (Hình 12 & 13)."""
    scenarios_str = "\n".join([f"Scenario {i+1}: {str(s)}" for i, s in enumerate(scenarios)])
    reqs_block = "\n".join(f"- {r}" for r in requirements)
    system_prompt = """You are an expert in system-level test development. Your task is to create a concise, high-level test purpose for each provided test scenario. A test purpose should describe what the test case intends to verify.
Your output must ONLY be a numbered list of test purposes, with each item corresponding to a scenario. DO NOT include any introductory or concluding remarks.
"""
    user_prompt = f"""Based on the following system requirements and {len(scenarios)} test scenarios, generate a test purpose for each scenario.
Your output must contain exactly {len(scenarios)} numbered test purposes.

System Requirements:
{reqs_block}

Test Scenarios:
{scenarios_str}

Output the result as a numbered list, where each item corresponds to a scenario. For example:
1. [Test purpose for Scenario 1]
2. [Test purpose for Scenario 2]
"""
    return system_prompt + user_prompt

def create_prompt_for_test_specification(test_purpose: str, test_scenario: dict, requirements: list, few_shot_examples: list):
    """Tạo prompt để sinh Test Specification cuối cùng (JSON) (Hình 14 & 15)."""
    example_str = ""
    for ex in few_shot_examples:
        example_str += f"EXAMPLE REQUIREMENT:\n{ex['requirement_text']}\n"
        example_str += f"EXAMPLE TEST SPECIFICATION (JSON):\n{ex['test_spec_json']}\n---\n"

    reqs_block = "\n".join(f"- {r}" for r in requirements)
    system_prompt = """You are an AI test developer in the automotive industry. Your task is to write a detailed, system-level test specification.
Your output must be a single, valid JSON object with four keys: "purpose", "precondition", "execution", "notes".
"""
    user_prompt = f"""Write a test specification for the following test purpose and test scenario.

Input Requirements:
{reqs_block}

Test Purpose: {test_purpose}
Test Scenario: {str(test_scenario)}

---
Here are some examples of similar requirements and their corresponding test specifications. Use them as a reference for style, structure, and content:
{example_str}
---

Generate the test specification JSON object now. Do not change the purpose. Respond only with the JSON object.
"""
    return system_prompt + user_prompt

# ==============================================================================
# PROMPT CHO REFLECTION AGENT
# ==============================================================================

def create_prompt_for_reflection(original_requirements: list, generated_spec: dict):
    import json
    """Tạo prompt cho Reflection Agent để đánh giá và cải thiện Test Spec."""
    reqs_block = "\n".join(f"- {r}" for r in original_requirements)
    system_prompt = """You are an AI test supervisor in the automotive industry, renowned for your meticulous attention to detail and upholding industry standards (like ISO 26262). Your task is to review a generated test specification and improve it.
Your output must be a single, valid JSON object representing the improved test specification.
"""
    user_prompt = f"""Please review and refine the following generated test specification.

Original System Requirements:
{reqs_block}

Generated Test Specification (JSON to be reviewed):
{json.dumps(generated_spec, indent=2)}

Critique and Refine:
- Is the 'purpose' clear and directly verifiable?
- Are the 'preconditions' complete? Is anything missing for a real-world test (e.g., system status, sensor states)?
- Are the 'execution' steps logical, unambiguous, and testable? Add more detail if needed.
- Are there any important 'notes' for the tester regarding safety or specific conditions?

Return the improved and refined JSON object. If no improvements are needed, return the original JSON object.
"""
    return system_prompt + user_prompt

def create_prompt_for_requirement_extraction(raw_doc_content: str, rules: str):
    """Tạo prompt để trích xuất User Requirements từ tài liệu thô."""
    system_prompt = f"""You are an expert in software requirements engineering. Your task is to extract user requirements from the provided raw document content.
You must strictly follow the "Bộ Quy Tắc Viết Yêu Cầu (User Requirement)" provided below.
Each extracted requirement must be atomic (one requirement, one sentence), clearly state conditions and outcomes ("If... Then..." logic), be testable, and focus on "What" the system does, not "How" it does it (black-box testing).

Bộ Quy Tắc Viết Yêu Cầu (User Requirement):
{rules}

Your output should be a numbered list of extracted user requirements, one requirement per line.
"""
    user_prompt = f"""Extract user requirements from the following raw document content:

Raw Document Content (JSON):
{raw_doc_content}

Extract and list the user requirements now, strictly following the rules.
"""
    return system_prompt + user_prompt
