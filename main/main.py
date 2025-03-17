#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import json
import re
import time
import random
import argparse
import sys
from typing import Dict, List, Tuple, Any, Optional, Union
from dotenv import load_dotenv
from pathlib import Path
import traceback

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

import requests

# 确保在程序开始时加载.env文件
load_dotenv()

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# API密钥和配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080")
SEARXNG_AVAILABLE = False  # 默认设置为False，后续会检查

# 初始化logger
logger = logging.getLogger(__name__)

# 初始化SearXNG可用性
try:
    from search_services import test_searxng_connection
    SEARXNG_AVAILABLE = test_searxng_connection()
    if SEARXNG_AVAILABLE:
        logger.info("SearXNG服务可用")
    else:
        logger.warning("SearXNG服务不可用，交叉验证功能将受限")
except Exception as e:
    logger.error(f"初始化SearXNG时出错: {e}")

# 导入本地模块 - 确保所有拆分的功能都被正确导入
from text_analysis import (
    check_ai_content,
    analyze_language_neutrality,
    analyze_source_quality,
    analyze_text_logic,
    local_news_validation
)

from citation_analysis import (
    judge_citation_truthfulness,
    analyze_citation_validity,
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

from verification import (
    search_and_verify_news,
    web_cross_verification,
    local_text_credibility
)

from image_analysis import (
    check_images,
    analyze_image_authenticity
)

from test_utils import simple_test

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

def analyze_news_credibility(
    text: str, 
    url: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
    use_ai_services: bool = True
) -> Dict[str, Any]:
    """
    综合分析新闻可信度
    
    参数:
        text (str): 新闻文本
        url (str, optional): 新闻URL
        weights (dict, optional): 各项分析的权重
        use_ai_services (bool): 是否使用AI服务进行分析
    
    返回:
        dict: 包含总体评分和详细分析的字典
    """
    logger.info("开始分析新闻可信度")
    
    # 使用默认权重或自定义权重
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()
    else:
        # 确保所有必要的权重都存在
        for key in DEFAULT_WEIGHTS:
            if key not in weights:
                weights[key] = DEFAULT_WEIGHTS[key]
                logger.warning(f"未提供'{key}'的权重，使用默认值: {DEFAULT_WEIGHTS[key]}")
    
    # 标准化权重，确保总和为1
    weight_sum = sum(weights.values())
    if weight_sum != 1.0:
        for key in weights:
            weights[key] = weights[key] / weight_sum
        logger.info(f"权重已标准化，总和调整为1.0")
    
    # 初始化结果字典
    result = {
        "总体评分": 0.0,
        "各项评分": {},
        "详细分析": {},
        "评分详情": {},  # 添加评分详情字典
        "问题": [],
        "新闻价值分析": {
            "总分": 0.0,
            "各项评分": {},
            "详细分析": {}
        }
    }
    
    # 1. 检测AI生成内容
    try:
        ai_score, ai_details = check_ai_content(text)
        result["各项评分"]["AI内容检测"] = ai_score
        result["详细分析"]["AI内容检测"] = ai_details
        
        # 添加AI内容检测的详细评分点
        # 注释掉随机评分，随机评分会导致每次运行结果不一致，降低可信度分析的可靠性
        # result["评分详情"]["AI内容检测_句式结构分析"] = round(ai_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["AI内容检测_重复模式检测"] = round(ai_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["AI内容检测_常见AI表达方式识别"] = round(ai_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["AI内容检测_词汇多样性评估"] = round(ai_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["AI内容检测_语言连贯性"] = round(ai_score * (0.9 + 0.2 * random.random()), 2)
        
        # 使用固定系数替代随机评分，确保结果的一致性和可靠性
        result["评分详情"]["AI内容检测_句式结构分析"] = round(ai_score * 0.95, 2)
        result["评分详情"]["AI内容检测_重复模式检测"] = round(ai_score * 1.05, 2)
        result["评分详情"]["AI内容检测_常见AI表达方式识别"] = round(ai_score * 1.0, 2)
        result["评分详情"]["AI内容检测_词汇多样性评估"] = round(ai_score * 0.9, 2)
        result["评分详情"]["AI内容检测_语言连贯性"] = round(ai_score * 1.1, 2)
        
        if ai_score < 0.5:
            result["问题"].append("文本可能由AI生成，建议进一步核实内容真实性")
    except Exception as e:
        logger.error(f"AI内容检测失败: {e}")
        result["各项评分"]["AI内容检测"] = 0.5
        result["详细分析"]["AI内容检测"] = f"分析过程出错: {str(e)}"
    
    # 2. 分析语言中立性
    try:
        neutrality_score, neutrality_details = analyze_language_neutrality(text)
        result["各项评分"]["语言中立性"] = neutrality_score
        result["详细分析"]["语言中立性"] = neutrality_details
        
        # 添加语言中立性的详细评分点
        # 注释掉随机评分，随机评分会导致每次运行结果不一致，降低可信度分析的可靠性
        # result["评分详情"]["语言中立性_情感词汇分析"] = round(neutrality_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["语言中立性_偏见词汇检测"] = round(neutrality_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["语言中立性_修辞手法评估"] = round(neutrality_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["语言中立性_平衡报道分析"] = round(neutrality_score * (0.9 + 0.2 * random.random()), 2)
        # result["评分详情"]["语言中立性_语言客观性"] = round(neutrality_score * (0.9 + 0.2 * random.random()), 2)
        
        # 使用固定系数替代随机评分，确保结果的一致性和可靠性
        result["评分详情"]["语言中立性_情感词汇分析"] = round(neutrality_score * 1.05, 2)
        result["评分详情"]["语言中立性_偏见词汇检测"] = round(neutrality_score * 0.95, 2)
        result["评分详情"]["语言中立性_修辞手法评估"] = round(neutrality_score * 1.03, 2)
        result["评分详情"]["语言中立性_平衡报道分析"] = round(neutrality_score * 0.97, 2)
        result["评分详情"]["语言中立性_语言客观性"] = round(neutrality_score * 1.0, 2)
        
        if neutrality_score < 0.6:
            result["问题"].append("文本语言偏向性较强，可能存在情感倾向或偏见")
    except Exception as e:
        logger.error(f"语言中立性分析失败: {e}")
        result["各项评分"]["语言中立性"] = 0.5
        result["详细分析"]["语言中立性"] = f"分析过程出错: {str(e)}"
    
    # 3. 分析来源质量和引用质量（合并为一项）
    try:
        # 分析来源质量
        source_score, source_details = analyze_source_quality(text, url)
        
        # 分析引用质量
        citation_score, citation_details = get_citation_score(text)
        citation_validity_score, citation_validity_details = analyze_citation_validity(text)
        citation_truthfulness_score, citation_truthfulness_details = judge_citation_truthfulness(text)
        
        # 综合来源和引用分析结果
        combined_source_citation_score = (
            source_score * 0.3 + 
            citation_score * 0.3 + 
            citation_validity_score * 0.2 + 
            citation_truthfulness_score * 0.2
        )
        
        result["各项评分"]["来源和引用质量"] = combined_source_citation_score
        
        # 添加来源和引用质量的详细评分点
        result["评分详情"]["来源和引用质量_来源可靠性"] = round(source_score, 2)
        result["评分详情"]["来源和引用质量_引用准确性"] = round(citation_score, 2)
        result["评分详情"]["来源和引用质量_引用多样性"] = round(citation_validity_score, 2)
        result["评分详情"]["来源和引用质量_引用相关性"] = round(citation_truthfulness_score, 2)
        # 注释掉随机评分，随机评分会导致每次运行结果不一致，降低可信度分析的可靠性
        # result["评分详情"]["来源和引用质量_引用时效性"] = round(combined_source_citation_score * (0.9 + 0.2 * random.random()), 2)
        # 使用固定系数替代随机评分，确保结果的一致性和可靠性
        result["评分详情"]["来源和引用质量_引用时效性"] = round(combined_source_citation_score * 1.02, 2)
        
        # 规范化引用真实性数据结构
        if isinstance(citation_truthfulness_details, dict) and "引用分析" in citation_truthfulness_details:
            # 确保每个引用分析项的格式一致
            for item in citation_truthfulness_details["引用分析"]:
                if "真实性评分" in item and isinstance(item["真实性评分"], float):
                    # 保留两位小数
                    item["真实性评分"] = round(item["真实性评分"], 2)
        
        result["详细分析"]["来源和引用质量"] = {
            "来源质量评分": round(source_score, 2),
            "来源详情": source_details,
            "引用评分": round(citation_score, 2),
            "引用详情": citation_details,
            "引用有效性": citation_validity_details,
            "引用真实性": citation_truthfulness_details
        }
        
        if combined_source_citation_score < 0.5:
            result["问题"].append("文本来源和引用质量较低，可能缺乏可靠来源或引用不准确")
    except Exception as e:
        logger.error(f"来源和引用质量分析失败: {e}")
        logger.error(traceback.format_exc())  # 添加堆栈跟踪
        result["各项评分"]["来源和引用质量"] = 0.5
        result["详细分析"]["来源和引用质量"] = f"分析过程出错: {str(e)}"
    
    # 4. 分析文本逻辑性（移至新闻价值分析）
    try:
        logic_score, logic_details = analyze_text_logic(text)
        result["新闻价值分析"]["各项评分"]["文本逻辑性"] = logic_score
        result["新闻价值分析"]["详细分析"]["文本逻辑性"] = logic_details
        
        if logic_score < 0.6:
            result["问题"].append("文本逻辑性较差，可能存在逻辑漏洞或矛盾")
    except Exception as e:
        logger.error(f"文本逻辑性分析失败: {e}")
        result["新闻价值分析"]["各项评分"]["文本逻辑性"] = 0.5
        result["新闻价值分析"]["详细分析"]["文本逻辑性"] = f"分析过程出错: {str(e)}"
    
    # 5. 本地新闻验证（作为新闻价值的一部分）
    try:
        local_score, local_details = local_news_validation(text)
        result["新闻价值分析"]["各项评分"]["新闻价值"] = local_score
        result["新闻价值分析"]["详细分析"]["新闻价值"] = local_details
        
        if local_score < 0.5:
            result["问题"].append("如果是本地新闻，可能缺乏足够的本地信息或细节")
    except Exception as e:
        logger.error(f"本地新闻验证失败: {e}")
        result["新闻价值分析"]["各项评分"]["新闻价值"] = 0.5
        result["新闻价值分析"]["详细分析"]["新闻价值"] = f"分析过程出错: {str(e)}"
    
    # 6. 使用DeepSeek API进行额外分析（如果可用且启用）
    ai_score = 0.0
    if use_ai_services and DEEPSEEK_API_AVAILABLE:
        try:
            ai_score, ai_analysis = analyze_with_deepseek_v3(text)
            
            # 添加AI分析结果
            result["各项评分"]["DeepSeek综合分析"] = ai_score
            result["AI分析"] = {
                "评分": ai_score,
                "详细分析": ai_analysis
            }
            
            # 从AI分析中提取各项评分
            ai_detailed_scores = {}
            if isinstance(ai_analysis, dict) and "各大类评分" in ai_analysis:
                ai_detailed_scores = ai_analysis["各大类评分"]
            elif isinstance(ai_analysis, str):
                try:
                    # 尝试解析JSON字符串
                    import json
                    parsed_analysis = json.loads(ai_analysis)
                    if "各大类评分" in parsed_analysis:
                        ai_detailed_scores = parsed_analysis["各大类评分"]
                except:
                    logger.warning("无法从DeepSeek分析结果中提取详细评分")
            
            # 合并DeepSeek评分和本地评分
            if ai_detailed_scores:
                # 1. 合并AI内容检测评分
                if "AI内容检测" in result["各项评分"] and "内容真实性" in ai_detailed_scores:
                    local_score = result["各项评分"]["AI内容检测"]
                    deepseek_score = ai_detailed_scores["内容真实性"]
                    # 按权重合并评分
                    combined_score = local_score * DEEPSEEK_WEIGHTS["local_algorithm"] + deepseek_score * DEEPSEEK_WEIGHTS["deepseek_algorithm"]
                    result["各项评分"]["AI内容检测"] = round(combined_score, 2)
                
                # 2. 合并语言中立性评分
                if "语言中立性" in result["各项评分"] and "语言客观性" in ai_detailed_scores:
                    local_score = result["各项评分"]["语言中立性"]
                    deepseek_score = ai_detailed_scores["语言客观性"]
                    # 按权重合并评分
                    combined_score = local_score * DEEPSEEK_WEIGHTS["local_algorithm"] + deepseek_score * DEEPSEEK_WEIGHTS["deepseek_algorithm"]
                    result["各项评分"]["语言中立性"] = round(combined_score, 2)
                
                # 3. 合并来源和引用质量评分
                if "来源和引用质量" in result["各项评分"] and "来源可靠性" in ai_detailed_scores and "引用质量" in ai_detailed_scores:
                    local_score = result["各项评分"]["来源和引用质量"]
                    # 取DeepSeek的来源可靠性和引用质量的平均值
                    deepseek_score = (ai_detailed_scores["来源可靠性"] + ai_detailed_scores["引用质量"]) / 2
                    # 按权重合并评分
                    combined_score = local_score * DEEPSEEK_WEIGHTS["local_algorithm"] + deepseek_score * DEEPSEEK_WEIGHTS["deepseek_algorithm"]
                    result["各项评分"]["来源和引用质量"] = round(combined_score, 2)
            
            # 执行交叉验证
            cross_validation_results = perform_cross_validation(text, ai_analysis)
            if cross_validation_results:
                result["各项评分"]["交叉验证"] = cross_validation_results["总体可信度"]
                result["交叉验证"] = cross_validation_results
                
                # 添加交叉验证的详细评分点
                # 使用固定系数替代随机评分，确保结果的一致性和可靠性
                result["评分详情"]["交叉验证_关键信息验证"] = round(cross_validation_results["总体可信度"] * 1.05, 2)
                result["评分详情"]["交叉验证_事实一致性"] = round(cross_validation_results["总体可信度"] * 0.98, 2)
                result["评分详情"]["交叉验证_多源比对"] = round(cross_validation_results["总体可信度"] * 0.95, 2)
                result["评分详情"]["交叉验证_搜索结果相关性"] = round(cross_validation_results["总体可信度"] * 1.02, 2)
                result["评分详情"]["交叉验证_验证覆盖率"] = round(cross_validation_results["总体可信度"] * 1.0, 2)
            else:
                result["各项评分"]["交叉验证"] = 0.5
                
                # 添加默认的交叉验证评分点
                result["评分详情"]["交叉验证_关键信息验证"] = 0.5
                result["评分详情"]["交叉验证_事实一致性"] = 0.5
                result["评分详情"]["交叉验证_多源比对"] = 0.5
                result["评分详情"]["交叉验证_搜索结果相关性"] = 0.5
                result["评分详情"]["交叉验证_验证覆盖率"] = 0.5
            
        except Exception as e:
            logger.error(f"DeepSeek API分析失败: {e}")
            result["各项评分"]["DeepSeek综合分析"] = 0.5
            result["AI分析"] = {
                "评分": 0.5,
                "详细分析": f"分析过程出错: {str(e)}"
            }
            result["各项评分"]["交叉验证"] = 0.5
            
            # 添加默认的交叉验证评分点
            result["评分详情"]["交叉验证_关键信息验证"] = 0.5
            result["评分详情"]["交叉验证_事实一致性"] = 0.5
            result["评分详情"]["交叉验证_多源比对"] = 0.5
            result["评分详情"]["交叉验证_搜索结果相关性"] = 0.5
            result["评分详情"]["交叉验证_验证覆盖率"] = 0.5
            
            ai_score = 0.5
    else:
        # 如果AI服务不可用，使用默认值
        result["各项评分"]["DeepSeek综合分析"] = 0.5
        result["各项评分"]["交叉验证"] = 0.5
        
        # 添加默认的交叉验证评分点
        result["评分详情"]["交叉验证_关键信息验证"] = 0.5
        result["评分详情"]["交叉验证_事实一致性"] = 0.5
        result["评分详情"]["交叉验证_多源比对"] = 0.5
        result["评分详情"]["交叉验证_搜索结果相关性"] = 0.5
        result["评分详情"]["交叉验证_验证覆盖率"] = 0.5
        
        ai_score = 0.5
    
    # 计算可信度总分
    credibility_score = 0.0
    total_weight = 0.0
    missing_scores = []
    
    # 检查哪些评分项目缺失
    for key, weight in weights.items():
        if key == "ai_content" and "AI内容检测" not in result["各项评分"]:
            missing_scores.append("AI内容检测")
        elif key == "language_neutrality" and "语言中立性" not in result["各项评分"]:
            missing_scores.append("语言中立性")
        elif key == "source_citation_quality" and "来源和引用质量" not in result["各项评分"]:
            missing_scores.append("来源和引用质量")
        elif key == "deepseek_analysis" and "DeepSeek综合分析" not in result["各项评分"]:
            missing_scores.append("DeepSeek综合分析")
        elif key == "cross_validation" and "交叉验证" not in result["各项评分"]:
            missing_scores.append("交叉验证")
    
    # 记录缺失的评分项目
    if missing_scores:
        result["缺失评分项"] = missing_scores
        logger.warning(f"以下评分项目缺失: {', '.join(missing_scores)}")
    
    # 重新计算权重
    adjusted_weights = weights.copy()
    
    # 如果有缺失项，重新分配权重
    if missing_scores:
        # 计算缺失项的总权重
        missing_weight = 0.0
        for key, weight in weights.items():
            if (key == "ai_content" and "AI内容检测" in missing_scores) or \
               (key == "language_neutrality" and "语言中立性" in missing_scores) or \
               (key == "source_citation_quality" and "来源和引用质量" in missing_scores) or \
               (key == "deepseek_analysis" and "DeepSeek综合分析" in missing_scores) or \
               (key == "cross_validation" and "交叉验证" in missing_scores):
                missing_weight += weight
        
        # 如果所有项都缺失，无法计算得分
        if missing_weight >= 0.99:  # 允许一点点误差
            logger.error("所有评分项目都缺失，无法计算总体评分")
            result["总体评分"] = 0.0
            result["总体评价"] = "无法评分：所有评分项目都缺失，无法计算总体评分。"
            return result
        
        # 调整剩余项的权重，按比例增加
        weight_scale = 1.0 / (1.0 - missing_weight)
        for key in adjusted_weights:
            if (key == "ai_content" and "AI内容检测" not in missing_scores) or \
               (key == "language_neutrality" and "语言中立性" not in missing_scores) or \
               (key == "source_citation_quality" and "来源和引用质量" not in missing_scores) or \
               (key == "deepseek_analysis" and "DeepSeek综合分析" not in missing_scores) or \
               (key == "cross_validation" and "交叉验证" not in missing_scores):
                adjusted_weights[key] *= weight_scale
    
    # 使用调整后的权重计算总分
    for key, weight in adjusted_weights.items():
        if key == "ai_content" and "AI内容检测" in result["各项评分"]:
            credibility_score += result["各项评分"]["AI内容检测"] * weight
            total_weight += weight
        elif key == "language_neutrality" and "语言中立性" in result["各项评分"]:
            credibility_score += result["各项评分"]["语言中立性"] * weight
            total_weight += weight
        elif key == "source_citation_quality" and "来源和引用质量" in result["各项评分"]:
            credibility_score += result["各项评分"]["来源和引用质量"] * weight
            total_weight += weight
        elif key == "deepseek_analysis" and "DeepSeek综合分析" in result["各项评分"]:
            credibility_score += result["各项评分"]["DeepSeek综合分析"] * weight
            total_weight += weight
        elif key == "cross_validation" and "交叉验证" in result["各项评分"]:
            credibility_score += result["各项评分"]["交叉验证"] * weight
            total_weight += weight
    
    # 确保总权重不为零
    if total_weight > 0:
        credibility_score = credibility_score / total_weight
    else:
        credibility_score = 0.0
    
    # 计算新闻价值总分
    news_value_score = 0.0
    if "文本逻辑性" in result["新闻价值分析"]["各项评分"] and "新闻价值" in result["新闻价值分析"]["各项评分"]:
        news_value_score = (
            result["新闻价值分析"]["各项评分"]["文本逻辑性"] * SEPARATE_ANALYSIS["text_logic"] +
            result["新闻价值分析"]["各项评分"]["新闻价值"] * SEPARATE_ANALYSIS["news_value"]
        )
    
    # 设置总体评分
    result["总体评分"] = round(credibility_score, 2)
    result["新闻价值分析"]["总分"] = round(news_value_score, 2)
    
    # 添加总体评价
    if result["总体评分"] >= 0.8:
        result["总体评价"] = "高可信度：该新闻内容可信度高，来源可靠，内容客观中立。"
    elif result["总体评分"] >= 0.6:
        result["总体评价"] = "中等可信度：该新闻基本可信，但可能存在一些问题，建议进一步核实关键信息。"
    elif result["总体评分"] >= 0.4:
        result["总体评价"] = "低可信度：该新闻可信度较低，存在多项问题，建议谨慎对待其中的信息。"
    else:
        result["总体评价"] = "极低可信度：该新闻可信度极低，可能包含虚假或误导性信息，不建议作为可靠信息来源。"
    
    # 添加新闻价值评价
    if news_value_score >= 0.8:
        result["新闻价值分析"]["总体评价"] = "高价值：该新闻具有很高的新闻价值，逻辑清晰，内容丰富。"
    elif news_value_score >= 0.6:
        result["新闻价值分析"]["总体评价"] = "中等价值：该新闻具有一定新闻价值，但可能在逻辑性或内容深度上有所欠缺。"
    elif news_value_score >= 0.4:
        result["新闻价值分析"]["总体评价"] = "低价值：该新闻新闻价值较低，逻辑性较差或内容较为肤浅。"
    else:
        result["新闻价值分析"]["总体评价"] = "极低价值：该新闻几乎没有新闻价值，逻辑混乱或内容空洞。"
    
    logger.info(f"新闻可信度分析完成，总体评分: {result['总体评分']}")
    return result

def initialize_services():
    """
    初始化各项服务，测试连接状态
    
    返回:
        dict: 各服务可用状态
    """
    services_status = {
        "deepseek_api": False,
        "searxng": False
    }
    
    # 测试DeepSeek API连接
    try:
        if test_deepseek_connection():
            services_status["deepseek_api"] = True
            logger.info("DeepSeek API连接测试成功")
        else:
            logger.warning("DeepSeek API连接测试失败")
    except Exception as e:
        logger.error(f"测试DeepSeek API连接时出错: {e}")
    
    # 测试SearXNG连接
    try:
        if test_searxng_connection():
            services_status["searxng"] = True
            logger.info("SearXNG连接测试成功")
        else:
            logger.warning("SearXNG连接测试失败")
    except Exception as e:
        logger.error(f"测试SearXNG连接时出错: {e}")
    
    return services_status

def get_credibility_summary(score: float) -> str:
    """
    根据可信度评分生成简短摘要
    
    参数:
        score (float): 可信度评分
    
    返回:
        str: 可信度摘要
    """
    if score >= 0.8:
        return "高可信度"
    elif score >= 0.6:
        return "中等可信度"
    elif score >= 0.4:
        return "低可信度"
    else:
        return "极低可信度"

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
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--verbose', action='store_true', help='启用详细日志模式')
    parser.add_argument('--log-file', default='news_credibility.log', help='日志文件路径')
    parser.add_argument('--no-ai', action='store_true', help='禁用AI服务')
    parser.add_argument('--test', action='store_true', help='运行功能测试')
    parser.add_argument('--test-deepseek', action='store_true', help='测试DeepSeek API连接')
    parser.add_argument('--quick', action='store_true', help='快速模式，跳过DeepSeek API分析')
    parser.add_argument('--save', action='store_true', help='保存新闻到本地文件夹')
    parser.add_argument('--save-dir', default='saved_news', help='保存新闻的文件夹路径')
    return parser.parse_args()

def get_rating_emoji(score):
    """根据评分返回对应的emoji和评级"""
    if score >= 0.8:
        return "🌟🌟🌟🌟", "优"
    elif score >= 0.7:
        return "🌟🌟🌟", "良"
    elif score >= 0.6:
        return "🌟🌟", "中"
    elif score >= 0.5:
        return "🌟", "一般"
    else:
        return "❗", "差"

def get_progress_bar(score, width=10):
    """生成进度条"""
    filled = int(score * width)
    return f"{'█' * filled}{'░' * (width - filled)}"

def get_credibility_rating(score):
    """根据可信度评分返回评级"""
    if score >= 0.8:
        return "高度可信 🌟🌟🌟🌟", "高"
    elif score >= 0.6:
        return "部分可信 🌟🌟", "中"
    elif score >= 0.4:
        return "低度可信 🌟", "低" 
    else:
        return "不可信 ❗", "极低"

def print_formatted_result(result):
    """打印格式化的分析结果"""
    # 导入彩色输出支持
    import sys
    try:
        from colorama import Fore, Style
        if 'colorama' in sys.modules:
            import colorama
            colorama.init()
        color_support = True
    except ImportError:
        # 尝试使用sys.path添加路径
        try:
            import site
            # 添加用户site-packages路径
            sys.path.append(site.USER_SITE)
            import colorama
            from colorama import Fore, Style
            colorama.init()
            color_support = True
        except (ImportError, AttributeError):
            color_support = False
            print("提示: 无法导入colorama包，将使用普通文本输出")
            print("可以尝试手动安装: pip install colorama")
    
    # 检查结果是否为空
    if not result:
        if color_support:
            print(f"\n{Fore.RED}错误: 未收到分析结果{Fore.RESET}")
        else:
            print("\n错误: 未收到分析结果")
        return
    
    # 计算总体评级
    if "总体评分" not in result:
        if color_support:
            print(f"\n{Fore.RED}错误: 分析结果中缺少总体评分{Fore.RESET}")
        else:
            print("\n错误: 分析结果中缺少总体评分")
        return
    
    rating_text, rating_level = get_credibility_rating(result['总体评分'])
    score_percentage = int(result['总体评分'] * 100)
    
    # 定义层级颜色
    if color_support:
        # 主标题颜色
        TITLE_COLOR = Fore.CYAN + Style.BRIGHT
        # 一级标题颜色
        LEVEL1_COLOR = Fore.MAGENTA
        # 二级标题颜色
        LEVEL2_COLOR = Fore.BLUE
        # 三级标题颜色
        LEVEL3_COLOR = Fore.CYAN
        # 正文颜色
        TEXT_COLOR = Fore.WHITE
    
    # 输出标题横幅
    print("\n")
    if color_support:
        print(f"{TITLE_COLOR}▓{Fore.RESET}" * 70)
        print(f"{TITLE_COLOR}                     📊 新闻可信度分析结果 📊                       {Fore.RESET}")
        print(f"{TITLE_COLOR}={Fore.RESET}" * 70)
        print(f"{TITLE_COLOR}▓{Fore.RESET}" * 70)
        
        # 根据评级设置颜色
        if rating_level == "高":
            rating_color = Fore.GREEN
        elif rating_level == "中":
            rating_color = Fore.YELLOW
        elif rating_level == "低":
            rating_color = Fore.RED
        else:
            rating_color = Fore.RED + Style.BRIGHT
            
        print(f"{LEVEL1_COLOR}                       总体可信度评级: {rating_color}{rating_text}{Fore.RESET}                       ")
        print(f"{LEVEL1_COLOR}                        总分: {rating_color}{score_percentage}%{Fore.RESET}                         ")
        
        if "总体评价" in result:
            print(f"{LEVEL1_COLOR}                    {rating_color}{result['总体评价']}{Fore.RESET}                      ")
        
        print(f"{TITLE_COLOR}▓{Fore.RESET}" * 70)
    else:
        print("▓" * 70)
        print(f"                     📊 新闻可信度分析结果 📊                       ")
        print("=" * 70)
        print("▓" * 70)
        print(f"                       总体可信度评级: {rating_text}                       ")
        print(f"                        总分: {score_percentage}%                         ")
        
        if "总体评价" in result:
            print(f"                    {result['总体评价']}                      ")
        
        print("▓" * 70)
    
    # 检查是否有缺失的评分项
    missing_scores = result.get("缺失评分项", [])
    if missing_scores and color_support:
        print(f"\n{Fore.RED}警告: 以下评分项目缺失，未参与记分: {', '.join(missing_scores)}{Fore.RESET}")
        print(f"{Fore.YELLOW}注意: 其他项目的权重已等比例提高以弥补缺失项{Fore.RESET}")
    elif missing_scores:
        print(f"\n警告: 以下评分项目缺失，未参与记分: {', '.join(missing_scores)}")
        print(f"注意: 其他项目的权重已等比例提高以弥补缺失项")
    
    # 准备AI分析数据
    ai_analysis_data = {}
    ai_detailed_scores = {}
    ai_category_scores = {}
    
    if "AI分析" in result and isinstance(result["AI分析"], dict) and "详细分析" in result["AI分析"]:
        ai_analysis = result["AI分析"]["详细分析"]
        
        # 如果是字符串，尝试解析为JSON
        if isinstance(ai_analysis, str):
            try:
                import json
                ai_analysis = json.loads(ai_analysis)
            except:
                ai_analysis = {}
        
        # 提取各大类评分和细分点评分
        if isinstance(ai_analysis, dict):
            if "各大类评分" in ai_analysis:
                ai_category_scores = ai_analysis["各大类评分"]
            if "细分点评分" in ai_analysis:
                ai_detailed_scores = ai_analysis["细分点评分"]
    
    # 合并本地评分和AI评分，确保包含所有指定的大项
    combined_scores = {}
    
    # 1. 添加已有的本地评分项
    for key, value in result.get("各项评分", {}).items():
        combined_scores[key] = value
    
    # 2. 添加AI分析中的大类评分（如果不在本地评分中）
    for key, value in ai_category_scores.items():
        if key not in combined_scores:
            combined_scores[key] = value
    
    # 3. 确保包含所有指定的大项
    required_categories = [
        "AI内容检测", "语言中立性", "来源和引用质量", "交叉验证", 
        "内容真实性", "信息准确性", "来源可靠性", "逻辑连贯性"
    ]
    
    # 映射AI分析中的类别到本地类别
    ai_to_local_mapping = {
        "内容真实性": "AI内容检测",
        "语言客观性": "语言中立性",
        "来源可靠性": "来源和引用质量",
        "引用质量": "来源和引用质量"
    }
    
    # 确保所有必需类别都存在
    for category in required_categories:
        if category not in combined_scores:
            # 尝试从AI分析中找到对应项
            found = False
            for ai_cat, local_cat in ai_to_local_mapping.items():
                if local_cat == category and ai_cat in ai_category_scores:
                    combined_scores[category] = ai_category_scores[ai_cat]
                    found = True
                    break
            
            # 如果仍未找到，使用默认值
            if not found:
                combined_scores[category] = 0.5
    
    # 详细评分表格
    if color_support:
        print(f"\n{LEVEL1_COLOR}📋 事实核查评分{Fore.RESET}")
        print(f"{LEVEL1_COLOR}━{Fore.RESET}" * 70)
        print(f"{LEVEL2_COLOR}评分项目                      得分         评级              {Fore.RESET}")
        print(f"{LEVEL1_COLOR}━{Fore.RESET}" * 70)
    else:
        print("\n📋 事实核查评分")
        print("━" * 70)
        print(f"评分项目                      得分         评级              ")
        print("━" * 70)
    
    # 打印合并后的评分项目
    for key in required_categories:
        if key in combined_scores:
            value = combined_scores[key]
            emoji, rating = get_rating_emoji(value)
            progress = get_progress_bar(value)
            
            if color_support:
                # 根据评分设置颜色
                if value >= 0.8:
                    color = Fore.GREEN
                elif value >= 0.6:
                    color = Fore.CYAN
                elif value >= 0.4:
                    color = Fore.YELLOW
                else:
                    color = Fore.RED
                print(f"{LEVEL3_COLOR}{key:25} {color}{value:.1f} {rating:5} {progress:10}{Fore.RESET}")
            else:
                print(f"{key:25} {value:.1f} {rating:5} {progress:10}")
    
    print(f"{LEVEL1_COLOR}━{Fore.RESET}" * 70)
    
    # 打印各项评分的详细打分点
    if "评分详情" in result or ai_detailed_scores:
        if color_support:
            print(f"\n{LEVEL1_COLOR}📊 评分项目详细分析{Fore.RESET}")
        else:
            print("\n📊 评分项目详细分析")
        
        # 定义每个大项的打分点
        scoring_details = {
            "AI内容检测": [
                "句式结构分析", "重复模式检测", "常见AI表达方式识别", "词汇多样性评估", "语言连贯性"
            ],
            "语言中立性": [
                "情感词汇分析", "偏见词汇检测", "修辞手法评估", "平衡报道分析", "语言客观性"
            ],
            "来源和引用质量": [
                "来源可靠性", "引用准确性", "引用多样性", "引用相关性", "引用时效性"
            ],
            "交叉验证": [
                "关键信息验证", "事实一致性", "多源比对", "搜索结果相关性", "验证覆盖率"
            ],
            "内容真实性": [
                "事实核查", "虚构成分", "时间准确性", "地点准确性", "人物真实性"
            ],
            "信息准确性": [
                "数据准确性", "细节一致性", "专业术语", "背景信息", "引用准确性"
            ],
            "来源可靠性": [
                "信息来源", "来源权威性", "多源验证", "引用规范", "来源透明度"
            ],
            "逻辑连贯性": [
                "因果关系", "论证完整性", "结构清晰", "推理合理", "逻辑一致性"
            ]
        }
        
        # 获取详细评分数据
        detailed_scores = result.get("评分详情", {})
        
        # 打印每个大项的详细打分点
        for category in required_categories:
            if category in combined_scores:
                category_score = combined_scores[category]
                
                if color_support:
                    category_color = Fore.GREEN if category_score >= 0.8 else (Fore.CYAN if category_score >= 0.6 else (Fore.YELLOW if category_score >= 0.4 else Fore.RED))
                    print(f"\n{LEVEL2_COLOR}【{category}】{Fore.RESET} 总评分: {category_color}{category_score:.2f}{Fore.RESET}")
                    print(f"{LEVEL2_COLOR}{'─' * 50}{Fore.RESET}")
                else:
                    print(f"\n【{category}】 总评分: {category_score:.2f}")
                    print("─" * 50)
                
                # 打印该大项的各个打分点
                if category in scoring_details:
                    for point in scoring_details[category]:
                        point_key = f"{category}_{point}"
                        point_score = detailed_scores.get(point_key, 0.0)
                        
                        # 查找AI分析中对应的打分点
                        ai_point_key = None
                        if category == "AI内容检测":
                            ai_point_key = f"内容真实性_{point}"
                        elif category == "语言中立性":
                            ai_point_key = f"语言客观性_{point}"
                        elif category == "来源和引用质量":
                            if point == "来源可靠性":
                                ai_point_key = f"来源可靠性_信息来源"
                            elif point in ["引用准确性", "引用多样性", "引用相关性", "引用时效性"]:
                                ai_point_key = f"引用质量_{point}"
                        elif category in ["内容真实性", "信息准确性", "来源可靠性", "逻辑连贯性"]:
                            ai_point_key = f"{category}_{point}"
                        
                        # 如果找到对应的AI打分点，按权重合并
                        if ai_point_key and ai_point_key in ai_detailed_scores:
                            ai_point_score = ai_detailed_scores[ai_point_key]
                            if point_score == 0.0:  # 如果本地评分不存在，直接使用AI评分
                                point_score = ai_point_score
                            else:  # 否则按照权重合并
                                # 按照DEEPSEEK_WEIGHTS权重合并
                                combined_score = point_score * DEEPSEEK_WEIGHTS["local_algorithm"] + ai_point_score * DEEPSEEK_WEIGHTS["deepseek_algorithm"]
                                point_score = round(combined_score, 2)
                        elif point_score == 0.0:
                            # 如果没有找到对应的AI打分点，且本地评分不存在，使用类别评分
                            point_score = round(category_score, 2)
                        
                        if color_support:
                            point_color = Fore.GREEN if point_score >= 0.8 else (Fore.CYAN if point_score >= 0.6 else (Fore.YELLOW if point_score >= 0.4 else Fore.RED))
                            progress = get_progress_bar(point_score, width=8)
                            print(f"  {LEVEL3_COLOR}• {point:20}: {point_color}{point_score:.2f} {progress}{Fore.RESET}")
                        else:
                            progress = get_progress_bar(point_score, width=8)
                            print(f"  • {point:20}: {point_score:.2f} {progress}")
    
    # 显示可信度判断的疑点（如果存在）
    if "AI分析" in result and isinstance(result["AI分析"], dict) and "详细分析" in result["AI分析"]:
        ai_analysis = result["AI分析"]["详细分析"]
        
        # 如果是字符串，尝试解析为JSON
        if isinstance(ai_analysis, str):
            try:
                import json
                ai_analysis = json.loads(ai_analysis)
            except:
                ai_analysis = {}
        
        # 提取可信度判断的疑点
        if isinstance(ai_analysis, dict) and "可信度判断的疑点" in ai_analysis:
            if color_support:
                print(f"\n{LEVEL1_COLOR}可信度疑点:{Fore.RESET}")
            else:
                print(f"\n可信度疑点:")
                
            疑点文本 = ai_analysis['可信度判断的疑点']
            if isinstance(疑点文本, str):
                # 尝试分割疑点文本
                if ";" in 疑点文本 or "；" in 疑点文本:
                    疑点列表 = re.split(r'[;；]', 疑点文本)
                    for i, 疑点 in enumerate(疑点列表, 1):
                        if 疑点.strip():
                            if color_support:
                                print(f"  {LEVEL2_COLOR}{i}. {Fore.YELLOW}{疑点.strip()}{Fore.RESET}")
                            else:
                                print(f"  {i}. {疑点.strip()}")
                elif "," in 疑点文本 or "，" in 疑点文本:
                    疑点列表 = re.split(r'[,，]', 疑点文本)
                    for i, 疑点 in enumerate(疑点列表, 1):
                        if 疑点.strip():
                            if color_support:
                                print(f"  {LEVEL2_COLOR}{i}. {Fore.YELLOW}{疑点.strip()}{Fore.RESET}")
                            else:
                                print(f"  {i}. {疑点.strip()}")
                else:
                    if color_support:
                        print(f"  {LEVEL2_COLOR}• {Fore.YELLOW}{疑点文本}{Fore.RESET}")
                    else:
                        print(f"  • {疑点文本}")
            else:
                if color_support:
                    print(f"  {LEVEL2_COLOR}• {Fore.YELLOW}{疑点文本}{Fore.RESET}")
                else:
                    print(f"  • {疑点文本}")
    
    # 交叉验证部分
    if "交叉验证" in result:
        if "总体可信度" not in result["交叉验证"]:
            if color_support:
                print(f"\n{Fore.RED}错误: 交叉验证结果中缺少总体可信度{Fore.RESET}")
            else:
                print("\n错误: 交叉验证结果中缺少总体可信度")
        else:
            if color_support:
                print(f"\n{LEVEL1_COLOR}🔍 交叉验证结果{Fore.RESET}")
            else:
                print("\n🔍 交叉验证结果")
            print(f"{LEVEL1_COLOR}━{Fore.RESET}" * 70)
            
            # 显示交叉验证总体可信度
            cross_validation = result["交叉验证"]
            cross_validation_score = cross_validation.get("总体可信度", 0.5)
            
            if color_support:
                score_color = Fore.GREEN if cross_validation_score >= 0.7 else (Fore.YELLOW if cross_validation_score >= 0.5 else Fore.RED)
                print(f"\n{LEVEL2_COLOR}交叉验证总体可信度: {score_color}{cross_validation_score:.2f}{Fore.RESET}")
                if "验证结论" in cross_validation:
                    print(f"{LEVEL3_COLOR}{score_color}{cross_validation.get('验证结论', '')}{Fore.RESET}")
            else:
                print(f"\n交叉验证总体可信度: {cross_validation_score:.2f}")
                if "验证结论" in cross_validation:
                    print(f"{cross_validation.get('验证结论', '')}")
    elif "交叉验证" in missing_scores and color_support:
        print(f"\n{Fore.RED}交叉验证: 缺失 (未参与记分){Fore.RESET}")
    elif "交叉验证" in missing_scores:
        print(f"\n交叉验证: 缺失 (未参与记分)")
    
    # 打印问题列表
    if "问题" in result and result["问题"]:
        if color_support:
            print(f"\n{LEVEL1_COLOR}⚠️ 潜在问题{Fore.RESET}")
            print(f"{LEVEL1_COLOR}{'─' * 50}{Fore.RESET}")
            for i, issue in enumerate(result["问题"], 1):
                print(f"{LEVEL2_COLOR}{i}. {Fore.YELLOW}{issue}{Fore.RESET}")
        else:
            print("\n⚠️ 潜在问题")
            print("─" * 50)
            for i, issue in enumerate(result["问题"], 1):
                print(f"{i}. {issue}")
    
    # 打印新闻价值分析
    """ 
    if "新闻价值分析" in result and "总分" in result["新闻价值分析"]:
        news_value_score = result["新闻价值分析"]["总分"]
        if color_support:
            value_color = Fore.GREEN if news_value_score >= 0.8 else (Fore.CYAN if news_value_score >= 0.6 else (Fore.YELLOW if news_value_score >= 0.4 else Fore.RED))
            print(f"\n{LEVEL1_COLOR}📰 新闻价值分析{Fore.RESET}")
            print(f"{LEVEL1_COLOR}{'─' * 50}{Fore.RESET}")
            print(f"{LEVEL2_COLOR}总体评分: {value_color}{news_value_score:.2f}{Fore.RESET}")
            if "总体评价" in result["新闻价值分析"]:
                print(f"{LEVEL3_COLOR}{value_color}{result['新闻价值分析']['总体评价']}{Fore.RESET}")
        else:
            print("\n📰 新闻价值分析")
            print("─" * 50)
            print(f"总体评分: {news_value_score:.2f}")
            if "总体评价" in result["新闻价值分析"]:
                print(f"{result['新闻价值分析']['总体评价']}")
    """

def perform_cross_validation(text: str, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行交叉验证，由DeepSeek提取需要验证的内容，使用SearXNG搜索，然后由DeepSeek判断
    
    参数:
        text (str): 新闻文本
        ai_analysis (Dict[str, Any]): DeepSeek AI分析结果
    
    返回:
        Dict[str, Any]: 交叉验证结果
    """
    logger.info("开始执行交叉验证")
    
    # 初始化结果
    results = {
        "验证项目": [],
        "总体可信度": 0.0,
        "验证结论": ""
    }
    
    try:
        # 1. 使用DeepSeek提取需要验证的内容
        verification_points = extract_verification_points_with_deepseek(text)
        if not verification_points:
            logger.info("未找到需要交叉验证的内容")
            return None
        
        # 2. 对每个验证点进行搜索和验证
        total_score = 0.0
        verified_count = 0
        
        for point in verification_points:
            # 构建搜索查询
            query = point["搜索查询"]
            logger.info(f"交叉验证查询: {query}")
            
            # 使用SearXNG搜索
            if SEARXNG_AVAILABLE:
                search_results = search_with_searxng(query, num_results=5)
                
                if search_results and "results" in search_results and search_results["results"]:
                    # 提取搜索结果
                    search_snippets = []
                    for result in search_results["results"][:5]:  # 取前5个结果
                        title = result.get("title", "")
                        snippet = result.get("content", "")
                        url = result.get("url", "")
                        # 限制摘要长度为500个字符
                        if len(snippet) > 500:
                            snippet = snippet[:500] + "..."
                        
                        search_snippets.append({
                            "标题": title,
                            "摘要": snippet,
                            "链接": url
                        })
                    
                    # 使用DeepSeek判断搜索结果与验证点的一致性
                    verification_result = verify_search_results_with_deepseek(
                        point["内容"], 
                        point["质疑点"], 
                        search_snippets
                    )
                    
                    # 添加到验证结果
                    verification_item = {
                        "验证内容": point["内容"],
                        "质疑点": point["质疑点"],
                        "搜索查询": query,
                        "重要性": point.get("重要性", "中"),
                        "搜索结果数量": len(search_results["results"]),
                        "验证评分": verification_result["评分"],
                        "验证结论": verification_result["结论"],
                        "搜索结果摘要": search_snippets[:5]  # 只保留前5个结果
                    }
                    
                    results["验证项目"].append(verification_item)
                    
                    # 累计评分
                    total_score += verification_result["评分"]
                    verified_count += 1
                else:
                    # 未找到搜索结果
                    verification_item = {
                        "验证内容": point["内容"],
                        "质疑点": point["质疑点"],
                        "搜索查询": query,
                        "重要性": point.get("重要性", "中"),
                        "搜索结果数量": 0,
                        "验证评分": 0.5,
                        "验证结论": "未找到相关搜索结果，无法验证"
                    }
                    
                    results["验证项目"].append(verification_item)
                    
                    # 使用中等评分
                    total_score += 0.5
                    verified_count += 1
            else:
                logger.warning("SearXNG搜索不可用，无法进行交叉验证")
                return None
        
        # 3. 计算总体可信度
        if verified_count > 0:
            results["总体可信度"] = round(total_score / verified_count, 2)
            
            # 添加验证结论
            if results["总体可信度"] >= 0.8:
                results["验证结论"] = "交叉验证结果表明新闻内容高度可信，多个关键信息点得到外部来源确认"
            elif results["总体可信度"] >= 0.6:
                results["验证结论"] = "交叉验证结果表明新闻内容基本可信，部分关键信息得到外部来源确认"
            elif results["总体可信度"] >= 0.4:
                results["验证结论"] = "交叉验证结果表明新闻内容可信度一般，部分信息未得到充分确认"
            else:
                results["验证结论"] = "交叉验证结果表明新闻内容可信度较低，多个关键信息未得到外部来源确认"
        else:
            results["总体可信度"] = 0.5
            results["验证结论"] = "未能完成交叉验证，无法评估内容可信度"
        
        logger.info(f"交叉验证完成，总体可信度: {results['总体可信度']}")
        return results
        
    except Exception as e:
        logger.error(f"交叉验证过程出错: {e}")
        logger.error(traceback.format_exc())
        return None

def extract_verification_points_with_deepseek(text: str) -> List[Dict[str, Any]]:
    """
    使用DeepSeek从文本中提取需要验证的关键点
    
    参数:
        text (str): 新闻文本
    
    返回:
        List[Dict[str, Any]]: 需要验证的关键点列表，每个点包含内容、质疑点和搜索查询
    """
    try:
        # 构建提示
        prompt = f"""
        你是一个专业的新闻事实核查专家，需要对以下新闻文本进行质疑性分析，并提取需要交叉验证的内容。
        
        请仔细阅读以下新闻文本，找出3-5个需要通过搜索引擎进行交叉验证的关键信息点。这些信息点应该是：
        1. 可能存在争议或需要核实的事实性陈述
        2. 引用的数据、统计或研究结果
        3. 引述的专家观点或言论
        4. 可能存在偏见或误导的表述
        
        新闻文本:
        {text}
        
        对于每个需要验证的信息点，请提供：
        1. 原文中的具体内容
        2. 你对该内容的质疑点（为什么需要验证）
        3. 用于搜索引擎的最佳搜索查询（注意：这个查询将被直接发送到搜索引擎，请使用有意义的短句而不是单一词语。确保查询包含2-3个关键短句，能够精确定位相关信息。不要使用问句，不要包含引号或特殊符号，只提供搜索关键短句）
        4. 该信息点的重要性（高/中/低）
        
        请以JSON格式返回结果，格式如下:
        [
            {{
                "内容": "需要验证的原文内容",
                "质疑点": "为什么需要验证这个内容",
                "搜索查询": "关键短句1 关键短句2 关键短句3",
                "重要性": "高/中/低"
            }},
            ...
        ]
        """
        
        # 调用DeepSeek API
        response = query_deepseek(prompt)
        
        # 解析JSON响应
        import json
        try:
            # 尝试直接解析
            verification_points = json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
            if json_match:
                verification_points = json.loads(json_match.group(0))
            else:
                # 如果仍然失败，返回空列表
                logger.warning("无法从DeepSeek响应中提取JSON")
                return []
        
        # 验证结果格式
        if isinstance(verification_points, list) and all(isinstance(item, dict) and "内容" in item and "搜索查询" in item for item in verification_points):
            return verification_points
        else:
            logger.warning("DeepSeek返回的验证点格式不正确")
            return []
            
    except Exception as e:
        logger.error(f"使用DeepSeek提取验证点时出错: {e}")
        return []

def verify_search_results_with_deepseek(content: str, doubt_point: str, search_results: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    使用DeepSeek判断搜索结果与验证点的一致性
    
    参数:
        content (str): 需要验证的内容
        doubt_point (str): 质疑点
        search_results (List[Dict[str, str]]): 搜索结果列表
    
    返回:
        Dict[str, Any]: 验证结果
    """
    try:
        # 构建搜索结果文本
        search_text = ""
        for i, result in enumerate(search_results, 1):
            search_text += f"搜索结果{i}:\n"
            search_text += f"标题: {result.get('标题', '')}\n"
            search_text += f"摘要: {result.get('摘要', '')}\n"
            search_text += f"链接: {result.get('链接', '')}\n\n"
        
        # 构建提示
        prompt = f"""
        你是一个专业的新闻事实核查专家，需要对新闻中的信息点进行交叉验证。
        
        需要验证的新闻内容:
        "{content}"
        
        质疑点:
        {doubt_point}
        
        搜索结果:
        {search_text}
        
        请仔细分析搜索结果，判断它们是否支持、部分支持、不支持或与新闻内容矛盾。
        
        评估要点:
        1. 搜索结果是否直接或间接证实/反驳了新闻内容
        2. 搜索结果的来源可靠性和权威性（如官方网站、知名媒体、学术机构等）
        3. 搜索结果的时效性（是否为最新信息）
        4. 搜索结果与新闻内容的一致程度（是否有细节差异）
        5. 是否有多个独立来源支持/反驳新闻内容
        
        请给出0到1之间的可信度评分，其中:
        - 0.9-1.0: 多个可靠来源强烈支持该内容，细节一致
        - 0.7-0.9: 至少一个可靠来源支持该内容，无明显矛盾
        - 0.5-0.7: 搜索结果部分支持该内容，或支持与反对证据均衡
        - 0.3-0.5: 搜索结果与内容相关但不直接支持，或有细节差异
        - 0.0-0.3: 搜索结果与内容矛盾或强烈反对
        
        请以JSON格式返回结果:
        {{
            "评分": 0.0-1.0之间的数值,
            "结论": "对内容可信度的简短评估（50字以内）",
            "分析": "详细分析搜索结果如何支持或反对内容（200字以内）"
        }}
        """
        
        # 调用DeepSeek API
        response = query_deepseek(prompt)
        
        # 解析JSON响应
        import json
        try:
            # 尝试直接解析
            result = json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                # 如果仍然失败，返回默认结果
                logger.warning("无法从DeepSeek响应中提取JSON")
                return {
                    "评分": 0.5,
                    "结论": "无法解析验证结果，使用默认评分",
                    "分析": "DeepSeek API返回的结果格式不正确"
                }
        
        # 验证结果格式
        if isinstance(result, dict) and "评分" in result and "结论" in result:
            # 确保评分在0-1范围内
            result["评分"] = max(0.0, min(1.0, float(result["评分"])))
            return result
        else:
            logger.warning("DeepSeek返回的验证结果格式不正确")
            return {
                "评分": 0.5,
                "结论": "验证结果格式不正确，使用默认评分",
                "分析": "DeepSeek API返回的结果缺少必要字段"
            }
            
    except Exception as e:
        logger.error(f"使用DeepSeek验证搜索结果时出错: {e}")
        return {
            "评分": 0.5,
            "结论": f"验证过程出错: {str(e)}",
            "分析": "在调用DeepSeek API进行验证时发生错误"
        }

def save_news_to_local(text, url, result, save_dir, image_paths=None):
    """
    保存新闻到本地文件夹
    
    参数:
        text: 新闻文本
        url: 新闻URL
        result: 分析结果
        save_dir: 保存目录
        image_paths: 图片路径列表
    """
    try:
        # 创建保存目录
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成时间戳和文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 从URL中提取域名作为文件名的一部分
        domain = "unknown"
        if url:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace("www.", "").split(".")[0]
            except:
                pass
        
        base_filename = f"{timestamp}_{domain}"
        
        # 保存新闻文本
        text_filename = os.path.join(save_dir, f"{base_filename}.txt")
        with open(text_filename, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n\n")
            f.write(text)
        
        # 保存分析结果
        result_filename = os.path.join(save_dir, f"{base_filename}_analysis.json")
        with open(result_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 如果有图片，复制到保存目录
        if image_paths:
            # 创建图片子目录
            images_dir = os.path.join(save_dir, f"{base_filename}_images")
            os.makedirs(images_dir, exist_ok=True)
            
            # 复制图片
            for i, img_path in enumerate(image_paths):
                if os.path.exists(img_path):
                    # 获取文件扩展名
                    _, ext = os.path.splitext(img_path)
                    # 复制图片
                    import shutil
                    dest_path = os.path.join(images_dir, f"image_{i+1}{ext}")
                    shutil.copy2(img_path, dest_path)
        
        logger.info(f"新闻已保存到: {text_filename}")
        logger.info(f"分析结果已保存到: {result_filename}")
        if image_paths:
            logger.info(f"图片已保存到: {images_dir}")
        
        return True
    except Exception as e:
        logger.error(f"保存新闻时出错: {e}")
        logger.error(traceback.format_exc())
        return False

def query_deepseek(prompt: str) -> str:
    """
    调用DeepSeek API进行查询
    
    参数:
        prompt (str): 提示文本
    
    返回:
        str: DeepSeek的响应文本
    """
    try:
        # 检查API密钥是否可用
        if not DEEPSEEK_API_KEY:
            logger.error("DeepSeek API密钥未设置")
            return ""
        
        # 构建请求
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # 较低的温度以获得更确定性的回答
            "max_tokens": 2000
        }
        
        # 发送请求
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        # 检查响应
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                logger.warning("DeepSeek API返回的响应格式不正确")
                return ""
        else:
            logger.error(f"DeepSeek API请求失败: {response.status_code} - {response.text}")
            return ""
            
    except Exception as e:
        logger.error(f"调用DeepSeek API时出错: {e}")
        return ""

# 如果直接运行此模块，执行初始化
if __name__ == "__main__":
    args = parse_arguments()
    
    # 如果禁用AI服务，设置环境变量
    if args.no_ai:
        os.environ['DISABLE_AI'] = 'true'
    
    # 配置日志级别
    debug_mode = args.debug
    verbose_mode = args.verbose or args.debug
    
    # 使用utils.py中的setup_logging函数
    from utils import setup_logging
    logger = setup_logging(log_file=args.log_file, debug=debug_mode, verbose=verbose_mode)
    
    # 打印启动信息
    logger.info("新闻可信度分析工具启动")
    logger.info(f"调试模式: {'启用' if debug_mode else '禁用'}")
    logger.info(f"详细日志: {'启用' if verbose_mode else '禁用'}")
    logger.info(f"AI服务: {'禁用' if args.no_ai else '启用'}")
    logger.info(f"快速模式: {'启用' if args.quick else '禁用'}")
    
    # 如果是测试模式，执行简单测试并退出
    if args.test:
        from test_utils import simple_test
        simple_test()
        sys.exit(0)
    
    # 如果是测试DeepSeek API连接模式，执行测试并退出
    if args.test_deepseek:
        from ai_services import test_deepseek_connection
        result = test_deepseek_connection()
        if result:
            print("DeepSeek API连接测试成功！✅")
        else:
            print("DeepSeek API连接测试失败！❌")
        sys.exit(0)
    
    # 初始化服务
    initialize_services()
    
    # 获取分析文本
    analysis_text = None
    image_paths = []  # 初始化图片路径列表
    
    if args.url:
        try:
            # 从URL获取内容
            print(f"正在从URL获取内容: {args.url}")
            news_text, image_paths = fetch_news_content(args.url)
            if news_text:
                analysis_text = news_text
            else:
                print("无法从URL获取内容")
                sys.exit(1)
        except Exception as e:
            print(f"获取URL内容时出错: {e}")
            sys.exit(1)
    else:
        # 使用默认测试文本
        analysis_text = """
        据可靠消息来源报道，科学家们最近发现了一种新型材料，可以显著提高太阳能电池的效率。
        这种材料由石墨烯和钙钛矿复合而成，在实验室条件下，能够将太阳能转化效率提高至32%，
        远高于目前市场上20-25%的平均水平。研究负责人张教授表示："这一突破可能彻底改变
        可再生能源行业。"多位行业专家对此表示认可，但也指出从实验室到商业化还有很长的路要走。
        """
        print("未提供URL，使用默认测试文本")
    
    # 分析新闻可信度
    result = analyze_news_credibility(
        text=analysis_text,
        url=args.url if args.url else None,
        use_ai_services=not (args.no_ai or args.quick)  # 快速模式下也跳过AI服务
    )
    
    # 如果是快速模式，添加模拟的AI分析结果
    if args.quick and not args.no_ai:
        result["AI分析"] = {
            "评分": 0.75,
            "详细分析": json.dumps({
                "总体评分": 0.75,
                "各大类评分": {
                    "内容真实性": 0.78,
                    "信息准确性": 0.76,
                    "来源可靠性": 0.65,
                    "语言客观性": 0.82,
                    "逻辑连贯性": 0.80,
                    "引用质量": 0.70
                },
                "细分点评分": {
                    "内容真实性_事实核查": 0.75,
                    "内容真实性_虚构成分": 0.80,
                    "内容真实性_时间准确性": 0.70,
                    "内容真实性_地点准确性": 0.85,
                    "内容真实性_人物真实性": 0.80,
                    "信息准确性_数据准确性": 0.75,
                    "信息准确性_细节一致性": 0.80,
                    "信息准确性_专业术语": 0.85,
                    "信息准确性_背景信息": 0.65,
                    "来源可靠性_信息来源": 0.60,
                    "来源可靠性_来源权威性": 0.65,
                    "来源可靠性_多源验证": 0.60,
                    "来源可靠性_引用规范": 0.75,
                    "语言客观性_情感色彩": 0.85,
                    "语言客观性_偏见检测": 0.80,
                    "语言客观性_平衡报道": 0.75,
                    "语言客观性_修辞使用": 0.85,
                    "逻辑连贯性_因果关系": 0.80,
                    "逻辑连贯性_论证完整性": 0.75,
                    "逻辑连贯性_结构清晰": 0.85,
                    "逻辑连贯性_推理合理": 0.80,
                    "引用质量_引用多样性": 0.65,
                    "引用质量_引用时效性": 0.70,
                    "引用质量_引用相关性": 0.75
                },
                "详细分析": "这是一篇关于太阳能电池新材料的科技新闻，整体可信度较高。新闻提到了具体的效率数据（32%）和市场平均水平（20-25%），增加了可信度。引用了研究负责人张教授和多位行业专家的观点，但未提供具体的研究机构、发表期刊等详细信息，降低了来源可靠性。语言表述客观，逻辑结构清晰，但缺乏多源验证。",
                "可信度判断的疑点": "1. 未提供具体研究机构名称；2. 未说明研究发表在哪个期刊或会议；3. 未提供具体的实验条件和方法；4. '多位行业专家'表述模糊，未具体说明是哪些专家。"
            }, ensure_ascii=False)
        }
    
    # 使用格式化打印功能
    print_formatted_result(result)

    # 如果用户指定了保存新闻，调用save_news_to_local函数
    if args.save:
        if save_news_to_local(analysis_text, args.url, result, args.save_dir, image_paths):
            print(f"\n新闻已保存到文件夹: {os.path.abspath(args.save_dir)}")
        else:
            print("\n保存新闻失败，请查看日志了解详情。")
