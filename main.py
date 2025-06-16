# This is a sample Python script.

# Press ⇧F10 to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
import json
import logging
import sys
from typing import Dict, Any, AsyncGenerator
import asyncio
import time

# 导入智能提示词管理器
from prompt_manager import smart_get_prompt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bond_parser.log')
    ]
)
logger = logging.getLogger(__name__)

# 提示词模板字典
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

app = FastAPI()

class BondTextInput(BaseModel):
    text: str
    prompt_type: str = "单一指令解析"  # 默认使用单一指令解析

class SmartBondTextInput(BaseModel):
    text: str
    context: str = ""  # 可选的上下文信息

class ChatInput(BaseModel):
    question: str
    context: str = ""  # 可选的上下文信息

class BondParsedOutput(BaseModel):
    assetCode: str
    assetName: str
    trdSide: str
    amount: float
    rate: float
    amountReqFlag: bool
    rateReqFlag: bool
    fundName: list = []  # 可选字段，默认为空列表

class SmartBondParsedOutput(BaseModel):
    parsed_data: BondParsedOutput
    ai_analysis: Dict[str, Any]

def get_prompt_template(prompt_type: str, **kwargs) -> str:
    """获取指定类型的提示词模板并填充参数"""
    if prompt_type not in PROMPT_TEMPLATES:
        logger.warning(f"Unknown prompt type: {prompt_type}, using default")
        prompt_type = "单一指令解析"
    
    template = PROMPT_TEMPLATES[prompt_type]
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing parameter for prompt template {prompt_type}: {e}")
        raise ValueError(f"Missing parameter for prompt template: {e}")

def normalize_parsed_data(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """标准化解析后的数据，确保数据类型正确"""
    try:
        logger.info(f"Normalizing parsed data: {parsed_data}")
        
        # 创建标准化后的数据字典
        normalized_data = {}
        
        # 处理 assetCode - 确保是字符串
        normalized_data["assetCode"] = str(parsed_data.get("assetCode", ""))
        
        # 处理 assetName - 确保是字符串
        normalized_data["assetName"] = str(parsed_data.get("assetName", ""))
        
        # 处理 trdSide - 转换布尔值或其他类型为字符串
        trd_side = parsed_data.get("trdSide", "")
        if isinstance(trd_side, bool):
            # 如果是布尔值，根据业务逻辑转换（这里需要根据实际情况调整）
            normalized_data["trdSide"] = "买入" if trd_side else "卖出"
        elif isinstance(trd_side, str):
            normalized_data["trdSide"] = trd_side
        else:
            normalized_data["trdSide"] = str(trd_side)
        
        # 处理 amount - 确保是 float
        amount = parsed_data.get("amount")
        if amount is None:
            normalized_data["amount"] = 0.0
        elif isinstance(amount, str):
            try:
                # 移除可能的非数字字符
                amount_str = amount.replace(",", "").replace("万", "").replace("亿", "")
                normalized_data["amount"] = float(amount_str)
                # 处理万、亿单位
                if "万" in str(parsed_data.get("amount", "")):
                    normalized_data["amount"] *= 10000
                elif "亿" in str(parsed_data.get("amount", "")):
                    normalized_data["amount"] *= 100000000
            except (ValueError, TypeError):
                logger.warning(f"Could not convert amount to float: {amount}")
                normalized_data["amount"] = 0.0
        else:
            try:
                normalized_data["amount"] = float(amount)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert amount to float: {amount}")
                normalized_data["amount"] = 0.0
        
        # 处理 rate - 确保是 float
        rate = parsed_data.get("rate")
        if rate is None:
            normalized_data["rate"] = 0.0
        elif isinstance(rate, str):
            try:
                # 移除百分号
                rate_str = rate.replace("%", "")
                normalized_data["rate"] = float(rate_str)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert rate to float: {rate}")
                normalized_data["rate"] = 0.0
        else:
            try:
                normalized_data["rate"] = float(rate)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert rate to float: {rate}")
                normalized_data["rate"] = 0.0
        
        # 处理 amountReqFlag - 确保是布尔值
        amount_req_flag = parsed_data.get("amountReqFlag", False)
        normalized_data["amountReqFlag"] = bool(amount_req_flag)
        
        # 处理 rateReqFlag - 确保是布尔值
        rate_req_flag = parsed_data.get("rateReqFlag", False)
        normalized_data["rateReqFlag"] = bool(rate_req_flag)
        
        # 处理 fundName - 确保是列表
        fund_name = parsed_data.get("fundName", [])
        if isinstance(fund_name, list):
            normalized_data["fundName"] = fund_name
        elif isinstance(fund_name, str):
            # 如果是字符串，尝试分割成列表
            normalized_data["fundName"] = [fund_name] if fund_name else []
        else:
            normalized_data["fundName"] = []
        
        logger.info(f"Normalized data: {normalized_data}")
        return normalized_data
        
    except Exception as e:
        logger.error(f"Error normalizing parsed data: {str(e)}")
        raise ValueError(f"Error normalizing parsed data: {str(e)}")

def validate_ollama_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """验证并处理 Ollama 模型返回的数据"""
    try:
        logger.info(f"Validating Ollama response: {json.dumps(response_data, ensure_ascii=False)}")
        
        if "response" not in response_data:
            logger.error(f"Invalid Ollama response format: {response_data}")
            raise ValueError("Invalid response format from Ollama model")
        
        response_text = response_data["response"]
        logger.info(f"Raw model response: {response_text}")
        
        # 清理响应文本
        cleaned_text = response_text.strip()
        # 移除可能的 markdown 代码块标记
        cleaned_text = cleaned_text.replace("```json", "").replace("```", "").strip()
        
        # 尝试直接解析 JSON
        try:
            parsed_response = json.loads(cleaned_text)
            logger.info(f"Successfully parsed JSON response: {parsed_response}")
            # 标准化数据类型
            return normalize_parsed_data(parsed_response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            # 如果直接解析失败，尝试从文本中提取 JSON
            import re
            # 使用更宽松的 JSON 匹配模式
            json_match = re.search(r'\{[^{}]*\}', cleaned_text)
            if json_match:
                json_str = json_match.group()
                logger.info(f"Extracted JSON string: {json_str}")
                try:
                    parsed_response = json.loads(json_str)
                    return normalize_parsed_data(parsed_response)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {str(e)}")
                    # 尝试修复常见的 JSON 格式问题
                    try:
                        # 修复可能的单引号问题
                        json_str = json_str.replace("'", '"')
                        # 修复可能的键值对格式问题
                        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                        parsed_response = json.loads(json_str)
                        return normalize_parsed_data(parsed_response)
                    except Exception as e:
                        logger.error(f"Failed to fix and parse JSON: {str(e)}")
                        raise ValueError(f"Invalid JSON format in extracted string: {str(e)}")
            
            # 如果无法提取 JSON，尝试构建一个基本的响应
            try:
                # 尝试从文本中提取关键信息
                asset_code_match = re.search(r'(\d{2}国债\d{2})', cleaned_text)
                trd_side_match = re.search(r'(买入|卖出)', cleaned_text)
                
                # 处理带星号的金额
                amount_match = re.search(r'\*?(\d+(?:\.\d+)?[万|亿])', cleaned_text)
                amount_req_flag = amount_match and '*' in amount_match.group(0)
                
                # 处理带星号的利率
                rate_match = re.search(r'\*?(\d+(?:\.\d+)?%)', cleaned_text)
                rate_req_flag = rate_match and '*' in rate_match.group(0)
                
                if asset_code_match:
                    # 提取金额数值
                    amount_value = 0.0
                    if amount_match:
                        amount_str = amount_match.group(1)
                        amount_value = float(amount_str.replace("万", "").replace("亿", ""))
                        if "万" in amount_str:
                            amount_value *= 10000
                        elif "亿" in amount_str:
                            amount_value *= 100000000
                    
                    # 提取利率数值
                    rate_value = 0.0
                    if rate_match:
                        rate_str = rate_match.group(1)
                        rate_value = float(rate_str.replace("%", ""))
                    
                    basic_response = {
                        "assetCode": asset_code_match.group(1),
                        "assetName": asset_code_match.group(1),
                        "trdSide": trd_side_match.group(1) if trd_side_match else "未知",
                        "amount": amount_value,
                        "rate": rate_value,
                        "amountReqFlag": amount_req_flag or "可议价" in cleaned_text or "价格可议" in cleaned_text,
                        "rateReqFlag": rate_req_flag or "可议价" in cleaned_text or "价格可议" in cleaned_text,
                        "fundName": []
                    }
                    logger.info(f"Created basic response from text: {basic_response}")
                    return normalize_parsed_data(basic_response)
            except Exception as e:
                logger.error(f"Failed to create basic response: {str(e)}")
            
            logger.error(f"Could not extract JSON from response: {cleaned_text}")
            raise ValueError("Could not extract valid JSON from model response")
    except Exception as e:
        logger.error(f"Error validating Ollama response: {str(e)}")
        raise

def call_ollama_model(text: str, prompt_type: str = "单一指令解析") -> dict:
    """Call the local Ollama Qwen model for text parsing"""
    try:
        logger.info(f"Calling Ollama model with text: {text}, prompt_type: {prompt_type}")
        
        # 检查 Ollama 服务是否可用
        try:
            # 使用 /api/tags 端点检查服务状态
            health_check = requests.get("http://localhost:11434/api/tags")
            health_check.raise_for_status()
            logger.info("Ollama service is available")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama service is not available: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not available. Please ensure Ollama is running with 'ollama serve' command."
            )

        # 检查模型是否已下载
        try:
            models_response = requests.get("http://localhost:11434/api/tags")
            models = models_response.json()
            logger.info(f"Available models: {json.dumps(models, ensure_ascii=False)}")
            if "qwen3:0.6b" not in [model["name"] for model in models.get("models", [])]:
                logger.error("qwen3:0.6b model is not available")
                raise HTTPException(
                    status_code=503,
                    detail="qwen3:0.6b model is not available. Please run 'ollama pull qwen3:0.6b' first."
                )
        except Exception as e:
            logger.error(f"Error checking model availability: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Error checking model availability. Please ensure Ollama is properly configured."
            )

        # 使用提示词模板
        prompt = get_prompt_template(prompt_type, text=text)
        
        # 构建请求数据
        request_data = {
            "model": "qwen3:0.6b",
            "prompt": prompt,
            "stream": False
        }
        logger.info(f"Sending request to Ollama: {json.dumps(request_data, ensure_ascii=False)}")

        response = requests.post(
            "http://localhost:11434/api/generate",
            json=request_data,
            timeout=30  # 添加超时设置
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Received response from Ollama: {json.dumps(result, ensure_ascii=False)}")
        
        # 验证和处理响应
        parsed_data = validate_ollama_response(result)
        
        # 验证必要字段
        required_fields = ["assetCode", "assetName", "trdSide", "amount", "rate", "amountReqFlag", "rateReqFlag"]
        missing_fields = [field for field in required_fields if field not in parsed_data]
        if missing_fields:
            logger.error(f"Missing required fields in parsed data: {missing_fields}")
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        logger.info(f"Successfully parsed bond data: {parsed_data}")
        return parsed_data
        
    except requests.exceptions.Timeout:
        logger.error("Request to Ollama model timed out")
        raise HTTPException(status_code=504, detail="Request to Ollama model timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calling Ollama model: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in call_ollama_model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/parse-bond-text", response_model=BondParsedOutput)
async def parse_bond_text(input_data: BondTextInput):
    """
    Parse bond trading text and extract structured information
    """
    try:
        logger.info(f"Received request to parse bond text: {input_data.text}, prompt_type: {input_data.prompt_type}")
        parsed_data = call_ollama_model(input_data.text, input_data.prompt_type)
        
        # 验证数据类型
        try:
            result = BondParsedOutput(**parsed_data)
            logger.info(f"Successfully validated and returned parsed data: {result}")
            return result
        except Exception as e:
            logger.error(f"Error validating parsed data: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error validating parsed data: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in parse_bond_text: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing bond text: {str(e)}")

@app.post("/smart-parse-bond-text", response_model=SmartBondParsedOutput)
async def smart_parse_bond_text(input_data: SmartBondTextInput):
    """
    智能解析债券交易文本 - AI自动选择最适合的提示词模板
    """
    try:
        logger.info(f"Received smart parse request: {input_data.text}, context: {input_data.context}")
        
        # 使用AI智能选择提示词
        prompt_result = smart_get_prompt(input_data.text, input_data.context)
        
        logger.info(f"AI recommended prompt type: {prompt_result['recommended_prompt_type']}")
        logger.info(f"AI reasoning: {prompt_result['reasoning']}")
        
        # 调用模型解析（使用AI推荐的提示词类型）
        parsed_data = call_ollama_model(
            input_data.text, 
            prompt_result['recommended_prompt_type']
        )
        
        # 验证解析结果
        try:
            validated_parsed_data = BondParsedOutput(**parsed_data)
        except Exception as e:
            logger.error(f"Error validating parsed data: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error validating parsed data: {str(e)}"
            )
        
        # 构建包含AI分析的响应
        result = SmartBondParsedOutput(
            parsed_data=validated_parsed_data,
            ai_analysis={
                "recommended_prompt_type": prompt_result['recommended_prompt_type'],
                "reasoning": prompt_result['reasoning'],
                "text_characteristics": prompt_result['text_characteristics'],
                "confidence": "high",  # 可以根据需要添加置信度评估
                "processing_time": time.time()  # 可以添加处理时间
            }
        )
        
        logger.info(f"Successfully completed smart parsing with AI analysis")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in smart_parse_bond_text: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in smart bond text parsing: {str(e)}")

@app.get("/prompt-analysis")
async def analyze_prompt_selection(text: str):
    """
    分析文本特征和AI推荐的提示词类型（仅用于调试和分析）
    """
    try:
        logger.info(f"Analyzing prompt selection for text: {text}")
        
        # 使用智能提示词管理器进行分析
        analysis_result = smart_get_prompt(text)
        
        return {
            "input_text": text,
            "analysis": analysis_result,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error in prompt analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing prompt selection: {str(e)}")

async def stream_ollama_response(text: str) -> AsyncGenerator[str, None]:
    """Stream response from Ollama model"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:0.6b",
                "prompt": text,
                "stream": True
            },
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    json_response = json.loads(line)
                    if "response" in json_response:
                        yield f"data: {json.dumps({'content': json_response['response']}, ensure_ascii=False)}\n\n"
                    if json_response.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"Error in stream_ollama_response: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

@app.post("/chat")
async def chat_endpoint(chat_input: ChatInput):
    """Interactive chat endpoint with SSE"""
    async def event_generator():
        try:
            # 使用提示词模板
            context_info = f'上下文信息：{chat_input.context}' if chat_input.context else ''
            prompt = get_prompt_template(
                "债券交易助手对话", 
                question=chat_input.question,
                context_info=context_info
            )
            
            # 发送思考过程
            yield f"data: {json.dumps({'type': 'thinking', 'content': '开始分析问题...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.5)
            
            # 流式返回模型响应
            async for chunk in stream_ollama_response(prompt):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in chat endpoint: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@app.get("/prompt-templates")
async def get_prompt_templates():
    """获取所有可用的提示词模板名称"""
    try:
        # 使用智能提示词管理器获取模板信息
        from prompt_manager import get_available_prompts
        available_prompts = get_available_prompts()
        
        return {
            "available_templates": available_prompts["available_prompts"],
            "descriptions": available_prompts["descriptions"],
            "legacy_templates": list(PROMPT_TEMPLATES.keys()),  # 保留原有模板信息
            "smart_prompt_manager": "enabled"
        }
    except Exception as e:
        logger.error(f"Error getting prompt templates: {str(e)}")
        # 如果智能管理器出错，回退到原有模板
        return {
            "available_templates": list(PROMPT_TEMPLATES.keys()),
            "templates": PROMPT_TEMPLATES,
            "smart_prompt_manager": "disabled",
            "error": str(e)
        }

@app.get("/smart-features")
async def get_smart_features():
    """获取智能功能特性信息"""
    try:
        from prompt_manager import prompt_manager
        
        return {
            "smart_prompt_selection": {
                "enabled": True,
                "version": "1.0.0",
                "description": "AI自动选择最适合的提示词模板"
            },
            "features": {
                "text_analysis": "分析文本特征（*号、多产品、可议价、问答等）",
                "intelligent_recommendation": "基于特征智能推荐提示词类型",
                "reasoning_explanation": "提供详细的推理过程说明",
                "template_management": "支持模板的增删改查和导入导出"
            },
            "supported_prompt_types": prompt_manager.get_available_prompts()["available_prompts"],
            "detection_capabilities": {
                "asterisk_marking": "检测*号请示标记",
                "multiple_products": "识别多产品交易指令",
                "negotiable_keywords": "识别可议价关键词",
                "question_detection": "检测问答模式",
                "fund_names": "识别基金名称"
            }
        }
    except Exception as e:
        logger.error(f"Error getting smart features: {str(e)}")
        return {
            "smart_prompt_selection": {
                "enabled": False,
                "error": str(e)
            }
        }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting bond text parsing service...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
