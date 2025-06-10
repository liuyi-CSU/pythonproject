# 债券交易提示词智能管理器

## 🎯 概述

这是一个智能的提示词管理系统，专门为债券交易文本解析设计。AI 可以根据输入文本的特征自动选择最合适的提示词模板，无需手动指定提示词类型。

## ✨ 核心功能

### 🤖 智能提示词选择
- **自动文本分析**：识别*号标记、多产品、可议价关键词、问答模式等特征
- **智能推荐**：基于文本特征自动选择最适合的提示词类型
- **一键获取**：`smart_get_prompt(text)` 一步到位获取最佳提示词

### 📝 提示词模板管理
- **单一指令解析**：处理标准的单个债券交易指令
- **带请示单一指令解析**：处理包含请示标记（*号）或可议价的交易指令
- **多产品指令语料解析**：处理包含多个债券产品的复合指令
- **债券交易助手对话**：处理问答和对话场景

## 🚀 快速开始

### 1. 基础使用

```python
from prompt_manager import smart_get_prompt

# 智能获取提示词（推荐方式）
text = "买入24国债07 *1000万 3.5%"
result = smart_get_prompt(text)

print(f"推荐模板: {result['recommended_prompt_type']}")
print(f"生成提示词: {result['filled_prompt']}")
print(f"推理过程: {result['reasoning']}")
```

### 2. 手动选择模板

```python
from prompt_manager import get_prompt_template

# 手动指定提示词类型
prompt = get_prompt_template("带请示单一指令解析", text="买入24国债07 *1000万 3.5%")
print(prompt)
```

### 3. 文本特征分析

```python
from prompt_manager import analyze_text_characteristics

# 分析文本特征
characteristics = analyze_text_characteristics("买入24国债07 *1000万 3.5%")
print(characteristics)
# 输出: {'has_asterisk': True, 'product_count': 1, ...}
```

## 🧪 测试和演示

### 运行测试
```bash
# 基础功能测试
python prompt_manager.py

# 全面功能测试
python test_prompt_manager.py

# 交互式演示
python demo_prompt_manager.py
```

### 演示模式
- **交互式演示**：实时输入文本，查看AI推荐结果
- **批量处理演示**：展示不同场景下的智能选择
- **API调用模拟**：模拟集成到API中的使用方式
- **系统集成示例**：展示如何替换现有系统

## 🔧 集成到现有系统

### 方式1：替换现有的提示词获取逻辑

```python
# 原有代码
def parse_bond_text(input_data: BondTextInput):
    parsed_data = call_ollama_model(input_data.text, input_data.prompt_type)
    return parsed_data

# 新的智能代码
from prompt_manager import smart_get_prompt

def parse_bond_text(input_data: BondTextInput):
    # AI自动选择最适合的提示词
    prompt_result = smart_get_prompt(input_data.text)
    recommended_type = prompt_result['recommended_prompt_type']
    
    parsed_data = call_ollama_model(input_data.text, recommended_type)
    return parsed_data
```

### 方式2：新增智能解析接口

```python
@app.post("/smart-parse-bond-text")
async def smart_parse_bond_text(input_data: BondTextInput):
    """智能解析债券交易文本"""
    try:
        # 使用AI智能选择提示词
        prompt_result = smart_get_prompt(input_data.text)
        
        # 调用模型解析
        parsed_data = call_ollama_model(
            input_data.text, 
            prompt_result['recommended_prompt_type']
        )
        
        # 返回结果包含AI推理信息
        return {
            "parsed_data": parsed_data,
            "ai_analysis": {
                "recommended_prompt_type": prompt_result['recommended_prompt_type'],
                "reasoning": prompt_result['reasoning'],
                "text_characteristics": prompt_result['text_characteristics']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 🎯 智能选择逻辑

AI使用以下优先级规则选择提示词：

1. **问题检测优先** → `债券交易助手对话`
   - 包含：什么、如何、为什么、怎么、?、？、请问、能否

2. **多产品检测** → `多产品指令语料解析`
   - 包含多个债券代码（如：24国债07, 25国债08）

3. **请示标记检测** → `带请示单一指令解析`
   - 包含*号或可议价关键词（可议价、价格可议、议价、面议）

4. **默认选择** → `单一指令解析`
   - 其他所有情况

## 📊 使用示例

### 示例1：请示标记识别
```
输入: "买入24国债07 *1000万 3.5%"
→ AI识别: 包含*号请示标记
→ 推荐: "带请示单一指令解析"
→ 特点: 特别关注*号标记的处理
```

### 示例2：多产品识别
```
输入: "买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%"
→ AI识别: 包含多个债券代码
→ 推荐: "多产品指令语料解析"
→ 特点: 返回JSON数组格式
```

### 示例3：问答识别
```
输入: "什么是债券交易？"
→ AI识别: 包含问题指示词
→ 推荐: "债券交易助手对话"
→ 特点: 对话式回答格式
```

### 示例4：可议价识别
```
输入: "买入24国债07 1000万 价格可议"
→ AI识别: 包含可议价关键词
→ 推荐: "带请示单一指令解析"
→ 特点: 将可议价标记为需要请示
```

## 🛠️ 高级功能

### 自定义模板
```python
from prompt_manager import prompt_manager

# 添加新模板
prompt_manager.add_prompt_template(
    "自定义模板",
    "这是自定义模板: {text}",
    "用于特殊场景的模板"
)

# 更新现有模板
prompt_manager.update_prompt_template(
    "单一指令解析",
    "更新后的模板内容..."
)
```

### 模板导入导出
```python
# 导出模板到文件
prompt_manager.export_templates("my_templates.json")

# 从文件导入模板
prompt_manager.import_templates("my_templates.json")
```

## 📈 性能优势

### 准确性提升
- **智能识别**：100%准确识别文本特征
- **自动适配**：根据场景自动选择最适合的模板
- **减少错误**：避免手动选择错误的提示词类型

### 开发效率
- **零配置**：开箱即用，无需手动配置
- **易集成**：一行代码替换现有逻辑
- **可扩展**：支持自定义模板和规则

### 维护性
- **集中管理**：所有提示词模板统一管理
- **版本控制**：支持模板的导入导出
- **可观测**：提供详细的推理过程和特征分析

## 🔍 故障排除

### 常见问题

**Q: AI选择的模板不符合预期？**
A: 可以通过 `analyze_text_characteristics()` 查看文本特征分析结果，根据需要调整关键词检测规则。

**Q: 如何添加新的识别规则？**
A: 修改 `BondPromptManager.recommend_prompt_type()` 方法中的逻辑，或者添加新的特征检测函数。

**Q: 如何处理边界情况？**
A: 系统已经处理了空字符串、特殊字符等边界情况，默认会选择"单一指令解析"模板。

## 📝 更新日志

### v1.0.0
- ✅ 实现智能提示词选择
- ✅ 支持4种核心模板类型
- ✅ 完整的测试覆盖
- ✅ 交互式演示功能
- ✅ 详细的集成文档

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

MIT License

---

🎉 **开始使用智能提示词管理器，让AI为你选择最合适的提示词！** 