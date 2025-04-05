# 新闻可信度分析工具

这是一个强大的新闻可信度分析工具，能够通过多种方法评估新闻内容的可信度，帮助用户识别可能的虚假信息、偏见内容或低质量报道。

## 功能特点

该工具提供以下核心功能：

1. **AI生成内容检测**：识别文本是否由AI生成，包括使用DeepSeek API进行高级检测
2. **图像真实性分析**：检测图像是否经过篡改或生成
3. **语言中立性分析**：评估文本的情感倾向、偏见和极端表述
4. **来源质量分析**：评估新闻来源的可靠性和权威性
5. **引用有效性评估**：验证文本中的引用和数据
6. **引用质量评估**：分析文本中引用的数量、多样性和权威性
7. **文本逻辑分析**：检查文本的逻辑一致性和论证质量
8. **网络交叉验证**：通过搜索引擎验证新闻内容的真实性
9. **本地新闻验证**：使用本地规则和模式识别验证新闻内容
10. **网页新闻分析**：直接分析网页内容，提取标题、作者、发布日期等元数据
11. **域名信任评估**：评估新闻来源网站的可信度，包括检查是否为权威媒体、政府或教育机构

## 安装要求

1. Python 3.8+
2. 创建并激活虚拟环境（推荐）：

   ```bash
   # 创建虚拟环境
   python -m venv myenv
   
   # 在Windows上激活虚拟环境
   myenv\Scripts\activate
   
   # 在macOS/Linux上激活虚拟环境
   source myenv/bin/activate
   ```

3. 安装所需依赖：
   ```bash
   pip install -r requirements.txt
   ```

4. 配置环境变量：
   - 创建`.env`文件，添加以下内容：
   ```
   DEEPSEEK_API_KEY=你的DeepSeek API密钥
   ```

## 使用方法

### 基本用法

```bash
# 分析文本文件
python news_credibility.py --file path/to/news.txt

# 分析URL
python news_credibility.py --url https://example.com/news-article

# 分析URL并自动下载图片进行分析
python news_credibility.py --url https://example.com/news-article --download-images

# 直接分析文本
python news_credibility.py --text "这是一段需要分析的新闻文本..."

# 保存分析结果到文件
python news_credibility.py --file path/to/news.txt --output results.txt

# 启用调试模式
python news_credibility.py --file path/to/news.txt --debug

# 分析包含图像的新闻
python news_credibility.py --file path/to/news.txt --images image1.jpg image2.png

# 禁用在线验证（仅使用本地分析）
python news_credibility.py --file path/to/news.txt --no-online

# 指定临时图片存储目录
python news_credibility.py --url https://example.com/news-article --download-images --temp-dir ./temp
```

### 测试连接

```bash
# 测试DeepSeek API连接
python news_credibility.py --test-deepseek

# 测试SearXNG搜索引擎连接
python news_credibility.py --test-searxng
```

### 退出虚拟环境

当你完成工作后，可以使用以下命令退出虚拟环境：

```bash
# 在Windows/macOS/Linux上退出虚拟环境
deactivate
```

## 网页新闻分析

当使用`--url`参数时，工具会自动提取网页内容并分析以下元数据：

- 标题
- 作者
- 发布日期
- 来源
- 图片（可选择下载并分析）

使用`--download-images`参数可以自动下载网页中的图片并进行分析，这对于检测新闻中的图像是否经过篡改或AI生成非常有用。

## 域名信任评估

工具内置了一个可信域名列表，包括：

- 政府和教育机构域名（.gov, .edu, .ac.）
- 国际主流媒体（BBC, CNN, Reuters等）
- 中文主流媒体（新华网, 人民网, 中国日报等）
- 其他国家/地区的主流媒体

当分析网页新闻时，工具会自动评估域名的可信度，并将结果纳入总体评分。

## 分析报告

分析完成后，工具将生成一份详细的报告，包括：

- 总得分和可信度评级
- 各项评估指标的详细得分和分析
- 具体的问题点和建议
- 网页元数据（如果分析的是URL）
- 域名信任评估（如果分析的是URL）

## 评分标准

可信度评级基于总分：
- 80-100分：高可信度
- 60-79分：中等可信度
- 40-59分：低可信度
- 0-39分：极低可信度

## 注意事项

1. 在线验证功能需要互联网连接
2. DeepSeek API功能需要有效的API密钥
3. 图像分析需要提供有效的图像文件路径
4. 分析结果仅供参考，建议结合其他信息来源进行判断
5. 网页分析功能可能对某些网站的内容提取不完整，这取决于网站的结构

## 故障排除

如果遇到依赖库安装问题，可以尝试：

```bash
# 更新pip
pip install --upgrade pip

# 单独安装可能出问题的依赖
pip install scipy
pip install python-whois
```

如果遇到SSL证书问题，可以尝试：

```bash
# 更新证书
pip install --upgrade certifi
```

## 许可证

MIT License

## 贡献

欢迎提交问题报告和改进建议！test
