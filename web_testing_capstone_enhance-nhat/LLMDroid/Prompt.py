SUMMERIZE_PAGE_PROMPT = """Analyze this web page and provide a JSON response.

Website: {website_url}
Page HTML Description:
{page_html}

Top explored pages:
{top_pages_desc}

Provide:
1. A brief overview (max 30 words) of the page's purpose
2. List of 3-5 important functionalities with their element IDs
3. Importance ranking (1-10) compared to other pages

Respond ONLY with valid JSON in this format:
{{
    "overview": "brief description",
    "functionalities": {{
        "functionality_name": "element_id",
        ...
    }},
    "importance": 5
}}"""

SELECT_TARGET_PAGE = """Select the best page and functionality to test next for comprehensive web testing.

Website: {website_url}

Explored pages and their functionalities:
{pages_desc}

Strategy:
- Prioritize navigation-related functionalities
- Choose functionalities that lead to new pages
- Avoid already tested functionalities

Respond ONLY with valid JSON:
{{
    "target_page_id": 0,
    "target_functionality": "functionality_name",
    "target_element_id": "element_id",
    "reasoning": "brief explanation"
}}"""

GUIDE_EXECUTION_STEP_PROMPT = """Guide the next step to execute this functionality.

Target functionality: {target_functionality}
Previous actions: {actions_desc}

Current page:
{page_html}

Respond ONLY with valid JSON:
{{
    "finished": false,
    "element_id": "element_id_to_interact",
    "action_type": "click|input|scroll",
    "input_text": "text if action is input, otherwise empty"
}}"""
