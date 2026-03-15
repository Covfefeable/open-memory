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

    def extract_memory_info(self, user_input, llm_output, existing_memories=None):
        """
        利用大模型从用户输入和LLM回答中提取记忆类型和内容。
        返回一个包含 'type' 和 'content' 的字典列表。
        
        参数:
            user_input (str): 用户的输入消息。
            llm_output (str): LLM 的回复消息。
            existing_memories (list, optional): 已存在的记忆字典列表 ({'type': '...', 'content': '...'})，用于去重。
        """
        existing_memories_text = ""
        if existing_memories:
            existing_memories_text = "\n".join([f"- {m.get('type')}: {m.get('content')}" for m in existing_memories])

        system_prompt = f"""
        你是一个帮助提取公文写作场景下用户记忆的AI助手。
        分析用户的输入和大模型的回答，并提取具有长期保存价值的记忆，严格按照以下四种类型分类：

        1. type: 'position'（岗位）
           - 包含：用户的具体工作岗位、单位名称、职务信息。
           - 示例：陕西省大明宫街道街道办、市委宣传部科员、某公司HR。

        2. type: 'work_content'（日常工作内容）
           - 包含：从用户输入中推断出的日常职责、负责的项目、经常处理的事务。
           - 示例：负责撰写年度总结报告、经常处理群众信访事件、主要工作是组织协调会议。

        3. type: 'writing_preference'（写作偏好）
           - 包含：喜欢的文章风格、用词用语风格、常用词组和句子、喜欢的文章标题和段落标题。
           - 示例：喜欢使用“排比句”、偏好“严肃严谨”的文风、文章标题常采用“对仗结构”、常用“抓好落实、稳步推进”等词汇。
           - 注意：不要将临时的写作要求（如“本次要求不少于800字”、“这篇要加入最新数据”）作为长期偏好提取。

        **已有记忆列表**（请检查新提取的内容是否与以下内容重复，如果完全重复则忽略，如果有更新则提取）：
        {existing_memories_text}

        **提取规则**：
        1. content 字段需要存储核心信息，简明扼要地总结。
        2. 如果输入仅包含临时的指令、闲聊、问候，请返回空数组 []。
        3. 必须以JSON数组格式返回结果，每个元素包含 'type' 和 'content' 两个键。
        4. 不要返回任何 Markdown 格式，只返回纯 JSON 数组。
        5. **去重检查**：如果提取的信息在“已有记忆列表”中已经存在（语义高度相似），请不要再次提取；如果是新的信息或更新，则正常提取。

        示例1：
        输入："我是大明宫街道办的，我们最近经常处理老旧小区改造的问题，你帮我写个总结，我比较喜欢段落标题用对仗的四字词语。"
        输出：
        [
          {{"type": "position", "content": "用户所在单位是大明宫街道办"}},
          {{"type": "work_content", "content": "用户近期经常处理老旧小区改造的问题"}},
          {{"type": "writing_preference", "content": "用户喜欢段落标题使用对仗的四字词语"}}
        ]

        示例2：
        输入："你好，睡了吗。"
        输出：[]
        """
        
        user_message = f"""
        用户输入：{user_input}
        大模型回答：{llm_output}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                # 移除可能存在的 json_object 约束，因为它有时会强制生成字典包裹
                # 我们需要原始列表
            )
            
            content = response.choices[0].message.content.strip()
            # 如果内容被包含在 ```json 代码块中，进行处理
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            parsed = json.loads(content)
            
            # 处理 LLM 可能将数组包裹在 "memories" 或 "result" 等键中的情况
            if isinstance(parsed, dict):
                # 尝试在字典中找到列表类型的值
                for key, value in parsed.items():
                    if isinstance(value, list):
                        return value
                return []
            
            if isinstance(parsed, list):
                return parsed
                
            return []
        except Exception as e:
            raise Exception(f"LLM 提取失败: {str(e)}")

    def extract_historical_context(self, user_input, llm_output):
        """
        从用户输入和 LLM 输出中提取历史上下文。
        返回包含 'type' 和 'content' 的字典，或者 None。
        """
        system_prompt = """
        你是一个帮助提取公文写作场景下用户记忆的AI助手。
        请对用户每一轮对话的输入内容、上传的文件的文件名、文件的内容进行提炼总结，生成一条【历史对话核心内容】类型的记忆。
        
        **提取维度**：
        用户提问的内容、上传的文件名、文件的核心内容、未来可能复用的重要背景事实、核心论点或关键事件记录、关键数据、核心工作内容等信息。
        
        **提取要求**：
        1. 必须生成一条且仅一条总结性内容。
        2. content 字段需要存储核心信息，内容详实且结构清晰。
        3. 如果输入仅包含临时的指令、闲聊、问候（如“你好”、“在吗”），请返回 null。
        4. 必须以JSON格式返回结果，包含 'type' 和 'content' 两个键。type 固定为 'historical_context'。
        5. 不要返回任何 Markdown 格式，只返回纯 JSON 对象。

        **示例**：
        输入：
        用户输入：询问本单位2025年度党建工作考核相关事宜，具体包括考核指标细则、材料报送时间、考核流程及加分项要求...
        大模型回答：...（相关回答）...

        输出：
        {
          "type": "historical_context",
          "content": "用户询问2025年度党建工作考核事宜。核心内容包括：《2025年度基层党建工作考核实施方案》涵盖6大板块28项指标；考核分自查、交叉、集中三阶段；首次将“党建与业务融合成效”纳入核心指标（占比30%）；材料报送截止12月20日；加分项最高10分。核心工作是各支部自查及牵头科室组织检查。"
        }
        """
        
        user_message = f"""
        用户输入：{user_input}
        大模型回答：{llm_output}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            content = response.choices[0].message.content.strip()
            # 如果内容被包含在 ```json 代码块中，进行处理
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            if content.strip() == "null":
                return None
                
            parsed = json.loads(content)
            if isinstance(parsed, dict) and 'content' in parsed:
                parsed['type'] = 'historical_context' # 确保类型正确
                return parsed
            
            return None
        except Exception as e:
            # 记录错误但不崩溃，仅返回 None
            print(f"历史上下文提取失败: {str(e)}")
            return None

    def compress_memories(self, combined_text):
        """
        压缩、去重并总结记忆列表。
        返回包含 'type' 和 'content' 的字典列表。
        """
        system_prompt = """
        你是一个专业的公文写作记忆整理专家。你的任务是整理用户的长期记忆库。
        
        输入是一系列用户的记忆片段（包含原始内容和类型）。
        你需要执行以下操作：
        1. **合并**：将相关的记忆点合并。例如“在市委宣传部工作”和“是市委宣传部的科员”应合并。
        2. **去重**：删除完全重复或语义高度重复的信息。
        3. **归纳**：将零散的细节归纳为更高级别的特征。例如“喜欢对仗标题”、“偏好排比句”归纳为“写作偏好：文风严谨，喜欢使用排比和对仗结构”。
        4. **冲突解决**：如果存在冲突信息，保留看似更新或更具体的信息，或者将冲突点一并记录。
        5. **精简**：去除冗余修饰词，保持信息高密度。

        输出要求：
        必须以JSON数组格式返回结果，每个元素包含 'type' 和 'content' 两个键。
        
        type 必须是以下四种之一：
        - position (岗位)
        - work_content (日常工作内容)
        - writing_preference (写作偏好)
        - historical_context (历史对话核心内容)
        
        只返回纯 JSON 数组，不要返回任何 Markdown 格式。
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
            
            # 如果内容被包含在 ```json 代码块中，进行处理
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
            raise Exception(f"LLM 压缩失败: {str(e)}")
