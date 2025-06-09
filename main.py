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

app = FastAPI()

class BondTextInput(BaseModel):
    text: str

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
            return parsed_response
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
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {str(e)}")
                    # 尝试修复常见的 JSON 格式问题
                    try:
                        # 修复可能的单引号问题
                        json_str = json_str.replace("'", '"')
                        # 修复可能的键值对格式问题
                        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                        return json.loads(json_str)
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
                        "rateReqFlag": rate_req_flag or "可议价" in cleaned_text or "价格可议" in cleaned_text
                    }
                    logger.info(f"Created basic response from text: {basic_response}")
                    return basic_response
            except Exception as e:
                logger.error(f"Failed to create basic response: {str(e)}")
            
            logger.error(f"Could not extract JSON from response: {cleaned_text}")
            raise ValueError("Could not extract valid JSON from model response")
    except Exception as e:
        logger.error(f"Error validating Ollama response: {str(e)}")
        raise

def call_ollama_model(text: str) -> dict:
    """Call the local Ollama Qwen model for text parsing"""
    try:
        logger.info(f"Calling Ollama model with text: {text}")
        
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

        # 构建请求数据
        request_data = {
            "model": "qwen3:0.6b",
            "prompt": f"""请将以下债券交易文本解析为JSON格式，只返回JSON对象，不要包含其他文字说明：
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
        logger.info(f"Received request to parse bond text: {input_data.text}")
        parsed_data = call_ollama_model(input_data.text)
        
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
            # 构建提示词
            prompt = f"""你是一个专业的债券交易助手。请基于以下信息回答问题：

问题：{chat_input.question}

{f'上下文信息：{chat_input.context}' if chat_input.context else ''}

请逐步思考并回答。每步思考都要清晰说明。"""
            
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

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting bond text parsing service...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
