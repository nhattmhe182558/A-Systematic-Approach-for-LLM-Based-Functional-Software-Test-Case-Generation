import pandas as pd
import json
from typing import List, Dict

# Assuming LLMCaller is imported from your module
# from your_module import LLMCaller

def extract_excel_data(filename):
    """
    Extract data from an Excel file and return as a list of dictionaries.
    Skips the first row (formulas) and uses the second row as column names.
    
    Args:
        filename: Path to the Excel file
        
    Returns:
        List of dictionaries with column names as keys
    """
    # Read Excel file, skipping the first row and using second row as header
    df = pd.read_excel(filename, header=0, engine='openpyxl')
    
    # Convert DataFrame to list of dictionaries
    data = df.to_dict('records')
    
    return data


def save_to_excel(data: List[Dict], filename: str):
    """
    Save list of dictionaries to Excel file.
    
    Args:
        data: List of dictionaries to save
        filename: Output Excel filename
    """
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"Saved data to {filename}")


def evaluate_test_mapping(test_result: Dict, form_validations: List[Dict], llm_caller) -> List[int]:
    """
    Use LLM to evaluate which form validation rules are relevant to a test result.
    
    Args:
        test_result: Dictionary containing test information (ID, test_name, test_intent, etc.)
        form_validations: List of dictionaries containing form validation rules
        llm_caller: LLMCaller instance
        
    Returns:
        List of form validation IDs that are relevant to the test
    """
    # Prepare the prompt for the LLM
    prompt = f"""You are a QA analyst evaluating test cases against form validation rules.

Given this test case:
- ID: {test_result.get('ID')}
- Test Name: {test_result.get('test_name')}
- Test Intent: {test_result.get('test_intent')}
- Test Status: {test_result.get('test_status')}

Analyze which of the following form validation rules are relevant to this test case. Consider:
- Does the test verify this validation rule?
- Does the test interact with the screen/element mentioned?
- Does the test intent align with validating this rule?
- It could be using during the test, no need for it to verify the intent

Form Validation Rules:
{json.dumps(form_validations, indent=2)}

Return a JSON object with a list of relevant form validation IDs (numbers only).
If no validation rules are relevant, return an empty array.

Example response format:
{{"relevant_ids": [77, 82, 95]}}
or
{{"relevant_ids": []}}"""

    # Define the schema for the response
    schema = {
        "type": "object",
        "properties": {
            "relevant_ids": {
                "type": "array",
                "items": {
                    "type": "integer"
                },
                "description": "List of form validation IDs that are relevant to the test case"
            }
        },
        "required": ["relevant_ids"]
    }

    try:
        # Use generate_json with schema
        response = llm_caller.generate_json(prompt, schema=schema)
        print(f"  LLM Response: {response}")
        return response['relevant_ids']
        
    except Exception as e:
        print(f"  Error evaluating test mapping: {e}")
        return []


# Example usage
if __name__ == "__main__":
    # Import LLMCaller (adjust import path as needed)
    from LLMCaller import LLMCaller
    
    # Initialize LLMCaller with your API keys
    API_KEYS = [
        "AIzaSyAg6FEWAQBflLyCMmlgRjg62sKNwB-oGZo",
    ]
    
    llm_caller = LLMCaller(API_KEYS, model_name='gemini-2.5-flash')
    
    try:
        # Extract test results
        results = extract_excel_data("test_result.xlsx")
        
        # Extract form validations
        form_test = extract_excel_data("form_compare.xlsx")
        
        print(f"Loaded {len(results)} test results")
        print(f"Loaded {len(form_test)} form validation rules\n")
        
        # Initialize relevant_ids field for each form validation rule
        for row in form_test:
            row["Relevant_testcase"] = []

        # Evaluate and map test results to form validation rules
        for i, result in enumerate(results, 1):
            print(f"\nProcessing test {i}/{len(results)}: {result.get('ID')}")
            print(f"  Test Name: {result.get('test_name')}")
            
            # Get matching form validation IDs from LLM
            matching_ids = evaluate_test_mapping(result, form_test, llm_caller)
            
            # Store the matching IDs in the test result
            result["relevant_ids"] = matching_ids
            print(f"  Mapped to form validation IDs: {matching_ids}")

            # Update form_test items with the test case ID
            for form_test_id in matching_ids:
                for item in form_test:
                    if int(item["ID"]) == form_test_id:
                        item["Relevant_testcase"].append(result["ID"])
                        break

        # Save updated form_test to Excel
        output_filename = "form_compare_updated.xlsx"
        save_to_excel(form_test, output_filename)
        
        # Optionally, also save updated test results
        results_output_filename = "test_result_updated.xlsx"
        save_to_excel(results, results_output_filename)
        
        print(f"\n{'='*60}")
        print("Processing complete!")
        print(f"Form validation rules saved to: {output_filename}")
        print(f"Test results saved to: {results_output_filename}")
        print(f"{'='*60}")
            
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()