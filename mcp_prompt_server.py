#!/usr/bin/env python3
"""
MCP Server for Bond Trading Prompt Templates

This server provides tools for AI to intelligently select appropriate prompt templates
for bond trading text parsing based on text analysis.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-prompt-server")

# 从 main.py 导入提示词模板
PROMPT_TEMPLATES = {
    "单一指令解析": """请将以下债券交易文本解析为JSON格式，只返回JSON对象，不要包含其他文字说明：
{text}

需要提取的字段：
- assetCode: 债券代码为含有 4 位数字及以上纯数字不包括（小数点，加号等任意特殊字符）且不能被100整除或者含有任一关键字 (.IB,.SH,.SZ等，该关键字支持配置)；
- assetName: 债券名称
- trdSide: 交易方向（买入/卖出）
- amount: 交易金额（数字）
- rate: 利率（数字）
- amountReqFlag: 金额是否需请示（布尔值，当金额前有*号时为true）
- rateReqFlag: 利率是否需请示（布尔值，当利率前有*号时为true）

""",
    
    "带请示单一指令解析": """请将以下债券交易文本解析为JSON格式，特别注意标有*号的金额和利率需要请示，只返回JSON对象，不要包含其他文字说明：
{text}

需要提取的字段：
- assetCode: 债券代码为含有 4 位数字及以上纯数字不包括（小数点，加号等任意特殊字符）且不能被100整除或者含有任一关键字 (.IB,.SH,.SZ等，该关键字支持配置)；
- assetName: 债券名称
- trdSide: 交易方向（买入/卖出）
- amount: 交易金额（数字）
- rate: 利率（数字）
- amountReqFlag: 金额是否需请示（布尔值，当金额前有*号或包含"可议价"、"价格可议"等关键词时为true）
- rateReqFlag: 利率是否需请示（布尔值，当利率前有*号或包含"可议价"、"价格可议"等关键词时为true）

""",
    
    "债券交易助手对话": """你是一个专业的债券交易助手。请基于以下信息回答问题：

问题：{question}

{context_info}

请逐步思考并回答。每步思考都要清晰说明。""",
    
    "多产品指令语料解析": """请将以下包含多个债券产品的交易文本解析为JSON数组格式，每个产品对应一个JSON对象，只返回JSON数组，不要包含其他文字说明：
{text}

每个产品需要提取的字段：
- assetCode: 债券代码为含有 4 位数字及以上纯数字不包括（小数点，加号等任意特殊字符）且不能被100整除或者含有任一关键字 (.IB,.SH,.SZ等，该关键字支持配置)；
- assetName: 债券名称
- trdSide: 交易方向（买入/卖出）
- amount: 交易金额（数字）
- rate: 利率（数字）
- amountReqFlag: 金额是否需请示（布尔值，当金额前有*号时为true）
- rateReqFlag: 利率是否需请示（布尔值，当利率前有*号时为true）
- fundName: 基金名称,这是个list,需要提取出基金名称,可能包含多个基金名称

"""
}

def analyze_text_characteristics(text: str) -> Dict[str, Any]:
    """分析文本特征，用于选择合适的提示词模板"""
    characteristics = {
        "has_asterisk": False,         # 是否包含*号（请示标记）
        "has_multiple_products": False, # 是否包含多个基金
        "has_negotiable_keywords": False, # 是否包含可议价关键词
        "product_count": 0,            # 产品数量
        "bond_codes": [],              # 债券代码列表
        "has_fund_names": False,       # 是否包含基金名称
        "is_chat_question": False,     # 是否是聊天问题
    }
    
    # 检查是否包含*号
    characteristics["has_asterisk"] = "*" in text
    
    # 检查可议价关键词
    negotiable_keywords = ["可议价", "价格可议", "议价", "面议"]
    characteristics["has_negotiable_keywords"] = any(keyword in text for keyword in negotiable_keywords)
    
    # 检查债券代码模式（如：24国债07, 25国债01等）
    bond_pattern = r'\d{2}国债\d{2}'
    bond_matches = re.findall(bond_pattern, text)
    characteristics["bond_codes"] = bond_matches
    characteristics["product_count"] = len(bond_matches)



    # 检查基金名称（通常包含"货币"、"基金"等关键词）
    fund_keywords = ["货币", "基金", "景益", "景顺"]
    characteristics["has_fund_names"] = any(keyword in text for keyword in fund_keywords)
    characteristics["has_multiple_products"] = len(bond_matches) > 1
    
    # 检查是否是问题/聊天模式
    question_indicators = ["什么", "如何", "为什么", "怎么", "?", "？", "请问", "能否"]
    characteristics["is_chat_question"] = any(indicator in text for indicator in question_indicators)
    
    return characteristics

def recommend_prompt_type(text: str) -> str:
    """基于文本特征推荐合适的提示词类型"""
    characteristics = analyze_text_characteristics(text)
    
    # 如果是问题/聊天模式
    if characteristics["is_chat_question"]:
        return "债券交易助手对话"
    
    # 如果包含多个产品
    if characteristics["has_multiple_products"]:
        return "多产品指令语料解析"
    
    # 如果包含请示标记或可议价关键词
    if characteristics["has_asterisk"] or characteristics["has_negotiable_keywords"]:
        return "带请示单一指令解析"
    
    # 默认使用单一指令解析
    return "单一指令解析"

# 创建MCP服务器
server = Server("bond-prompt-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """列出所有可用的工具"""
    return [
        Tool(
            name="get_available_prompts",
            description="获取所有可用的提示词模板类型和描述",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="analyze_text",
            description="分析文本特征，识别债券交易文本的关键信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要分析的债券交易文本"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="recommend_prompt",
            description="基于文本特征智能推荐最适合的提示词模板类型",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "债券交易文本"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="get_prompt_template",
            description="获取指定类型的提示词模板",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt_type": {
                        "type": "string",
                        "description": "提示词类型",
                        "enum": list(PROMPT_TEMPLATES.keys())
                    },
                    "text": {
                        "type": "string",
                        "description": "要填入模板的文本（可选）"
                    },
                    "question": {
                        "type": "string",
                        "description": "聊天问题（仅对话模板需要）"
                    },
                    "context_info": {
                        "type": "string",
                        "description": "上下文信息（仅对话模板需要）"
                    }
                },
                "required": ["prompt_type"]
            }
        ),
        Tool(
            name="smart_get_prompt",
            description="智能选择并获取最适合的提示词模板（组合了分析和推荐功能）",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "债券交易文本或聊天问题"
                    },
                    "context_info": {
                        "type": "string",
                        "description": "上下文信息（可选）"
                    }
                },
                "required": ["text"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """处理工具调用"""
    try:
        if name == "get_available_prompts":
            result = {
                "available_prompts": list(PROMPT_TEMPLATES.keys()),
                "descriptions": {
                    "单一指令解析": "用于解析单个债券交易指令的基础模板",
                    "带请示单一指令解析": "用于解析包含请示标记（*号）或可议价关键词的单个债券交易指令",
                    "债券交易助手对话": "用于债券交易相关的问答对话",
                    "多产品指令语料解析": "用于解析包含多个债券产品的交易文本"
                }
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "analyze_text":
            text = arguments["text"]
            characteristics = analyze_text_characteristics(text)
            return [TextContent(type="text", text=json.dumps(characteristics, ensure_ascii=False, indent=2))]
        
        elif name == "recommend_prompt":
            text = arguments["text"]
            recommended_type = recommend_prompt_type(text)
            characteristics = analyze_text_characteristics(text)
            
            result = {
                "recommended_prompt_type": recommended_type,
                "reason": f"基于文本特征分析推荐使用'{recommended_type}'",
                "text_characteristics": characteristics
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "get_prompt_template":
            prompt_type = arguments["prompt_type"]
            
            if prompt_type not in PROMPT_TEMPLATES:
                return [TextContent(type="text", text=f"错误：未找到提示词类型 '{prompt_type}'")]
            
            template = PROMPT_TEMPLATES[prompt_type]
            
            # 根据模板类型填充参数
            if prompt_type == "债券交易助手对话":
                question = arguments.get("question", "")
                context_info = arguments.get("context_info", "")
                if question:
                    context_part = f'上下文信息：{context_info}' if context_info else ''
                    filled_template = template.format(question=question, context_info=context_part)
                else:
                    filled_template = template
            else:
                text = arguments.get("text", "")
                if text:
                    filled_template = template.format(text=text)
                else:
                    filled_template = template
            
            result = {
                "prompt_type": prompt_type,
                "template": filled_template
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "smart_get_prompt":
            text = arguments["text"]
            context_info = arguments.get("context_info", "")
            
            # 智能推荐提示词类型
            recommended_type = recommend_prompt_type(text)
            characteristics = analyze_text_characteristics(text)
            
            # 获取模板
            template = PROMPT_TEMPLATES[recommended_type]
            
            # 填充模板
            if recommended_type == "债券交易助手对话":
                context_part = f'上下文信息：{context_info}' if context_info else ''
                filled_template = template.format(question=text, context_info=context_part)
            else:
                filled_template = template.format(text=text)
            
            result = {
                "recommended_prompt_type": recommended_type,
                "text_characteristics": characteristics,
                "filled_prompt": filled_template,
                "reasoning": f"基于以下特征选择了'{recommended_type}'模板：" + 
                           f"包含*号={characteristics['has_asterisk']}, " +
                           f"多产品={characteristics['has_multiple_products']}, " +
                           f"是问题={characteristics['is_chat_question']}, " +
                           f"产品数量={characteristics['product_count']}"
            }
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"错误：未知工具 '{name}'")]
    
    except Exception as e:
        logger.error(f"调用工具 {name} 时出错: {str(e)}")
        return [TextContent(type="text", text=f"错误：{str(e)}")]

async def main():
    """运行MCP服务器"""
    logger.info("启动Bond Prompt MCP Server...")
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main()) 