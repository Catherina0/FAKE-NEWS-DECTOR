#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import traceback
import os
import json
import argparse
import sys
from typing import Dict, List, Tuple, Any, Optional, Union
from pathlib import Path

# 确保在程序开始时加载.env文件
from dotenv import load_dotenv
load_dotenv()

# 初始化logger
logger = logging.getLogger(__name__)

# 导入本地模块
from text_analysis import (
    check_ai_content,
    analyze_language_neutrality,
    analyze_source_quality,
    analyze_text_logic,
    local_news_validation
)

from citation_analysis import (
    judge_citation_truthfulness,
    get_citation_score
)

from ai_services import (
    analyze_with_deepseek_v3,
    test_deepseek_connection,
    query_deepseek,
    DEEPSEEK_API_AVAILABLE
)

from search_services import (
    verify_citation_with_searxng,
    test_searxng_connection,
    search_with_searxng,
    SEARXNG_AVAILABLE
)

from web_utils import (
    get_text_from_url,
    fetch_news_content,
    evaluate_domain_trust
)

from validation import (
    perform_cross_validation,
    extract_verification_points_with_deepseek,
    verify_search_results_with_deepseek
)

from image_analysis import (
    check_images,
    analyze_image_authenticity
)

from service_checker import (
    initialize_services,
    print_service_status
)

from result_formatter import (
    print_formatted_result,
    get_credibility_summary,
    get_rating_emoji,
    get_progress_bar,
    get_credibility_rating
)

from config import (
    DEFAULT_WEIGHTS,
    DEEPSEEK_WEIGHTS,
    SEPARATE_ANALYSIS,
    setup_python_path
)

from utils import setup_logging
from test_utils import simple_test
from core_analyzer import analyze_news_credibility, save_news_to_local

# 添加项目根目录到Python路径
setup_python_path()

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='新闻可信度分析工具',
        epilog='''
命令组合示例:
  基本分析:    python main.py --url https://example.com/news/article
  快速分析:    python main.py --url https://example.com/news/article --quick
  保存新闻:    python main.py --url https://example.com/news/article --save
  完整分析并保存: python main.py --url https://example.com/news/article --save --save-dir my_news
  不使用AI服务:  python main.py --url https://example.com/news/article --no-ai
  调试模式:    python main.py --url https://example.com/news/article --debug --verbose
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--url', help='新闻URL')
    parser.add_argument('--text', help='新闻文本')
    parser.add_argument('--file', help='包含新闻文本的文件路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--verbose', action='store_true', help='启用详细日志模式')
    parser.add_argument('--log-file', default='news_credibility.log', help='日志文件路径')
    parser.add_argument('--no-ai', action='store_true', help='禁用AI服务')
    parser.add_argument('--no-online', action='store_true', help='禁用在线验证')
    parser.add_argument('--test', action='store_true', help='运行功能测试')
    parser.add_argument('--test-deepseek', action='store_true', help='测试DeepSeek API连接')
    parser.add_argument('--quick', action='store_true', help='快速模式，跳过DeepSeek API分析')
    parser.add_argument('--save', action='store_true', help='保存新闻到本地文件夹')
    parser.add_argument('--save-dir', default='saved_news', help='保存新闻的文件夹路径')
    parser.add_argument('--language', '--lang', default='zh', choices=['zh', 'en'], help='输出语言 (zh: 中文, en: 英文)')
    return parser.parse_args()

def main():
    """主程序入口"""
    args = parse_arguments()
    
    # 如果禁用AI服务，设置环境变量
    if args.no_ai:
        os.environ['DISABLE_AI'] = 'true'
    
    # 配置日志级别
    debug_mode = args.debug
    verbose_mode = args.verbose or args.debug
    
    # 使用utils.py中的setup_logging函数
    logger = setup_logging(log_file=args.log_file, debug=debug_mode, verbose=verbose_mode)
    
    # 打印启动信息
    logger.info("新闻可信度分析工具启动")
    logger.info(f"调试模式: {'启用' if debug_mode else '禁用'}")
    logger.info(f"详细日志: {'启用' if verbose_mode else '禁用'}")
    logger.info(f"AI服务: {'禁用' if args.no_ai else '启用'}")
    logger.info(f"快速模式: {'启用' if args.quick else '禁用'}")
    
    # 如果是测试模式，执行简单测试并退出
    if args.test:
        simple_test()
        sys.exit(0)
    
    # 如果是测试DeepSeek API连接模式，执行测试并退出
    if args.test_deepseek:
        result = test_deepseek_connection()
        if result:
            print("DeepSeek API连接测试成功！✅")
        else:
            print("DeepSeek API连接测试失败！❌")
        sys.exit(0)
    
    # 初始化服务并显示服务状态
    services_status = initialize_services()
    print_service_status(services_status)
    
    # 获取分析文本
    analysis_text = None
    image_paths = []  # 初始化图片路径列表
    
    if args.url:
        url = args.url
        logger.info(f"正在获取URL内容: {url}")
        
        # 使用标准方法获取URL内容
        text = get_text_from_url(url)
            
        if not text:
            logger.error(f"无法从URL获取内容: {url}")
            logger.error("请检查URL是否正确，网站是否可访问，或者网站是否禁止爬虫")
            print(f"错误: 无法从URL获取内容: {url}")
            print("可能的原因:")
            print("1. URL不正确或网站无法访问")
            print("2. 网站禁止爬虫或需要特殊处理")
            print("3. 网络连接问题")
            print("\n尝试使用默认测试文本继续...")
            
            # 使用默认测试文本作为备选
            text = """
            【测试新闻】近日，某知名科技公司宣布开发出能在5分钟内充满电的新型电池技术。
            该技术据称使用了一种特殊的石墨烯材料，可以大幅提高电池充电速度。
            公司首席科学家李某表示:"这项技术将彻底改变电动汽车行业。"
            然而，专家对此持谨慎态度，有分析认为该技术在大规模生产前还需要解决安全性问题。
            """
            logger.info("使用默认测试文本代替无法获取的URL内容")
        
        analysis_text = text
        # 获取图片
        _, image_paths = fetch_news_content(url)
    elif args.text:
        analysis_text = args.text
        logger.info("使用提供的文本进行分析")
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                analysis_text = f.read()
            logger.info(f"从文件读取内容: {args.file}")
        except Exception as e:
            logger.error(f"读取文件时出错: {e}")
            print(f"错误: 无法读取文件: {e}")
            sys.exit(1)
    else:
        # 使用默认测试文本
        analysis_text = """
        据可靠消息来源报道，科学家们最近发现了一种新型材料，可以显著提高太阳能电池的效率。
        这种材料由石墨烯和钙钛矿复合而成，在实验室条件下，能够将太阳能转化效率提高至32%，
        远高于目前市场上20-25%的平均水平。研究负责人张教授表示："这一突破可能彻底改变
        可再生能源行业。"多位行业专家对此表示认可，但也指出从实验室到商业化还有很长的路要走。
        """
        print("未提供内容来源，使用默认测试文本")
    
    # 分析新闻可信度
    result = analyze_news_credibility(
        text=analysis_text,
        url=args.url if args.url else None,
        use_ai_services=not (args.no_ai or args.quick),  # 快速模式下也跳过AI服务
        use_online=not args.no_online  # 是否使用在线验证
    )
    
    # 使用格式化打印功能
    print_formatted_result(result, language=args.language)

    # 如果用户指定了保存新闻，调用save_news_to_local函数
    if args.save:
        if save_news_to_local(analysis_text, args.url, result, args.save_dir, image_paths):
            if args.language == 'zh':
                print(f"\n新闻已保存到文件夹: {os.path.abspath(args.save_dir)}")
            else:
                print(f"\nNews saved to folder: {os.path.abspath(args.save_dir)}")
        else:
            if args.language == 'zh':
                print("\n保存新闻失败，请查看日志了解详情。")
            else:
                print("\nFailed to save news, please check the logs for details.")

if __name__ == "__main__":
    main()
