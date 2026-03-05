import os
from openai import OpenAI
import json

class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ.get("LLM_MODEL_API_KEY"),
            base_url=os.environ.get("LLM_MODEL_BASE_URL")
        )
        self.model = os.environ.get("LLM_MODEL_NAME")

    def extract_memory_info(self, user_input):
        """
        Extracts memory type and content from user input using LLM.
        Returns a dictionary with 'type' (preference|fact) and 'content'.
        """
        system_prompt = """
        You are an AI assistant helping to organize user memories.
        Analyze the user's input and extract:
        1. type: 'preference' (if it's about likes/dislikes/habits) or 'fact' (if it's about objective information).
        2. content: The core information to be stored, summarized clearly.
        
        Return the result as a JSON object with keys 'type' and 'content'.
        Example:
        Input: "I don't like eating spicy food."
        Output: {"type": "preference", "content": "User does not like spicy food"}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            raise Exception(f"LLM extraction failed: {str(e)}")
