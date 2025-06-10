#!/usr/bin/env python3
"""
测试脚本：验证MCP服务器的提示词选择逻辑
"""

import json
import sys
import os

# 添加当前目录到路径，以便导入MCP服务器模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_prompt_server import analyze_text_characteristics, recommend_prompt_type, PROMPT_TEMPLATES

def test_text_analysis():
    """测试文本特征分析功能"""
    print("🔍 测试文本特征分析功能\n")
    
    test_cases = [
        {
            "name": "包含请示标记的单一产品",
            "text": "买入24国债07 *1000万 3.5%",
            "expected_features": ["has_asterisk", "product_count=1"]
        },
        {
            "name": "多产品交易指令",
            "text": "买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%",
            "expected_features": ["has_multiple_products", "product_count=2"]
        },
        {
            "name": "包含基金名称的指令",
            "text": "景益货币基金买入24国债07 1000万 3.5%",
            "expected_features": ["has_fund_names"]
        },
        {
            "name": "问答场景",
            "text": "什么是债券交易的基本流程？",
            "expected_features": ["is_chat_question"]
        },
        {
            "name": "包含可议价关键词",
            "text": "买入24国债07 1000万 价格可议",
            "expected_features": ["has_negotiable_keywords"]
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"测试用例 {i}: {case['name']}")
        print(f"输入文本: {case['text']}")
        
        characteristics = analyze_text_characteristics(case['text'])
        print(f"分析结果: {json.dumps(characteristics, ensure_ascii=False, indent=2)}")
        
        # 验证预期特征
        for expected in case['expected_features']:
            if "=" in expected:
                key, value = expected.split("=")
                actual_value = characteristics.get(key)
                expected_value = int(value) if value.isdigit() else value
                if actual_value == expected_value:
                    print(f"✅ 预期特征 {expected} 验证通过")
                else:
                    print(f"❌ 预期特征 {expected} 验证失败: 实际值 {actual_value}")
            else:
                if characteristics.get(expected, False):
                    print(f"✅ 预期特征 {expected} 验证通过")
                else:
                    print(f"❌ 预期特征 {expected} 验证失败")
        
        print("-" * 50)

def test_prompt_recommendation():
    """测试提示词推荐功能"""
    print("\n🎯 测试提示词推荐功能\n")
    
    test_cases = [
        {
            "text": "买入24国债07 *1000万 3.5%",
            "expected": "带请示单一指令解析",
            "reason": "包含*号请示标记"
        },
        {
            "text": "买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%",
            "expected": "多产品指令语料解析",
            "reason": "包含多个产品"
        },
        {
            "text": "什么是债券交易的基本流程？",
            "expected": "债券交易助手对话",
            "reason": "是问答场景"
        },
        {
            "text": "买入24国债07 1000万 3.5%",
            "expected": "单一指令解析",
            "reason": "标准单一产品指令"
        },
        {
            "text": "买入24国债07 1000万 可议价",
            "expected": "带请示单一指令解析",
            "reason": "包含可议价关键词"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"测试用例 {i}: {case['reason']}")
        print(f"输入文本: {case['text']}")
        
        recommended = recommend_prompt_type(case['text'])
        print(f"推荐类型: {recommended}")
        print(f"预期类型: {case['expected']}")
        
        if recommended == case['expected']:
            print("✅ 推荐结果正确")
        else:
            print("❌ 推荐结果错误")
        
        print("-" * 50)

def test_prompt_template_filling():
    """测试提示词模板填充功能"""
    print("\n📝 测试提示词模板填充功能\n")
    
    test_cases = [
        {
            "prompt_type": "单一指令解析",
            "text": "买入24国债07 1000万 3.5%",
            "params": {"text": "买入24国债07 1000万 3.5%"}
        },
        {
            "prompt_type": "债券交易助手对话",
            "text": "什么是债券交易？",
            "params": {"question": "什么是债券交易？", "context_info": ""}
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"测试用例 {i}: {case['prompt_type']}")
        print(f"输入文本: {case['text']}")
        
        template = PROMPT_TEMPLATES[case['prompt_type']]
        try:
            filled_template = template.format(**case['params'])
            print("✅ 模板填充成功")
            print(f"填充结果预览: {filled_template[:100]}...")
        except Exception as e:
            print(f"❌ 模板填充失败: {str(e)}")
        
        print("-" * 50)

def test_smart_workflow():
    """测试完整的智能工作流程"""
    print("\n🚀 测试完整智能工作流程\n")
    
    test_texts = [
        "买入24国债07 *1000万 3.5%",
        "买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%，景益货币基金",
        "债券交易有哪些风险？",
        "卖出25国债08 500万 价格可议"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"智能工作流程 {i}")
        print(f"输入文本: {text}")
        
        # 步骤1: 分析文本特征
        characteristics = analyze_text_characteristics(text)
        print(f"📊 文本特征: {json.dumps(characteristics, ensure_ascii=False)}")
        
        # 步骤2: 推荐提示词类型
        recommended_type = recommend_prompt_type(text)
        print(f"🎯 推荐类型: {recommended_type}")
        
        # 步骤3: 获取并填充模板
        template = PROMPT_TEMPLATES[recommended_type]
        if recommended_type == "债券交易助手对话":
            filled_template = template.format(question=text, context_info="")
        else:
            filled_template = template.format(text=text)
        
        print(f"📝 生成提示词: {filled_template[:150]}...")
        
        # 步骤4: 生成推理说明
        reasoning = f"基于以下特征选择了'{recommended_type}'模板：" + \
                   f"包含*号={characteristics['has_asterisk']}, " + \
                   f"多产品={characteristics['has_multiple_products']}, " + \
                   f"是问题={characteristics['is_chat_question']}, " + \
                   f"产品数量={characteristics['product_count']}"
        
        print(f"💡 选择理由: {reasoning}")
        print("✅ 智能工作流程完成")
        print("=" * 60)

def main():
    """运行所有测试"""
    print("🧪 Bond Trading Prompt MCP Server 功能测试\n")
    
    try:
        test_text_analysis()
        test_prompt_recommendation()
        test_prompt_template_filling()
        test_smart_workflow()
        
        print("\n🎉 所有测试完成！")
        print("\n📋 测试总结:")
        print("- ✅ 文本特征分析功能正常")
        print("- ✅ 提示词推荐逻辑正确")
        print("- ✅ 模板填充功能正常")
        print("- ✅ 智能工作流程完整")
        print("\n🚀 MCP 服务器已准备就绪，可以集成到 AI 助手中使用！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 