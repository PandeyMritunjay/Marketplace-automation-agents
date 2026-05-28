import openai
from typing import Dict, Any, Optional
from lighthouse.config import settings
import json


class OpenAIService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
    
    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate a chat completion."""
        kwargs = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = openai.ChatCompletion.create(**kwargs)
        return response.choices[0].message.content
    
    def json_completion(
        self,
        messages: list[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate a JSON completion with schema validation."""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temperature
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    
    def extract_structured_data(
        self,
        text: str,
        extraction_prompt: str,
        schema_description: str
    ) -> Dict[str, Any]:
        """Extract structured data from unstructured text."""
        messages = [
            {
                "role": "system",
                "content": f"You are a data extraction expert. Extract information according to this schema: {schema_description}. Return valid JSON only."
            },
            {
                "role": "user",
                "content": f"{extraction_prompt}\n\nText to extract from:\n{text}"
            }
        ]
        
        return self.json_completion(messages, {})
