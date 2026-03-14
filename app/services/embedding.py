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
        使用配置的模型为给定的文本生成嵌入向量。
        返回一个浮点数列表。
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float",
                dimensions=int(os.environ.get("EMBEDDING_DIMENSION", 1536))
            )
            
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"嵌入生成失败: {str(e)}")
