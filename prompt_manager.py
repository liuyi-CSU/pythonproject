#!/usr/bin/env python3
"""
独立的提示词管理器 - 智能选择债券交易提示词模板

不依赖MCP库，可以直接集成到现有系统中使用
"""

import json
import re
from typing import Dict, List, Any, Optional

class BondPromptManager:
    """债券交易提示词智能管理器"""
    
    def __init__(self):
        """初始化提示词模板"""
        self.prompt_templates = {
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
    
    def analyze_text_characteristics(self, text: str) -> Dict[str, Any]:
        """分析文本特征，用于选择合适的提示词模板"""
        characteristics = {
            "has_asterisk": False,         # 是否包含*号（请示标记）
            "has_multiple_products": False, # 是否包含多个基金名称
            "has_negotiable_keywords": False, # 是否包含可议价关键词
            "product_count": 0,            # 产品数量
            "bond_codes": [],              # 债券代码列表
            "has_fund_names": False,       # 是否包含基金名称
            "fund_names": [],              # 检测到的基金名称列表
            "fund_count": 0,               # 基金名称数量
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
        
        # 检查基金名称（更精确的基金名称识别）
        fund_patterns = [
            r'([^，。；！？\s]*基金)',                    # 包含"基金"的词组（更精确）
            r'(富国[^，。；！？\s买卖]{0,4})',            # 富国系列（限制后续字符）
            r'(华夏[^，。；！？\s买卖]{0,4})',            # 华夏系列  
            r'(嘉实[^，。；！？\s买卖]{0,4})',            # 嘉实系列
            r'(广发[^，。；！？\s买卖]{0,4})',            # 广发系列
            r'(易方达[^，。；！？\s买卖]{0,4})',          # 易方达系列
            r'(博时[^，。；！？\s买卖]{0,4})',            # 博时系列
            r'(招商[^，。；！？\s买卖]{0,4})',            # 招商系列
            r'(南方[^，。；！？\s买卖]{0,4})',            # 南方系列
            r'(工银[^，。；！？\s买卖]{0,4})',            # 工银系列
            r'(建信[^，。；！？\s买卖]{0,4})',            # 建信系列
            r'([^，。；！？\s]*货币)',                    # 包含"货币"的词组（更精确）
            r'(景[^，。；！？\s买卖]{0,4})',  # 景顺
            r'([^，。；！？\s]*货币)',                    # 包含"基金"的词组（更精确）
        ]
        
        fund_names = []
        for pattern in fund_patterns:
            matches = re.findall(pattern, text)
            fund_names.extend(matches)
        
        # 去重并过滤掉过短的匹配
        fund_names = list(set([name for name in fund_names if len(name.strip()) > 1]))
        
        characteristics["fund_names"] = fund_names
        characteristics["fund_count"] = len(fund_names)
        characteristics["has_fund_names"] = len(fund_names) > 0
        
        # 修改has_multiple_products的判断逻辑：基于基金名称数量而不是债券代码数量
        characteristics["has_multiple_products"] = len(fund_names) > 1
        
        # 检查是否是问题/聊天模式
        question_indicators = ["什么", "如何", "为什么", "怎么", "?", "？", "请问", "能否"]
        characteristics["is_chat_question"] = any(indicator in text for indicator in question_indicators)
        
        return characteristics
    
    def recommend_prompt_type(self, text: str) -> str:
        """基于文本特征推荐合适的提示词类型"""
        characteristics = self.analyze_text_characteristics(text)
        
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
    
    def get_prompt_template(self, prompt_type: str, **kwargs) -> str:
        """获取指定类型的提示词模板并填充参数"""
        if prompt_type not in self.prompt_templates:
            raise ValueError(f"未知的提示词类型: {prompt_type}")
        
        template = self.prompt_templates[prompt_type]
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"缺少模板参数: {e}")
    
    def smart_get_prompt(self, text: str, context_info: str = "") -> Dict[str, Any]:
        """智能选择并获取最适合的提示词模板（一步到位）"""
        # 分析文本特征
        characteristics = self.analyze_text_characteristics(text)
        
        # 推荐提示词类型
        recommended_type = self.recommend_prompt_type(text)
        
        # 获取并填充模板
        if recommended_type == "债券交易助手对话":
            context_part = f'上下文信息：{context_info}' if context_info else ''
            filled_prompt = self.get_prompt_template(
                recommended_type, 
                question=text, 
                context_info=context_part
            )
        else:
            filled_prompt = self.get_prompt_template(recommended_type, text=text)
        
        # 生成推理说明
        reasoning = f"基于以下特征选择了'{recommended_type}'模板：" + \
                   f"包含*号={characteristics['has_asterisk']}, " + \
                   f"多基金名称={characteristics['has_multiple_products']}, " + \
                   f"是问题={characteristics['is_chat_question']}, " + \
                   f"基金数量={characteristics['fund_count']}, " + \
                   f"检测到的基金={characteristics['fund_names']}"
        
        return {
            "recommended_prompt_type": recommended_type,
            "text_characteristics": characteristics,
            "filled_prompt": filled_prompt,
            "reasoning": reasoning
        }
    
    def get_available_prompts(self) -> Dict[str, Any]:
        """获取所有可用的提示词模板类型和描述"""
        return {
            "available_prompts": list(self.prompt_templates.keys()),
            "descriptions": {
                "单一指令解析": "用于解析单个债券交易指令的基础模板",
                "带请示单一指令解析": "用于解析包含请示标记（*号）或可议价关键词的单个债券交易指令",
                "债券交易助手对话": "用于债券交易相关的问答对话",
                "多产品指令语料解析": "用于解析包含多个债券产品的交易文本"
            }
        }
    
    def add_prompt_template(self, name: str, template: str, description: str = ""):
        """添加新的提示词模板"""
        self.prompt_templates[name] = template
    
    def update_prompt_template(self, name: str, template: str):
        """更新现有的提示词模板"""
        if name not in self.prompt_templates:
            raise ValueError(f"提示词模板 '{name}' 不存在")
        self.prompt_templates[name] = template
    
    def export_templates(self, file_path: str):
        """导出提示词模板到JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.prompt_templates, f, ensure_ascii=False, indent=2)
    
    def import_templates(self, file_path: str):
        """从JSON文件导入提示词模板"""
        with open(file_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)
        self.prompt_templates.update(templates)

# 创建全局实例，方便直接使用
prompt_manager = BondPromptManager()

# 便捷函数，与原有的函数接口兼容
def analyze_text_characteristics(text: str) -> Dict[str, Any]:
    """分析文本特征"""
    return prompt_manager.analyze_text_characteristics(text)

def recommend_prompt_type(text: str) -> str:
    """推荐提示词类型"""
    return prompt_manager.recommend_prompt_type(text)

def get_prompt_template(prompt_type: str, **kwargs) -> str:
    """获取提示词模板"""
    return prompt_manager.get_prompt_template(prompt_type, **kwargs)

def smart_get_prompt(text: str, context_info: str = "") -> Dict[str, Any]:
    """智能获取提示词"""
    return prompt_manager.smart_get_prompt(text, context_info)

def get_available_prompts() -> Dict[str, Any]:
    """获取可用提示词"""
    return prompt_manager.get_available_prompts()

# 导出提示词模板字典，方便其他模块使用
PROMPT_TEMPLATES = prompt_manager.prompt_templates

if __name__ == "__main__":
    # 如果直接运行此文件，进行简单的测试
    print("🤖 Bond Prompt Manager 测试")
    print("=" * 50)
    
    test_cases = [
        "买入24国债07 *1000万 3.5%",
        "买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%",
        "什么是债券交易？",
        "买入25国债08 500万 价格可议"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {text}")
        result = smart_get_prompt(text)
        print(f"推荐类型: {result['recommended_prompt_type']}")
        print(f"推理: {result['reasoning']}")
        print(f"生成的提示词长度: {len(result['filled_prompt'])} 字符")
    
    print("\n✅ 测试完成！") 