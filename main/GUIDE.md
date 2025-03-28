# 新闻可信度分析工具使用指南

本文档提供新闻可信度分析工具的详细使用说明。该工具已重构为多个模块，每个模块负责特定的功能。

## 文件结构

整个项目被拆分为以下模块：

1. **main.py** - 程序入口，只负责命令行交互和流程控制
2. **core_analyzer.py** - 核心分析逻辑，包含主要的分析功能
3. **text_analysis.py** - 文本分析和评估
4. **citation_analysis.py** - 引用分析和提取
5. **citation_validation.py** - 引用验证和真实性评估
6. **validation.py** - 内容交叉验证，协调验证流程
7. **verification.py** - 新闻内容在线验证和本地可信度评估
8. **web_utils.py** - 网络工具和内容获取功能
9. **ai_services.py** - AI服务接口
10. **search_services.py** - 搜索服务接口
11. **utils.py** - 通用工具函数
12. **image_analysis.py** - 图像分析功能
13. **result_formatter.py** - 分析结果格式化和显示
14. **service_checker.py** - 服务状态检查
15. **config.py** - 配置和环境变量
16. **test_utils.py** - 测试工具函数

## 系统自检功能

程序启动时会自动执行系统自检，检查所有依赖服务的可用性并显示状态报告。自检内容包括：

1. **DeepSeek API 状态检查**
   - 如果DeepSeek API不可用，将显示受影响的功能：
     - 引用真实性判断(judge_citation_truthfulness)
     - 引用有效性分析(analyze_citation_validity)
     - 引用质量评估(get_citation_score)
     - 深度新闻分析(analyze_with_deepseek_v3)
     - 交叉验证(perform_cross_validation)
     - 验证点提取(extract_verification_points_with_deepseek)
     - 搜索结果验证(verify_search_results_with_deepseek)

2. **SearXNG 搜索引擎状态检查**
   - 如果SearXNG不可用，将显示受影响的功能：
     - 交叉验证(perform_cross_validation)
     - 搜索验证(search_with_searxng)
     - 引用验证(verify_citation_with_searxng)

如果关键服务不可用，系统会自动降级到使用本地算法进行分析，但精度可能受限。

### 服务降级处理

当关键服务不可用时，系统会采取以下降级策略：

1. **DeepSeek API不可用时**：
   - AI内容检测将完全依赖本地算法
   - 引用分析将使用基本规则进行评估
   - 交叉验证功能将受限
   - 权重配置会自动调整，更依赖本地算法

2. **SearXNG不可用时**：
   - 引用验证将使用替代方法（内容一致性分析、语言特征分析）
   - 交叉验证将无法执行网络搜索验证

## 命令行选项

程序提供了多种命令行选项以适应不同的使用场景：

```bash
# 使用默认测试文本
python main.py

# 分析指定的URL
python main.py --url https://example.com/news/article

# 分析提供的文本
python main.py --text "这是一篇需要分析的新闻文本..."

# 分析文件中的内容
python main.py --file path/to/news.txt
```

### 高级选项

```bash
# 不使用在线验证
python main.py --no-online

# 不使用AI服务
python main.py --no-ai

# 启用调试模式
python main.py --debug

# 启用详细日志
python main.py --verbose

# 指定日志文件路径
python main.py --log-file custom_log.log

# 快速模式（跳过DeepSeek API分析）
python main.py --quick

# 运行功能测试
python main.py --test

# 保存分析结果到本地
python main.py --url https://example.com/news/article --save

# 指定保存目录
python main.py --url https://example.com/news/article --save --save-dir my_news

# 测试DeepSeek API连接
python main.py --test-deepseek
```

## 彩色输出支持

本工具支持终端彩色输出，使分析结果更加直观：

- 高可信度评分（≥0.8）显示为绿色
- 中等可信度评分（≥0.6）显示为青色
- 低可信度评分（≥0.4）显示为黄色
- 极低可信度评分（<0.4）显示为红色

如果系统无法导入`colorama`包，程序会自动降级为普通文本输出。

## 评分权重

本工具采用混合算法评估新闻可信度，权重分配如下：

### 当DeepSeek API可用时

当DeepSeek API可用时，系统会采用混合评分机制：

- **本地算法评分占总评分的20%**
- DeepSeek AI分析结果占总评分的80%

### 当DeepSeek API不可用时

当DeepSeek API不可用时，系统会完全依赖本地算法进行评分，权重分配如下：

- AI内容检测 (15%)
- 语言中立性 (20%)
- 来源和引用质量 (20%)
- DeepSeek综合分析 (30%)（此时使用默认值）
- 交叉验证 (15%)（此时使用默认值）

可以通过修改`config.py`中的`DEFAULT_WEIGHTS`字典来调整各项本地分析的权重。

## 交叉验证功能

交叉验证是本工具的重要特性，它通过以下步骤验证新闻内容的可信度：

1. **提取验证点** - 从文本中提取需要验证的关键事实陈述，按重要性分类
2. **搜索验证** - 使用SearXNG搜索引擎查找相关信息
3. **AI判断** - 使用DeepSeek AI判断搜索结果与验证点的一致性
4. **生成报告** - 生成详细的交叉验证报告，包括每个验证点的评分和结论

### 交叉验证流程详解

validation.py模块实现了完整的交叉验证功能，主要包括以下步骤：

1. **前置条件检查**：检查必要服务（DeepSeek API和SearXNG搜索引擎）的可用性。如果任一服务不可用，交叉验证将无法完整执行。

2. **提取验证点**：
   - 使用`extract_verification_points_with_deepseek()`函数从文本中提取5个关键的事实陈述作为验证点
   - 对每个验证点标记重要性（高/中/低）和生成适合搜索的关键词
   - 如果DeepSeek API不可用或提取失败，会调用`generate_default_verification_points()`生成默认验证点

3. **验证每个关键点**：
   - 对每个验证点构建搜索查询并使用SearXNG执行搜索
   - 通过`verify_search_results_with_deepseek()`函数评估搜索结果与验证点的一致性
   - 生成单个验证点的评分（0-1）和结论

4. **生成总体评分**：
   - 综合各个验证点的评分，根据重要性加权计算总体可信度
   - 生成总体验证结论

5. **故障安全机制**：
   - 当DeepSeek API返回无法解析的JSON时，使用正则表达式提取有效部分
   - 当SearXNG连接中断时，使用已验证的点计算部分结果
   - 当验证过程出错时，使用`generate_default_verification_result()`提供基本评估

### 交叉验证数据结构与处理

交叉验证生成的数据可能以多种形式存在，系统实现了强大的数据处理机制：

1. **数据结构多样性处理**：
   - 交叉验证数据可能以不同键名存储（"验证点"、"verification_points"、"claims"等）
   - result_formatter实现灵活的数据提取策略，支持多种命名约定和格式
   - 对每种可能的数据结构都实现专门的解析逻辑

2. **来源数量智能估算**：
   - 首先尝试直接的来源计数字段（如"source_count"、"搜索结果总数"等）
   - 备选策略包括计算sources/相关来源/verified_sources数组长度
   - 当来源计数为0但搜索结果存在时，使用搜索结果数作为估计值
   - 完整记录日志，确保来源计数推导过程可追溯

3. **验证点结果统计**：
   - 系统会自动统计搜索结果数量及无结果的验证点
   - 累计计算所有验证点的搜索结果总数
   - 即使原始数据结构不完整，也能有效提取信息

### 降级验证机制

当AI服务不可用时，validation.py会实施以下降级验证策略：

1. **关键词匹配降级**：
   - 当DeepSeek API无法用于验证搜索结果时，系统会使用基本的关键词匹配算法
   - 通过计算验证点与搜索结果之间的词汇重叠度来评估一致性
   - 生成基本的评分和结论，但会标明结果精度有限

2. **默认验证点生成**：
   - 当无法使用AI提取验证点时，系统会从文本中提取前几个重要句子作为验证点
   - 自动为这些句子生成搜索关键词

3. **验证失败处理**：
   - 所有验证功能都包含完善的异常处理
   - 在关键服务失败时提供降级但可用的结果

## 引用真实性评估

本工具使用多种方法评估新闻中引用内容的真实性：

1. **SearXNG搜索验证** - 对于未指明来源的引用，系统会自动使用SearXNG搜索引擎进行网络验证，查找是否有相同或相似的内容存在于互联网上。

2. **来源可靠性评估** - 对于指明了来源的引用，系统会评估来源的可靠性和权威性。

3. **替代评估方法** - 当SearXNG搜索不可用或受到访问限制时，系统会使用替代方法进行评估：
   - 内容一致性分析 - 检查引用内容与上下文的一致性
   - 语言特征分析 - 分析引用的语言特征是否符合预期
   - 专业术语使用 - 检查专业术语的使用是否准确

### SearXNG配置

为了使引用验证功能正常工作，需要正确配置SearXNG搜索引擎：

1. **安装SearXNG**：
   ```bash
   # 使用Docker安装SearXNG
   docker pull searxng/searxng
   docker run -d -p 8080:8080 --name searxng searxng/searxng
   ```

2. **配置环境变量**：
   在`.env`文件中设置SearXNG URL：
   ```
   SEARXNG_URL=http://localhost:8080/search
   ```

3. **测试连接**：
   ```bash
   # 测试SearXNG连接
   python -c "from search_services import test_searxng_connection; print(test_searxng_connection())"
   ```

## 结果格式与显示

分析结果采用分级结构显示，主要包括以下几个部分：

1. **各模块分析结果** - 使用▶符号标记不同分析模块的结果
2. **详细评分与描述** - 每个模块下使用•符号列出详细评分点和描述
3. **DeepSeek多维度评分** - 使用缩进格式显示AI分析的多维度评分
4. **交叉验证结果** - 显示验证点、搜索结果和验证结论
5. **图片分析结果** - 用特殊边框显示图片分析部分
6. **结论摘要** - 提供总体分析结论

### 多层次信息展示

result_formatter.py模块实现了多层次信息展示架构：

1. **分层信息展示**：
   - 顶层展示总体评分和评级
   - 二级展示主要维度评分（内容真实性、信息准确性等）
   - 三级展示细分评分和具体分析
   - 四级展示交叉验证结果
   - 五级展示问题分析

2. **动态内容适应**：
   - 根据可用数据动态调整显示内容
   - 当特定分析不可用时提供合理的替代信息
   - 自动处理数据缺失情况，确保UI连贯性

3. **用户体验优化**：
   - 使用视觉分隔符（横线、色块）增强可读性
   - 进度条可视化评分
   - a色彩编码传达信息重要性（成功/警告/错误）
   - 简洁明了的问题描述和建议

### 问题分析机制

result_formatter.py的analyze_problems函数实现了全面的问题检测和分析：

1. **问题条件精确判定**：
   - 分析总体可信度，低于阈值时添加问题警告
   - 分析各维度评分，对不达标的评分维度生成具体问题
   - 智能分析交叉验证，仅在真正缺乏来源时报告来源不足问题
   - 避免误报，提高问题分析准确性

2. **交叉验证问题特殊处理**：
   - 当搜索结果充足时不会错误报告来源不足问题
   - 分别评估验证点问题和来源问题，提供精准分析
   - 根据搜索结果数动态调整来源数量判断

3. **问题分类与排序**：
   - 按严重程度分类（严重/中等）
   - 问题按严重性排序显示
   - 对每个问题提供具体的改进建议

### 错误恢复与容错机制

系统实现了多层次的错误恢复与容错机制：

1. **多级数据验证**：
   - 验证数据类型（dict、list、str等）
   - 验证评分范围（0-1之间）
   - 验证键存在性和值有效性
   
2. **降级显示策略**：
   - 当完整交叉验证不可用时，使用权重信息显示基础内容
   - 当评分缺失时，使用合理的默认值并标明
   - 在极端数据缺失情况下仍提供基本信息框架

3. **异常处理链**：
   - 在每个处理环节实现try-except块
   - 捕获并记录具体异常，避免整个显示过程中断
   - 提供友好的错误信息，保留内部错误详情便于调试

### 输出格式示例

```
▶ AI生成内容检测
  • 综合评分: 0.32 
  • DeepSeek多维度评分 (AI生成内容):
    - 表达模式: 0.80
    - 词汇多样性: 0.70
    - 句子变化: 0.70
    - 上下文连贯性: 0.80
    - 人类特征: 0.70

  • DeepSeek分析:
    文本的表达模式较为正式，符合科技新闻的常见风格，词汇使用较为多样...

▶ 语言中立性
  • 综合评分: 0.87 
  • DeepSeek多维度评分 (语言中立性):
    - 情感词汇: 0.80
    - 情感平衡: 0.90
    - 极端表述: 0.85
    - 煽动性表达: 0.85
    - 主观评价: 0.80

▶ 来源质量
  • 政府/教育/军事域名，提高可信度
  • 引用了有限的来源 (1个)
  • 未发现权威来源引用

▶ 图片分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  图像可信度评估：较低
  未检测到明确的图像描述
  图像真实性平均评分: 0.93

  图片 1 分析:
      元数据分析: 图像不包含EXIF元数据，可能已被处理或是截图
      质量分析: 图像清晰度高; 图像边缘丰富，细节较多; 图像色彩分布自然
      一致性分析: 图像光照分布自然; 图像饱和度分布异常
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 彩色显示

系统会根据不同类型的信息使用不同的颜色和格式进行显示：

- 标题和小标题使用不同级别的颜色突出显示
- 评分会根据高低使用不同颜色（绿色、青色、黄色、红色）
- 警告和错误信息使用黄色或红色显示
- 信息层次结构通过缩进和颜色区分

## 配置文件与环境变量

本工具使用配置文件和环境变量来管理设置：

### 环境变量

在项目根目录的`.env`文件中配置以下环境变量：

```
# DeepSeek API配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# SearXNG搜索引擎配置
SEARXNG_URL=http://localhost:8080/search

# 日志配置
LOG_LEVEL=INFO
DEBUG_MODE=false
```

### 配置文件

`config.py`文件包含程序的主要配置项：

- 默认权重配置（DEFAULT_WEIGHTS）
- 颜色和格式化设置
- 文件路径配置
- 服务可用性标志（DEEPSEEK_API_AVAILABLE, SEARXNG_AVAILABLE）
- 日志设置函数

## 模块功能说明

### main.py - 程序入口

- `parse_arguments()` - 解析命令行参数
- `main()` - 主程序入口，组织工作流
- `setup_environment()` - 设置程序环境
- `print_banner()` - 显示程序横幅
- `handle_test_mode()` - 处理测试模式功能

### core_analyzer.py - 核心分析逻辑

- `analyze_news_credibility()` - 综合分析新闻可信度
- `save_news_to_local()` - 保存新闻到本地
- `analyze_news_content()` - 分析新闻内容核心功能
- `calculate_final_score()` - 计算综合评分
- `weight_check()` - 检查权重配置
- `extract_issues()` - 提取可信度问题
- `calculate_weighted_score()` - 计算加权分数

### text_analysis.py - 文本分析和评估

- `check_ai_content()` - 检测内容是否由AI生成（使用本地算法）
- `analyze_language_neutrality()` - 分析语言中立性
- `analyze_source_quality()` - 分析来源质量
- `analyze_text_logic()` - 分析文本逻辑性
- `basic_logic_analysis()` - 基本逻辑分析
- `local_news_validation()` - 验证本地新闻
- `detect_bias_words()` - 检测偏见词汇
- `check_exaggeration()` - 检查夸张表述
- `measure_readability()` - 测量可读性
- `check_clickbait()` - 检测标题党特征

### citation_analysis.py - 引用分析和提取

- `extract_citations()` - 从文本中提取引用内容
- `judge_citation_truthfulness()` - 判断引用内容真实性（使用DeepSeek API）
- `analyze_citation_validity()` - 分析引用有效性（使用DeepSeek API）
- `get_citation_score()` - 获取引用质量评分（使用DeepSeek API）
- `identify_citation_sources()` - 识别引用来源
- `count_direct_quotes()` - 统计直接引用
- `evaluate_citation_diversity()` - 评估引用多样性
- `check_anonymous_sources()` - 检查匿名来源

### citation_validation.py - 引用验证

- `validate_citations()` - 验证文本中引用的真实性
- `generate_validation_summary()` - 生成验证摘要
- `extract_and_validate_quotes()` - 提取并验证引用内容
- `verify_quote_with_searxng()` - 使用搜索引擎验证引用
- `analyze_quote_consistency()` - 分析引用的内部一致性
- `score_citation_verification()` - 对引用验证进行评分

### validation.py - 内容交叉验证

- `perform_cross_validation()` - 执行交叉验证，协调整个验证流程
- `extract_verification_points_with_deepseek()` - 使用DeepSeek从文本中提取需要验证的关键点
- `verify_search_results_with_deepseek()` - 使用DeepSeek判断搜索结果与验证点的一致性
- `generate_default_verification_points()` - 在DeepSeek API不可用时生成默认验证点
- `generate_default_verification_result()` - 在验证失败时生成基础验证结果

### verification.py - 新闻在线验证

- `search_and_verify_news()` - 搜索并验证新闻内容
- `web_cross_verification()` - 网络交叉验证
- `local_text_credibility()` - 本地文本可信度分析
- `check_google_trends()` - 检查Google趋势
- `evaluate_web_presence()` - 评估网络存在情况
- `compare_with_similar_news()` - 与类似新闻比较

### service_checker.py - 服务状态检查

- `initialize_services()` - 初始化服务连接
- `print_service_status()` - 打印服务状态
- `test_all_services()` - 测试所有服务连接状态
- `get_service_status_report()` - 获取服务状态报告
- `check_search_services()` - 检查搜索服务状态
- `check_ai_services()` - 检查AI服务状态

### result_formatter.py - 分析结果格式化

- `print_formatted_result()` - 格式化打印结果，按模块分类组织输出，使用▶符号标记各部分
- `get_credibility_summary()` - 根据可信度评分生成简短的总结性描述
- `get_rating_emoji()` - 将数值评分转换为对应的emoji表示和评级
- `get_progress_bar()` - 生成可视化进度条用于展示评分
- `get_credibility_rating()` - 将评分转换为文字评级和等级

result_formatter.py模块负责将分析结果以结构化、易读的方式呈现给用户。输出采用分级结构，主要包括以下模块：

1. **AI生成内容检测** - 显示内容是否可能由AI生成的评分和多维度分析
2. **语言中立性** - 分析文本语言的客观性和中立程度
3. **来源质量** - 评估文章引用的来源可靠性
4. **域名可信度** - 分析网站域名的可信程度
5. **引用有效性与质量** - 检查引用的准确性和质量
6. **本地新闻验证** - 验证本地相关性指标
7. **逻辑分析** - 评估文本的逻辑结构和连贯性
8. **交叉验证** - 展示通过互联网验证的结果
9. **图片分析** - 特殊格式显示图片真实性分析

### config.py - 配置模块

- `setup_python_path()` - 设置Python路径
- `setup_logging()` - 配置日志系统
- `DEFAULT_WEIGHTS` - 默认评分权重
- `DEEPSEEK_WEIGHTS` - DeepSeek评分权重
- `init_colorama()` - 初始化彩色输出
- `load_config()` - 加载配置信息
- `update_weights()` - 更新权重配置

### web_utils.py - 网络工具

- `get_text_from_url()` - 从URL获取文本内容
- `evaluate_domain_trust()` - 评估域名可信度
- `fetch_news_content()` - 获取新闻内容
- `extract_main_content()` - 提取网页主要内容
- `detect_paywalls()` - 检测付费墙
- `clean_html_content()` - 清理HTML内容
- `get_domain_info()` - 获取域名信息
- `check_domain_reputation()` - 检查域名声誉
- `retrieve_webpage_metadata()` - 获取网页元数据

### search_services.py - 搜索服务

- `query_searxng()` - 查询SearXNG搜索引擎
- `search_with_searxng()` - 使用SearXNG搜索
- `verify_citation_with_searxng()` - 使用SearXNG验证引用
- `test_searxng_connection()` - 测试SearXNG连接
- `parse_searxng_results()` - 解析SearXNG结果
- `format_search_query()` - 格式化搜索查询
- `filter_search_results()` - 过滤搜索结果
- `check_result_relevance()` - 检查结果相关性
- `extract_snippet_information()` - 提取摘要信息

### ai_services.py - AI服务

- `test_deepseek_connection()` - 测试DeepSeek连接
- `query_deepseek()` - 查询DeepSeek API
- `analyze_with_deepseek_v3()` - 使用DeepSeek v3分析文本
- `detect_ai_generated_content()` - 检测AI生成内容
- `analyze_news_credibility_with_ai()` - 使用AI分析新闻可信度
- `extract_facts_from_text()` - 从文本中提取事实
- `analyze_text_sentiment()` - 分析文本情感
- `summarize_text()` - 文本摘要生成
- `handle_api_errors()` - 处理API错误

### utils.py - 通用工具

- `setup_logging()` - 设置日志
- `colored()` - 彩色文本输出
- `get_category_name()` - 获取类别名称
- `load_environment_variables()` - 加载环境变量
- `find_common_substrings()` - 查找公共子字符串
- `format_time()` - 格式化时间
- `save_json()` - 保存JSON数据
- `load_json()` - 加载JSON数据
- `sanitize_filename()` - 净化文件名
- `create_directory()` - 创建目录

### image_analysis.py - 图像分析

- `check_images()` - 检查图像与文本的一致性
- `analyze_image_authenticity()` - 分析图像真实性
- `extract_image_metadata()` - 提取图像元数据
- `detect_image_manipulation()` - 检测图像操作
- `analyze_image_quality()` - 分析图像质量
- `compare_image_with_text()` - 比较图像与文本
- `get_image_features()` - 获取图像特征
- `check_image_consistency()` - 检查图像一致性

### test_utils.py - 测试工具

- `simple_test()` - 执行简单功能测试
- `test_deepseek_connection()` - 测试DeepSeek连接
- `test_searxng_services()` - 测试SearXNG服务
- `run_integration_test()` - 运行集成测试
- `generate_test_report()` - 生成测试报告
- `benchmark_performance()` - 基准性能测试
