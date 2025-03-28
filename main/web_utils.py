#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import logging
import time
import random
import json
import os
import re
import traceback
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import tempfile
from fake_useragent import UserAgent
import chardet
import urllib.parse
from PIL import Image, ImageStat
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# 导入本地模块
from utils import Colors, colored

logger = logging.getLogger(__name__)

def get_text_from_url(url, max_retries=3, backoff_factor=0.5):
    """
    从URL获取文本内容
    
    参数:
        url: 网页URL
        max_retries: 最大重试次数
        backoff_factor: 重试延迟因子
    
    返回:
        (文本内容, 图片URL列表)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        logger.info(f"正在获取URL内容: {url}")
        
        # 创建定制的会话，禁用证书验证警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 使用会话对象进行重试
        session = requests.Session()
        
        # 创建重试适配器
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # 定制重试策略，增加对SSL错误的重试
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 添加重试循环以处理SSLError
        for attempt in range(max_retries + 1):
            try:
                response = session.get(
                    url, 
                    headers=headers, 
                    timeout=15,  # 增加超时时间
                    verify=False  # 禁用SSL证书验证
                )
                response.raise_for_status()
                break  # 如果成功获取响应，跳出循环
            except requests.exceptions.SSLError as ssl_err:
                if attempt < max_retries:
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"SSL错误，等待 {wait_time:.2f} 秒后重试 ({attempt + 1}/{max_retries}): {ssl_err}")
                    time.sleep(wait_time)
                else:
                    # 最后一次尝试，再次失败后抛出异常
                    logger.error(f"所有SSL重试尝试均失败: {ssl_err}")
                    raise
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
                if attempt < max_retries:
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"连接错误，等待 {wait_time:.2f} 秒后重试 ({attempt + 1}/{max_retries}): {conn_err}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"所有连接重试尝试均失败: {conn_err}")
                    raise
            except Exception as e:
                logger.error(f"请求过程中发生错误: {e}")
                raise
        
        # 尝试其他方法获取内容
        if 'response' not in locals():
            logger.warning("所有请求尝试均失败，尝试使用其他方法...")
            
            # 可以在这里添加其他获取网页内容的方法
            # 例如使用Selenium或其他HTTP客户端
            
            return None, []
        
        # 检测编码
        if response.encoding == 'ISO-8859-1':
            # 尝试从内容中检测编码
            encodings = re.findall(r'charset=["\']?([\w-]+)', response.text)
            if encodings:
                response.encoding = encodings[0]
            else:
                # 尝试自动检测编码
                detected = chardet.detect(response.content)
                response.encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除脚本和样式元素
        for script in soup(["script", "style"]):
            script.extract()
        
        # 获取标题
        title = soup.title.string if soup.title else ""
        
        # 获取正文内容
        # 尝试找到主要内容区域
        main_content = None
        
        # 常见的内容容器ID和类名
        content_selectors = [
            'article', '.article', '#article', '.post', '#post', '.content', '#content',
            '.main', '#main', '.body', '#body', '.entry', '#entry', '.text', '#text',
            'main', '[role="main"]', '.story', '#story', '.story-body', '.story-content'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # 选择最长的内容块
                main_content = max(elements, key=lambda x: len(x.get_text()))
                break
        
        # 如果没有找到主要内容区域，使用整个body
        if not main_content:
            main_content = soup.body
        
        # 提取文本
        text = title + "\n\n" + main_content.get_text(separator='\n', strip=True)
        
        # 清理文本
        text = re.sub(r'\n{3,}', '\n\n', text)  # 删除多余的空行
        text = re.sub(r'\s{2,}', ' ', text)     # 删除多余的空格
        
        # 提取图片URL
        image_urls = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                # 转换为绝对URL
                abs_url = urljoin(url, src)
                image_urls.append(abs_url)
        
        logger.info(f"成功获取URL内容，文本长度: {len(text)}，图片数量: {len(image_urls)}")
        return text, image_urls
    
    except Exception as e:
        logger.error(f"获取URL内容时出错: {e}")
        logger.error(traceback.format_exc())
        return None, []

def search_with_searxng(query, max_attempts=3, use_local=True):
    """
    使用SearXNG搜索引擎进行搜索
    
    参数:
        query: 搜索查询
        max_attempts: 最大尝试次数
        use_local: 是否使用本地SearXNG实例
    
    返回:
        搜索结果列表
    """
    # 本地SearXNG实例URL
    local_searxng_url = "http://localhost:8080/search"
    
    # 公共SearXNG实例列表
    public_searxng_instances = [
        "https://searx.be/search",
        "https://search.mdosch.de/search",
        "https://search.unlocked.link/search",
        "https://search.ononoki.org/search",
        "https://searx.tiekoetter.com/search"
    ]
    
    # 随机选择一个公共实例
    if not use_local:
        searxng_url = random.choice(public_searxng_instances)
        logger.info(f"使用公共SearXNG实例: {searxng_url}")
    else:
        searxng_url = local_searxng_url
        logger.info(f"使用本地SearXNG实例: {searxng_url}")
    
    logger.info(f"搜索查询: '{query}'")
    
    # 基本请求参数
    params = {
        'q': query,
        'format': 'json',
        'categories': 'general',
        'language': 'zh-CN',
        'time_range': '',
        'safesearch': '0',
        'engines': 'google,duckduckgo,bing,brave,qwant,startpage,wikidata,wikipedia'
    }
    
    logger.debug(f"完整请求URL: {searxng_url}?{urllib.parse.urlencode(params)}")
    
    # 本地实例简化版请求
    if use_local:
        for attempt in range(max_attempts):
            try:
                logger.info(f"SearXNG搜索尝试 {attempt+1}/{max_attempts}: {query}")
                
                # 使用简单的 GET 请求访问本地实例
                response = requests.get(
                    searxng_url,
                    params=params,
                    timeout=30
                )
                
                logger.debug(f"SearXNG响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        results = response.json()
                        results_count = len(results.get('results', []))
                        logger.info(f"SearXNG搜索成功，找到 {results_count} 个结果")
                        return results
                    except Exception as e:
                        logger.error(f"解析SearXNG响应时出错: {e}")
                        # 继续尝试下一个
                else:
                    logger.error(f"SearXNG搜索失败，状态码: {response.status_code}")
                    logger.error(f"响应内容: {response.text[:500]}...")
            except Exception as e:
                logger.error(f"SearXNG搜索出错: {e}")
                logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 等待后重试
            wait_time = 2 * (attempt + 1)
            logger.info(f"等待 {wait_time} 秒后重试")
            time.sleep(wait_time)
    
    # 使用公共实例
    try:
        # 使用随机 User-Agent
        ua = UserAgent()
        random_ua = ua.random
        
        headers = {
            'User-Agent': random_ua,
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': searxng_url.split('/search')[0],
            'Referer': searxng_url.split('/search')[0]
        }
        
        # 对公共实例使用 POST 请求
        response = requests.post(
            searxng_url,
            data=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            try:
                results = response.json()
                results_count = len(results.get('results', []))
                logger.info(f"公共SearXNG搜索成功，找到 {results_count} 个结果")
                return results
            except Exception as e:
                logger.error(f"解析公共SearXNG响应时出错: {e}")
        else:
            logger.error(f"公共SearXNG搜索失败，状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"公共SearXNG搜索出错: {e}")
        logger.error(f"错误详情: {traceback.format_exc()}")
    
    logger.error("所有SearXNG搜索尝试均失败")
    return {"results": []}

def verify_citation_with_searxng(citation_text):
    """
    使用SearXNG验证引用内容
    
    参数:
        citation_text: 引用文本
    
    返回:
        (验证结果, 相似度分数, 详细信息)
    """
    # 清理引用文本
    clean_text = re.sub(r'\s+', ' ', citation_text).strip()
    
    # 如果文本太短，不进行验证
    if len(clean_text) < 10:
        return False, 0, "引用文本太短，无法进行有效验证"
    
    # 如果文本太长，截取前100个字符进行搜索
    search_text = clean_text[:100] if len(clean_text) > 100 else clean_text
    
    try:
        # 使用SearXNG搜索
        logger.info(f"使用SearXNG验证引用: {search_text}")
        search_results = search_with_searxng(f'"{search_text}"')
        
        if not search_results or 'results' not in search_results or not search_results['results']:
            logger.warning("SearXNG搜索未返回结果")
            return False, 0, "未找到相关搜索结果"
        
        # 分析搜索结果
        found_matches = []
        total_score = 0
        
        for result in search_results['results'][:5]:  # 只分析前5个结果
            result_title = result.get('title', '')
            result_content = result.get('content', '')
            
            # 计算相似度
            from utils import find_common_substrings
            common_substrings = find_common_substrings(clean_text, result_title + " " + result_content)
            
            if common_substrings:
                # 计算最长公共子串占原文本的比例
                longest_substring = common_substrings[0]
                similarity = len(longest_substring) / len(clean_text)
                
                found_matches.append({
                    'title': result_title,
                    'url': result.get('url', ''),
                    'similarity': similarity,
                    'common_text': longest_substring
                })
                
                total_score += similarity
        
        # 计算平均相似度分数
        avg_score = total_score / len(found_matches) if found_matches else 0
        
        # 根据相似度判断验证结果
        if avg_score > 0.5:
            return True, avg_score, f"引用内容在 {len(found_matches)} 个搜索结果中找到高度相似内容"
        elif avg_score > 0.3:
            return True, avg_score, f"引用内容在 {len(found_matches)} 个搜索结果中找到部分相似内容"
        elif found_matches:
            return False, avg_score, f"引用内容在搜索结果中仅找到少量相似内容"
        else:
            return False, 0, "未在搜索结果中找到相似内容"
    
    except Exception as e:
        logger.error(f"验证引用时出错: {e}")
        logger.error(traceback.format_exc())
        return False, 0, f"验证过程出错: {str(e)}"

def test_searxng_connection():
    """
    测试SearXNG连接
    
    返回:
        连接是否成功
    """
    try:
        logger.info("测试SearXNG连接")
        results = search_with_searxng("test connection", max_attempts=1)
        if results and 'results' in results and results['results']:
            logger.info("SearXNG连接测试成功")
            return True
        else:
            logger.warning("SearXNG连接测试失败：未返回结果")
            return False
    except Exception as e:
        logger.error(f"SearXNG连接测试失败: {e}")
        return False

def analyze_search_results(results, query):
    """
    分析搜索结果
    
    参数:
        results: 搜索结果
        query: 搜索查询
    
    返回:
        分析结果
    """
    if not results or 'results' not in results or not results['results']:
        return {
            'found': False,
            'count': 0,
            'sources': [],
            'analysis': "未找到相关搜索结果"
        }
    
    search_results = results['results']
    sources = []
    
    for result in search_results[:10]:  # 只分析前10个结果
        source = {
            'title': result.get('title', ''),
            'url': result.get('url', ''),
            'content': result.get('content', ''),
            'engine': result.get('engine', '')
        }
        sources.append(source)
    
    # 分析结果
    analysis = f"找到 {len(search_results)} 个相关结果"
    
    return {
        'found': True,
        'count': len(search_results),
        'sources': sources,
        'analysis': analysis
    }

def evaluate_domain_trust(url):
    """
    评估域名可信度
    
    参数:
        url: 网站URL
    
    返回:
        (可信度评分, 评估详情)
    """
    if not url:
        return 0.5, "未提供URL，无法评估域名可信度"
    
    try:
        # 解析URL获取域名
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        if not domain:
            return 0.5, "无效的URL格式，无法提取域名"
        
        # 移除www前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        
        logger.info(f"评估域名可信度: {domain}")
        
        # 高可信度域名列表
        high_trust_domains = [
            # 国际主流新闻机构
            'nytimes.com', 'washingtonpost.com', 'wsj.com', 'economist.com', 
            'bbc.co.uk', 'bbc.com', 'reuters.com', 'apnews.com', 'bloomberg.com',
            'ft.com', 'cnn.com', 'nbcnews.com', 'abcnews.go.com', 'cbsnews.com',
            'theguardian.com', 'independent.co.uk', 'time.com', 'npr.org',
            
            # 中文主流新闻机构
            'people.com.cn', 'xinhuanet.com', 'chinadaily.com.cn', 'cctv.com',
            'china.org.cn', 'gmw.cn', 'huanqiu.com', 'ce.cn', 'cnr.cn',
            'thepaper.cn', 'bjnews.com.cn', 'yicai.com', 'caixin.com',
            
            # 科学和学术网站
            'nature.com', 'science.org', 'sciencedirect.com', 'springer.com',
            'wiley.com', 'ieee.org', 'acm.org', 'nih.gov', 'who.int',
            'edu.cn', 'ac.cn', 'cas.cn',
            
            # 政府网站
            'gov.cn', 'gov', 'mil', 'edu', 'org.cn'
        ]
        
        # 中等可信度域名列表
        medium_trust_domains = [
            # 其他新闻和媒体网站
            'forbes.com', 'businessinsider.com', 'theatlantic.com', 'vox.com',
            'slate.com', 'vice.com', 'huffpost.com', 'buzzfeed.com',
            'ifeng.com', 'sina.com.cn', 'sohu.com', 'qq.com', '163.com',
            
            # 百科和知识网站
            'wikipedia.org', 'britannica.com', 'baike.baidu.com',
            
            # 社交媒体（有一定内容审核）
            'medium.com', 'substack.com', 'zhihu.com', 'douban.com'
        ]
        
        # 低可信度域名特征
        low_trust_patterns = [
            r'[\d]{3,}news', r'[\d]{3,}info', r'news[\d]{3,}', r'info[\d]{3,}',
            r'breaking[\d]{3,}', r'daily[\d]{3,}', r'[\d]{3,}daily',
            r'truth[\d]{3,}', r'real[\d]{3,}', r'[\d]{3,}truth', r'[\d]{3,}real'
        ]
        
        # 检查是否为高可信度域名
        for trusted_domain in high_trust_domains:
            if domain.endswith(trusted_domain):
                return 0.9, f"域名 {domain} 属于高可信度域名"
        
        # 检查是否为中等可信度域名
        for medium_domain in medium_trust_domains:
            if domain.endswith(medium_domain):
                return 0.7, f"域名 {domain} 属于中等可信度域名"
        
        # 检查是否匹配低可信度模式
        for pattern in low_trust_patterns:
            if re.search(pattern, domain):
                return 0.3, f"域名 {domain} 匹配低可信度模式"
        
        # 检查域名年龄和其他因素（这里简化处理）
        # 实际应用中可以查询WHOIS数据库获取域名注册时间
        
        # 默认返回中等偏低可信度
        return 0.5, f"域名 {domain} 未在已知可信或不可信列表中，给予中等评分"
    
    except Exception as e:
        logger.error(f"评估域名可信度时出错: {e}")
        return 0.5, f"评估域名可信度时出错: {str(e)}"

def fetch_news_content(url):
    """
    获取新闻内容
    
    参数:
        url: 新闻URL
    
    返回:
        (新闻文本, 图片路径列表)
    """
    try:
        # 获取文本和图片URL
        text, image_urls = get_text_from_url(url)
        
        if not text:
            logger.error(f"无法从URL获取内容: {url}")
            return None, []
        
        # 下载图片
        image_paths = []
        if image_urls:
            logger.info(f"开始筛选和下载图片，共找到 {len(image_urls)} 张图片")
            
            # 创建临时目录
            temp_dir = os.path.join(os.getcwd(), "temp_images")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 创建会话对象用于下载
            session = requests.Session()
            retry_strategy = Retry(
                total=3,  # 最大重试次数
                backoff_factor=0.5,  # 重试等待时间因子
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # 筛选和下载图片，最多9张
            downloaded_count = 0
            for i, img_url in enumerate(image_urls):
                if downloaded_count >= 9:  # 最多下载9张图片
                    break
                    
                try:
                    # 预先检查图片是否有效
                    for attempt in range(3):  # 最多重试3次
                        try:
                            img_response = session.get(
                                img_url,
                                timeout=10,
                                verify=False,  # 禁用SSL验证
                                stream=True,
                                headers={
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                                }
                            )
                            img_response.raise_for_status()
                            break  # 如果成功就跳出重试循环
                        except requests.exceptions.SSLError as ssl_err:
                            if attempt < 2:  # 最后一次尝试就不等待了
                                wait_time = 0.5 * (2 ** attempt)
                                logger.warning(f"下载图片时遇到SSL错误，等待 {wait_time:.2f} 秒后重试: {ssl_err}")
                                time.sleep(wait_time)
                            else:
                                raise  # 最后一次尝试失败，抛出异常
                    
                    # 检查内容类型
                    content_type = img_response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        logger.info(f"跳过非图片内容: {img_url}, 类型: {content_type}")
                        continue
                    
                    # 检查图片大小
                    content_length = int(img_response.headers.get('Content-Length', 0))
                    if content_length < 5 * 1024:  # 小于5KB的图片可能是图标或无意义图片
                        logger.info(f"跳过过小图片: {img_url}, 大小: {content_length/1024:.2f}KB")
                        continue
                    
                    # 生成唯一文件名
                    file_ext = os.path.splitext(img_url.split('?')[0])[1]
                    if not file_ext or len(file_ext) > 5:
                        file_ext = '.jpg'  # 默认扩展名
                    
                    file_name = f"img_{int(time.time())}_{i}{file_ext}"
                    file_path = os.path.join(temp_dir, file_name)
                    
                    # 下载图片
                    logger.info(f"下载图片: {img_url} -> {file_path}")
                    
                    # 保存图片
                    with open(file_path, 'wb') as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    # 检查图片是否为纯色或无意义图片
                    try:
                        img = Image.open(file_path)
                        
                        # 检查图片尺寸
                        width, height = img.size
                        if width < 100 or height < 100:
                            logger.info(f"跳过尺寸过小的图片: {file_path}, 尺寸: {width}x{height}")
                            os.remove(file_path)
                            continue
                        
                        # 检查是否为纯色图片
                        if img.mode == 'RGB':
                            stat = ImageStat.Stat(img)
                            # 计算每个通道的标准差，如果都很小，可能是纯色图片
                            r_std, g_std, b_std = stat.stddev
                            if r_std < 10 and g_std < 10 and b_std < 10:
                                logger.info(f"跳过纯色图片: {file_path}")
                                os.remove(file_path)
                                continue
                    except Exception as e:
                        logger.warning(f"检查图片质量时出错: {e}, 仍然保留图片")
                    
                    image_paths.append(file_path)
                    downloaded_count += 1
                    logger.info(f"图片下载成功: {file_path} ({downloaded_count}/9)")
                
                except Exception as e:
                    logger.error(f"下载图片时出错: {e}")
                    continue
        
        return text, image_paths
    
    except Exception as e:
        logger.error(f"获取新闻内容时出错: {e}")
        logger.error(traceback.format_exc())
        return None, []

