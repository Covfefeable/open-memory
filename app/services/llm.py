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
        Returns a list of dictionaries with 'type' (preference|fact) and 'content'.
        """
        system_prompt = """
        你是一个帮助整理用户记忆的AI助手。
        分析用户的输入并提取：
        1. type: 'preference'（如果涉及喜好/厌恶/习惯）或 'fact'（如果涉及客观信息）。
        2. content: 需要存储的核心信息，简明扼要地总结。
        
        以JSON数组格式返回结果，每个元素包含 'type' 和 'content' 两个键。
        如果用户输入中没有包含任何值得记忆的信息（如闲聊、问候等），请返回空数组 []。
        不要返回任何 Markdown 格式，只返回纯 JSON 数组。
        
        示例1：
        输入："我不喜欢吃辣，但我喜欢吃甜食。"
        输出：[{"type": "preference", "content": "用户不喜欢吃辣"}, {"type": "preference", "content": "用户喜欢吃甜食"}]
        
        示例2：
        输入："今天天气真好。"
        输出：[]
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                # Removing json_object constraint as it sometimes forces a dict wrapper
                # We want a raw list
            )
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            parsed = json.loads(content)
            
            # Handle cases where LLM might wrap the array in a key like "memories" or "result"
            if isinstance(parsed, dict):
                # Try to find a list value in the dict
                for key, value in parsed.items():
                    if isinstance(value, list):
                        return value
                return []
            
            if isinstance(parsed, list):
                return parsed
                
            return []
        except Exception as e:
            raise Exception(f"LLM extraction failed: {str(e)}")

    def compress_memories(self, combined_text):
        """
        Compresses, deduplicates and summarizes a list of memories.
        Returns a list of dictionaries with 'type' and 'content'.
        """
        system_prompt = """
        你是一个专业的记忆整理专家。你的任务是整理用户的长期记忆库。
        
        输入是一系列用户的记忆片段（包含原始内容和类型）。
        你需要执行以下操作：
        1. **合并**：将相关的记忆点合并。例如“喜欢吃苹果”和“最爱的水果是苹果”应合并。
        2. **去重**：删除完全重复或语义高度重复的信息。
        3. **归纳**：将零散的细节归纳为更高级别的特征。例如“周一去健身房”、“周三练腿”、“周五有氧”归纳为“用户有规律的健身习惯（周一、三、五）”。
        4. **冲突解决**：如果存在冲突信息，保留看似更新或更具体的信息，或者将冲突点一并记录。
        5. **精简**：去除冗余修饰词，保持信息高密度。
        
        **目标**：输出一个新的记忆列表，其条目数量必须少于输入的条目数量，同时保留所有关键信息。
        
        以JSON数组格式返回结果，每个元素包含 'type' (preference/fact) 和 'content'。
        不要返回任何 Markdown 格式，只返回纯 JSON 数组。
        
        输出示例：
        [
            {"type": "preference", "content": "用户喜欢吃川菜，特别是麻婆豆腐"},
            {"type": "fact", "content": "用户住在北京市朝阳区"},
            {"type": "preference", "content": "用户习惯每周一三五去健身房"}
        ]
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"以下是需要整理的记忆列表：\n\n{combined_text}"}
                ],
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            parsed = json.loads(content)
            
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if isinstance(value, list):
                        return value
                return []
            
            if isinstance(parsed, list):
                return parsed
                
            return []
        except Exception as e:
            raise Exception(f"LLM compression failed: {str(e)}")
