import os
from openai import OpenAI

class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ.get("EMBEDDING_MODEL_API_KEY"),
            base_url=os.environ.get("EMBEDDING_MODEL_BASE_URL")
        )
        self.model = os.environ.get("EMBEDDING_MODEL_NAME")

    def generate_embedding(self, text):
        """
        Generates embedding for the given text using the configured model.
        Returns a list of floats.
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Embedding generation failed: {str(e)}")
