#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback
from datetime import datetime

# 定义彩色日志格式化器
class ColoredFormatter(logging.Formatter):
    """
    自定义的彩色日志格式化器
    """
    COLORS = {
        'DEBUG': '\033[94m',  # 蓝色
        'INFO': '\033[0m',    # 默认
        'WARNING': '\033[93m', # 黄色
        'ERROR': '\033[91m',   # 红色
        'CRITICAL': '\033[91m\033[1m'  # 红色加粗
    }
    
    RESET = '\033[0m'
    
    def format(self, record):
        log_message = super().format(record)
        levelname = record.levelname
        if levelname in self.COLORS:
            log_message = f"{self.COLORS[levelname]}{log_message}{self.RESET}"
        return log_message

# 配置日志
def setup_logging(log_file="news_credibility.log", debug=False, verbose=False):
    """
    设置日志配置
    
    参数:
        log_file: 日志文件路径
        debug: 是否开启调试模式
        verbose: 是否开启详细日志模式
    
    返回:
        logging.Logger: 日志记录器实例
    """
    # 设置根日志级别
    root_level = logging.DEBUG if debug else logging.INFO
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(root_level)
    console_formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # 文件中始终记录所有日志
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 为web_utils和ai_services模块设置更详细的日志级别
    if verbose:
        for module in ['news_credibility.web_utils', 'news_credibility.ai_services', 'web_utils', 'ai_services']:
            module_logger = logging.getLogger(module)
            module_logger.setLevel(logging.DEBUG)
    
    # 输出启动消息
    logger = logging.getLogger(__name__)
    logger.debug("日志系统初始化完成")
    return logger

# 颜色类
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
    if bold:
        return f"{color}{Colors.BOLD}{text}{Colors.ENDC}"
    return f"{color}{text}{Colors.ENDC}"

def get_category_name(key):
    """获取分类名称"""
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

def load_environment_variables():
    """加载环境变量"""
    try:
        from dotenv import load_dotenv
        load_dotenv()  # 从.env文件加载环境变量
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if api_key:
            logging.info("已加载DeepSeek API密钥")
            return True
        else:
            logging.warning("未设置DEEPSEEK_API_KEY环境变量")
            return False
    except ImportError:
        logging.warning("未安装python-dotenv库，无法从.env文件加载环境变量")
        return False

def find_common_substrings(str1, str2, min_length=5, max_time=2, max_substrings=10):
    """
    查找两个字符串之间的共同子串
    
    参数:
        str1: 第一个字符串
        str2: 第二个字符串
        min_length: 最小子串长度
        max_time: 最大执行时间（秒）
        max_substrings: 最大返回子串数量
    
    返回:
        共同子串列表，按长度降序排序
    """
    if not str1 or not str2:
        return []
    
    start_time = datetime.now()
    common_substrings = []
    
    # 转换为小写以进行不区分大小写的比较
    str1_lower = str1.lower()
    str2_lower = str2.lower()
    
    # 动态规划方法查找所有公共子串
    len1, len2 = len(str1_lower), len(str2_lower)
    dp = [[0 for _ in range(len2 + 1)] for _ in range(len1 + 1)]
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            # 检查是否超时
            if (datetime.now() - start_time).total_seconds() > max_time:
                logging.warning(f"查找公共子串超时，返回已找到的 {len(common_substrings)} 个结果")
                # 按长度排序并返回前N个
                return sorted(common_substrings, key=len, reverse=True)[:max_substrings]
            
            if str1_lower[i-1] == str2_lower[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                if dp[i][j] >= min_length:
                    # 找到一个长度至少为min_length的公共子串
                    end = i
                    start = end - dp[i][j]
                    substring = str1[start:end]
                    
                    # 检查是否已经包含在现有子串中
                    is_contained = False
                    for existing in common_substrings:
                        if substring in existing:
                            is_contained = True
                            break
                    
                    if not is_contained:
                        common_substrings.append(substring)
    
    # 按长度排序并返回前N个
    return sorted(common_substrings, key=len, reverse=True)[:max_substrings] 