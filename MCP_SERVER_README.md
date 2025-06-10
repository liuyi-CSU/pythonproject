# Bond Trading Prompt Template MCP Server

这是一个 MCP (Model Context Protocol) 服务器，用于智能地选择和管理债券交易文本解析的提示词模板。AI 可以根据输入文本的特征自动选择最合适的提示词模板。

## 功能特性

### 🤖 智能提示词选择
- **自动分析文本特征**：识别是否包含*号、多产品、可议价关键词等
- **智能推荐模板**：基于文本特征自动选择最适合的提示词类型
- **一键获取**：组合分析和模板获取，一步到位

### 📝 提示词模板管理
- **单一指令解析**：处理标准的单个债券交易指令
- **带请示单一指令解析**：处理包含请示标记（*号）的交易指令
- **多产品指令语料解析**：处理包含多个债券产品的复合指令
- **债券交易助手对话**：处理问答和对话场景

## 安装和设置

### 1. 安装依赖
```bash
pip install -r requirements_mcp.txt
```

### 2. 配置 AI 助手
将 `mcp_config.json` 中的配置添加到你的 AI 助手配置中（如 Claude Desktop）。

### 3. 运行服务器
```bash
python mcp_prompt_server.py
```

## 可用工具

### 1. `get_available_prompts`
**功能**：获取所有可用的提示词模板类型和描述
**参数**：无
**返回**：所有可用模板列表和详细描述

### 2. `analyze_text`
**功能**：分析文本特征，识别债券交易文本的关键信息
**参数**：
- `text`: 要分析的债券交易文本

**返回示例**：
```json
{
  "has_asterisk": true,
  "has_multiple_products": false,
  "has_negotiable_keywords": false,
  "product_count": 1,
  "bond_codes": ["24国债07"],
  "has_fund_names": false,
  "is_chat_question": false
}
```

### 3. `recommend_prompt`
**功能**：基于文本特征智能推荐最适合的提示词模板类型
**参数**：
- `text`: 债券交易文本

**返回示例**：
```json
{
  "recommended_prompt_type": "带请示单一指令解析",
  "reason": "基于文本特征分析推荐使用'带请示单一指令解析'",
  "text_characteristics": {...}
}
```

### 4. `get_prompt_template`
**功能**：获取指定类型的提示词模板
**参数**：
- `prompt_type`: 提示词类型（枚举值）
- `text`: 要填入模板的文本（可选）
- `question`: 聊天问题（仅对话模板需要）
- `context_info`: 上下文信息（仅对话模板需要）

### 5. `smart_get_prompt` ⭐ **推荐使用**
**功能**：智能选择并获取最适合的提示词模板（一步到位）
**参数**：
- `text`: 债券交易文本或聊天问题
- `context_info`: 上下文信息（可选）

**返回示例**：
```json
{
  "recommended_prompt_type": "带请示单一指令解析",
  "text_characteristics": {...},
  "filled_prompt": "请将以下债券交易文本解析为JSON格式...",
  "reasoning": "基于以下特征选择了'带请示单一指令解析'模板：包含*号=true, 多产品=false, 是问题=false, 产品数量=1"
}
```

## 使用示例

### 示例 1：分析包含请示标记的文本
```
输入文本："买入24国债07 *1000万 3.5%"
→ AI 自动识别包含*号
→ 推荐使用"带请示单一指令解析"模板
→ 返回填充好的提示词
```

### 示例 2：分析多产品交易文本
```
输入文本："买入24国债07 1000万 3.5%，卖出25国债08 2000万 3.8%"
→ AI 识别包含多个债券代码
→ 推荐使用"多产品指令语料解析"模板
→ 返回适合多产品解析的提示词
```

### 示例 3：处理问答场景
```
输入文本："什么是债券交易的基本流程？"
→ AI 识别为问题模式
→ 推荐使用"债券交易助手对话"模板
→ 返回对话式的提示词
```

## 智能选择逻辑

MCP 服务器使用以下逻辑智能选择提示词模板：

1. **问题检测优先**：如果包含问号、"什么"、"如何"等问题指示词 → 选择"债券交易助手对话"

2. **多产品检测**：如果包含多个债券代码 → 选择"多产品指令语料解析"

3. **请示标记检测**：如果包含*号或可议价关键词 → 选择"带请示单一指令解析"

4. **默认选择**：其他情况 → 选择"单一指令解析"

## 集成到现有系统

可以将此 MCP 服务器与现有的债券交易解析系统集成：

```python
# 在 main.py 中使用 MCP 服务器的推荐结果
def get_smart_prompt_type(text: str) -> str:
    # 调用 MCP 服务器的 smart_get_prompt 工具
    # 获取推荐的提示词类型
    return recommended_prompt_type

# 修改现有的解析函数
parsed_data = call_ollama_model(input_data.text, get_smart_prompt_type(input_data.text))
```

## 优势

1. **自动化**：无需手动选择提示词类型，AI 自动分析和推荐
2. **准确性**：基于文本特征的智能分析，提高提示词选择的准确性
3. **可扩展**：易于添加新的提示词模板和分析规则
4. **标准化**：通过 MCP 协议提供标准化的工具接口
5. **灵活性**：支持多种使用场景和自定义参数

## 技术架构

```
AI 助手 (Claude/GPT) 
    ↓ MCP Protocol
MCP Server (mcp_prompt_server.py)
    ↓ 智能分析
文本特征分析 + 提示词推荐
    ↓ 
返回最适合的提示词模板
```

这个 MCP 服务器让 AI 能够更智能地处理债券交易文本，自动选择最合适的解析策略，提高解析的准确性和效率。 