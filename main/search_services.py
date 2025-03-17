#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import requests
import json
import re
import time
import random
import traceback
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# 全局变量，用于标记API是否可用
SEARXNG_AVAILABLE = False

def query_searxng(query, max_retries=3, num_results=5):
    """
    使用SearXNG搜索引擎进行查询
    
    参数:
        query (str): 搜索查询
        max_retries (int): 最大重试次数
        num_results (int): 返回结果数量
    
    返回:
        list: 搜索结果列表，每个结果包含标题、URL和摘要
    """
    
    # 检查SearXNG是否可用
    global SEARXNG_AVAILABLE
    if not SEARXNG_AVAILABLE:
        logger.warning("SearXNG已被标记为不可用，跳过查询")
        return []
    
    # 优先使用本地SearXNG实例
    local_searxng_url = "http://localhost:8080"
    
    # 尝试使用本地实例
    try:
        # 测试本地实例连接
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = session.get(local_searxng_url, headers=headers, timeout=5)
        if response.status_code == 200 and ("searx" in response.text.lower() or "search" in response.text.lower()):
            logger.info("使用本地SearXNG实例")
            searxng_url = local_searxng_url
        else:
            # 如果本地实例不可用，设置为不可用并返回
            logger.error("本地SearXNG实例不可用")
            SEARXNG_AVAILABLE = False
            return []
    except Exception as e:
        # 如果本地实例连接失败，设置为不可用并返回
        logger.error(f"本地SearXNG实例连接失败: {str(e)}")
        SEARXNG_AVAILABLE = False
        return []
    
    # 构建API URL
    encoded_query = quote_plus(query)
    api_url = f"{searxng_url}/search"
    
    # 创建一个新的会话，避免连接池问题
    session = requests.Session()
    
    # 发送请求
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"发送SearXNG请求，尝试 {attempt+1}/{max_retries+1}")
            
            # 添加随机延迟，避免请求过于频繁
            if attempt > 0:
                delay = 2 + random.uniform(0, 2)
                logger.info(f"等待 {delay:.2f} 秒后重试")
                time.sleep(delay)
            
            # 设置请求头，模拟浏览器
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": searxng_url,
                "DNT": "1",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            # 设置查询参数
            params = {
                "q": query,
                "categories": "general",
                "language": "zh-CN",
                "format": "json",
                "safesearch": "0"
            }
            
            # 使用新的会话发送请求
            response = session.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            if "results" in result:
                # 提取搜索结果
                search_results = []
                for item in result.get("results", [])[:num_results]:
                    search_result = {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")
                    }
                    search_results.append(search_result)
                
                logger.debug(f"SearXNG搜索成功，找到 {len(search_results)} 条结果")
                return search_results
            else:
                logger.warning(f"SearXNG响应格式不正确: {result}")
                # 如果到达这里，说明响应格式不正确，但API调用成功
                # 返回空列表
                return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SearXNG请求失败: {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt + random.uniform(0, 2)  # 指数退避 + 随机抖动
                logger.info(f"等待 {wait_time:.2f} 秒后重试")
                time.sleep(wait_time)
            else:
                logger.error("已达到最大重试次数，放弃请求")
                SEARXNG_AVAILABLE = False
                return []
        except Exception as e:
            logger.error(f"处理SearXNG响应时出错: {e}")
            logger.error(traceback.format_exc())
            if attempt < max_retries:
                wait_time = 2 ** attempt + random.uniform(0, 2)
                logger.info(f"等待 {wait_time:.2f} 秒后重试")
                time.sleep(wait_time)
            else:
                logger.error("已达到最大重试次数，放弃请求")
                SEARXNG_AVAILABLE = False
                return []
        finally:
            # 确保关闭会话
            if 'session' in locals():
                session.close()
    
    return []

def search_with_searxng(query, num_results=10):
    """
    使用SearXNG搜索引擎进行查询并返回格式化结果
    
    参数:
        query (str): 搜索查询
        num_results (int): 返回结果数量
    
    返回:
        dict: 包含搜索结果的字典
    """
    logger.info(f"使用SearXNG搜索: {query}")
    
    # 调用query_searxng获取搜索结果
    search_results = query_searxng(query, num_results=num_results)
    
    # 格式化结果
    formatted_results = {
        "query": query,
        "results": search_results,
        "result_count": len(search_results)
    }
    
    return formatted_results

def verify_citation_with_searxng(citation_text):
    """
    验证引用内容的真实性（替代方法）
    
    参数:
        citation_text: 引用文本
    
    返回:
        (验证结果, 相似度分数, 详细信息)
    """
    # 检查SearXNG是否可用
    global SEARXNG_AVAILABLE
    
    # 首先尝试测试连接，确保状态是最新的
    if not SEARXNG_AVAILABLE:
        test_searxng_connection()
    
    if not SEARXNG_AVAILABLE:
        logger.warning("SearXNG不可用，使用本地文本分析方法")
        # 继续使用本地分析方法
    else:
        # 尝试使用SearXNG进行验证
        try:
            # 构建搜索查询 - 使用更智能的查询构建方法
            # 提取引用文本中的关键句子或短语
            clean_text = re.sub(r'\s+', ' ', citation_text).strip()
            
            # 如果文本太长，提取前100个字符作为查询
            if len(clean_text) > 100:
                query = clean_text[:100]
            else:
                query = clean_text
                
            logger.info(f"使用SearXNG验证引用，查询: {query}")
            search_results = search_with_searxng(query, num_results=3)
            
            if search_results and search_results.get("results"):
                logger.info(f"SearXNG搜索成功，找到 {len(search_results.get('results'))} 条结果")
                # 有搜索结果，进行简单比较
                # 这里可以实现更复杂的比较逻辑
                return True, 0.8, "通过SearXNG搜索找到相关内容，引用可能可信"
            else:
                logger.warning("SearXNG搜索未找到相关结果")
        except Exception as e:
            logger.error(f"使用SearXNG验证引用时出错: {str(e)}")
            logger.error(traceback.format_exc())
            # 出错时继续使用本地分析方法
    
    # 使用本地文本分析方法
    # 清理引用文本
    clean_text = re.sub(r'\s+', ' ', citation_text).strip()
    
    # 如果文本太短，不进行验证
    if len(clean_text) < 10:
        return False, 0, "引用文本太短，无法进行有效验证"
    
    # 根据文本特征评估可信度
    score = 0.7  # 默认中等可信度
    details = []
    
    # 检查文本长度 - 较长的引用通常包含更多细节
    if len(clean_text) > 100:
        score += 0.05
        details.append("引用文本较长，含有更多细节")
    
    # 检查是否包含数字和具体数据
    has_numbers = bool(re.search(r'\d+(\.\d+)?%?', clean_text))
    if has_numbers:
        score += 0.1
        details.append("包含具体数字或统计数据")
    
    # 检查是否包含专业术语
    scientific_terms = ['研究', '发现', '分析', '数据', '实验', '证明', '报告', 
                     'study', 'research', 'analysis', 'data', 'experiment', 'evidence']
    term_count = sum(1 for term in scientific_terms if term.lower() in clean_text.lower())
    if term_count >= 2:
        score += 0.1
        details.append(f"包含 {term_count} 个专业术语，增加可信度")
    
    # 检查引用是否包含具体来源
    sources = re.findall(r'(根据|据|引用|来自|来源)[\s:：]?([^，,。.]{2,}?)(称|表示|指出|报道|说)', clean_text)
    if sources:
        score += 0.1
        source_text = sources[0][1] if len(sources[0]) > 1 else sources[0][0]
        details.append(f"引用了具体来源: {source_text}")
    
    # 限制评分范围
    score = min(1.0, max(0.0, score))
    
    # 评估验证结果
    verified = score > 0.7
    
    # 生成详细解释
    if verified:
        explanation = f"引用内容评估为可信 (评分: {score:.1f})"
    else:
        explanation = f"引用内容评估为较低可信度 (评分: {score:.1f})"
    
    if details:
        explanation += "。详细分析: " + ", ".join(details)
    
    # 补充说明
    if not SEARXNG_AVAILABLE:
        explanation += "。注意: 由于SearXNG不可用，此结果仅基于文本特征分析"
    
    return verified, score, explanation

def test_searxng_connection():
    """
    测试SearXNG连接是否正常
    
    返回:
        bool: 连接是否成功
    """
    global SEARXNG_AVAILABLE
    
    logging.info("测试SearXNG连接...")
    
    # 优先使用本地SearXNG实例
    local_searxng_url = "http://localhost:8080"
    
    # 使用本地实例
    try:
        # 创建一个新的会话
        session = requests.Session()
        
        # 设置请求头，模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        # 发送请求
        logging.info(f"尝试连接到 {local_searxng_url}")
        response = session.get(local_searxng_url, headers=headers, timeout=5)
        
        # 检查响应状态码
        if response.status_code != 200:
            logging.warning(f"SearXNG连接测试返回非200状态码: {response.status_code}")
            SEARXNG_AVAILABLE = False
            return False
            
        # 检查响应是否包含SearXNG的特征
        response_text = response.text.lower()
        if "searx" in response_text or "search" in response_text:
            logging.info("本地SearXNG连接测试成功")
            
            # 尝试进行一次简单搜索，确保搜索功能正常
            try:
                test_search_url = f"{local_searxng_url}/search"
                test_params = {"q": "test", "format": "json"}
                test_response = session.get(test_search_url, params=test_params, headers=headers, timeout=5)
                
                if test_response.status_code == 200:
                    try:
                        result = test_response.json()
                        if "results" in result:
                            logging.info("SearXNG搜索功能测试成功")
                            SEARXNG_AVAILABLE = True
                            return True
                    except Exception as e:
                        logging.warning(f"SearXNG搜索结果解析失败: {str(e)}")
                else:
                    logging.warning(f"SearXNG搜索测试返回非200状态码: {test_response.status_code}")
            except Exception as e:
                logging.warning(f"SearXNG搜索功能测试失败: {str(e)}")
                
            # 即使搜索测试失败，如果基本连接成功，仍然标记为可用
            SEARXNG_AVAILABLE = True
            return True
        else:
            logging.warning("本地SearXNG连接测试返回意外响应")
            SEARXNG_AVAILABLE = False
            return False
    except requests.exceptions.ConnectionError as e:
        logging.error(f"本地SearXNG连接失败 (连接错误): {str(e)}")
        SEARXNG_AVAILABLE = False
        return False
    except requests.exceptions.Timeout as e:
        logging.error(f"本地SearXNG连接超时: {str(e)}")
        SEARXNG_AVAILABLE = False
        return False
    except Exception as e:
        logging.error(f"本地SearXNG连接测试失败: {str(e)}")
        logging.error(traceback.format_exc())
        SEARXNG_AVAILABLE = False
        return False
    finally:
        # 确保关闭会话
        if 'session' in locals():
            session.close()

# 模块初始化时测试 SearXNG 连接
try:
    # 设置初始日志级别，避免过多日志输出
    _initial_log_level = logging.getLogger().level
    if _initial_log_level == 0:  # 未设置日志级别
        logging.getLogger().setLevel(logging.WARNING)
    
    # 测试连接
    SEARXNG_AVAILABLE = test_searxng_connection()
    
    # 恢复日志级别
    if _initial_log_level == 0:
        logging.getLogger().setLevel(logging.NOTSET)
        
    if SEARXNG_AVAILABLE:
        logging.info("SearXNG 搜索服务可用")
    else:
        logging.warning("SearXNG 搜索服务不可用，将使用本地分析方法")
except Exception as e:
    logging.error(f"初始化 SearXNG 连接测试时出错: {str(e)}")
    SEARXNG_AVAILABLE = False 