# 新闻可信度分析工具使用指南

## 基本使用

### 命令行使用

```bash
python news_credibility.py --url https://example.com/news-article
python news_credibility.py --text "需要分析的新闻文本..."
```

### Python代码中使用

```python
from news_credibility import main

# 分析URL
result = main(url="https://example.com/news-article")

# 分析文本
result = main(text="需要分析的新闻文本...")

# 显示结果
print(result)
```

## 高级选项

### 单独使用各个分析模块

```python
from news_credibility import check_ai_content, fact_check, analyze_source_quality

# 检测AI生成内容
ai_prob, details = check_ai_content("需要分析的文本")

# 事实核查
facts_score, facts_details = fact_check("需要核查的文本")

# 分析来源质量
source_score, source_details = analyze_source_quality("文本", "https://example.com")
```

### 自定义分析权重

可以通过传递权重参数来调整各维度在最终评分中的重要性：

```python
from news_credibility import main

result = main(
    text="新闻文本",
    weights={
        "ai_content": 1.0,
        "facts": 2.0,      # 加倍重视事实准确性
        "source": 1.5,     # 提高来源质量权重
        "neutrality": 1.0,
        "cross_check": 1.0,
        "citations": 0.5   # 降低引用分数权重
    }
)
```

## 输出解释

分析结果包含以下部分：

1. **总体可信度评分**：0-100分，越高越可信
2. **可信度级别**：高、中、低或可疑
3. **各维度详细分析**：六个维度的独立评分和解释
4. **建议措施**：基于分析给出的建议

## 示例

查看`example.py`、`example_opensource.py`和`example_usage.py`获取更多使用示例。