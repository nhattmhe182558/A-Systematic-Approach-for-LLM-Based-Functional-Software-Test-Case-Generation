import google.generativeai as genai
import json
from typing import Any, Dict, Optional, List
from google.api_core.exceptions import PermissionDenied, ResourceExhausted
from google.api_core.exceptions import GoogleAPIError
from PIL import Image
from io import BytesIO
import base64

class LLMCaller:
    def __init__(self, api_keys, model_name='gemini-2.5-flash'):
        self.api_keys = api_keys
        self.current_index = 0
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self, generation_config: Optional[Dict] = None):
        """Initialize model with optional generation config."""
        genai.configure(api_key=self.api_keys[self.current_index])
        self.model = genai.GenerativeModel(
            self.model_name,
            generation_config=generation_config
        )
    
    def _switch_key(self):
        """Switch to next API key."""
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        genai.configure(api_key=self.api_keys[self.current_index])
        print(f"[LLMCaller] Switched to API key #{self.current_index}")
    
    def generate(self, *args, **kwargs) -> Any:
        """Original generate method."""
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(*args, **kwargs)
                return response
            except (PermissionDenied, ResourceExhausted, GoogleAPIError) as e:
                print(f"[LLMCaller] API key #{self.current_index} failed: {type(e).__name__} - {e}")
                self._switch_key()
        raise RuntimeError("All Gemini API keys failed after rotation.")
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
        # Build generation config
        config = {"response_mime_type": "application/json"}
        if schema:
            config["response_schema"] = schema
        
        # Reinitialize model with JSON config
        original_model = self.model
        self._initialize_model(generation_config=config)
        
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                # Restore original model
                self.model = original_model
                return json.loads(response.text)
                
            except (PermissionDenied, ResourceExhausted, GoogleAPIError) as e:
                print(f"[LLMCaller] API key #{self.current_index} failed: {type(e).__name__} - {e}")
                self._switch_key()
                self._initialize_model(generation_config=config)
                
            except json.JSONDecodeError as e:
                print(f"[LLMCaller] Failed to parse JSON: {e}")
                # Restore original model
                self.model = original_model
                raise
        
        # Restore original model before raising error
        self.model = original_model
        raise RuntimeError("All Gemini API keys failed after rotation.")
    

    def _prepare_image_for_gemini(self, image_base64: str) -> Image.Image:
        """
        Convert base64 string to PIL Image for Gemini
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            PIL Image object
        """
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        return image
        
    def generate_json_with_images(
        self, 
        prompt: str, 
        images: List[str], 
        schema: Optional[Dict] = None
    ) -> Dict:
        """
        Generate JSON response with multiple images.
        
        Args:
            prompt: Text prompt
            images: List of base64 encoded image strings
            schema: Optional JSON schema for response
            
        Returns:
            Parsed JSON response
        """
        # Build generation config
        config = {"response_mime_type": "application/json"}
        if schema:
            config["response_schema"] = schema
        
        # Convert all base64 images to PIL Images
        pil_images = [self._prepare_image_for_gemini(img) for img in images]
        
        # Reinitialize model with JSON config
        original_model = self.model
        self._initialize_model(generation_config=config)
        
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                # Gemini accepts list: [image1, image2, ..., text]
                content = pil_images + [prompt]
                response = self.model.generate_content(content)
                # Restore original model
                self.model = original_model
                return json.loads(response.text)
                
            except (PermissionDenied, ResourceExhausted, GoogleAPIError) as e:
                print(f"[LLMCaller] API key #{self.current_index} failed: {type(e).__name__} - {e}")
                self._switch_key()
                self._initialize_model(generation_config=config)
                
            except json.JSONDecodeError as e:
                print(f"[LLMCaller] Failed to parse JSON: {e}")
                # Restore original model
                self.model = original_model
                raise
        
        # Restore original model before raising error
        self.model = original_model
        raise RuntimeError("All Gemini API keys failed after rotation.")