#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import json
import sys
from typing import Dict, Any, Optional

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
from verification import local_text_credibility
from image_analysis import check_images
from utils import colored, Colors

logger = logging.getLogger(__name__)

def simple_test():
    """
    运行一个简单的功能测试，验证各个模块是否正常工作
    """
    logger.info("开始执行简单功能测试...")
    
    # 测试文本
    test_text = """
    据可靠消息来源报道，科学家们最近发现了一种新型材料，可以显著提高太阳能电池的效率。
    这种材料由石墨烯和钙钛矿复合而成，在实验室条件下，能够将太阳能转化效率提高至32%，
    远高于目前市场上20-25%的平均水平。研究负责人张教授表示："这一突破可能彻底改变
    可再生能源行业。"多位行业专家对此表示认可，但也指出从实验室到商业化还有很长的路要走。
    """
    
    print(colored("\n===== 功能测试开始 =====", Colors.HEADER, bold=True))
    
    # 1. 测试文本分析功能
    print(colored("\n>> 测试文本分析功能", Colors.BLUE, bold=True))
    
    try:
        print("- 检测AI生成内容...")
        ai_score, ai_details = check_ai_content(test_text)
        print(f"  结果: AI内容检测评分 = {ai_score:.2f}")
        
        print("- 分析语言中立性...")
        neutral_score, neutral_details = analyze_language_neutrality(test_text)
        print(f"  结果: 语言中立性评分 = {neutral_score:.2f}")
        
        print("- 分析来源质量...")
        source_score, source_details = analyze_source_quality(test_text)
        print(f"  结果: 来源质量评分 = {source_score:.2f}")
        
        print("- 分析文本逻辑性...")
        logic_score, logic_details = analyze_text_logic(test_text)
        print(f"  结果: 文本逻辑性评分 = {logic_score:.2f}")
        
        print("- 本地新闻验证...")
        local_score, local_details = local_news_validation(test_text)
        print(f"  结果: 本地新闻验证评分 = {local_score:.2f}")
        
        print(colored("  文本分析功能测试通过", Colors.GREEN))
    except Exception as e:
        print(colored(f"  文本分析功能测试失败: {e}", Colors.RED))
    
    # 2. 测试引用分析功能
    print(colored("\n>> 测试引用分析功能", Colors.BLUE, bold=True))
    
    try:
        print("- 判断引用真实性...")
        citation_truth = judge_citation_truthfulness(test_text)
        print(f"  结果: 引用真实性评分 = {citation_truth['score'] if isinstance(citation_truth, dict) and 'score' in citation_truth else citation_truth[0]:.2f}")
        
        print("- 获取引用质量评分...")
        citation_score, citation_details = get_citation_score(test_text)
        print(f"  结果: 引用质量总评分 = {citation_score:.2f}")
        print(f"  详情: {str(citation_details)[:100]}...")
        
        print(colored("  引用分析功能测试通过", Colors.GREEN))
    except Exception as e:
        print(colored(f"  引用分析功能测试失败: {e}", Colors.RED))
    
    # 3. 测试本地可信度评估
    print(colored("\n>> 测试本地可信度评估", Colors.BLUE, bold=True))
    
    try:
        print("- 执行本地文本可信度评估...")
        credibility_score, credibility_details = local_text_credibility(test_text)
        print(f"  结果: 本地可信度评分 = {credibility_score:.2f}")
        
        print(colored("  本地可信度评估测试通过", Colors.GREEN))
    except Exception as e:
        print(colored(f"  本地可信度评估测试失败: {e}", Colors.RED))
    
    # 4. 打印总结
    print(colored("\n===== 功能测试完成 =====", Colors.HEADER, bold=True))
    print("所有功能模块测试已完成。")
    
    return True

# 如果直接运行此模块，执行简单测试
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    simple_test() 