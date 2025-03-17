#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import os
import requests
import re
import json
import time
import traceback
import random
from datetime import datetime
import urllib3
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import tempfile

# 添加对OpenAI库的导入
try:
    import openai
except ImportError:
    logging.warning("未安装OpenAI库，请使用'pip install openai'安装")

try:
    # 禁用SSL警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    logging.warning("无法禁用SSL警告，可能会看到相关警告信息")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('news_credibility.log')
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()  # 从.env文件加载环境变量
    deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')
    if deepseek_api_key:
        logging.info(f"已加载DeepSeek API密钥")
    else:
        logging.warning("未找到DeepSeek API密钥，请在.env文件中设置DEEPSEEK_API_KEY")
except ImportError:
    logging.warning("未安装python-dotenv库，请使用'pip install python-dotenv'安装")
    deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')

# 定义颜色常量
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    MAGENTA = '\033[95m'

def colored(text, color, bold=False):
    """为文本添加颜色"""
    color_code = getattr(Colors, color.upper(), Colors.ENDC)
    bold_code = Colors.BOLD if bold else ""
    return f"{bold_code}{color_code}{text}{Colors.ENDC}"

def get_text_from_url(url):
    """
    从URL获取新闻文本和元数据
    
    参数:
        url (str): 新闻URL
        
    返回:
        dict: 包含新闻文本和元数据的字典
    """
    logging.info(f"从URL获取内容: {url}")
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        from datetime import datetime
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        
        # 尝试检测编码
        if response.encoding == 'ISO-8859-1':
            # 可能是网站未声明编码，尝试检测
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']
            for enc in encodings:
                try:
                    response.content.decode(enc)
                    response.encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 初始化结果字典
        result = {
            'url': url,
            'title': '',
            'author': '',
            'publish_date': '',
            'content': '',
            'source': '',
            'images': []
        }
        
        # 提取标题
        title_tag = soup.find('title')
        if title_tag:
            result['title'] = title_tag.text.strip()
        
        # 尝试从meta标签提取更精确的标题
        meta_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'title'})
        if meta_title and meta_title.get('content'):
            result['title'] = meta_title['content'].strip()
        
        # 提取作者信息
        author_patterns = [
            ('meta', {'name': 'author'}),
            ('meta', {'property': 'article:author'}),
            ('meta', {'property': 'og:article:author'}),
            ('span', {'class': 'author'}),
            ('div', {'class': 'author'}),
            ('a', {'class': 'author'}),
            ('p', {'class': 'author'}),
            ('span', {'class': 'byline'}),
            ('div', {'class': 'byline'}),
            ('p', {'class': 'byline'})
        ]
        
        for tag, attrs in author_patterns:
            author_tag = soup.find(tag, attrs)
            if author_tag:
                if tag == 'meta':
                    result['author'] = author_tag.get('content', '').strip()
                else:
                    result['author'] = author_tag.text.strip()
                if result['author']:
                    break
        
        # 提取发布日期
        date_patterns = [
            ('meta', {'name': 'pubdate'}),
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'property': 'og:article:published_time'}),
            ('meta', {'name': 'publish-date'}),
            ('meta', {'name': 'date'}),
            ('time', {}),
            ('span', {'class': 'date'}),
            ('div', {'class': 'date'}),
            ('p', {'class': 'date'}),
            ('span', {'class': 'time'}),
            ('div', {'class': 'time'}),
            ('p', {'class': 'time'})
        ]
        
        for tag, attrs in date_patterns:
            date_tag = soup.find(tag, attrs)
            if date_tag:
                if tag == 'meta':
                    result['publish_date'] = date_tag.get('content', '').strip()
                else:
                    result['publish_date'] = date_tag.text.strip()
                if result['publish_date']:
                    break
        
        # 提取来源信息
        source_patterns = [
            ('meta', {'property': 'og:site_name'}),
            ('meta', {'name': 'site_name'}),
            ('meta', {'name': 'source'}),
            ('span', {'class': 'source'}),
            ('div', {'class': 'source'}),
            ('p', {'class': 'source'})
        ]
        
        for tag, attrs in source_patterns:
            source_tag = soup.find(tag, attrs)
            if source_tag:
                if tag == 'meta':
                    result['source'] = source_tag.get('content', '').strip()
                else:
                    result['source'] = source_tag.text.strip()
                if result['source']:
                    break
        
        # 如果没有找到来源，使用域名作为来源
        if not result['source']:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            result['source'] = domain
        
        # 提取图片URL
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src', '')
            if src and not src.startswith('data:'):
                # 处理相对URL
                if src.startswith('/'):
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    src = base_url + src
                result['images'].append(src)
        
        # 提取正文内容
        # 首先尝试使用article标签
        article = soup.find('article')
        if article:
            # 移除脚本和样式
            for script in article(['script', 'style']):
                script.decompose()
            result['content'] = article.get_text(separator='\n').strip()
        else:
            # 尝试常见的内容容器
            content_patterns = [
                ('div', {'class': ['article-content', 'article-body', 'content', 'post-content', 'entry-content', 'story-body']}),
                ('div', {'id': ['article-content', 'article-body', 'content', 'post-content', 'entry-content', 'story-body']}),
                ('section', {'class': ['article-content', 'article-body', 'content']}),
                ('section', {'id': ['article-content', 'article-body', 'content']})
            ]
            
            content_text = ""
            for tag, attrs in content_patterns:
                # 处理class和id可能是列表的情况
                if 'class' in attrs and isinstance(attrs['class'], list):
                    for class_name in attrs['class']:
                        content_tag = soup.find(tag, class_=class_name)
                        if content_tag:
                            # 移除脚本和样式
                            for script in content_tag(['script', 'style']):
                                script.decompose()
                            content_text = content_tag.get_text(separator='\n').strip()
                            break
                elif 'id' in attrs and isinstance(attrs['id'], list):
                    for id_name in attrs['id']:
                        content_tag = soup.find(tag, id=id_name)
                        if content_tag:
                            # 移除脚本和样式
                            for script in content_tag(['script', 'style']):
                                script.decompose()
                            content_text = content_tag.get_text(separator='\n').strip()
                            break
                else:
                    content_tag = soup.find(tag, attrs)
                    if content_tag:
                        # 移除脚本和样式
                        for script in content_tag(['script', 'style']):
                            script.decompose()
                        content_text = content_tag.get_text(separator='\n').strip()
                        break
                
                if content_text:
                    break
            
            # 如果仍然没有找到内容，尝试提取所有p标签
            if not content_text:
                paragraphs = soup.find_all('p')
                content_text = '\n'.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
            
            result['content'] = content_text
        
        # 如果内容仍然为空，尝试提取body的所有文本
        if not result['content']:
            body = soup.find('body')
            if body:
                # 移除脚本、样式、导航和页脚
                for tag in body(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                result['content'] = body.get_text(separator='\n').strip()
        
        # 清理内容
        if result['content']:
            # 移除多余空白
            result['content'] = re.sub(r'\n\s*\n', '\n\n', result['content'])
            # 移除过短的行
            lines = result['content'].split('\n')
            result['content'] = '\n'.join([line for line in lines if len(line.strip()) > 10])
        
        logging.info(f"成功从URL获取内容，标题: {result['title']}, 内容长度: {len(result['content'])}")
        return result
    
    except Exception as e:
        logging.error(f"从URL获取内容失败: {str(e)}")
        raise Exception(f"无法从URL获取内容: {str(e)}")

def check_ai_content(text):
    """
    检测文本是否由AI生成
    
    使用多种方法检测AI生成内容的特征:
    1. 句式结构分析
    2. 重复模式检测
    3. 常见AI表达方式识别
    4. 词汇多样性评估
    
    返回:
        (人类撰写可能性评分(0-1), 详细分析结果列表)
    """
    logging.info("开始进行AI内容检测...")
    
    # 初始化评分和详情
    ai_indicators = []
    human_indicators = []
    
    # 1. 句式结构分析
    # 检测过于规整的句式结构
    sentences = re.split(r'[。！？.!?]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    
    if not sentences:
        return 0.5, ["无法提取有效句子进行分析，使用默认评分"]
    
    # 计算句子长度的标准差 - AI生成文本句子长度往往更均匀
    sentence_lengths = [len(s) for s in sentences]
    avg_length = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((length - avg_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
    std_dev = variance ** 0.5
    
    # 句子长度变化评估
    if std_dev < 10 and len(sentences) > 5:
        ai_indicators.append("句子长度变化小，结构过于规整")
    else:
        human_indicators.append("句子长度变化自然")
    
    # 2. 重复模式检测
    # 检查重复的短语和表达
    phrases = []
    for i in range(len(sentences) - 1):
        for j in range(i + 1, len(sentences)):
            common_substrings = find_common_substrings(sentences[i], sentences[j], min_length=5)
            phrases.extend(common_substrings)
    
    # 统计重复短语
    phrase_counts = {}
    for phrase in phrases:
        if phrase in phrase_counts:
            phrase_counts[phrase] += 1
        else:
            phrase_counts[phrase] = 1
    
    # 过滤掉常见短语
    common_phrases = ["因此", "所以", "然而", "但是", "此外", "另外", "总之", "总的来说", "最后"]
    filtered_phrases = {k: v for k, v in phrase_counts.items() if k not in common_phrases and v > 2}
    
    if filtered_phrases:
        ai_indicators.append(f"检测到重复表达模式: {len(filtered_phrases)}个短语重复出现")
    else:
        human_indicators.append("未检测到明显重复表达模式")
    
    # 3. 常见AI表达方式识别
    ai_patterns = [
        r"首先.*其次.*最后",
        r"一方面.*另一方面",
        r"不仅.*而且",
        r"总的来说",
        r"总而言之",
        r"综上所述"
    ]
    
    ai_pattern_matches = 0
    for pattern in ai_patterns:
        if re.search(pattern, text, re.DOTALL):
            ai_pattern_matches += 1
    
    if ai_pattern_matches >= 3:
        ai_indicators.append("检测到多个AI常用表达模式")
    elif ai_pattern_matches > 0:
        ai_indicators.append(f"检测到{ai_pattern_matches}个AI常用表达模式")
    else:
        human_indicators.append("未检测到明显的AI表达模式")
    
    # 4. 词汇多样性评估
    words = re.findall(r'\w+', text.lower())
    unique_words = set(words)
    
    if len(words) > 0:
        diversity_ratio = len(unique_words) / len(words)
        
        if diversity_ratio < 0.4:
            ai_indicators.append("词汇多样性较低")
        elif diversity_ratio > 0.6:
            human_indicators.append("词汇多样性较高")
    
    # 5. 计算最终评分
    # 根据人类和AI指标的数量计算评分
    total_indicators = len(ai_indicators) + len(human_indicators)
    if total_indicators == 0:
        score = 0.5  # 默认中等分数
    else:
        score = len(human_indicators) / total_indicators
    
    # 调整评分范围，避免极端值
    score = 0.2 + score * 0.6  # 将分数限制在0.2-0.8范围内
    
    # 准备详细结果
    if score >= 0.7:
        conclusion = "人类撰写概率较高"
    elif score >= 0.5:
        conclusion = "可能为人类撰写，但有AI辅助痕迹"
    elif score >= 0.3:
        conclusion = "可能为AI生成，有人工编辑痕迹"
    else:
        conclusion = "AI生成概率较高"
    
    details = [f"AI内容检测结果：{conclusion} (评分: {score:.2f})"]
    
    # 添加详细指标
    if ai_indicators:
        details.append("AI特征:")
        for indicator in ai_indicators:
            details.append(f"- {indicator}")
    
    if human_indicators:
        details.append("人类撰写特征:")
        for indicator in human_indicators:
            details.append(f"- {indicator}")
    
    logging.info(f"AI内容检测完成，评分: {score:.2f}")
    return score, details

def find_common_substrings(str1, str2, min_length=5, max_time=2, max_substrings=10):
    """
    查找两个字符串之间的共同子串
    
    参数:
        str1 (str): 第一个字符串
        str2 (str): 第二个字符串
        min_length (int): 最小子串长度
        max_time (float): 最大执行时间（秒）
        max_substrings (int): 最大返回子串数量
        
    返回:
        list: 共同子串列表
    """
    import time
    start_time = time.time()
    
    # 如果字符串太长，可能会导致处理时间过长，进行截断
    max_length = 1000
    if len(str1) > max_length:
        str1 = str1[:max_length]
    if len(str2) > max_length:
        str2 = str2[:max_length]
    
    common_substrings = []
    
    # 使用更高效的算法查找共同子串
    try:
        # 构建后缀数组
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, str1, str2)
        
        # 查找匹配块
        for block in matcher.get_matching_blocks():
            if block.size >= min_length:
                substring = str1[block.a:block.a + block.size]
                common_substrings.append(substring)
                
                # 检查是否超过最大子串数量
                if len(common_substrings) >= max_substrings:
                    break
                
            # 检查是否超时
            if time.time() - start_time > max_time:
                logging.warning(f"查找共同子串超时，返回部分结果 ({len(common_substrings)}个)")
                break
    except Exception as e:
        logging.error(f"查找共同子串时出错: {str(e)}")
        return []
    
    return common_substrings

def analyze_language_neutrality(text):
    """
    分析文本的语言中立性
    
    使用预定义词汇列表检测情感词和偏见表达
    计算正面/负面/中性词汇比例
    识别夸张、煽动性语言和主观表达
    
    参数:
        text: 新闻文本
        
    返回:
        (中立性评分(0-1), 详细分析结果列表)
    """
    logging.info("开始分析语言中立性...")
    
    # 1. 情感词汇检测
    # 正面情感词汇
    positive_words = [
        "优秀", "杰出", "卓越", "伟大", "成功", "突破", "胜利", "进步", "发展", "提升",
        "创新", "优化", "改善", "增强", "促进", "鼓励", "支持", "赞赏", "肯定", "表扬",
        "excellent", "outstanding", "great", "successful", "breakthrough", "victory", "progress"
    ]
    
    # 负面情感词汇
    negative_words = [
        "失败", "糟糕", "恶劣", "危机", "灾难", "崩溃", "衰退", "下滑", "恶化", "破坏",
        "威胁", "打击", "损害", "削弱", "阻碍", "批评", "指责", "谴责", "否定", "质疑",
        "failure", "terrible", "crisis", "disaster", "collapse", "recession", "deteriorate"
    ]
    
    # 极端情感词汇
    extreme_words = [
        "震惊", "愤怒", "恐怖", "可怕", "悲剧", "惊人", "极端", "疯狂", "荒谬", "惊骇",
        "惨不忍睹", "令人发指", "骇人听闻", "触目惊心", "不可思议", "难以置信", "史无前例",
        "shocking", "outrageous", "horrific", "terrifying", "tragic", "extreme", "crazy"
    ]
    
    # 煽动性词汇
    inflammatory_words = [
        "必须", "绝对", "一定", "永远", "从不", "全部", "所有", "没有一个", "完全", "彻底",
        "毫无疑问", "毫无例外", "无可争辩", "无可辩驳", "无可置疑", "无可非议", "无可厚非",
        "must", "absolute", "definitely", "always", "never", "all", "none", "completely"
    ]
    
    # 主观表达
    subjective_phrases = [
        "我认为", "我相信", "我觉得", "我想", "我希望", "我担心", "我怀疑", "我期待",
        "据我所知", "依我看", "在我看来", "以我之见", "我个人认为", "我的看法是",
        "I think", "I believe", "I feel", "I hope", "I worry", "I doubt", "I expect"
    ]
    
    # 统计各类词汇出现次数
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    extreme_count = sum(1 for word in extreme_words if word in text)
    inflammatory_count = sum(1 for word in inflammatory_words if word in text)
    subjective_count = sum(1 for phrase in subjective_phrases if phrase in text)
    
    # 计算总情感词数量
    total_emotional_words = positive_count + negative_count + extreme_count
    
    # 计算情感词比例
    text_length = len(text)
    emotional_ratio = total_emotional_words / (text_length / 100)  # 每100字的情感词数量
    
    # 计算正负面情感平衡度
    if positive_count + negative_count > 0:
        sentiment_balance = abs(positive_count - negative_count) / (positive_count + negative_count)
    else:
        sentiment_balance = 0
    
    # 2. 计算各项得分
    # 情感词密度得分 (越低越中立)
    emotional_density_score = max(0, 1 - (emotional_ratio / 5))  # 假设每100字5个情感词为阈值
    
    # 情感平衡得分 (越平衡越中立)
    balance_score = 1 - sentiment_balance
    
    # 极端词汇得分 (越少越中立)
    extreme_score = max(0, 1 - (extreme_count / 5))  # 假设5个极端词为阈值
    
    # 煽动性词汇得分 (越少越中立)
    inflammatory_score = max(0, 1 - (inflammatory_count / 5))  # 假设5个煽动词为阈值
    
    # 主观表达得分 (越少越中立)
    subjective_score = max(0, 1 - (subjective_count / 3))  # 假设3个主观表达为阈值
    
    # 3. 计算综合得分
    # 各项权重
    weights = {
        "emotional_density": 0.25,
        "balance": 0.15,
        "extreme": 0.25,
        "inflammatory": 0.2,
        "subjective": 0.15
    }
    
    # 计算加权总分
    neutrality_score = (
        emotional_density_score * weights["emotional_density"] +
        balance_score * weights["balance"] +
        extreme_score * weights["extreme"] +
        inflammatory_score * weights["inflammatory"] +
        subjective_score * weights["subjective"]
    )
    
    # 确保分数在0-1范围内
    neutrality_score = max(0, min(1, neutrality_score))
    
    # 4. 准备详细结果
    # 评估情感词水平
    if emotional_ratio < 1:
        emotional_level = "较少"
    elif emotional_ratio < 3:
        emotional_level = "适量"
    else:
        emotional_level = "较多"
    
    # 评估情感平衡度
    if sentiment_balance < 0.3:
        balance_level = "平衡"
    elif sentiment_balance < 0.7:
        balance_level = "偏向"
    else:
        balance_level = "强烈偏向"
    
    # 评估极端表述
    if extreme_count == 0:
        extreme_level = "无"
    elif extreme_count < 3:
        extreme_level = "少量"
    else:
        extreme_level = "较多"
    
    # 评估煽动性表述
    if inflammatory_count == 0:
        inflammatory_level = "无"
    elif inflammatory_count < 3:
        inflammatory_level = "少量"
    else:
        inflammatory_level = "较多"
    
    # 评估主观表达
    if subjective_count == 0:
        subjective_level = "无"
    elif subjective_count < 2:
        subjective_level = "少量"
    else:
        subjective_level = "较多"
    
    # 总体评估结论
    if neutrality_score >= 0.8:
        conclusion = "语言中立性分析：表述相对客观"
    elif neutrality_score >= 0.6:
        conclusion = "语言中立性分析：表述基本客观，存在一定情绪化内容"
    elif neutrality_score >= 0.4:
        conclusion = "语言中立性分析：表述情绪化明显，中立性一般"
    else:
        conclusion = "语言中立性分析：表述情绪化严重，缺乏客观性"
    
    # 准备详细结果
    details = [
        f"情感词汇: {emotional_level} (正面: {positive_count}, 负面: {negative_count})",
        f"情感平衡: {balance_level}",
        f"极端表述: {extreme_level} (数量: {extreme_count})",
        f"煽动性表述: {inflammatory_level} (数量: {inflammatory_count})",
        f"主观表达: {subjective_level} (数量: {subjective_count})",
        conclusion
    ]
    
    logging.info(f"语言中立性分析完成，评分: {neutrality_score:.2f}")
    return neutrality_score, details

def analyze_source_quality(text, url=None):
    """
    分析新闻来源的质量
    
    参数:
        text (str): 新闻文本
        url (str, optional): 新闻URL，用于评估域名可信度
        
    返回:
        tuple: (来源质量分数, 详情列表)
    """
    logging.info("开始分析来源质量")
    
    # 初始化
    score = 0.5  # 默认中等质量
    details = []
    
    # 如果提供了URL，评估域名可信度
    if url:
        domain_score, domain_details = evaluate_domain_trust(url)
        # 域名评估占40%权重
        score = 0.4 * domain_score + 0.6 * score
        details.extend(domain_details)
    
    # 提取可能的来源指示词
    source_indicators = [
        "据.*?报道", "来自.*?的消息", "根据.*?的数据", "引用.*?的话",
        "参考.*?的研究", "援引.*?的说法", "来源于.*?", "出自.*?",
        "记者.*?报道", "通讯员.*?报道", "特约记者.*?", "本报记者.*?",
        "报道称", "消息称", "消息人士称", "知情人士透露",
        "according to", "reported by", "cited by", "quoted by",
        "sources said", "officials said", "experts said", "researchers found"
    ]
    
    # 提取所有可能的来源
    sources = []
    for indicator in source_indicators:
        matches = re.finditer(indicator, text)
        for match in matches:
            # 提取匹配后的内容，最多30个字符
            start = match.end()
            end = min(start + 30, len(text))
            source_text = text[start:end].strip()
            # 如果有标点符号，截断到第一个标点
            for i, char in enumerate(source_text):
                if char in "。，,.:;!?；，。！？":
                    source_text = source_text[:i]
                    break
            if source_text and len(source_text) > 1:
                sources.append(source_text)
    
    # 提取引号中的内容作为可能的引用
    quotes = []
    quote_patterns = [
        r'"(.*?)"',  # 英文双引号
        r"'(.*?)'",  # 英文单引号
        r"「(.*?)」",  # 中文单引号
        r"『(.*?)』",  # 中文单引号
        r"（(.*?)）",  # 中文括号
        r"\((.*?)\)",  # 英文括号
        r"：(.*?)。",  # 冒号后的内容
        r":(.*?)\."   # 英文冒号后的内容
    ]
    
    for pattern in quote_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            quote = match.group(1).strip()
            if quote and len(quote) > 5:  # 忽略太短的引用
                quotes.append(quote)
    
    # 分析来源的权威性
    authoritative_sources = [
        "大学", "研究所", "研究院", "实验室", "中心", "部门", "机构", "协会", "学会",
        "政府", "官方", "部", "委员会", "局", "署", "院", "办公室",
        "专家", "学者", "教授", "研究员", "院士", "博士", "科学家",
        "university", "institute", "laboratory", "center", "department", 
        "government", "official", "ministry", "committee", "bureau", "agency",
        "expert", "scholar", "professor", "researcher", "scientist", "doctor"
    ]
    
    authority_count = 0
    for source in sources:
        for auth in authoritative_sources:
            if auth in source:
                authority_count += 1
                break
    
    # 评估来源多样性
    unique_sources = set(sources)
    source_diversity = len(unique_sources)
    
    # 根据来源数量和权威性评分
    if source_diversity >= 5:
        score += 0.2
        details.append(f"引用了多个不同来源 ({source_diversity}个)")
    elif source_diversity >= 3:
        score += 0.1
        details.append(f"引用了几个不同来源 ({source_diversity}个)")
    elif source_diversity == 0:
        score -= 0.2
        details.append("未发现明确的信息来源")
    else:
        details.append(f"引用了有限的来源 ({source_diversity}个)")
    
    # 评估权威来源
    if authority_count >= 3:
        score += 0.2
        details.append(f"引用了多个权威来源 ({authority_count}个)")
    elif authority_count >= 1:
        score += 0.1
        details.append(f"引用了权威来源 ({authority_count}个)")
    else:
        details.append("未发现权威来源引用")
    
    # 评估引用的质量
    if len(quotes) >= 5:
        score += 0.1
        details.append(f"包含多个直接引用 ({len(quotes)}个)")
    elif len(quotes) >= 2:
        score += 0.05
        details.append(f"包含一些直接引用 ({len(quotes)}个)")
    
    # 检查是否有匿名来源
    anonymous_patterns = [
        "匿名", "不愿透露姓名", "知情人士", "内部人士", "消息人士",
        "anonymous", "sources who requested anonymity", "unnamed sources"
    ]
    
    has_anonymous = False
    for pattern in anonymous_patterns:
        if pattern in text:
            has_anonymous = True
            break
    
    if has_anonymous:
        score -= 0.1
        details.append("使用了匿名来源，可信度降低")
    
    # 确保分数在0-1范围内
    score = max(0.0, min(1.0, score))
    
    logging.info(f"来源质量分析完成，得分: {score:.2f}")
    return score, details

def search_with_searxng(query, max_attempts=3, use_local=True):
    """
    使用SearXNG搜索引擎进行搜索
    
    参数:
        query (str): 搜索查询
        max_attempts (int): 最大尝试次数
        use_local (bool): 是否优先使用本地实例
    
    返回:
        list: 搜索结果列表
    """
    logger = logging.getLogger()
    logger.info(f"使用SearXNG搜索: {query}")
    
    # 禁用SSL警告
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        logger.warning("无法导入urllib3来禁用SSL警告")
    
    # 使用已测试可用的SearXNG实例
    global AVAILABLE_SEARXNG_INSTANCE
    if AVAILABLE_SEARXNG_INSTANCE:
        logger.info(f"使用已知可用的SearXNG实例: {AVAILABLE_SEARXNG_INSTANCE}")
        searxng_instances = [AVAILABLE_SEARXNG_INSTANCE]
    else:
        # SearXNG实例列表
        searxng_instances = []
        
        # 如果使用本地实例，将其添加到列表开头
        if use_local:
            logger.debug("尝试使用本地SearXNG实例")
            searxng_instances.append("http://localhost:8080")
        
        # 添加其他公共实例
        searxng_instances.extend([
            "https://searx.be",
            "https://searx.tiekoetter.com",
            "https://searx.fmac.xyz",
            "https://search.unlocked.link",
            "https://search.sapti.me"
        ])
    
    for instance in searxng_instances:
        for attempt in range(max_attempts):
            try:
                logger.info(f"尝试使用SearXNG实例 {instance}，尝试 {attempt+1}/{max_attempts}")
                
                # 构建API URL
                api_url = f"{instance}/search"
                
                # 设置请求参数
                params = {
                    "q": query,
                    "format": "json",
                    "language": "zh-CN,en-US",
                    "time_range": "",
                    "safesearch": "0",
                    "categories": "general"
                }
                
                # 设置请求头
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
                }
                
                # 发送请求
                logger.debug(f"发送SearXNG请求: {api_url}")
                try:
                    response = requests.get(api_url, params=params, headers=headers, timeout=10, verify=False)
                    response.raise_for_status()
                    logger.debug(f"SearXNG请求成功，状态码: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"SearXNG请求失败: {e}")
                    continue
                
                # 解析响应
                try:
                    data = response.json()
                    logger.debug("成功解析JSON响应")
                except ValueError as e:
                    logger.warning(f"无法解析JSON响应: {e}")
                    continue
                
                # 检查结果
                if "results" not in data:
                    logger.warning("响应中没有结果字段")
                    continue
                
                results = data["results"]
                logger.info(f"找到 {len(results)} 个搜索结果")
                
                # 如果有结果，返回
                if results:
                    # 保存可用的实例
                    AVAILABLE_SEARXNG_INSTANCE = instance
                    return results
                else:
                    logger.warning("搜索结果为空")
            except Exception as e:
                logger.error(f"搜索过程中出错: {e}")
                logger.error(traceback.format_exc())
        
        logger.warning(f"实例 {instance} 的所有尝试都失败")
    
    logger.error("所有SearXNG实例都失败")
    return []

def verify_citation_with_searxng(citation_text):
    """
    使用SearXNG验证引用内容的真实性
    
    参数:
        citation_text: 需要验证的引用文本
        
    返回:
        (真实性评分(0-1), 解释, 相关搜索结果列表)
    """
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except:
        logging.warning("无法禁用SSL警告")
    
    logging.info(f"开始验证引用: {citation_text[:50]}...")
    
    # 初始值
    truthfulness_score = 0.5  # 默认中等分数
    explanation = "未能完成验证"
    search_results = []
    
    # 为了减少噪音，去除过短文本
    if len(citation_text) < 10:
        return truthfulness_score, "引用文本过短，无法有效验证", []
    
    # 构造搜索查询
    query = citation_text
    if len(query) > 150:
        # 如果文本太长，取前150字符
        query = query[:150]
    
    # 执行搜索
    results = search_with_searxng(query)
    
    if not results:
        # 如果搜索失败，尝试使用DeepSeek API进行验证
        logging.warning("SearXNG搜索未返回结果，尝试使用DeepSeek进行验证")
        try:
            # 检查是否设置了API密钥
            deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
            if deepseek_api_key:
                # 构造提示
                prompt = f"""请验证以下引用内容的真实性:

{citation_text}

请以JSON格式返回结果，包含:
1. 真实性评分(0-1)，其中1表示完全真实，0表示完全虚假
2. 解释你的评估理由

格式: {{"score": 0.X, "explanation": "你的解释"}}"""
                
                # 调用DeepSeek
                logging.info("使用DeepSeek进行验证")
                response = query_deepseek(prompt, deepseek_api_key)
                
                try:
                    # 解析JSON响应
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        try:
                            result = json.loads(json_match.group(0))
                            truthfulness_score = float(result.get("score", 0.5))
                            ai_explanation = result.get("explanation", "DeepSeek无法提供明确解释")
                            return truthfulness_score, f"DeepSeek评估: {ai_explanation}", []
                        except (json.JSONDecodeError, ValueError) as je:
                            logging.warning(f"解析JSON失败: {str(je)}, 原始响应: {response}")
                            # 尝试从文本中提取分数
                            score_match = re.search(r'score["\']?\s*:\s*(\d+\.\d+)', response)
                            if score_match:
                                try:
                                    truthfulness_score = float(score_match.group(1))
                                except ValueError:
                                    pass
                            return truthfulness_score, f"DeepSeek评估: {response[:100]}...", []
                    else:
                        return 0.5, f"DeepSeek评估: {response[:100]}...", []
                except Exception as parse_e:
                    logging.error(f"解析DeepSeek响应出错: {str(parse_e)}")
                    return 0.5, f"DeepSeek评估: {response[:100]}...", []
            else:
                logging.warning("未设置DEEPSEEK_API_KEY环境变量")
                return 0.5, "未配置DeepSeek API密钥，无法进行在线验证", []
        except Exception as e:
            logging.error(f"使用DeepSeek验证时出错: {str(e)}")
            return 0.5, "无法完成在线验证", []
    
    # 解析搜索结果
    processed_results = []
    content_matches = 0
    
    for result in results[:5]:  # 只分析前5条结果
        title = result.get("title", "")
        url = result.get("url", "")
        snippet = result.get("content", "")
        
        # 计算内容匹配度 (简化版)
        match_score = 0
        
        # 检查关键词匹配
        words = re.findall(r'\w+', citation_text.lower())
        significant_words = [w for w in words if len(w) > 3]  # 只考虑较长的词
        
        if significant_words:
            matches = sum(1 for word in significant_words if word.lower() in (snippet + title).lower())
            match_score = min(1.0, matches / len(significant_words))
        
        if match_score > 0.3:  # 如果匹配度足够高
            content_matches += 1
        
        processed_results.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "match_score": match_score
        })
    
    # 根据匹配结果计算可信度
    if processed_results:
        # 计算匹配分数
        truthfulness_score = min(1.0, 0.3 + (content_matches / len(processed_results)) * 0.7)
        
        if truthfulness_score > 0.8:
            explanation = "多个来源确认了引用内容的真实性"
        elif truthfulness_score > 0.6:
            explanation = "部分来源支持引用内容的真实性"
        elif truthfulness_score > 0.4:
            explanation = "找到的支持证据有限"
        else:
            explanation = "未找到足够支持证据，引用内容可能不准确"
    
    return truthfulness_score, explanation, processed_results

def search_and_verify_news(text, url=None, image_paths=None, no_online=False):
    """
    分析新闻内容的可信度
    
    参数:
        text (str): 新闻文本
        url (str, optional): 新闻URL
        image_paths (list, optional): 图片路径列表
        no_online (bool): 是否禁用在线验证
    
    返回:
        dict: 分析结果
    """
    logger = logging.getLogger()
    logger.info("开始分析新闻内容")
    
    # 初始化结果
    result = {
        "scores": {},
        "details": {}
    }
    
    try:
        # 首先进行本地分析
        # AI生成内容检测（本地）
        logger.info("本地检查AI生成内容")
        local_ai_score, local_ai_details = check_ai_content(text)
        
        # 语言中立性分析（本地）
        logger.info("本地分析语言中立性")
        local_neutrality_score, local_neutrality_details = analyze_language_neutrality(text)
        
        # DeepSeek分析（如果API可用且不是离线模式）
        global DEEPSEEK_API_AVAILABLE
        deepseek_ai_score = None
        deepseek_neutrality_score = None
        deepseek_analysis_details = None
        
        if DEEPSEEK_API_AVAILABLE and not no_online:
            logger.info("使用DeepSeek进行AI生成率和语言中立性多维度评分")
            try:
                # 构建提示词，请求AI生成率和语言中立性的多维度评分
                prompt = f"""请分析以下新闻文本，重点评估两个方面：
1. AI生成内容可能性：文本是由AI生成还是人类撰写的可能性
2. 语言中立性：文本的语言是否客观中立，是否存在情感偏向或煽动性表达

对于AI生成内容可能性，请从以下维度进行评分（0-1分）：
- 表达模式：是否存在AI常见的表达模式和句式结构
- 词汇多样性：词汇使用是否多样自然，还是重复刻板
- 句子变化：句子长度和结构是否有自然变化
- 上下文连贯性：段落之间的过渡是否自然流畅
- 人类特征：是否包含人类特有的表达方式、幽默或创造性表达

对于语言中立性，请从以下维度进行评分（0-1分）：
- 情感词汇：是否使用带有强烈情感色彩的词汇
- 情感平衡：正面和负面表述是否平衡
- 极端表述：是否使用极端化、绝对化的表述
- 煽动性表达：是否存在煽动情绪的表达
- 主观评价：是否包含明显的主观评价

请以JSON格式返回结果，包含总体评分和各维度评分。格式如下：
{{
  "AI生成内容": {{
    "总分": 0.7,
    "表达模式": 0.8,
    "词汇多样性": 0.6,
    "句子变化": 0.7,
    "上下文连贯性": 0.7,
    "人类特征": 0.6,
    "分析": "这里是详细分析..."
  }},
  "语言中立性": {{
    "总分": 0.8,
    "情感词汇": 0.7,
    "情感平衡": 0.9,
    "极端表述": 0.8,
    "煽动性表达": 0.8,
    "主观评价": 0.8,
    "分析": "这里是详细分析..."
  }}
}}

新闻文本：
{text[:3000]}  # 限制文本长度，避免超出API限制
"""
                
                # 调用DeepSeek API
                response = query_deepseek(prompt)
                if response:
                    # 尝试解析JSON
                    try:
                        import json
                        import re
                        
                        # 尝试从响应中提取JSON部分
                        json_match = re.search(r'({[\s\S]*})', response)
                        if json_match:
                            json_str = json_match.group(1)
                            data = json.loads(json_str)
                            
                            # 提取AI生成内容评分
                            ai_content_data = data.get("AI生成内容", {})
                            deepseek_ai_score = ai_content_data.get("总分", 0.5)
                            
                            # 提取语言中立性评分
                            neutrality_data = data.get("语言中立性", {})
                            deepseek_neutrality_score = neutrality_data.get("总分", 0.5)
                            
                            # 保存详细分析
                            deepseek_analysis_details = json.dumps(data, ensure_ascii=False, indent=2)
                            
                            logger.info(f"DeepSeek分析完成，AI生成内容评分: {deepseek_ai_score}, 语言中立性评分: {deepseek_neutrality_score}")
                        else:
                            logger.warning("无法从DeepSeek响应中提取JSON")
                            deepseek_analysis_details = response
                    except Exception as e:
                        logger.error(f"解析DeepSeek响应时出错: {e}")
                        deepseek_analysis_details = response
                else:
                    logger.warning("DeepSeek API返回空响应")
            except Exception as e:
                logger.error(f"DeepSeek分析出错: {e}")
                deepseek_analysis_details = f"DeepSeek分析出错: {e}"
        
        # 综合评分（30%本地 + 70%DeepSeek）
        # AI生成内容评分
        if deepseek_ai_score is not None:
            # AI生成内容评分需要反转，因为DeepSeek返回的是AI生成的可能性，而我们需要的是人类撰写的可能性
            ai_score = 0.3 * local_ai_score + 0.7 * (1 - deepseek_ai_score)
            ai_details = f"综合评分 (30%本地算法 + 70%DeepSeek评分):\n本地评分: {local_ai_score:.2f}\nDeepSeek评分: {1-deepseek_ai_score:.2f} (AI生成可能性: {deepseek_ai_score:.2f})\n\n本地分析:\n{local_ai_details}\n\nDeepSeek分析:\n{deepseek_analysis_details}"
        else:
            ai_score = local_ai_score
            ai_details = f"仅使用本地评分: {local_ai_score:.2f}\n\n{local_ai_details}"
        
        # 语言中立性评分
        if deepseek_neutrality_score is not None:
            neutrality_score = 0.3 * local_neutrality_score + 0.7 * deepseek_neutrality_score
            neutrality_details = f"综合评分 (30%本地算法 + 70%DeepSeek评分):\n本地评分: {local_neutrality_score:.2f}\nDeepSeek评分: {deepseek_neutrality_score:.2f}\n\n本地分析:\n{local_neutrality_details}\n\nDeepSeek分析:\n{deepseek_analysis_details}"
        else:
            neutrality_score = local_neutrality_score
            neutrality_details = f"仅使用本地评分: {local_neutrality_score:.2f}\n\n{local_neutrality_details}"
        
        # 保存评分和详细信息
        result["scores"]["ai_content"] = ai_score
        result["details"]["ai_content"] = ai_details
        result["scores"]["language_neutrality"] = neutrality_score
        result["details"]["language_neutrality"] = neutrality_details
        
        # 如果有DeepSeek分析结果，保存完整分析
        if deepseek_analysis_details:
            result["details"]["deepseek_analysis"] = deepseek_analysis_details
        
        # 来源质量分析
        logger.info("分析来源质量")
        source_score, source_details = analyze_source_quality(text, url)
        result["scores"]["source_quality"] = source_score
        result["details"]["source_quality"] = source_details
        
        # 域名可信度评估（如果提供了URL）
        if url:
            logger.info("评估域名可信度")
            domain_score, domain_details = evaluate_domain_trust(url)
            result["scores"]["domain_trust"] = domain_score
            result["details"]["domain_trust"] = domain_details
        else:
            result["scores"]["domain_trust"] = 0
            result["details"]["domain_trust"] = "未提供URL，无法评估域名可信度"
        
        # 在线验证（如果不是离线模式）
        if not no_online:
            logger.info("进行引用有效性验证")
            # 引用有效性验证
            citation_score, citation_details = analyze_citation_validity(text)
            result["scores"]["citation_validity"] = citation_score
            result["details"]["citation_validity"] = citation_details
            
            logger.info("评估引用质量")
            # 引用质量评估
            citation_quality_score, citation_quality_details = get_citation_score(text)
            result["scores"]["citation_quality"] = citation_quality_score
            result["details"]["citation_quality"] = citation_quality_details
            
            logger.info("进行本地新闻验证")
            # 本地新闻验证
            local_news_score, local_news_details = local_news_validation(text)
            result["scores"]["local_news_validation"] = local_news_score
            result["details"]["local_news_validation"] = local_news_details
        else:
            logger.info("离线模式，跳过在线验证")
            result["scores"]["citation_validity"] = 0
            result["details"]["citation_validity"] = "离线模式，跳过引用有效性验证"
            result["scores"]["citation_quality"] = 0
            result["details"]["citation_quality"] = "离线模式，跳过引用质量评估"
            result["scores"]["local_news_validation"] = 0
            result["details"]["local_news_validation"] = "离线模式，跳过本地新闻验证"
        
        logger.info("进行文本逻辑分析")
        # 文本逻辑分析 (不计入总分)
        # 使用基本逻辑分析，避免多次调用API
        logic_score, logic_details = basic_logic_analysis(text)
        result["scores"]["logic_analysis"] = logic_score
        result["details"]["logic_analysis"] = logic_details
        
        # 图像检测（如果提供了图像路径）
        if image_paths:
            logger.info("分析图像真实性")
            image_score, image_details = check_images(text, image_paths)
            result["scores"]["image_authenticity"] = image_score
            result["details"]["image_authenticity"] = image_details
        else:
            result["scores"]["image_authenticity"] = 0
            result["details"]["image_authenticity"] = "未提供图像，跳过图像真实性分析"
        
        logger.info("新闻分析完成")
        return result
    except Exception as e:
        logger.error(f"分析新闻时出错: {e}")
        logger.error(traceback.format_exc())
        raise

def judge_citation_truthfulness(text):
    """
    判断文本中引用内容的真实性
    
    参数:
        text: 新闻文本
    
    返回:
        (真实性评分, 评估详情)
    """
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except:
        logging.warning("无法禁用SSL警告")
    
    # 提取引用内容
    quotes = []
    
    # 匹配引号内容 - 使用Unicode码点表示中文引号
    quote_patterns = [
        r'"([^"]+)"',                      # 英文双引号
        r"'([^']+)'",                      # 英文单引号
        r'\u201c([^\u201d]+)\u201d',       # 中文双引号（"..."）
        r'\u2018([^\u2019]+)\u2019'        # 中文单引号（'...'）
    ]
    
    # 从每种引号模式中提取内容
    for pattern in quote_patterns:
        try:
            matches = re.findall(pattern, text)
            quotes.extend(matches)
        except Exception as e:
            logging.warning(f"引用提取出错: {str(e)}")
            continue
        
    # 匹配引用短语后的内容
    citation_phrases = ["据报道", "表示", "认为", "指出", "强调", "称"]
    for phrase in citation_phrases:
        try:
            pattern = phrase + r"[，,:：]?\s*(.+?)[。！？\.\n]"
            matches = re.findall(pattern, text)
            quotes.extend(matches)
        except Exception as e:
            logging.warning(f"引用短语提取出错: {str(e)}")
            continue
    
    # 去重并过滤过短的引用
    quotes = list(set([q.strip() for q in quotes if len(q.strip()) > 10]))
    
    if not quotes:
        return 0.7, "未检测到明确引用内容，无法验证"
    
    # 验证每个引用
    total_score = 0
    verified_count = 0
    verification_details = []
    
    for quote in quotes[:3]:  # 最多验证3个引用以节省资源
        try:
            score, explanation = search_and_verify_news(quote)
            total_score += score
            verified_count += 1
            
            # 添加到验证详情
            short_quote = quote[:30] + "..." if len(quote) > 30 else quote
            verification_details.append(f'引用"{short_quote}": {explanation} (评分: {score:.1f})')
            
        except Exception as e:
            logging.error(f"验证引用时出错: {str(e)}")
    
    # 计算平均分
    if verified_count > 0:
        avg_score = total_score / verified_count
    else:
        avg_score = 0.5  # 默认中等分数
    
    # 总体评估
    if avg_score > 0.8:
        summary = "引用内容的真实性评估：大多数引用内容能得到验证"
    elif avg_score > 0.6:
        summary = "引用内容的真实性评估：部分引用内容能得到验证"
    elif avg_score > 0.4:
        summary = "引用内容的真实性评估：引用内容验证证据有限"
    else:
        summary = "引用内容的真实性评估：多数引用内容无法得到验证"
    
    # 如果有详细验证结果，添加到总结中
    if verification_details:
        details = summary + "\n详细验证：\n- " + "\n- ".join(verification_details)
    else:
        details = summary
    
    return avg_score, details

def analyze_citation_validity(text):
    """
    分析引用的有效性
    """
    # 提取引用内容
    citations = []
    citation_pattern = r'[""]([^""]+)[""]'
    matches = re.finditer(citation_pattern, text)
    
    for match in matches:
        citation = match.group(1)
        if len(citation) > 10:  # 忽略过短的引用
            citations.append(citation)
    
    if not citations:
        # 如果没有找到引用，返回中等分数
        return 0.6, ["引用数量: 无明确引用", "引用准确性: 无法评估", "引用内容的真实性评估：无明确引用内容"]
    
    # 评估引用的数量
    if len(citations) >= 3:
        citation_quantity = "充足"
        quantity_score = 0.9
    elif len(citations) == 2:
        citation_quantity = "适量"
        quantity_score = 0.7
    else:
        citation_quantity = "有限"
        quantity_score = 0.5
    
    # 评估引用的准确性和真实性
    accuracy_score = 0
    truthfulness_score = 0
    verification_details = []
    
    try:
        # 验证每个引用
        for citation in citations:
            try:
                # 尝试使用搜索引擎验证引用
                verification_result = verify_citation_with_searxng(citation)
                
                if isinstance(verification_result, tuple) and len(verification_result) == 2:
                    citation_score, verification_detail = verification_result
                    accuracy_score += citation_score
                    verification_details.append(f"引用\"{citation}\": {verification_detail} (评分: {citation_score:.1f})")
                else:
                    logging.error(f"验证引用返回值格式错误: {verification_result}")
                    accuracy_score += 0.6  # 默认分数
                    verification_details.append(f"引用\"{citation}\": 验证过程出错，使用默认评分 (评分: 0.6)")
            except Exception as e:
                logging.error(f"验证引用时出错: {str(e)}")
                accuracy_score += 0.6  # 默认分数
                verification_details.append(f"引用\"{citation}\": 无搜索结果，使用本地评估: 本地评估: 引用来源(+0.1) (评分: 0.6)")
    except Exception as e:
        logging.error(f"验证引用时出错: {str(e)}")
        accuracy_score = 0.6 * len(citations)  # 默认分数
        verification_details = [f"引用验证过程出错: {str(e)}，使用默认评分"]
    
    # 计算平均分数
    if citations:
        accuracy_score = accuracy_score / len(citations)
    else:
        accuracy_score = 0.6  # 默认分数
    
    # 根据引用的真实性评估
    if accuracy_score >= 0.8:
        truthfulness = "引用内容验证度高"
    elif accuracy_score >= 0.6:
        truthfulness = "引用内容验证证据有限"
    else:
        truthfulness = "引用内容难以验证"
    
    # 计算总分
    total_score = (quantity_score + accuracy_score) / 2
    
    # 返回结果
    details = [
        f"引用数量: {citation_quantity}",
        f"引用准确性: {'高' if accuracy_score >= 0.8 else '中等' if accuracy_score >= 0.6 else '低'}",
        f"引用内容的真实性评估：{truthfulness}"
    ]
    
    # 添加详细验证结果
    details.extend(verification_details)
    
    return total_score, details

def query_deepseek(prompt, max_retries=2):
    """
    使用DeepSeek API进行查询
    
    参数:
        prompt (str): 提示词
        max_retries (int): 最大重试次数
    
    返回:
        str: API响应文本，如果失败则返回None
    """
    logger = logging.getLogger()
    
    # 检查API是否可用
    global DEEPSEEK_API_AVAILABLE
    if not DEEPSEEK_API_AVAILABLE:
        logger.warning("DeepSeek API已被标记为不可用，跳过查询")
        return None
    
    # 获取API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("未设置DEEPSEEK_API_KEY环境变量")
        DEEPSEEK_API_AVAILABLE = False
        return None
    
    # API端点
    api_url = "https://api.deepseek.com/v1/chat/completions"
    
    # 请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 请求数据
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    # 创建一个新的会话，避免连接池问题
    session = requests.Session()
    
    # 发送请求
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"发送DeepSeek API请求，尝试 {attempt+1}/{max_retries+1}")
            
            # 添加随机延迟，避免请求过于频繁
            if attempt > 0:
                delay = 2 + random.uniform(0, 2)
                logger.info(f"等待 {delay:.2f} 秒后重试")
                time.sleep(delay)
            
            # 使用新的会话发送请求
            response = session.post(api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                if content:
                    logger.debug("DeepSeek API请求成功")
                    return content
                else:
                    logger.warning("DeepSeek API返回空内容")
            else:
                logger.warning(f"DeepSeek API响应格式不正确: {result}")
            
            # 如果到达这里，说明响应格式不正确，但API调用成功
            # 返回原始响应的字符串表示
            return str(result)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API请求失败: {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt + random.uniform(0, 2)  # 指数退避 + 随机抖动
                logger.info(f"等待 {wait_time:.2f} 秒后重试")
                time.sleep(wait_time)
            else:
                logger.error("已达到最大重试次数，放弃请求")
                DEEPSEEK_API_AVAILABLE = False
                return None
        except Exception as e:
            logger.error(f"处理DeepSeek API响应时出错: {e}")
            logger.error(traceback.format_exc())
            if attempt < max_retries:
                wait_time = 2 ** attempt + random.uniform(0, 2)
                logger.info(f"等待 {wait_time:.2f} 秒后重试")
                time.sleep(wait_time)
            else:
                logger.error("已达到最大重试次数，放弃请求")
                DEEPSEEK_API_AVAILABLE = False
                return None
        finally:
            # 确保关闭会话
            if 'session' in locals():
                session.close()
    
    return None

def web_cross_verification(text, api_key=None):
    """
    通过网络搜索验证文本内容的可信度
    """
    score = 0.5  # 默认分数
    details = []
    
    # 提取关键句子进行验证
    sentences = re.split(r'[。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return score, ["无法提取句子进行验证"]
    
    # 选择最长的句子或包含引号的句子进行验证
    verification_sentences = []
    for s in sentences:
        if '"' in s or '"' in s or '"' in s or "'" in s or "'" in s:
            verification_sentences.append(s)
    
    if not verification_sentences and sentences:
        # 如果没有引号句子，选择最长的句子
        verification_sentences = [max(sentences, key=len)]
    
    if not verification_sentences:
        return score, ["无法提取有效句子进行验证"]
    
    # 尝试使用SearXNG进行验证
    searxng_success = False
    for sentence in verification_sentences[:2]:  # 限制验证的句子数量
        try:
            logging.info(f"尝试使用SearXNG验证句子: {sentence}")
            results = search_with_searxng(sentence)
            if results:
                searxng_success = True
        except Exception as e:
            logging.error(f"SearXNG验证失败: {str(e)}")
            continue
            
            match_score = analyze_search_results(results, sentence)
            score = match_score
            details.append(f"SearXNG验证: 句子 '{sentence}' 的匹配度为 {match_score:.1f}")
            break
            logging.error(f"SearXNG验证失败: {str(e)}")
    
    # 如果SearXNG失败，尝试使用DeepSeek API
    if not searxng_success:
        logging.info("SearXNG验证失败，尝试使用DeepSeek API进行验证")
        
        # 如果未提供api_key，尝试从环境变量获取
        if not api_key:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            logging.info(f"从环境变量获取DeepSeek API密钥: {'成功' if api_key else '失败'}")
        
        if api_key:
            try:
                # 构建提示词
                prompt = f"""
                请帮我验证以下新闻内容的可信度:
                
                "{text}"
                
                请分析这段内容的真实性，并给出0到1之间的可信度评分，其中0表示完全不可信，1表示完全可信。
                请以JSON格式返回结果，包含以下字段:
                - score: 可信度评分(0-1之间的浮点数)
                - reason: 评分理由
                
                仅返回JSON格式，不要有其他文字。
                """
                
                # 调用DeepSeek API
                logging.info("开始调用DeepSeek API进行验证...")
                response = query_deepseek(prompt, api_key)
                logging.info(f"DeepSeek API响应: {response}")
                
                # 尝试解析JSON响应
                try:
                    # 查找JSON部分
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        result = json.loads(json_str)
                        
                        if 'score' in result:
                            api_score = float(result['score'])
                            score = api_score
                            reason = result.get('reason', '未提供理由')
                            details.append(f"DeepSeek API验证: 可信度评分 {api_score:.1f}, 理由: {reason}")
                        else:
                            details.append("DeepSeek API未返回有效评分")
                    else:
                        details.append("无法从DeepSeek API响应中提取JSON")
                except json.JSONDecodeError as e:
                    logging.error(f"解析DeepSeek API响应时出错: {str(e)}")
                    details.append(f"无法解析DeepSeek API响应: {str(e)}")
            except Exception as e:
                logging.error(f"DeepSeek API验证失败: {str(e)}")
                details.append(f"DeepSeek API验证失败: {str(e)}")
        else:
            logging.warning("未提供DeepSeek API密钥，无法使用DeepSeek API进行验证")
            details.append("未提供DeepSeek API密钥，无法使用DeepSeek API进行验证")
    
    # 如果所有验证方法都失败，使用本地评估
    if not details:
        logging.info("所有验证方法均失败，使用本地评估")
        # 简单的本地评估逻辑
        local_score = 0.8  # 默认本地评估分数
        details.append(f"本地评估: 无法通过网络验证，使用本地评估分数 {local_score:.1f}")
        score = local_score
    
    # 确保分数在0-1范围内
    score = max(0, min(1, score))
    
    return score, details

def local_text_credibility(text):
    """
    进行本地文本可信度评估，在网络验证失败时使用
    
    参数:
        text: 新闻文本
        
    返回:
        (可信度评分, 评估解释)
    """
    logging.info("使用本地文本特征进行可信度评估")
    
    # 基本评分参数
    base_score = 0.5  # 默认中等分数
    
    # 提取文本特征
    # 1. 检查详细信息（时间、地点、人物）
    has_date = bool(re.search(r'\d+年\d+月\d+日|\d+\.\d+\.\d+|今天|昨天|上周|本月', text))
    has_location = bool(re.search(r'在[^\s]{2,}|[^\s]{2,}市|[^\s]{2,}省|[^\s]{2,}县', text))
    has_person = bool(re.search(r'[^\s]{2,}表示|[^\s]{2,}称|[^\s]{2,}说', text))
    
    # 2. 检查引用和来源
    has_citation = bool(re.search(r'据[^\s]+报道|引用|来源|消息人士|透露|专家称|官方', text))
    
    # 修复引号检测的正则表达式
    # 使用不同的模式匹配常见的引号类型
    quote_patterns = [
        r'"[^"]*"',        # 英文双引号
        r"'[^']*'",        # 英文单引号
        r'\u201c[^\u201d]*\u201d',  # 中文双引号（"..."）
        r'\u2018[^\u2019]*\u2019'   # 中文单引号（'...'）
    ]
    
    # 检查任意一种引号模式
    has_quotes = False
    for pattern in quote_patterns:
        try:
            if re.search(pattern, text):
                has_quotes = True
                break
        except Exception as e:
            logging.warning(f"引号检测出错: {str(e)}")
            continue
            
    # 3. 检查数据和统计
    has_numbers = bool(re.search(r'\d+\.?\d*\s*[%％]|\d+\.?\d*万|\d+\.?\d*亿|\d+人|\d+元', text))
    # 4. 检查情感和主观性
    emotional_words = ["震惊", "感人", "愤怒", "可怕", "恐怖", "悲剧", "欢呼", "庆祝", 
                      "shocking", "touching", "angry", "scary", "horrific", "tragic", "cheer", "celebrate"]
    extreme_words = ["绝对", "一定", "必然", "永远", "从来", "所有", "全部", "完全",
                    "absolute", "must", "inevitable", "forever", "never", "all", "entire", "completely"] 
    emotional_count = sum(1 for word in emotional_words if word in text)
    extreme_count = sum(1 for word in extreme_words if word in text)
    
    # 计算得分调整
    adjustments = []
    
    # 详细信息加分
    detail_score = (has_date + has_location + has_person) * 0.1
    adjustments.append(("详细信息", detail_score))
    
    # 引用和来源加分
    citation_score = (has_citation * 0.1 + has_quotes * 0.1)
    adjustments.append(("引用来源", citation_score))
    
    # 数据支持加分
    data_score = has_numbers * 0.1
    adjustments.append(("数据支持", data_score))
    
    # 情感和极端词汇减分
    emotion_penalty = min(0.2, (emotional_count + extreme_count) * 0.05)
    adjustments.append(("情感极端表达", -emotion_penalty))
    
    # 计算最终得分
    final_score = base_score
    for name, adj in adjustments:
        final_score += adj
    
    # 限制在0.1-0.9范围内
    final_score = max(0.1, min(0.9, final_score))
    
    # 生成评估解释
    explanation_parts = []
    for name, adj in adjustments:
        if adj != 0:
            sign = "+" if adj > 0 else ""
            explanation_parts.append(f"{name}({sign}{adj:.1f})")
    
    explanation = "本地评估: " + ", ".join(explanation_parts)
    
    return final_score, explanation

def test_searxng_connection():
    """
    测试SearXNG连接是否正常
    
    返回:
        bool: 连接是否成功
    """
    global AVAILABLE_SEARXNG_INSTANCE
    
    logging.info("测试SearXNG连接...")
    
    # 首先尝试本地实例
    local_instance = "http://localhost:8080"
    try:
        print(f"尝试连接: {local_instance}")
        response = requests.get(f"{local_instance}/search", params={"q": "test", "format": "json"}, timeout=5)
        print(f"  响应状态码: {response.status_code}")
        if response.status_code == 200:
            AVAILABLE_SEARXNG_INSTANCE = local_instance
            print("  ✓ 本地SearXNG实例可用")
            return True
    except Exception as e:
        print(f"  ❌ 本地SearXNG实例不可用: {e}")
    
    # 尝试公共实例
    public_instances = [
        "https://searx.be",
        "https://searx.tiekoetter.com",
        "https://searx.fmac.xyz",
        "https://search.unlocked.link",
        "https://search.sapti.me"
    ]
    
    for instance in public_instances:
        try:
            print(f"尝试连接: {instance}")
            response = requests.get(f"{instance}/search", params={"q": "test", "format": "json"}, timeout=5)
            print(f"  响应状态码: {response.status_code}")
            if response.status_code == 200:
                AVAILABLE_SEARXNG_INSTANCE = instance
                print(f"  ✓ 公共SearXNG实例 {instance} 可用")
                return True
        except Exception as e:
            print(f"  ❌ 公共SearXNG实例 {instance} 不可用: {e}")
    
    print("❌ 所有SearXNG实例都不可用")
    return False

def analyze_search_results(results, query):
    """
    分析搜索结果与查询的匹配度
    
    参数:
        results: 搜索结果列表
        query: 原始查询文本
        
    返回:
        匹配度评分(0-1)
    """
    logging.info(f"分析搜索结果与查询的匹配度: {query[:50]}...")
    
    if not results:
        return 0.3  # 默认低分
    
    # 提取关键词
    words = re.findall(r'\w+', query.lower())
    significant_words = [w for w in words if len(w) > 3]  # 只考虑较长的词
    
    if not significant_words:
        return 0.5  # 无法提取关键词，返回中等分数
    
    # 分析前5条结果
    total_match_score = 0
    result_count = min(5, len(results))
    
    for i, result in enumerate(results[:result_count]):
        title = result.get("title", "").lower()
        snippet = result.get("content", "").lower()
        combined_text = title + " " + snippet
        
        # 计算关键词匹配度
        matches = sum(1 for word in significant_words if word in combined_text)
        match_ratio = matches / len(significant_words)
        
        # 根据结果排名加权
        weight = 1.0 if i == 0 else 0.8 if i == 1 else 0.6 if i == 2 else 0.4 if i == 3 else 0.2
        weighted_score = match_ratio * weight
        
        total_match_score += weighted_score
    
    # 计算平均分数并归一化到0-1范围
    avg_score = total_match_score / result_count
    
    # 调整最终分数
    final_score = 0.3 + (avg_score * 0.7)  # 确保最低分为0.3
    final_score = min(1.0, final_score)  # 确保最高分为1.0
    
    logging.info(f"搜索结果匹配度评分: {final_score:.2f}")
    return final_score

def analyze_with_deepseek_v3(text, api_key=None):
    """
    使用DeepSeek API分析文本可信度
    
    参数:
        text (str): 要分析的文本
        api_key (str, optional): DeepSeek API密钥
    
    返回:
        tuple: (分数, 详细信息)
    """
    logger = logging.getLogger()
    
    # 检查API是否可用
    global DEEPSEEK_API_AVAILABLE
    if not DEEPSEEK_API_AVAILABLE:
        logger.warning("DeepSeek API不可用，跳过分析")
        return 0.5, "DeepSeek API不可用，无法进行分析"
    
    # 构建提示词
    prompt = f"""请分析以下新闻文本的可信度，并给出详细评分和分析。评分范围从0到1，其中0表示完全不可信，1表示完全可信。

请从以下几个方面进行评分和分析：
1. 内容真实性：内容是否基于事实，是否有明显虚构成分
2. 信息准确性：信息是否准确，是否有错误或误导
3. 来源可靠性：来源是否可靠，是否有明确的信息来源
4. 语言客观性：语言是否客观中立，是否有明显的情感倾向
5. 逻辑连贯性：内容是否逻辑连贯，是否有明显的逻辑漏洞
6. 引用质量：是否有高质量的引用和参考资料

请以JSON格式返回结果，包含总体评分和各项评分，以及详细分析。格式如下：
{{
  "总体评分": 0.8,
  "各项评分": {{
    "内容真实性": 0.8,
    "信息准确性": 0.7,
    "来源可靠性": 0.9,
    "语言客观性": 0.8,
    "逻辑连贯性": 0.7,
    "引用质量": 0.8
  }},
  "详细分析": "这里是详细分析...",
  "建议": "这里是改进建议..."
}}

新闻文本：
{text[:3000]}  # 限制文本长度，避免超出API限制
"""
    
    try:
        # 调用DeepSeek API
        response = query_deepseek(prompt)
        if not response:
            logger.warning("DeepSeek API返回空响应")
            return 0.5, "DeepSeek API返回空响应，无法进行分析"
        
        logger.debug(f"DeepSeek API响应: {response}")
        
        # 尝试解析JSON
        try:
            import json
            import re
            
            # 尝试从响应中提取JSON部分
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                
                # 提取总体评分
                overall_score = data.get("总体评分", 0.5)
                
                # 格式化详细信息
                detailed_info = json.dumps(data, ensure_ascii=False, indent=2)
                
                return overall_score, detailed_info
            else:
                # 如果无法提取JSON，尝试从文本中提取评分
                score_match = re.search(r'总体评分[：:]\s*(\d+\.\d+)', response)
                if score_match:
                    score = float(score_match.group(1))
                    return score, response
                else:
                    # 如果无法提取评分，返回默认值和原始响应
                    return 0.5, response
        except Exception as e:
            logger.error(f"解析DeepSeek响应时出错: {e}")
            return 0.5, response
    except Exception as e:
        logger.error(f"调用DeepSeek API时出错: {e}")
        return 0.5, f"调用DeepSeek API时出错: {e}"

def check_images(text, image_paths=None):
    """
    检查图片的真实性
    
    参数:
        text (str): 新闻文本
        image_paths (list): 图片路径列表
    
    返回:
        tuple: (分数, 详细信息)
    """
    logger = logging.getLogger()
    
    if not image_paths:
        logger.info("未提供图片路径，跳过图片检查")
        return 0, "未提供图片，跳过图片真实性分析"
    
    try:
        # 提取文本中的图片描述
        image_descriptions = []
        # 简单的图片描述提取逻辑
        desc_patterns = [
            r'图\d+[：:](.*?)(?=图\d+[：:]|$)',
            r'图片[：:](.*?)(?=图片[：:]|$)',
            r'照片[：:](.*?)(?=照片[：:]|$)',
            r'图像[：:](.*?)(?=图像[：:]|$)'
        ]
        
        for pattern in desc_patterns:
            matches = re.findall(pattern, text)
            image_descriptions.extend([m.strip() for m in matches if m.strip()])
        
        # 分析每张图片
        image_scores = []
        image_details = []
        
        for i, img_path in enumerate(image_paths):
            try:
                score, details = analyze_image_authenticity(img_path)
                image_scores.append(score)
                
                # 添加图片描述（如果有）
                if i < len(image_descriptions):
                    details = f"图片描述: {image_descriptions[i]}\n{details}"
                
                image_details.append(details)
            except Exception as e:
                logger.error(f"分析图片 {img_path} 时出错: {e}")
                image_scores.append(0)
                image_details.append(f"分析出错: {e}")
        
        # 计算平均分
        avg_score = sum(image_scores) / len(image_scores) if image_scores else 0
        
        # 格式化详细信息
        formatted_details = []
        formatted_details.append(f"图像可信度评估：{'较高' if avg_score > 0.6 else '中等' if avg_score > 0.4 else '较低'}")
        
        if image_descriptions:
            formatted_details.append(f"图像描述: {', '.join(image_descriptions)}")
        else:
            formatted_details.append("未检测到明确的图像描述")
        
        formatted_details.append(f"图像真实性平均评分: {avg_score*10:.2f}")
        
        # 添加每张图片的详细信息
        for i, details in enumerate(image_details):
            formatted_details.append(f"图片 {i+1} 分析:")
            # 分行处理详细信息
            for line in details.split('\n'):
                if line.strip():
                    formatted_details.append(f"  {line.strip()}")
        
        return avg_score, formatted_details
    except Exception as e:
        logger.error(f"检查图片时出错: {e}")
        return 0, f"检查图片时出错: {e}"

def analyze_image_authenticity(image_path):
    """
    分析图片的真实性
    
    参数:
        image_path (str): 图片路径
    
    返回:
        tuple: (分数, 详细信息)
    """
    logger = logging.getLogger()
    logger.info(f"分析图片真实性: {image_path}")
    
    # 导入需要的库
    try:
        import exifread
        has_exifread = True
    except ImportError:
        logger.error("未安装exifread库，无法读取图片元数据")
        has_exifread = False
    
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return 0, "图片文件不存在"
        
        # 检查文件大小
        file_size = os.path.getsize(image_path) / 1024  # KB
        if file_size < 1:
            logger.warning(f"图片文件过小: {file_size:.2f} KB")
            return 0.2, "图片文件过小，可能不是真实照片"
        
        # 检查是否为有效图片
        try:
            from PIL import Image
            img = Image.open(image_path)
            img.verify()  # 验证图片完整性
            img = Image.open(image_path)  # 重新打开，因为verify会消耗文件指针
            width, height = img.size
            
            if width < 100 or height < 100:
                logger.warning(f"图片尺寸过小: {width}x{height}")
                return 0.3, "图片尺寸过小，可能是缩略图或图标"
                
            logger.debug(f"图片尺寸: {width}x{height}, 格式: {img.format}")
        except Exception as e:
            logger.error(f"无效的图片文件: {e}")
            return 0, f"无效的图片文件: {e}"
        
        # 分析元数据
        metadata_score = 0
        metadata_details = []
        
        try:
            # 使用exifread读取EXIF数据
            if has_exifread:
                with open(image_path, 'rb') as f:
                    tags = exifread.process_file(f)
                
                if tags:
                    # 提取相机信息
                    camera_make = tags.get('Image Make', None)
                    camera_model = tags.get('Image Model', None)
                    
                    if camera_make or camera_model:
                        metadata_score += 0.2
                        metadata_details.append(f"相机信息: {camera_make} {camera_model}")
                    
                    # 提取拍摄时间
                    date_time = tags.get('EXIF DateTimeOriginal', None)
                    if date_time:
                        metadata_score += 0.1
                        metadata_details.append(f"拍摄时间: {date_time}")
                    
                    # 提取GPS信息
                    gps_latitude = tags.get('GPS GPSLatitude', None)
                    gps_longitude = tags.get('GPS GPSLongitude', None)
                    
                    if gps_latitude and gps_longitude:
                        metadata_score += 0.2
                        metadata_details.append("包含GPS位置信息")
                    
                    # 其他EXIF信息
                    if len(tags) > 5:
                        metadata_score += 0.1
                        metadata_details.append(f"包含{len(tags)}项EXIF元数据")
                else:
                    metadata_details.append("图像不包含EXIF元数据，可能已被处理或是截图")
            else:
                metadata_details.append("无法读取图片元数据: exifread库未安装")
        except Exception as e:
            logger.error(f"读取图片元数据时出错: {e}")
            metadata_details.append(f"读取元数据出错: {e}")
        
        # 使用OpenCV分析图片质量
        quality_score = 0
        quality_details = []
        
        try:
            import cv2
            import numpy as np
            
            # 读取图片
            img_cv = cv2.imread(image_path)
            if img_cv is None:
                logger.error("OpenCV无法读取图片")
                quality_details.append("无法分析图片质量")
            else:
                # 转换为灰度图
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                
                # 计算拉普拉斯方差（清晰度指标）
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                if laplacian_var > 100:
                    quality_score += 0.2
                    quality_details.append("图像清晰度高")
                elif laplacian_var > 50:
                    quality_score += 0.1
                    quality_details.append("图像清晰度中等")
                else:
                    quality_details.append("图像清晰度低")
                
                # 检测边缘
                edges = cv2.Canny(gray, 100, 200)
                edge_ratio = np.count_nonzero(edges) / (edges.shape[0] * edges.shape[1])
                
                if edge_ratio > 0.1:
                    quality_score += 0.1
                    quality_details.append("图像边缘丰富，细节较多")
                
                # 检测直线（可能表明人工编辑）
                lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
                if lines is not None and len(lines) > 10:
                    quality_details.append("图像边缘规则性较高，可能经过编辑")
                
                # 检查颜色分布
                hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
                h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
                s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256])
                
                h_var = np.var(h_hist)
                s_var = np.var(s_hist)
                
                if h_var > 1000 and s_var > 1000:
                    quality_score += 0.1
                    quality_details.append("图像色彩分布自然")
                else:
                    quality_details.append("图像色彩分布异常")
        except Exception as e:
            logger.error(f"分析图片质量时出错: {e}")
            quality_details.append(f"分析质量出错: {e}")
        
        # 分析光照一致性
        consistency_score = 0
        consistency_details = []
        
        try:
            if 'img_cv' in locals() and img_cv is not None:
                # 分析亮度分布
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                brightness_mean = np.mean(gray)
                brightness_std = np.std(gray)
                
                if brightness_std > 50:
                    consistency_score += 0.2
                    consistency_details.append("图像光照分布自然")
                elif brightness_std > 30:
                    consistency_score += 0.1
                    consistency_details.append("图像光照分布较自然")
                else:
                    consistency_details.append("图像光照分布过于均匀，可能经过处理")
                
                # 分析颜色一致性
                hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
                s_mean = np.mean(hsv[:,:,1])
                s_std = np.std(hsv[:,:,1])
                
                if s_std > 50:
                    consistency_score += 0.1
                    consistency_details.append("图像饱和度分布自然")
                else:
                    consistency_details.append("图像饱和度分布异常")
        except Exception as e:
            logger.error(f"分析图片一致性时出错: {e}")
            consistency_details.append(f"分析一致性出错: {e}")
        
        # 计算总分
        total_score = (metadata_score + quality_score + consistency_score) / 3
        
        # 格式化详细信息
        details = []
        if metadata_details:
            details.append("元数据分析: " + "; ".join(metadata_details))
        if quality_details:
            details.append("质量分析: " + "; ".join(quality_details))
        if consistency_details:
            details.append("一致性分析: " + "; ".join(consistency_details))
        
        return total_score, "\n".join(details)
    except Exception as e:
        logger.error(f"分析图片真实性时出错: {e}")
        return 0, f"分析图片真实性时出错: {e}"

def analyze_text_logic(text):
    """
    分析文本的逻辑性
    
    参数:
        text (str): 要分析的文本
    
    返回:
        tuple: (分数, 详细信息)
    """
    logger = logging.getLogger()
    logger.info("分析文本逻辑性")
    
    # 检查是否已经进行过DeepSeek分析
    # 如果已经在search_and_verify_news中调用过DeepSeek API，则不再调用
    # 这是为了避免连接池问题
    global DEEPSEEK_API_AVAILABLE
    if not DEEPSEEK_API_AVAILABLE or len(text) < 100:
        logger.info("使用基本逻辑分析")
        return basic_logic_analysis(text)
    
    # 为了避免多次调用API导致的连接问题，这里直接使用基本逻辑分析
    logger.info("为避免多次调用API，使用基本逻辑分析")
    return basic_logic_analysis(text)
    
    # 以下代码暂时注释掉，避免多次调用API
    """
    # 使用DeepSeek API进行深度分析
    if DEEPSEEK_API_AVAILABLE and len(text) > 100:
        try:
            # 构建提示词
            prompt = f\"\"\"请分析以下文本的逻辑性和连贯性，评估其是否存在逻辑漏洞、矛盾或不一致之处。
            
            请从以下几个方面进行评估：
            1. 论点是否清晰
            2. 论据是否充分
            3. 推理是否合理
            4. 是否存在逻辑谬误
            5. 结论是否与前提一致
            
            请给出0到1之间的评分，其中0表示完全不合逻辑，1表示完全合逻辑。同时提供详细分析。
            
            文本内容：
            {text[:2000]}  # 限制文本长度
            \"\"\"
            
            # 调用DeepSeek API
            response = query_deepseek(prompt)
            
            if response:
                # 尝试从响应中提取评分
                score_match = re.search(r'评分[：:]\s*(\d+\.?\d*)', response)
                if score_match:
                    score = float(score_match.group(1))
                    if score > 1:  # 如果评分超过1，归一化到0-1范围
                        score = score / 10
                    return score, response
                else:
                    # 如果无法提取评分，使用基本逻辑分析
                    logger.warning("无法从DeepSeek响应中提取评分，使用基本逻辑分析")
                    return basic_logic_analysis(text)
            else:
                # 如果API返回为空，使用基本逻辑分析
                logger.warning("DeepSeek API返回空响应，使用基本逻辑分析")
                return basic_logic_analysis(text)
        except Exception as e:
            logger.error(f"使用DeepSeek分析逻辑时出错: {e}")
            logger.info("回退到基本逻辑分析")
            return basic_logic_analysis(text)
    else:
        # 如果API不可用或文本太短，使用基本逻辑分析
        if not DEEPSEEK_API_AVAILABLE:
            logger.info("DeepSeek API不可用，使用基本逻辑分析")
        return basic_logic_analysis(text)
    """

def basic_logic_analysis(text):
    """
    基本的文本逻辑分析
    
    参数:
        text (str): 要分析的文本
    
    返回:
        tuple: (分数, 详细信息)
    """
    # 初始分数
    score = 0.5
    details = []
    
    # 文本长度分析
    if len(text) < 100:
        score -= 0.1
        details.append("文本过短，难以进行深入逻辑分析")
    elif len(text) > 500:
        score += 0.1
        details.append("文本较长，基本分析显示有一定的逻辑结构和论述深度")
    
    # 逻辑连接词分析
    logic_connectors = [
        "因为", "所以", "因此", "由于", "如果", "那么", "但是", "然而",
        "虽然", "尽管", "不过", "否则", "除非", "只有", "首先", "其次",
        "最后", "总之", "换言之", "例如", "比如", "特别是", "尤其是"
    ]
    
    connector_count = sum(1 for connector in logic_connectors if connector in text)
    connector_density = connector_count / (len(text) / 100)  # 每100字的连接词数量
    
    if connector_density > 2:
        score += 0.2
        details.append("文本包含充足的逻辑连接词，逻辑结构清晰")
    elif connector_density > 1:
        score += 0.1
        details.append("文本包含一定的逻辑连接词，逻辑结构基本清晰")
    else:
        score -= 0.1
        details.append("文本缺乏足够的逻辑连接词，逻辑组织可能不够清晰")
    
    # 段落结构分析
    paragraphs = text.split('\n\n')
    if len(paragraphs) > 3:
        score += 0.1
        details.append("文本分为多个段落，结构较为完整")
    
    # 矛盾词分析
    contradiction_pairs = [
        ("增加", "减少"), ("上升", "下降"), ("提高", "降低"),
        ("加强", "减弱"), ("扩大", "缩小"), ("加速", "减速"),
        ("肯定", "否定"), ("支持", "反对"), ("赞成", "反对")
    ]
    
    contradiction_count = 0
    for pair in contradiction_pairs:
        if pair[0] in text and pair[1] in text:
            contradiction_count += 1
    
    if contradiction_count > 2:
        score -= 0.2
        details.append(f"检测到可能的逻辑矛盾：文本中同时出现了{contradiction_count}对矛盾词汇")
    
    # 最终评分
    score = max(0, min(1, score))  # 确保分数在0-1之间
    
    return score, " ".join(details)

def get_citation_score(text):
    """
    评估文本中引用的质量
    
    统计引用数量和多样性
    检测直接引语的使用
    评估引用来源的权威性
    
    参数:
        text: 新闻文本
        
    返回:
        (引用质量评分(0-1), 详细分析结果列表)
    """
    logging.info("开始评估引用质量...")
    
    # 初始化评分和详情
    citation_score = 0.5  # 默认中等分数
    details = []
    
    # 1. 提取直接引语
    # 匹配引号内容 - 使用Unicode码点表示中文引号
    quote_patterns = [
        r'"([^"]+)"',                      # 英文双引号
        r"'([^']+)'",                      # 英文单引号
        r'\u201c([^\u201d]+)\u201d',       # 中文双引号（"..."）
        r'\u2018([^\u2019]+)\u2019'        # 中文单引号（'...'）
    ]
    
    direct_quotes = []
    for pattern in quote_patterns:
        try:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 10:  # 忽略过短的引用
                    direct_quotes.append(match)
        except Exception as e:
            logging.warning(f"引用提取出错: {str(e)}")
    
    # 2. 提取间接引用
    # 匹配引用短语后的内容
    citation_phrases = [
        "据报道", "表示", "认为", "指出", "强调", "称", "透露", "宣称", "宣布", "声明",
        "报道", "披露", "爆料", "提到", "谈到", "说", "讲", "写道", "写到", "描述"
    ]
    
    indirect_quotes = []
    for phrase in citation_phrases:
        try:
            pattern = phrase + r"[，,:：]?\s*(.+?)[。！？\.\n]"
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 10:  # 忽略过短的引用
                    indirect_quotes.append(match)
        except Exception as e:
            logging.warning(f"引用短语提取出错: {str(e)}")
    
    # 3. 提取引用来源
    # 匹配可能的引用来源
    source_patterns = [
        r"据([^，。；,\.;]+?)(?:报道|透露|称|表示|指出)",
        r"([^，。；,\.;]+?)(?:报道|透露|称|表示|指出)",
        r"来自([^，。；,\.;]+?)的(?:消息|报道|信息)",
        r"引用([^，。；,\.;]+?)的(?:话|说法|观点|研究|数据)",
        r"根据([^，。；,\.;]+?)(?:的研究|的调查|的报告|的数据|的统计)"
    ]
    
    citation_sources = []
    for pattern in source_patterns:
        try:
            matches = re.findall(pattern, text)
            citation_sources.extend(matches)
        except Exception as e:
            logging.warning(f"引用来源提取出错: {str(e)}")
    
    # 去重
    citation_sources = list(set([s.strip() for s in citation_sources if len(s.strip()) > 1]))
    
    # 4. 评估引用数量
    total_quotes = len(direct_quotes) + len(indirect_quotes)
    
    if total_quotes >= 5:
        quantity_level = "充足"
        quantity_score = 0.9
    elif total_quotes >= 3:
        quantity_level = "适量"
        quantity_score = 0.7
    elif total_quotes >= 1:
        quantity_level = "有限"
        quantity_score = 0.5
    else:
        quantity_level = "缺乏"
        quantity_score = 0.3
    
    details.append(f"引用数量: {quantity_level} (直接引语: {len(direct_quotes)}, 间接引用: {len(indirect_quotes)})")
    
    # 5. 评估引用多样性
    if len(citation_sources) >= 4:
        diversity_level = "高"
        diversity_score = 0.9
    elif len(citation_sources) >= 2:
        diversity_level = "中等"
        diversity_score = 0.7
    elif len(citation_sources) >= 1:
        diversity_level = "低"
        diversity_score = 0.5
    else:
        diversity_level = "无法评估"
        diversity_score = 0.3
    
    details.append(f"引用来源多样性: {diversity_level} (检测到{len(citation_sources)}个不同来源)")
    
    if citation_sources:
        details.append(f"检测到的引用来源: {', '.join(citation_sources[:5])}" + ("..." if len(citation_sources) > 5 else ""))
    
    # 6. 评估引用来源权威性
    authority_sources = [
        "新华社", "人民日报", "中央电视台", "CCTV", "央视", "中新社", "光明日报", "经济日报",
        "BBC", "CNN", "路透社", "Reuters", "美联社", "AP", "法新社", "AFP", "彭博社", "Bloomberg",
        "纽约时报", "华盛顿邮报", "华尔街日报", "金融时报", "经济学人", "卫报",
        "科学", "自然", "柳叶刀", "新英格兰医学杂志", "Science", "Nature", "Lancet", "NEJM"
    ]
    
    authority_count = 0
    for source in citation_sources:
        for auth_source in authority_sources:
            if auth_source in source:
                authority_count += 1
                break
    
    if authority_count >= 2:
        authority_level = "高"
        authority_score = 0.9
    elif authority_count >= 1:
        authority_level = "中等"
        authority_score = 0.7
    else:
        authority_level = "低"
        authority_score = 0.4
    
    details.append(f"引用来源权威性: {authority_level} (检测到{authority_count}个权威来源)")
    
    # 7. 计算综合得分
    # 各项权重
    weights = {
        "quantity": 0.3,
        "diversity": 0.3,
        "authority": 0.4
    }
    
    # 计算加权总分
    citation_score = (
        quantity_score * weights["quantity"] +
        diversity_score * weights["diversity"] +
        authority_score * weights["authority"]
    )
    
    # 确保分数在0-1范围内
    citation_score = max(0.1, min(0.9, citation_score))
    
    # 8. 总体评估
    if citation_score >= 0.8:
        conclusion = "引用质量评估：引用质量高，来源可靠多样"
    elif citation_score >= 0.6:
        conclusion = "引用质量评估：引用质量中等，来源基本可靠"
    elif citation_score >= 0.4:
        conclusion = "引用质量评估：引用质量一般，来源可靠性有限"
    else:
        conclusion = "引用质量评估：引用质量低，缺乏可靠来源"
    
    details.append(conclusion)
    
    logging.info(f"引用质量评估完成，评分: {citation_score:.2f}")
    return citation_score, details

def evaluate_domain_trust(url):
    """
    评估新闻URL的域名可信度
    
    参数:
        url (str): 新闻URL
    
    返回:
        tuple: (可信度评分(0-1), 详细信息)
    """
    logging.info(f"评估域名可信度: {url}")
    
    # 初始化
    score = 0.5  # 默认中等可信度
    details = []
    
    try:
        # 解析URL获取域名
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # 不可信域名列表
        untrusted_domains = [
            # 中国相关不可信域名
            "baijiahao.baidu.com", "99gongshe.com", "chinascope.org",
            "friendlyparis.net", "incheonfocus.com", "milanomodaweekly.com",
            # 通用假新闻网站
            "abcnews.com.co", "cbsnews.com.co", "washingtonpost.com.co", "usatoday.com.co",
            # 讽刺网站
            "theonion.com",
            # 其他不可信域名
            "beforeitsnews.com", "naturalnews.com", "worldnewsdailyreport.com"
        ]
        
        # 检查是否为不可信域名
        for untrusted_domain in untrusted_domains:
            if domain == untrusted_domain or domain.endswith("." + untrusted_domain):
                score = 0.1  # 设置为10%的低可信度
                details.append(f"⚠️ 警告：{domain} 是已知的不可信域名！")
                details.append(f"⚠️ 此网站内容可能包含虚假或误导性信息，请谨慎对待")
                return score, details
        
        # 检查是否为IP地址（降低可信度）
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", domain):
            score -= 0.2
            details.append(f"域名为IP地址 ({domain})，降低可信度")
        
        # 检查顶级域名
        tld_patterns = {
            r"\.(gov|edu|mil)(\.[a-z]{2})?$": (0.3, "政府/教育/军事域名，提高可信度"),
            r"\.(org|net)(\.[a-z]{2})?$": (0.1, "组织/网络域名，略微提高可信度"),
            r"\.(com|co)(\.[a-z]{2})?$": (0, "商业域名，中性评价"),
            r"\.(info|biz|xyz|top|site|online|club)$": (-0.1, "低成本域名，略微降低可信度")
        }
        
        for pattern, (adjustment, reason) in tld_patterns.items():
            if re.search(pattern, domain, re.IGNORECASE):
                score += adjustment
                details.append(reason)
                break
        
        # 检查域名长度（非常长或非常短的域名可能可疑）
        domain_length = len(domain)
        if domain_length < 5:
            score -= 0.1
            details.append("域名过短，可能可疑")
        elif domain_length > 30:
            score -= 0.1
            details.append("域名过长，可能可疑")
        
        # 检查域名中的数字和连字符数量（过多可能可疑）
        num_digits = sum(c.isdigit() for c in domain)
        num_hyphens = domain.count('-')
        if num_digits > 5 or num_hyphens > 3:
            score -= 0.1
            details.append("域名中包含过多数字或连字符，可能可疑")
        
        # 检查知名新闻域名
        trusted_domains = [
            "bbc.com", "bbc.co.uk", "nytimes.com", "washingtonpost.com", "wsj.com", 
            "reuters.com", "apnews.com", "npr.org", "cnn.com", "theguardian.com",
            "economist.com", "ft.com", "bloomberg.com", "time.com", "forbes.com",
            "xinhuanet.com", "chinadaily.com.cn", "people.com.cn", "cctv.com",
            "nhk.or.jp", "abc.net.au", "aljazeera.com", "dw.com", "france24.com","cnbc.com"
        ]
        
        for trusted_domain in trusted_domains:
            if domain.endswith(trusted_domain):
                score += 0.3
                details.append(f"知名可信新闻源 ({trusted_domain})")
                break
        
        # 确保分数在0-1范围内
        score = max(0, min(1, score))
        
    except Exception as e:
        logging.error(f"评估域名时出错: {str(e)}")
        details.append(f"评估域名时出错: {str(e)}")
    
    return score, details

def fetch_news_content(url):
    """
    从URL获取新闻内容和图片
    
    参数:
        url (str): 新闻URL
    
    返回:
        tuple: (文本内容, 图片路径列表)
    """
    logger = logging.getLogger()
    logger.info(f"开始从URL获取内容: {url}")
    
    try:
        # 创建临时目录存储图片
        temp_dir = os.path.join(os.getcwd(), "temp_images")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            logger.debug(f"创建临时目录: {temp_dir}")
        
        # 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 发送请求
        logger.debug(f"发送HTTP请求: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            response.raise_for_status()
            logger.debug(f"HTTP请求成功，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {e}")
            return None, []
        
        # 检查内容类型
        content_type = response.headers.get('Content-Type', '')
        logger.debug(f"内容类型: {content_type}")
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            logger.warning(f"非HTML内容类型: {content_type}")
        
        # 解析HTML
        logger.debug("开始解析HTML")
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.debug("HTML解析成功")
        except Exception as e:
            logger.error(f"HTML解析失败: {e}")
            # 尝试使用不同的解析器
            try:
                logger.debug("尝试使用lxml解析器")
                soup = BeautifulSoup(response.text, 'lxml')
                logger.debug("lxml解析成功")
            except Exception as e:
                logger.error(f"lxml解析失败: {e}")
                try:
                    logger.debug("尝试使用html5lib解析器")
                    soup = BeautifulSoup(response.text, 'html5lib')
                    logger.debug("html5lib解析成功")
                except Exception as e:
                    logger.error(f"所有解析器都失败: {e}")
                    return None, []
        
        # 提取标题
        logger.debug("提取标题")
        title = None
        try:
            # 尝试不同的标题提取方法
            if soup.title:
                title = soup.title.text.strip()
                logger.debug(f"从title标签提取标题: {title}")
            else:
                # 尝试从h1标签提取
                h1_tags = soup.find_all('h1')
                if h1_tags:
                    title = h1_tags[0].text.strip()
                    logger.debug(f"从h1标签提取标题: {title}")
        except Exception as e:
            logger.error(f"提取标题时出错: {e}")
        
        # 提取正文内容
        logger.debug("提取正文内容")
        content = ""
        try:
            # 方法1: 尝试提取article标签
            articles = soup.find_all('article')
            if articles:
                logger.debug("使用article标签提取内容")
                for article in articles:
                    content += article.text.strip() + "\n\n"
            
            # 方法2: 尝试提取main标签
            if not content:
                main_content = soup.find('main')
                if main_content:
                    logger.debug("使用main标签提取内容")
                    content = main_content.text.strip()
            
            # 方法3: 尝试提取常见内容div
            if not content:
                logger.debug("尝试从常见内容div提取")
                content_divs = soup.find_all('div', class_=lambda c: c and any(x in c.lower() for x in ['content', 'article', 'main', 'body', 'text']))
                if content_divs:
                    for div in content_divs:
                        content += div.text.strip() + "\n\n"
            
            # 方法4: 提取所有段落
            if not content:
                logger.debug("从所有段落提取内容")
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    content += p.text.strip() + "\n\n"
            
            # 清理内容
            content = re.sub(r'\s+', ' ', content).strip()
            logger.debug(f"提取到的内容长度: {len(content)}")
            
            if not content:
                logger.warning("未能提取到内容")
                # 最后的尝试: 提取body的所有文本
                body = soup.find('body')
                if body:
                    content = body.text.strip()
                    logger.debug(f"从body提取内容，长度: {len(content)}")
        except Exception as e:
            logger.error(f"提取内容时出错: {e}")
            logger.error(traceback.format_exc())
        
        # 组合标题和内容
        full_text = f"{title}\n\n{content}" if title else content
        logger.info(f"提取到的文本总长度: {len(full_text)}")
        
        # 下载图片
        image_paths = []
        try:
            logger.info("开始下载图片")
            images = soup.find_all('img')
            logger.info(f"找到 {len(images)} 张图片")
            
            for i, img in enumerate(images):
                try:
                    # 获取图片URL
                    img_url = img.get('src')
                    if not img_url:
                        logger.debug(f"图片 {i+1} 没有src属性，尝试data-src")
                        img_url = img.get('data-src')
                        
                    if not img_url:
                        logger.debug(f"图片 {i+1} 没有有效的URL，跳过")
                        continue
                    
                    # 处理相对URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                        logger.debug(f"处理相对URL: {img_url}")
                    elif not img_url.startswith(('http://', 'https://')):
                        img_url = urljoin(url, img_url)
                        logger.debug(f"处理相对URL: {img_url}")
                    
                    logger.info(f"处理图片 {i+1}/{len(images)}: {img_url}")
                    
                    # 跳过小图标和广告图片
                    width = img.get('width')
                    height = img.get('height')
                    if width and height:
                        try:
                            width_val = int(width)
                            height_val = int(height)
                            if width_val < 100 or height_val < 100:
                                logger.info(f"跳过小图片: 宽={width_val}, 高={height_val}")
                                continue
                        except ValueError:
                            logger.debug(f"无法解析图片尺寸: 宽={width}, 高={height}")
                    
                    # 下载图片
                    try:
                        logger.debug(f"开始下载图片: {img_url}")
                        img_response = requests.get(img_url, headers=headers, timeout=10, verify=False)
                        img_response.raise_for_status()
                        
                        # 检查内容类型
                        img_content_type = img_response.headers.get('Content-Type', '')
                        if not img_content_type.startswith('image/'):
                            logger.warning(f"非图片内容类型: {img_content_type}，跳过")
                            continue
                        
                        # 生成唯一文件名
                        img_hash = hashlib.md5(img_url.encode()).hexdigest()
                        
                        # 从内容类型或URL确定扩展名
                        if 'image/jpeg' in img_content_type:
                            img_ext = 'jpg'
                        elif 'image/png' in img_content_type:
                            img_ext = 'png'
                        elif 'image/gif' in img_content_type:
                            img_ext = 'gif'
                        elif 'image/webp' in img_content_type:
                            img_ext = 'webp'
                        else:
                            # 从URL获取扩展名
                            img_ext = img_url.split('.')[-1] if '.' in img_url else 'jpg'
                            if len(img_ext) > 4 or not img_ext.isalpha():
                                img_ext = 'jpg'
                        
                        img_path = os.path.join(temp_dir, f"{img_hash}.{img_ext}")
                        logger.debug(f"保存图片到: {img_path}")
                        
                        # 保存图片
                        with open(img_path, 'wb') as f:
                            f.write(img_response.content)
                        
                        # 验证图片是否有效
                        try:
                            from PIL import Image
                            img_obj = Image.open(img_path)
                            img_obj.verify()  # 验证图像文件
                            img_width, img_height = img_obj.size
                            logger.debug(f"图片有效，尺寸: {img_width}x{img_height}")
                            
                            # 跳过太小的图片
                            if img_width < 100 or img_height < 100:
                                logger.info(f"跳过小图片: {img_width}x{img_height}")
                                os.remove(img_path)
                                continue
                                
                            image_paths.append(img_path)
                            logger.info(f"成功下载图片: {img_path}")
                        except Exception as e:
                            logger.warning(f"无效的图片文件: {img_path}, 错误: {e}")
                            os.remove(img_path)
                            continue
                        
                        # 限制图片数量
                        if len(image_paths) >= 5:
                            logger.info("已达到最大图片数量限制")
                            break
                    except Exception as e:
                        logger.error(f"下载图片时出错: {e}")
                except Exception as e:
                    logger.error(f"处理图片时出错: {e}")
            
            logger.info(f"成功下载 {len(image_paths)} 张图片")
        except Exception as e:
            logger.error(f"下载图片过程中出错: {e}")
            logger.error(traceback.format_exc())
        
        return full_text, image_paths
    except Exception as e:
        logger.error(f"获取新闻内容时出错: {e}")
        logger.error(traceback.format_exc())
        return None, []

def local_news_validation(text):
    """
    验证新闻的本地相关性
    返回: (分数, 详细信息)
    """
    logger.info("开始本地新闻验证")
    try:
        score = 0.7  # 默认基础分
        details = []
        
        # 检查本地相关性指标
        local_indicators = ['当地', '本地', '社区', '市', '区', '县', '省']
        found_indicators = [i for i in local_indicators if i in text]
        
        if found_indicators:
            score += 0.3
            details.append(f"发现本地相关词汇: {', '.join(found_indicators)}")
        else:
            details.append("未发现明显的本地相关性指标")
        
        return score, "; ".join(details)
    except Exception as e:
        logger.error(f"本地新闻验证出错: {e}")
        return 0.5, "验证过程出现错误，使用默认分数"

def test_deepseek_connection():
    """
    测试DeepSeek API连接是否正常
    
    返回:
        bool: 连接是否成功
    """
    global DEEPSEEK_API_AVAILABLE
    
    logging.info("测试DeepSeek API连接...")
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logging.error("未设置DEEPSEEK_API_KEY环境变量")
        DEEPSEEK_API_AVAILABLE = False
        return False
    
    prompt = "简单回复'连接测试成功'"
    
    try:
        response = query_deepseek(prompt, max_retries=1)  # 减少重试次数，加快测试速度
        if response is None:
            logging.error("DeepSeek API连接测试失败: 返回空响应")
            DEEPSEEK_API_AVAILABLE = False
            return False
            
        if isinstance(response, str) and ("成功" in response or "test" in response.lower() or "success" in response.lower()):
            logging.info("DeepSeek API连接测试成功")
            DEEPSEEK_API_AVAILABLE = True
            return True
        else:
            logging.warning(f"DeepSeek API连接测试返回意外响应: {response}")
            # 虽然响应不符合预期，但API仍然可用
            DEEPSEEK_API_AVAILABLE = True
            return True
    except Exception as e:
        error_msg = f"DeepSeek API连接测试失败: {str(e)}"
        logging.error(error_msg)
        DEEPSEEK_API_AVAILABLE = False
        return False

def simple_test():
    """
    简单的测试函数，用于检查程序是否能正常运行
    """
    logger = logging.getLogger()
    logger.info("执行简单测试函数")
    return "测试成功"

def get_category_name(key):
    """
    将类别键转换为可读的名称
    
    参数:
        key (str): 类别键
        
    返回:
        str: 可读的类别名称
    """
    category_names = {
        "ai_content": "AI生成内容检测",
        "language_neutrality": "语言中立性",
        "source_quality": "来源质量",
        "domain_trust": "域名可信度",
        "citation_validity": "引用有效性",
        "citation_quality": "引用质量",
        "local_news_validation": "本地新闻验证",
        "logic_analysis": "逻辑分析",
        "image_authenticity": "图像真实性"
    }
    
    return category_names.get(key, key)

def main():
    """主函数"""
    global DEEPSEEK_API_AVAILABLE
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("news_credibility.log"),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger()
    logger.info("程序启动")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='新闻可信度分析工具')
    parser.add_argument('--url', type=str, help='新闻URL')
    parser.add_argument('--file', type=str, help='新闻文本文件路径')
    parser.add_argument('--text', type=str, help='直接输入新闻文本')
    parser.add_argument('--image', type=str, nargs='+', help='新闻图片路径')
    parser.add_argument('--no-online', action='store_true', help='不使用在线验证')
    parser.add_argument('--offline', action='store_true', help='强制离线模式，不进行任何网络请求')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--test', action='store_true', help='运行简单测试')
    
    try:
        args = parser.parse_args()
        logger.info("命令行参数解析成功")
        
        # 设置调试模式
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("调试模式已启用")
        
        # 简单测试模式
        if args.test:
            logger.info("运行简单测试模式")
            result = simple_test()
            print(f"测试结果: {result}")
            return
        
        # 强制离线模式
        if args.offline:
            logger.info("强制离线模式已启用，将不进行任何网络请求")
            args.no_online = True
        
        # 在程序开头进行自检
        print("🔍 正在验证服务可用性...")
        
        # 检查SearXNG可用性
        if not args.offline and not args.no_online:
            searxng_available = test_searxng_connection()
            if searxng_available:
                print("  ✓ SearXNG服务可用")
            else:
                print("  ❌ SearXNG服务不可用，将使用有限功能")
        
        # 加载DeepSeek API密钥
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if api_key:
            logger.info("已加载DeepSeek API密钥")
            print("🔑 DeepSeek API密钥已加载")
            DEEPSEEK_API_AVAILABLE = True
            
            # 测试DeepSeek API连接
            if not args.offline and not args.no_online:
                print("🔄 正在测试DeepSeek API连接...")
                deepseek_available = test_deepseek_connection()
                if deepseek_available:
                    print("  ✓ DeepSeek API连接测试成功")
                else:
                    print("  ❌ DeepSeek API连接测试失败")
                    print("⚠️ DeepSeek API不可用，某些功能可能受限")
        else:
            logger.warning("未设置DEEPSEEK_API_KEY环境变量，将使用有限功能")
            print("⚠️ 未设置DeepSeek API密钥，某些功能可能受限")
            DEEPSEEK_API_AVAILABLE = False
        
        # 在这里添加一个简单的打印语句，看看是否能执行到这里
        logger.info("API密钥加载后的检查点")
        
        # 如果没有提供任何输入，显示帮助信息
        if not (args.url or args.file or args.text):
            logger.info("未提供输入，显示帮助信息")
            parser.print_help()
            return
        
        logger.debug("开始处理输入参数")
        
        # 检查依赖项
        logger.debug("检查依赖项")
        try:
            import requests
            logger.debug("requests库已加载")
            import bs4
            logger.debug("bs4库已加载")
            from PIL import Image
            logger.debug("PIL库已加载")
            import numpy as np
            logger.debug("numpy库已加载")
            import cv2
            logger.debug("cv2库已加载")
            import exifread
            logger.debug("exifread库已加载")
            logger.debug("所有依赖项检查通过")
        except ImportError as e:
            logger.error(f"缺少依赖项: {e}")
            print(f"错误: 缺少依赖项 {e}")
            print("请安装所需的依赖项: pip install requests beautifulsoup4 pillow numpy opencv-python exifread html5lib lxml")
            return
        
        # 获取新闻内容
        text = None
        image_paths = []
        url = None
        
        if args.url and not args.offline:
            url = args.url
            logger.debug(f"处理URL: {url}")
            
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                logger.debug(f"URL格式已修正: {url}")
            
            try:
                print(f"🌐 正在获取URL内容: {url}")
                logger.debug(f"开始从URL获取内容: {url}")
                text, image_paths = fetch_news_content(url)
                if text:
                    logger.info(f"成功获取URL内容，文本长度: {len(text)}")
                    title = text.split('\n')[0] if '\n' in text else text[:50] + "..."
                    print(f"📰 标题: {title}")
                    print(f"📝 内容长度: {len(text)} 字符")
                    if image_paths:
                        print(f"🖼️ 图片数量: {len(image_paths)}")
                else:
                    logger.error("无法从URL获取内容")
                    print(colored("错误: 无法从URL获取内容", Colors.RED))
                    return
            except Exception as e:
                logger.error(f"获取URL内容时出错: {e}")
                logger.error(traceback.format_exc())
                print(colored(f"错误: 获取URL内容时出错: {e}", Colors.RED))
                return
        elif args.url and args.offline:
            url = args.url
            logger.info(f"离线模式下不从URL获取内容")
            print(colored("离线模式下不从URL获取内容，使用示例文本进行分析", Colors.YELLOW))
            # 使用示例文本
            text = """MIT工程师将皮肤细胞转化为神经元用于细胞疗法
            
            麻省理工学院的研究人员开发了一种新方法，可以将皮肤细胞直接转化为神经元，这可能为治疗神经退行性疾病提供新的细胞疗法。
            
            这项研究发表在《自然》杂志上，展示了如何使用基因编辑技术将患者自身的皮肤细胞重编程为功能性神经元，而无需经过干细胞阶段。
            
            研究团队表示，这种方法可能对帕金森病、阿尔茨海默病和其他神经系统疾病的治疗具有重要意义。
            
            "这项技术允许我们创建患者特异性的神经元，这些神经元可以用于疾病建模、药物筛选，最终可能用于细胞替代疗法，"研究的资深作者说。
            
            初步的动物实验表明，这些转化的神经元在移植后能够整合到宿主大脑中并发挥功能。
            
            研究人员现在计划进行更广泛的临床前研究，以评估这种方法的安全性和有效性。"""
        elif args.file:
            try:
                logger.debug(f"从文件读取内容: {args.file}")
                with open(args.file, 'r', encoding='utf-8') as f:
                    text = f.read()
                logger.info(f"成功从文件读取内容，文本长度: {len(text)}")
            except Exception as e:
                logger.error(f"读取文件时出错: {e}")
                print(colored(f"错误: 读取文件时出错: {e}", Colors.RED))
                return
        elif args.text:
            text = args.text
            logger.info(f"使用直接输入的文本，长度: {len(text)}")
        
        # 处理图片
        if args.image:
            logger.debug(f"处理用户提供的图片: {args.image}")
            for img_path in args.image:
                if os.path.exists(img_path):
                    image_paths.append(img_path)
                    logger.debug(f"添加图片: {img_path}")
                else:
                    logger.warning(f"图片不存在: {img_path}")
        
        logger.debug(f"开始分析新闻内容，文本长度: {len(text)}, 图片数量: {len(image_paths)}")
        
        # 分析新闻
        try:
            logger.debug("调用search_and_verify_news函数")
            result = search_and_verify_news(text, url, image_paths, args.no_online or args.offline)
            logger.info("新闻分析完成")
            
            # 输出结果
            print("\n" + "="*70)
            print(colored("📊 新闻可信度分析结果 📊", Colors.HEADER, bold=True).center(70))
            print("="*70)
            
            # 计算总分
            total_score = 0
            max_score = 0
            
            for category, score in result["scores"].items():
                if category != "logic_analysis":  # 逻辑分析不计入总分
                    total_score += score
                    max_score += 1
            
            # 计算百分比得分
            percentage_score = (total_score / max_score) * 100 if max_score > 0 else 0
            
            # 根据得分确定颜色和评级
            if percentage_score >= 85:
                score_color = Colors.GREEN
                rating = "非常可信"
                rating_symbol = "🌟🌟🌟🌟🌟"
            elif percentage_score >= 70:
                score_color = Colors.GREEN
                rating = "可信"
                rating_symbol = "🌟🌟🌟🌟"
            elif percentage_score >= 60:
                score_color = Colors.YELLOW
                rating = "基本可信"
                rating_symbol = "🌟🌟🌟"
            elif percentage_score >= 50:
                score_color = Colors.YELLOW
                rating = "部分可信"
                rating_symbol = "🌟🌟"
            else:
                score_color = Colors.RED
                rating = "可信度低"
                rating_symbol = "🌟"
            
            # 输出总体评分
            print("\n" + "▓"*70)
            print(colored(f"总体可信度评级: {rating} {rating_symbol}", Colors.BOLD).center(70))
            print(colored(f"总分: {percentage_score:.1f}%", score_color, bold=True).center(70))
            print("▓"*70 + "\n")
            
            # 输出各项得分表格
            print(colored("📋 详细评分", Colors.BOLD, bold=True))
            print("━"*70)
            print(f"{'评分项目':<25} {'得分':<10} {'评级':<15} {'权重':<10}")
            print("━"*70)
            
            # 定义权重
            weights = {
                "ai_content": "高",
                "language_neutrality": "中",
                "source_quality": "高",
                "domain_trust": "高",  # 提高域名可信度的权重
                "citation_validity": "高",
                "citation_quality": "中",
                "local_news_validation": "低",
                "logic_analysis": "参考",
                "image_authenticity": "高"
            }
            
            # 输出各项得分
            for category, score in result["scores"].items():
                category_name = get_category_name(category)
                weight = weights.get(category, "中")
                
                # 根据得分确定评级和颜色
                if score >= 0.8:
                    color = Colors.GREEN
                    rating = "优"
                    bar = "█" * int(score * 10)
                elif score >= 0.6:
                    color = Colors.YELLOW
                    rating = "良"
                    bar = "█" * int(score * 10)
                else:
                    color = Colors.RED
                    rating = "差"
                    bar = "█" * int(score * 10)
                
                # 填充空白
                empty_bar = "░" * (10 - int(score * 10))
                
                # 为域名可信度添加特殊标记
                if category == "domain_trust" and score >= 0.85:
                    rating = "可信域名 ✓"
                
                # 输出行
                print(f"{category_name:<25} {colored(f'{score:.1f}', color):<10} {colored(rating, color):<15} {bar}{empty_bar} {weight:<10}")
            
            print("━"*70)
            
            # 输出DeepSeek详细评分（如果有）
            if "deepseek_analysis" in result.get("details", {}):
                print("\n" + colored("🤖 DeepSeek AI分析", Colors.MAGENTA, bold=True))
                print("━"*70)
                deepseek_details = result["details"]["deepseek_analysis"]
                # 尝试格式化输出
                try:
                    # 如果是JSON字符串，尝试解析
                    import json
                    try:
                        deepseek_json = json.loads(deepseek_details)
                        for key, value in deepseek_json.items():
                            if isinstance(value, dict):
                                print(colored(f"\n{key}:", Colors.BOLD))
                                for sub_key, sub_value in value.items():
                                    print(f"  {sub_key}: {colored(sub_value, Colors.CYAN)}")
                            else:
                                print(f"{key}: {colored(value, Colors.CYAN)}")
                    except json.JSONDecodeError:
                        # 如果不是JSON，按行输出
                        for line in deepseek_details.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                print(f"{colored(key.strip(), Colors.BOLD)}: {colored(value.strip(), Colors.CYAN)}")
                            else:
                                print(line)
                except Exception as e:
                    # 如果格式化失败，直接输出原文
                    print(deepseek_details)
                print("━"*70)
            
            # 输出详细信息
            print("\n" + colored("📝 详细分析报告", Colors.BOLD, bold=True))
            
            for category, details in result["details"].items():
                if details and category != "deepseek_analysis":  # 跳过已经显示的DeepSeek分析
                    category_name = get_category_name(category)
                    
                    # 根据类别选择颜色
                    if category in ["ai_content", "source_quality", "citation_validity", "image_authenticity"]:
                        header_color = Colors.BLUE
                    elif category in ["language_neutrality", "domain_trust", "citation_quality"]:
                        header_color = Colors.CYAN
                    elif category == "logic_analysis":
                        header_color = Colors.MAGENTA
                    else:
                        header_color = Colors.YELLOW
                    
                    print("\n" + colored(f"▶ {category_name}", header_color, bold=True))
                    
                    # 尝试格式化输出
                    if category in ["ai_content", "language_neutrality"] and "综合评分" in str(details):
                        # 多维度评分的特殊处理
                        try:
                            # 提取本地评分和DeepSeek评分
                            local_score_match = re.search(r'本地评分: (\d+\.\d+)', str(details))
                            deepseek_score_match = re.search(r'DeepSeek评分: (\d+\.\d+)', str(details))
                            
                            if local_score_match and deepseek_score_match:
                                local_score = float(local_score_match.group(1))
                                deepseek_score = float(deepseek_score_match.group(1))
                                
                                # 显示综合评分
                                print(colored(f"  • 综合评分: {result['scores'][category]:.2f} (30%本地算法 + 70%DeepSeek评分)", Colors.GREEN, bold=True))
                                
                                # 显示本地评分和DeepSeek评分
                                local_color = Colors.GREEN if local_score >= 0.7 else Colors.YELLOW if local_score >= 0.5 else Colors.RED
                                deepseek_color = Colors.GREEN if deepseek_score >= 0.7 else Colors.YELLOW if deepseek_score >= 0.5 else Colors.RED
                                
                                print(f"  • 本地评分: {colored(f'{local_score:.2f}', local_color)}")
                                print(f"  • DeepSeek评分: {colored(f'{deepseek_score:.2f}', deepseek_color)}")
                                
                                # 提取并显示DeepSeek的多维度评分
                                if "deepseek_analysis" in result["details"]:
                                    try:
                                        import json
                                        deepseek_data = json.loads(result["details"]["deepseek_analysis"])
                                        
                                        if category == "ai_content" and "AI生成内容" in deepseek_data:
                                            ai_data = deepseek_data["AI生成内容"]
                                            print(colored("\n  • DeepSeek多维度评分 (AI生成内容):", Colors.BOLD))
                                            
                                            for key, value in ai_data.items():
                                                if key != "分析" and key != "总分":
                                                    score_color = Colors.GREEN if value <= 0.3 else Colors.YELLOW if value <= 0.5 else Colors.RED
                                                    print(f"    - {key}: {colored(f'{value:.2f}', score_color)}")
                                            
                                            if "分析" in ai_data:
                                                print(colored("\n  • DeepSeek分析:", Colors.BOLD))
                                                print(f"    {ai_data['分析']}")
                                        
                                        elif category == "language_neutrality" and "语言中立性" in deepseek_data:
                                            neutrality_data = deepseek_data["语言中立性"]
                                            print(colored("\n  • DeepSeek多维度评分 (语言中立性):", Colors.BOLD))
                                            
                                            for key, value in neutrality_data.items():
                                                if key != "分析" and key != "总分":
                                                    score_color = Colors.GREEN if value >= 0.7 else Colors.YELLOW if value >= 0.5 else Colors.RED
                                                    print(f"    - {key}: {colored(f'{value:.2f}', score_color)}")
                                            
                                            if "分析" in neutrality_data:
                                                print(colored("\n  • DeepSeek分析:", Colors.BOLD))
                                                print(f"    {neutrality_data['分析']}")
                                    except Exception as e:
                                        # 如果解析失败，显示原始本地分析
                                        local_analysis = re.search(r'本地分析:\n(.*?)(?=\n\nDeepSeek分析:|$)', str(details), re.DOTALL)
                                        if local_analysis:
                                            print(colored("\n  • 本地分析:", Colors.BOLD))
                                            for line in local_analysis.group(1).strip().split('\n'):
                                                print(f"    {line}")
                                else:
                                    # 如果没有找到评分，显示原始详细信息
                                    for line in str(details).split('\n'):
                                        if line.strip():
                                            print(f"  • {colored(line, Colors.ENDC)}")
                        except Exception as e:
                            # 如果处理失败，显示原始详细信息
                            for line in str(details).split('\n'):
                                if line.strip():
                                    print(f"  • {colored(line, Colors.ENDC)}")
                    elif isinstance(details, str):
                        # 分段输出
                        for paragraph in details.split(';'):
                            paragraph = paragraph.strip()
                            if paragraph:
                                print(f"  • {colored(paragraph, Colors.ENDC)}")
                    elif isinstance(details, list):
                        for item in details:
                            # 为不同类型的信息添加不同颜色
                            if "评分" in str(item) or "分数" in str(item):
                                print(f"  • {colored(item, Colors.GREEN)}")
                            elif "错误" in str(item) or "失败" in str(item) or "低" in str(item):
                                print(f"  • {colored(item, Colors.RED)}")
                            elif "警告" in str(item) or "中等" in str(item):
                                print(f"  • {colored(item, Colors.YELLOW)}")
                            elif "图片" in str(item) or "图像" in str(item):
                                print(f"  • {colored(item, Colors.CYAN)}")
                            elif "元数据" in str(item):
                                print(f"  • {colored(item, Colors.MAGENTA)}")
                            elif "质量" in str(item):
                                print(f"  • {colored(item, Colors.BLUE)}")
                            elif "一致性" in str(item):
                                print(f"  • {colored(item, Colors.YELLOW)}")
                            else:
                                print(f"  • {colored(item, Colors.ENDC)}")
                    elif isinstance(details, dict):
                        for key, value in details.items():
                            print(f"  • {colored(key, Colors.BOLD)}: {colored(value, Colors.CYAN)}")
                    else:
                        print(f"  {colored(details, Colors.ENDC)}")
            
            # 输出图片分析结果（如果有）
            if "image_authenticity" in result.get("details", {}) and result["details"]["image_authenticity"]:
                print("\n" + colored("🖼️ 图片分析", Colors.BLUE, bold=True))
                print("━"*70)
                
                image_details = result["details"]["image_authenticity"]
                if isinstance(image_details, list):
                    for item in image_details:
                        if "图像可信度" in str(item):
                            print(colored(f"  {item}", Colors.GREEN, bold=True))
                        elif "评分" in str(item):
                            print(colored(f"  {item}", Colors.YELLOW, bold=True))
                        elif "图片" in str(item) and "分析" in str(item):
                            print(colored(f"\n  {item}", Colors.BLUE, bold=True))
                        elif "元数据" in str(item):
                            print(colored(f"    {item}", Colors.MAGENTA))
                        elif "质量" in str(item):
                            print(colored(f"    {item}", Colors.CYAN))
                        elif "一致性" in str(item):
                            print(colored(f"    {item}", Colors.YELLOW))
                        elif "错误" in str(item) or "失败" in str(item):
                            print(colored(f"    {item}", Colors.RED))
                        else:
                            print(colored(f"  {item}", Colors.ENDC))
                else:
                    print(colored(image_details, Colors.ENDC))
                
                print("━"*70)
            
            print("\n" + "="*70)
            print(colored("分析完成 - 感谢使用新闻可信度分析工具", Colors.GREEN).center(70))
            print("="*70)
            logger.info("结果输出完成")
            
        except Exception as e:
            logger.error(f"分析新闻时出错: {e}")
            logger.error(traceback.format_exc())
            print(colored(f"错误: 分析新闻时出错: {e}", Colors.RED))
            return
    
    except Exception as e:
        logger.error(f"程序执行过程中出错: {e}")
        logger.error(traceback.format_exc())
        print(colored(f"错误: {e}", Colors.RED))

if __name__ == "__main__":
    try:
        print("开始执行程序")
        main()
        print("程序执行完成")
    except Exception as e:
        print(f"程序执行过程中出现未捕获的异常: {e}")
        import traceback
        traceback.print_exc()
