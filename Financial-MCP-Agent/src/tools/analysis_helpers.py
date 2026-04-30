"""Agent分析辅助函数。"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


async def llm_generate_analysis(system_prompt: str, user_prompt: str) -> str:
    """调用兼容 OpenAI 的模型生成分析。"""
    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_COMPATIBLE_API_KEY"),
        base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL"),
        temperature=0.3,
    )
    response = await llm.ainvoke(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
    return response.content
