#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置和环境变量模块
包含程序所需的所有配置、常量和环境变量设置
"""

import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv


# 尝试导入colorama，如果失败则提供备用方案
try:
    from colorama import Fore, Style
    colorama_available = True
except ImportError:
    # 尝试使用pip安装colorama
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama"])
        from colorama import Fore, Style
        colorama_available = True
    except:
        # 如果安装失败，定义空的Fore和Style类
        colorama_available = False
        class Fore:
            RED = ''
            GREEN = ''
            YELLOW = ''
            BLUE = ''
            MAGENTA = ''
            CYAN = ''
            WHITE = ''
            RESET = ''
        class Style:
            BRIGHT = ''
            NORMAL = ''
            RESET_ALL = ''

# 确保在程序开始时加载.env文件
print("正在加载.env文件...")
dotenv_path = Path('.env')
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"找到并加载.env文件: {dotenv_path}")
else:
    print("警告: 未找到.env文件，将使用环境变量或默认值")

# API密钥和配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
print(f"DEEPSEEK_API_KEY设置状态: {'已设置' if DEEPSEEK_API_KEY else '未设置'}")

# DeepSeek API URL
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

# 检查两种可能的SearXNG环境变量名称
SEARXNG_URL = os.getenv("SEARXNG_URL", os.getenv("SEARXNG_INSTANCE", "http://localhost:8080"))
SEARXNG_AVAILABLE = False  # 默认设置为False，后续会检查
DEEPSEEK_API_AVAILABLE = bool(DEEPSEEK_API_KEY)  # 如果API密钥已设置，则认为API可用

# 是否允许使用公共SearXNG实例（当本地实例不可用时）
USE_PUBLIC_SEARXNG = os.getenv("USE_PUBLIC_SEARXNG", "false").lower() in ["true", "1", "yes", "y"]

# 初始化logger
logger = logging.getLogger(__name__)

# 权重配置
DEFAULT_WEIGHTS = {
    "ai_content": 0.15,        # AI生成内容检测（本地+DeepSeek）
    "language_neutrality": 0.2, # 语言中立性分析
    "source_citation_quality": 0.2, # 来源和引用质量分析
    "deepseek_analysis": 0.3,   # DeepSeek综合分析
    "cross_validation": 0.15    # 交叉验证
}

# 当DeepSeek可用时的权重配置
DEEPSEEK_WEIGHTS = {
    "local_algorithm": 0.2,    # 本地算法权重
    "deepseek_algorithm": 0.8  # DeepSeek算法权重
}

# 不计入可信度评分的分析项目
SEPARATE_ANALYSIS = {
    "text_logic": 0.5,         # 文本逻辑性（占新闻价值分析的50%）
    "news_value": 0.5          # 新闻价值（占新闻价值分析的50%）
}

# 添加项目根目录到Python路径
def setup_python_path():
    project_root = Path(__file__).parent.absolute()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# 颜色定义 - 对格式化输出有用
if colorama_available:
    TITLE_COLOR = Fore.CYAN + Style.BRIGHT
    HEADER_COLOR = Fore.MAGENTA + Style.BRIGHT 
    SUBHEADER_COLOR = Fore.BLUE + Style.BRIGHT
    SECTION_COLOR = Fore.BLUE + Style.BRIGHT
    DETAIL_COLOR = Fore.WHITE + Style.BRIGHT
    TEXT_COLOR = Fore.WHITE
    WARNING_COLOR = Fore.YELLOW + Style.BRIGHT
    ERROR_COLOR = Fore.RED + Style.BRIGHT
    SUCCESS_COLOR = Fore.GREEN + Style.BRIGHT
    INFO_COLOR = Fore.CYAN
    NEUTRAL_COLOR = Fore.WHITE
    RESET_COLOR = Style.RESET_ALL
else:
    TITLE_COLOR = ""
    HEADER_COLOR = ""
    SUBHEADER_COLOR = ""
    SECTION_COLOR = ""
    DETAIL_COLOR = ""
    TEXT_COLOR = ""
    WARNING_COLOR = ""
    ERROR_COLOR = ""
    SUCCESS_COLOR = ""
    INFO_COLOR = ""
    NEUTRAL_COLOR = ""
    RESET_COLOR = ""

# 设置日志
def setup_logging(log_file="news_credibility.log", debug=False, verbose=False):
    """设置日志级别和格式"""
    from utils import setup_logging as utils_setup_logging
    return utils_setup_logging(log_file=log_file, debug=debug, verbose=verbose)

# 初始化
setup_python_path() 