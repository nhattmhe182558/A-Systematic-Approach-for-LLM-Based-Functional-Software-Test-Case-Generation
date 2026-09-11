import json
import google.generativeai as genai
from typing import Dict, List, Optional
from LLMDroid.dataObject import PageCluster
from LLMDroid.Prompt import SUMMERIZE_PAGE_PROMPT, SELECT_TARGET_PAGE, GUIDE_EXECUTION_STEP_PROMPT
class GeminiInterface:
    """Interface for Google Gemini API"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def summarize_page(self, page_html: str, website_url: str, top_pages: List[PageCluster]) -> Dict:
        """Summarize page using Gemini API"""
        
        top_pages_desc = "\n".join([
            f"Page {i}: {cluster.summary[:100]}" 
            for i, cluster in enumerate(top_pages[:5])
        ])
        
        prompt = SUMMERIZE_PAGE_PROMPT.format(
    website_url=website_url,
    page_html=page_html,
    top_pages_desc=top_pages_desc
)
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip())
            return result
        except Exception as e:
            print(f"[LLM Error] {e}")
            return {
                "overview": "Page overview unavailable",
                "functionalities": {},
                "importance": 5
            }
    
    def select_target(self, top_pages: List[PageCluster], website_url: str) -> Optional[Dict]:
        """Select target page and functionality using Gemini API"""
        
        if not top_pages:
            return None
        
        pages_desc = "\n".join([
            f"Page {cluster.root_page.page_id}: {cluster.summary}\n  Functionalities: {list(cluster.functionalities.keys())[:3]}"
            for cluster in top_pages[:10]
        ])
        
        prompt = SELECT_TARGET_PAGE.format(
            website_url=website_url,
            pages_desc=pages_desc
        )
                
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip())
            return result
        except Exception as e:
            print(f"[LLM Error] {e}")
            return None
    
    def guide_execution_step(self, page_html: str, previous_actions: List[str], 
                            target_functionality: str) -> Dict:
        """Guide execution step using Gemini API"""
        
        actions_desc = "\n".join(previous_actions[-3:]) if previous_actions else "None"
        
        prompt = GUIDE_EXECUTION_STEP_PROMPT.format(
            target_functionality=target_functionality,
            actions_desc=actions_desc,
            page_html=page_html
        )
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text.strip())
            return result
        except Exception as e:
            print(f"[LLM Error] {e}")
            return {"finished": True, "element_id": "", "action_type": ""}
