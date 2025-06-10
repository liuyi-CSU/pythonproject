#!/usr/bin/env python3
"""
提示词管理器演示脚本 - 模拟实际使用场景
"""

import json
from prompt_manager import smart_get_prompt, get_available_prompts

def print_header(title):
    """打印标题"""
    print("\n" + "="*60)
    print(f"🎯 {title}")
    print("="*60)

def demo_interactive_mode():
    """交互式演示模式"""
    print_header("交互式提示词智能选择演示")
    
    print("💡 输入债券交易文本，AI将自动选择最适合的提示词模板")
    print("💡 输入 'quit' 退出，输入 'help' 查看可用模板")
    
    while True:
        print("\n" + "-"*40)
        user_input = input("📝 请输入债券交易文本: ").strip()
        
        if user_input.lower() == 'quit':
            print("👋 再见！")
            break
        elif user_input.lower() == 'help':
            available = get_available_prompts()
            print("\n📋 可用提示词模板:")
            for prompt_type in available['available_prompts']:
                description = available['descriptions'][prompt_type]
                print(f"  - {prompt_type}: {description}")
            continue
        elif not user_input:
            print("❌ 请输入有效的文本")
            continue
        
        try:
            # 使用智能提示词管理器
            result = smart_get_prompt(user_input)
            
            print(f"\n🤖 AI分析结果:")
            print(f"📊 推荐模板: {result['recommended_prompt_type']}")
            print(f"💡 推理过程: {result['reasoning']}")
            
            print(f"\n📝 生成的提示词:")
            print("-" * 40)
            print(result['filled_prompt'])
            print("-" * 40)
            
            print(f"\n📏 提示词长度: {len(result['filled_prompt'])} 字符")
            
        except Exception as e:
            print(f"❌ 处理失败: {str(e)}")

def demo_batch_processing():
    """批量处理演示"""
    print_header("批量处理演示")
    
    # 模拟实际业务场景的测试数据
    test_scenarios = [
        {
            "scenario": "普通单一债券交易",
            "texts": [
                "买入24国债07 1000万 3.5%",
                "卖出25国债08 500万 3.2%"
            ]
        },
        {
            "scenario": "包含请示标记的交易",
            "texts": [
                "买入24国债07 *1000万 3.5%",
                "卖出25国债08 500万 *3.2%"
            ]
        },
        {
            "scenario": "多产品复合交易",
            "texts": [
                "买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%",
                "景益货币基金买入24国债07 1000万 3.5%，景顺货币基金卖出25国债08 500万 3.2%"
            ]
        },
        {
            "scenario": "可议价交易",
            "texts": [
                "买入24国债07 1000万 价格可议",
                "卖出25国债08 500万 可议价"
            ]
        },
        {
            "scenario": "问答咨询",
            "texts": [
                "什么是债券交易？",
                "债券交易有哪些风险？",
                "如何计算债券收益率？"
            ]
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n🎬 场景: {scenario['scenario']}")
        print("-" * 50)
        
        for i, text in enumerate(scenario['texts'], 1):
            print(f"\n📝 示例 {i}: {text}")
            
            try:
                result = smart_get_prompt(text)
                print(f"   🎯 推荐模板: {result['recommended_prompt_type']}")
                print(f"   📊 特征分析: 包含*号={result['text_characteristics']['has_asterisk']}, "
                      f"多产品={result['text_characteristics']['has_multiple_products']}, "
                      f"是问题={result['text_characteristics']['is_chat_question']}")
                
            except Exception as e:
                print(f"   ❌ 处理失败: {str(e)}")

def demo_api_simulation():
    """模拟API调用演示"""
    print_header("API调用模拟演示")
    
    print("🔧 模拟将提示词管理器集成到现有API中...")
    
    def simulate_api_call(text, context=""):
        """模拟API调用"""
        print(f"\n📡 API调用: /smart-parse")
        print(f"📥 输入参数: text='{text}', context='{context}'")
        
        try:
            # 使用智能提示词管理器
            result = smart_get_prompt(text, context)
            
            # 模拟API响应
            api_response = {
                "status": "success",
                "data": {
                    "recommended_prompt_type": result['recommended_prompt_type'],
                    "prompt": result['filled_prompt'],
                    "analysis": result['text_characteristics'],
                    "reasoning": result['reasoning']
                }
            }
            
            print(f"📤 API响应: {json.dumps(api_response, ensure_ascii=False, indent=2)}")
            return api_response
            
        except Exception as e:
            error_response = {
                "status": "error",
                "message": str(e)
            }
            print(f"📤 API响应: {json.dumps(error_response, ensure_ascii=False, indent=2)}")
            return error_response
    
    # 模拟几个API调用
    test_calls = [
        {"text": "买入24国债07 *1000万 3.5%"},
        {"text": "什么是债券交易？", "context": "用户是新手投资者"},
        {"text": "买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%"}
    ]
    
    for call in test_calls:
        simulate_api_call(**call)

def demo_integration_example():
    """集成示例演示"""
    print_header("集成到现有系统示例")
    
    print("🔧 演示如何将智能提示词管理器集成到现有的债券解析系统中...")
    
    # 模拟原有系统的函数
    def old_parse_bond_text(text, prompt_type="单一指令解析"):
        """原有的解析函数（简化版）"""
        print(f"🔄 原有系统: 使用固定提示词类型 '{prompt_type}' 解析文本")
        return f"使用 {prompt_type} 解析: {text}"
    
    def new_parse_bond_text(text, context=""):
        """新的智能解析函数"""
        print(f"🚀 新系统: 使用AI智能选择提示词类型")
        
        # 使用智能提示词管理器
        result = smart_get_prompt(text, context)
        
        print(f"   🎯 AI推荐: {result['recommended_prompt_type']}")
        print(f"   💡 推理: {result['reasoning']}")
        
        # 这里可以继续调用实际的模型解析
        return {
            "prompt_type": result['recommended_prompt_type'],
            "prompt": result['filled_prompt'],
            "analysis": result['text_characteristics']
        }
    
    # 对比演示
    test_text = "买入24国债07 *1000万 3.5%"
    
    print(f"\n📝 测试文本: {test_text}")
    print("\n🔄 原有方式:")
    old_result = old_parse_bond_text(test_text)
    print(f"   结果: {old_result}")
    
    print("\n🚀 新的智能方式:")
    new_result = new_parse_bond_text(test_text)
    print(f"   结果: 智能选择了 '{new_result['prompt_type']}' 模板")

def main():
    """主函数"""
    print("🎉 债券交易提示词智能管理器演示")
    print("=" * 60)
    
    while True:
        print("\n📋 请选择演示模式:")
        print("1. 交互式演示 (推荐)")
        print("2. 批量处理演示")
        print("3. API调用模拟")
        print("4. 系统集成示例")
        print("5. 退出")
        
        choice = input("\n🎯 请输入选择 (1-5): ").strip()
        
        if choice == '1':
            demo_interactive_mode()
        elif choice == '2':
            demo_batch_processing()
        elif choice == '3':
            demo_api_simulation()
        elif choice == '4':
            demo_integration_example()
        elif choice == '5':
            print("\n👋 感谢使用！")
            break
        else:
            print("❌ 无效选择，请输入 1-5")

if __name__ == "__main__":
    main() 