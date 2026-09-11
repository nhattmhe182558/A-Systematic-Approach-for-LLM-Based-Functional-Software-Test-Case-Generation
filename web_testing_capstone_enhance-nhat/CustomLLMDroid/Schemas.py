EVALUATE_NEXT_STEP_SCHEMA = {
    "type": "object",
    "properties": {
            "action": {
                "type": "string",
                "enum": ["click", "input", "upload" ,"wait","done"]
            },
            "selector_type": {
                "type": "string",
                "enum": ["id", "name", "class", "xpath", "text"]
            },
            "selector_value": {
                "type": "string"
            },
            "input_value": {
                "type": "string"
            },
            "reasoning": {
                "type": "string"
            },
            "done": {
                "type": "boolean"
            },
            "web_fail": {
                "type": "boolean"
            },
            "llm_fail" :
            {
                "type": "boolean"
            }
    },
    "required": ["action", "selector_type" , "selector_value", "input_value","reasoning", "web_fail", "llm_fail", "done"]
}

CHOOSE_EXISTING_STEP_SCHEMA = {
    "type": "object",
    "properties": {
            "tc_id":{
                "type": "string"
            },
            "confidence":{
                "type": "string"
            },
            "reasoning": {
                "type": "string"
            },
    },
    "required": ["tc_id", "confidence", "reasoning"]
}

GENERATE_FALSE_TESTCASE_SCHEMA = {
    "type": "object",
    "properties": {
        "execute_log": {
            "type": "array",
            "description": "The full sequence of action steps based on the success path, but modified to induce the failure.",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["click", "input", "done"],
                        "description": "The action to perform.."
                    },
                    "selector_type": {
                        "type": "string",
                        "description": "The type of selector (e.g., 'id', 'xpath', 'css')."
                    },
                    "selector_value": {
                        "type": "string",
                        "description": "The value of the selector."
                    },
                    "input_value": {
                        "type": "string",
                        "description": "The input text, if action is 'input'. Use an invalid/incorrect value to cause the failure."
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation for this specific step, especially if it was modified."
                    },
                    "done":
                    {
                        "type": "boolean"
                    }
                },
                "required": ["action", "selector_type", "selector_value", "input_value",  "reasoning"]
            }
        }
    },
    "required": ["execute_log"]
}

GENERATE_FALSE_TESTCASE_SCHEMAS = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "description": "Test steps that lead to failure",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["click", "input", "done"],
                        "description": "Action to perform"
                    },
                    "selector_type": {
                        "type": "string",
                        "enum": ["id", "name", "class", "xpath", "text"],
                        "description": "Type of selector"
                    },
                    "selector_value": {
                        "type": "string",
                        "description": "Value of the selector"
                    },
                    "input_value": {
                        "type": "string",
                        "description": "Value to input (for input actions)"
                    }
                },
                "required": ["action"]
            }
        },
        "assertions": {
            "type": "array",
            "description": "Assertions to verify the failure",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "element_exists",
                            "element_not_exists",
                            "text_contains",
                            "text_equals",
                            "url_contains",
                            "url_equals",
                            "element_visible",
                            "element_not_visible",
                            "element_enabled",
                            "element_disabled",
                            "attribute_equals",
                            "attribute_contains"
                        ]
                    },
                    "selector_type": {
                        "type": "string",
                        "enum": ["id", "name", "class", "xpath", "text"]
                    },
                    "selector_value": {
                        "type": "string"
                    },
                    "expected_value": {
                        "type": "string"
                    },
                    "attribute_name": {
                        "type": "string"
                    },
                    "description": {
                        "type": "string"
                    }
                },
                "required": ["type", "description"]
            }
        }
    },
    "required": ["steps", "assertions"]
}

VALIDATION_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "valid_action": {
            "type": "boolean",
            "description": "Whether the action executed without errors"
        },
        "result": {
            "type": "boolean",
            "description": "Whether the testcase follows the expected description"
        },
        "llm_fail":{
            "type": "boolean",
            "description": "Whether the execution log has been gen by LLM fail and cannot execute, in case web fail true mark this one false"
        },
        "web_fail":{
            "type": "boolean",
            "description": "Whether the web fail to show element or function that should been there"
        },
        "reasoning": {
            "type": "string",
            "description": "Explanation of why the test succeeded or failed"
        },
        "assertion_selector": {
            "type": "object",
            "properties": {
                "selector_type": {
                    "type": "string",
                    "enum": ["id", "name", "xpath", "css", "class_name"]
                },
                "selector_value": {
                    "type": "string",
                    "description": "The selector value that can be used for assertion"
                },
                "expected_content": {
                    "type": "string",
                    "description": "The expected text/attribute value for assertion"
                }
            },
            "required": ["selector_type", "selector_value", "expected_content"]
        }
    },
    "required": ["valid_action", "result", "reasoning", "assertion_selector"]
}