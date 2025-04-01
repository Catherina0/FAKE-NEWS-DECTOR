#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
结果格式化模块
负责对分析结果进行格式化和显示
"""

import sys
import logging
import traceback
from typing import Dict, Any, Tuple
from config import (
    colorama_available, Fore, Style,
    TITLE_COLOR, HEADER_COLOR, SUBHEADER_COLOR, 
    DETAIL_COLOR, WARNING_COLOR, ERROR_COLOR,
    SUCCESS_COLOR, RESET_COLOR, DEFAULT_WEIGHTS,
    DEEPSEEK_API_AVAILABLE, SEARXNG_AVAILABLE,
    SECTION_COLOR, INFO_COLOR, NEUTRAL_COLOR
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def format_score(score: float) -> str:
    """格式化评分为两位小数的字符串"""
    return f"{float(score):.2f}"

def get_credibility_summary(score: float) -> str:
    """
    根据可信度评分生成简短摘要
    
    参数:
        score (float): 可信度评分 (0-1)
    
    返回:
        str: 可信度摘要
    """
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "无法评估：评分数据异常"
    
    if score >= 0.8:
        return "新闻内容可靠性高，论据充分，信息准确，来源可靠"
    elif score >= 0.6:
        return "新闻基本可信，但建议核实关键信息"
    elif score >= 0.4:
        return "新闻可信度存在问题，建议谨慎对待"
    else:
        return "新闻可信度严重不足，可能包含虚假或误导信息"

def get_ai_content_description(score: float) -> str:
    """
    根据AI生成内容评分提供描述
    
    参数:
        score (float): AI生成评分 (0-1，越高表示越像人类写作)
    
    返回:
        str: 描述性文本
    """
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "无法评估AI生成可能性"
    
    if score >= 0.85:
        return "文本高度符合人类写作特征，AI生成可能性很低"
    elif score >= 0.7:
        return "文本整体符合人类写作特征，AI生成可能性较低"
    elif score >= 0.5:
        return "文本有部分AI生成特征，但仍保留人类写作风格"
    elif score >= 0.3:
        return "文本呈现明显的AI生成特征，可能是AI辅助创作"
    else:
        return "文本极有可能由AI生成，人类写作特征极少"

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
    if score is None:
        # 对于None值，返回空进度条
        return f"{'░' * width}"
    
    # 确保score是浮点数
    try:
        score_float = float(score)
    except (TypeError, ValueError):
        # 如果无法转换为浮点数，返回空进度条
        return f"{'░' * width}"
    
    # 确保分数在0-1范围内
    score_float = max(0.0, min(1.0, score_float))
    
    filled = int(score_float * width)
    return f"{'█' * filled}{'░' * (width - filled)}"

def get_credibility_rating(score):
    """根据可信度评分返回评级"""
    if score >= 0.8:
        return f"{TITLE_COLOR}高度可信 🌟🌟🌟🌟{RESET_COLOR}", "高"
    elif score >= 0.6:
        return f"{SUCCESS_COLOR}部分可信 🌟🌟{RESET_COLOR}", "中"
    elif score >= 0.4:
        return f"{WARNING_COLOR}低度可信 🌟{RESET_COLOR}", "低" 
    else:
        return f"{ERROR_COLOR}不可信 ❗{RESET_COLOR}", "极低"

def validate_score(score: Any, source: str = "未知") -> float:
    """验证并转换评分"""
    try:
        score_float = float(score)
        if not 0 <= score_float <= 1:
            logger.warning(f"评分超出范围[0-1]: {score_float} (来源: {source})")
            return max(0.0, min(1.0, score_float))
        return score_float
    except (TypeError, ValueError) as e:
        logger.error(f"评分转换失败: {score} (来源: {source}) - {str(e)}")
        raise ValueError(f"无效的评分值: {score}")

def validate_data(data: Dict[str, Any], required_fields: list, context: str = "") -> bool:
    """验证数据完整性"""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logger.warning(f"{context} - 缺失字段: {', '.join(missing_fields)}")
        return False
    return True

def calculate_weighted_score(main_scores: dict, cross_validation_data: dict = None) -> Tuple[float, dict]:
    """
    计算加权总分
    
    参数:
        main_scores: 包含各维度评分的字典
        cross_validation_data: 交叉验证数据
    
    返回:
        Tuple[float, dict]: (加权总分, 各维度权重)
    """
    # 定义各维度的权重（总和为0.7，为交叉验证预留0.3）
    weights = {
        "内容真实性": 0.15,  # 
        "信息准确性": 0.15,  #
        "来源可靠性": 0.15,  #
        "引用质量": 0.10,    #
        "语言客观性": 0.08,  #
        "逻辑连贯性": 0.07,  
        "交叉验证": 0.30     # 新增交叉验证权重
    }
    
    total_weight = 0
    weighted_sum = 0
    used_weights = {}
    
    # 记录输入数据，帮助调试
    logger.debug(f"计算加权分数 - 主要评分: {main_scores}")
    logger.debug(f"计算加权分数 - 交叉验证数据: {cross_validation_data}")
    
    # 处理主要维度评分
    for dimension, weight in weights.items():
        if dimension == "交叉验证":
            continue  # 跳过交叉验证，稍后处理
        if dimension in main_scores:
            try:
                score = validate_score(main_scores[dimension], f"维度评分.{dimension}")
                weighted_sum += score * weight
                total_weight += weight
                used_weights[dimension] = weight
                logger.debug(f"{dimension} 评分: {score:.2f}, 权重: {weight}")
            except ValueError:
                logger.warning(f"跳过无效的评分项: {dimension}")
                continue
    
    # 处理交叉验证评分
    if cross_validation_data and isinstance(cross_validation_data, dict):
        try:
            # 首先尝试直接使用score字段
            if "score" in cross_validation_data:
                cross_validation_score = validate_score(cross_validation_data["score"], "交叉验证.score")
                logger.debug(f"使用交叉验证直接提供的评分: {cross_validation_score}")
            else:
                # 如果没有score字段，尝试从其他字段推断
                cross_validation_score = 0.0
                
                # 从一致性数据中提取
                consistency = cross_validation_data.get("consistency", cross_validation_data.get("一致性", 0))
                if consistency:
                    try:
                        if isinstance(consistency, str) and "%" in consistency:
                            # 处理百分比字符串
                            consistency = float(consistency.strip("%")) / 100
                        else:
                            consistency = float(consistency)
                        cross_validation_score = consistency
                        logger.debug(f"从一致性数据中提取交叉验证评分: {cross_validation_score}")
                    except (ValueError, TypeError):
                        logger.warning(f"无法从一致性数据中提取评分: {consistency}")
                
                # 从来源可信度中提取
                if cross_validation_score == 0.0:
                    source_credibility = cross_validation_data.get("source_credibility", cross_validation_data.get("来源可信度", ""))
                    if isinstance(source_credibility, str):
                        if "高度可信" in source_credibility:
                            cross_validation_score = 0.9
                        elif "可信" in source_credibility:
                            cross_validation_score = 0.7
                        elif "部分可信" in source_credibility:
                            cross_validation_score = 0.5
                        elif "低可信" in source_credibility:
                            cross_validation_score = 0.3
                        else:
                            cross_validation_score = 0.1
                        logger.debug(f"从source_credibility提取交叉验证评分: {cross_validation_score}")
            
            # 考虑来源数量影响评分
            source_count = cross_validation_data.get("source_count", 0)
            if source_count > 5:
                cross_validation_score = min(1.0, cross_validation_score * 1.2)
                logger.debug(f"来源数量较多，提升评分至: {cross_validation_score}")
            elif source_count < 2:
                cross_validation_score = cross_validation_score * 0.8
                logger.debug(f"来源数量较少，降低评分至: {cross_validation_score}")
            logger.debug(f"考虑来源数量后的交叉验证评分: {cross_validation_score}")
            
            # 创建一个至少0.4的默认得分，避免无效评分
            if cross_validation_score <= 0:
                cross_validation_score = 0.4
                logger.warning(f"交叉验证评分无效或过低，使用默认值: {cross_validation_score}")
            
            weighted_sum += cross_validation_score * weights["交叉验证"]
            total_weight += weights["交叉验证"]
            used_weights["交叉验证"] = weights["交叉验证"]
            logger.debug(f"交叉验证评分: {cross_validation_score:.2f}, 权重: {weights['交叉验证']}")
        except Exception as e:
            logger.warning(f"处理交叉验证评分时出错: {str(e)}")
            # 使用默认评分
            cross_validation_score = 0.5
            logger.info(f"交叉验证处理失败，使用默认评分: {cross_validation_score}")
            weighted_sum += cross_validation_score * weights["交叉验证"]
            total_weight += weights["交叉验证"]
            used_weights["交叉验证"] = weights["交叉验证"]
    
    # 如果没有有效的评分项，但有交叉验证数据
    if total_weight == 0 and cross_validation_data:
        logger.warning("主要评分项为空，尝试单独使用交叉验证数据")
        try:
            # 尝试从交叉验证中提取评分
            if hasattr(cross_validation_data, 'get'):
                cv_score = cross_validation_data.get('score', 0.7)  # 默认使用0.7
                return float(cv_score), {"交叉验证": 1.0}
        except Exception as e:
            logger.error(f"尝试使用交叉验证数据失败: {str(e)}")
    
    # 如果没有有效的评分项，返回None
    if total_weight == 0:
        logger.warning("没有有效评分项，返回None")
        return None, {}
    
    # 重新归一化权重
    if total_weight < 1.0:
        normalization_factor = 1.0 / total_weight
        weighted_sum *= normalization_factor
        used_weights = {k: v * normalization_factor for k, v in used_weights.items()}
    
    logger.info(f"计算得到加权总分: {weighted_sum:.2f}")
    return weighted_sum, used_weights

def analyze_problems(result: dict, total_score: float, main_scores: dict, cross_validation_data: dict) -> list:
    """
    AI分析存在的问题
    
    参数:
        result: 完整的分析结果
        total_score: 总分
        main_scores: 主要维度评分
        cross_validation_data: 交叉验证数据
    
    返回:
        list: 问题列表，每个问题是一个字典，包含严重程度、描述和建议
    """
    problems = []
    
    # 1. 分析总体可信度
    if total_score < 0.4:
        problems.append({
            "severity": "严重",
            "type": "总体可信度",
            "description": f"新闻整体可信度极低 ({total_score:.1%})",
            "suggestion": "建议谨慎对待该新闻内容，需要大量额外验证",
            "color": ERROR_COLOR
        })
    elif total_score < 0.6:
        problems.append({
            "severity": "中等",
            "type": "总体可信度",
            "description": f"新闻可信度较低 ({total_score:.1%})",
            "suggestion": "建议进一步核实关键信息",
            "color": WARNING_COLOR
        })
    
    # 2. 分析各维度评分
    dimension_thresholds = {
        "内容真实性": (0.6, "核实新闻中的关键事实和数据"),
        "信息准确性": (0.6, "检查信息的准确性和完整性"),
        "来源可靠性": (0.6, "验证信息来源的权威性"),
        "引用质量": (0.6, "检查引用的准确性和可靠性"),
        "语言客观性": (0.5, "注意可能存在的主观偏见"),
        "逻辑连贯性": (0.5, "检查内容的逻辑性和连贯性")
    }
    
    for dim, (threshold, suggestion) in dimension_thresholds.items():
        if dim in main_scores:
            score = float(main_scores[dim])
            if score < threshold:
                severity = "严重" if score < 0.4 else "中等"
                problems.append({
                    "severity": severity,
                    "type": dim,
                    "description": f"{dim}评分过低 ({score:.1%})",
                    "suggestion": suggestion,
                    "color": ERROR_COLOR if score < 0.4 else WARNING_COLOR
                })
    
    # 3. 分析交叉验证
    if cross_validation_data and isinstance(cross_validation_data, dict):
        # 改进源计数检测，优先使用来源数量或搜索结果总数
        source_count = 0
        search_results_count = 0
        
        # 尝试多种可能的键名获取来源数量
        for key in ["source_count", "sources_count", "搜索结果总数", "来源数量", "相关来源数"]:
            if key in cross_validation_data and isinstance(cross_validation_data[key], (int, float, str)):
                try:
                    source_count = int(cross_validation_data[key])
                    logger.info(f"从键名 '{key}' 获取到来源数量: {source_count}")
                    break
                except (ValueError, TypeError):
                    logger.warning(f"无法将 {key}:{cross_validation_data[key]} 转换为整数")
        
        # 如果找不到直接的计数字段，尝试从sources列表获取
        if source_count == 0 and "sources" in cross_validation_data and isinstance(cross_validation_data["sources"], list):
            source_count = len(cross_validation_data["sources"])
            logger.info(f"从sources列表长度获取来源数量: {source_count}")
        
        # 如果找不到sources列表，尝试从相关来源获取
        if source_count == 0 and "相关来源" in cross_validation_data and isinstance(cross_validation_data["相关来源"], list):
            source_count = len(cross_validation_data["相关来源"])
            logger.info(f"从相关来源列表长度获取来源数量: {source_count}")
        
        # 如果找不到相关来源，尝试从verified_sources获取
        if source_count == 0 and "verified_sources" in cross_validation_data and isinstance(cross_validation_data["verified_sources"], list):
            source_count = len(cross_validation_data["verified_sources"])
            logger.info(f"从verified_sources列表长度获取来源数量: {source_count}")
        
        # 检查验证点是否存在
        no_result_count = 0
        verification_points = []
        
        # 尝试获取验证点列表和搜索结果计数
        if "验证点" in cross_validation_data and isinstance(cross_validation_data["验证点"], list):
            verification_points = cross_validation_data["验证点"]
            # 计算没有搜索结果的验证点数量
            no_result_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("搜索结果数量", 0) == 0)
            logger.info(f"从验证点中发现无搜索结果的点数: {no_result_count}")
            
            # 尝试从验证点中获取搜索结果总数
            for p in verification_points:
                if isinstance(p, dict):
                    if "搜索结果" in p and isinstance(p["搜索结果"], int):
                        search_results_count += p["搜索结果"]
                    elif "搜索结果数量" in p and isinstance(p["搜索结果数量"], int):
                        search_results_count += p["搜索结果数量"]
                        
        elif "verification_points" in cross_validation_data and isinstance(cross_validation_data["verification_points"], list):
            verification_points = cross_validation_data["verification_points"]
            # 计算没有搜索结果的验证点数量
            no_result_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("搜索结果数量", 0) == 0)
            logger.info(f"从verification_points中发现无搜索结果的点数: {no_result_count}")
            
            # 尝试从验证点中获取搜索结果总数
            for p in verification_points:
                if isinstance(p, dict):
                    if "搜索结果" in p and isinstance(p["搜索结果"], int):
                        search_results_count += p["搜索结果"]
                    elif "搜索结果数量" in p and isinstance(p["搜索结果数量"], int):
                        search_results_count += p["搜索结果数量"]
                        
        elif "claims" in cross_validation_data and isinstance(cross_validation_data["claims"], list):
            verification_points = cross_validation_data["claims"]
            # 计算没有搜索结果的验证点数量
            no_result_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("搜索结果数量", 0) == 0)
            logger.info(f"从claims中发现无搜索结果的点数: {no_result_count}")
            
            # 尝试从验证点中获取搜索结果总数
            for p in verification_points:
                if isinstance(p, dict):
                    if "搜索结果" in p and isinstance(p["搜索结果"], int):
                        search_results_count += p["搜索结果"]
                    elif "搜索结果数量" in p and isinstance(p["搜索结果数量"], int):
                        search_results_count += p["搜索结果数量"]
        
        # 如果搜索结果数大于0但来源计数为0，使用搜索结果数作为来源计数的估计
        if search_results_count > 0 and source_count == 0:
            logger.info(f"使用搜索结果数量({search_results_count})作为来源数量估计")
            source_count = search_results_count
            
        # 添加来源不足问题（仅当搜索结果确实不足时）
        if source_count < 2 and search_results_count < 3:
            problems.append({
                "severity": "中等",
                "type": "交叉验证",
                "description": f"缺乏足够的交叉验证来源 (仅{source_count}个)",
                "suggestion": "建议寻找更多独立来源验证信息",
                "color": WARNING_COLOR
            })
        
        # 添加验证点问题
        if no_result_count > 0:
            verification_points_count = len(verification_points) if verification_points else 0
            problems.append({
                "severity": "中等",
                "type": "交叉验证完整性",
                "description": f"{no_result_count}个验证点未找到相关信息 (共{verification_points_count}个验证点)",
                "suggestion": "建议针对这些特定信息点进行额外验证",
                "color": WARNING_COLOR
            })
        
        # 分析来源可信度
        credibility = cross_validation_data.get("source_credibility", "")
        if isinstance(credibility, str) and ("低可信" in credibility or "不可信" in credibility):
            problems.append({
                "severity": "严重",
                "type": "交叉验证",
                "description": "交叉验证来源可信度低",
                "suggestion": "建议寻找更权威的信息来源",
                "color": ERROR_COLOR
            })
    
    return problems

def print_problems_section(problems: list):
    """打印问题分析部分"""
    print(f"\n{SUBHEADER_COLOR}四、问题点分析{RESET_COLOR}")
    print(f"{DETAIL_COLOR}{'━' * 70}{RESET_COLOR}")
    
    if not problems:
        print(f"{SUCCESS_COLOR}  ✓ 未发现明显问题{RESET_COLOR}")
        print(f"{DETAIL_COLOR}  • 建议：保持批判性思维，关注信息更新{RESET_COLOR}")
        return
    
    # 按严重程度排序（严重 > 中等）
    problems.sort(key=lambda x: 0 if x["severity"] == "严重" else 1)
    
    for i, problem in enumerate(problems, 1):
        color = problem["color"]
        print(f"\n{color}{i}. {problem['type']}问题:{RESET_COLOR}")
        print(f"{color}  ⚠️ 严重性：{problem['severity']}{RESET_COLOR}")
        print(f"{color}    - {problem['description']}{RESET_COLOR}")
        print(f"{color}    - 建议：{problem['suggestion']}{RESET_COLOR}")

def print_formatted_result(result: Dict[str, Any], colored_output: bool = True) -> None:
    """
    格式化打印分析结果
    
    参数:
        result (Dict[str, Any]): 分析结果字典
        colored_output (bool): 是否使用彩色输出
    """
    try:
        logger.info("开始格式化分析结果")
        logger.debug(f"输入数据: {result}")
        
        # 验证输入数据
        if not isinstance(result, dict):
            raise TypeError(f"输入数据类型错误: 期望 dict, 获得 {type(result)}")
        
        # 1. 处理总体评分 - 使用加权计算
        logger.debug("开始处理总体评分")
        
        # 获取主要评分数据
        main_scores = {}
        scoring_details = result.get("评分详情", {})
        deepseek_data = result.get("原始分析数据", {}).get("deepseek_full_response", {})
        
        # 提取AI生成内容检测数据
        ai_content_data = None
        # 尝试多个可能的键名称
        for key in ["AI生成内容", "ai_content", "AI_content", "ai_generation_detection", "AI生成检测"]:
            if key in result and result[key]:
                ai_content_data = result[key]
                logger.info(f"找到AI生成内容检测数据，键名: {key}")
                break
        
        # 如果没有找到，尝试从deepseek数据中提取
        if not ai_content_data and isinstance(deepseek_data, dict):
            for key in ["AI生成内容", "ai_content", "AI_content", "ai_generation", "ai率"]:
                if key in deepseek_data:
                    ai_content_data = deepseek_data[key]
                    logger.info(f"从deepseek数据中提取AI生成内容检测数据，键名: {key}")
                    break
            
            # 如果还没找到，则搜索所有可能包含AI检测相关信息的键
            if not ai_content_data:
                for key in deepseek_data:
                    if isinstance(deepseek_data[key], dict) and any(ai_term in key.lower() for ai_term in ["ai", "人工智能", "机器", "生成"]):
                        ai_content_data = deepseek_data[key]
                        logger.info(f"从deepseek数据通过关键词搜索找到AI生成内容检测数据，键名: {key}")
                        break
        
        # 记录找到的AI生成内容检测数据
        logger.debug(f"提取的AI生成内容检测数据: {ai_content_data}")
        
        # 更全面地尝试提取交叉验证数据
        cross_validation_data = None
        # 尝试多个可能的键名称
        for key in ["cross_validation", "交叉验证", "crossValidation", "cross-validation", "validation_results"]:
            if key in result and result[key]:
                cross_validation_data = result[key]
                logger.info(f"找到交叉验证数据，键名: {key}")
                break
        
        # 如果找不到交叉验证数据，检查是否有相关日志信息可以提取
        if not cross_validation_data:
            logger.warning("在结果字典中未找到交叉验证数据，尝试从其他位置提取")
            # 尝试从validation字段或其他可能包含交叉验证信息的字段中提取
            for key in ["validation", "verification", "外部验证", "信息验证", "web_validation"]:
                if key in result:
                    cross_validation_data = result[key]
                    logger.info(f"从其他位置找到交叉验证数据，键名: {key}")
                    break
            
            # 如果还是没找到，尝试从deepseek_data中查找
            if not cross_validation_data and isinstance(deepseek_data, dict):
                for key in ["交叉验证", "验证", "cross_validation"]:
                    if key in deepseek_data:
                        cross_validation_data = deepseek_data[key]
                        logger.info(f"从deepseek数据中找到交叉验证数据，键名: {key}")
                        break
            
            # 如果还是没找到，创建一个基本结构用于显示
            if not cross_validation_data and "cv_score" in result:
                cross_validation_data = {
                    "score": result["cv_score"],
                    "source_count": result.get("cv_source_count", 0),
                    "unique_sources": result.get("cv_unique_sources", 0),
                    "source_credibility": result.get("cv_credibility", "未知"),
                    "timeliness": result.get("cv_timeliness", "未知")
                }
                logger.info("从分散字段构建交叉验证数据")
        
        # 记录找到的交叉验证数据
        logger.debug(f"提取的交叉验证数据: {cross_validation_data}")
        
        # 从多个来源收集评分数据
        if isinstance(scoring_details, dict):
            for key, value in scoring_details.items():
                if key.startswith(("内容真实性", "信息准确性", "来源可靠性", "引用质量", "语言客观性", "逻辑连贯性")):
                    clean_key = key.split("_")[-1] if "_" in key else key
                    main_scores[clean_key] = value
        
        # 如果评分详情中没有数据，尝试从deepseek数据获取
        if not main_scores and isinstance(deepseek_data, dict):
            main_scores = deepseek_data.get("各大类评分", {})
        
        # 计算加权总分，包含交叉验证
        total_score, weights = calculate_weighted_score(main_scores, cross_validation_data)
        
        if total_score is None:
            error_msg = "无法计算加权总分，评分数据无效"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        total_score_pct = total_score * 100
        score_source = "加权计算"
        logger.info(f"最终总分: {total_score_pct:.1f}% (来源: {score_source})")
        
        # 记录使用的权重
        logger.info("使用的维度权重:")
        for dimension, weight in weights.items():
            logger.info(f"  {dimension}: {weight:.2f}")
        
        # 获取评级
        rating_text, rating_level = get_credibility_rating(total_score)
        logger.debug(f"可信度评级: {rating_text} (级别: {rating_level})")
        
        # 顶部横幅
        print(f"\n{HEADER_COLOR}{'=' * 70}{RESET_COLOR}")
        print(f"{HEADER_COLOR}{'📊 新闻可信度分析报告 📊':^70}{RESET_COLOR}")
        print(f"{HEADER_COLOR}{'=' * 70}{RESET_COLOR}")
        
        # 总评部分
        print(f"\n{TITLE_COLOR}{'▓' * 70}{RESET_COLOR}")
        print(f"{TITLE_COLOR}{'总体可信度评级: ' + rating_text:^70}{RESET_COLOR}")
        print(f"{TITLE_COLOR}{f'总分: {total_score_pct:.1f}% (来源: {score_source})':^70}{RESET_COLOR}")
        print(f"{TITLE_COLOR}{'▓' * 70}{RESET_COLOR}")
        
        # 获取摘要
        summary = get_credibility_summary(total_score)
        logger.debug(f"生成总体评估摘要: {summary}")
        print(f"\n{SECTION_COLOR}〖 总体评估 〗{RESET_COLOR}")
        print(f"{DETAIL_COLOR}{summary}{RESET_COLOR}")
        
        # 一、内容真实性与准确性分析
        print(f"\n{SUBHEADER_COLOR}一、内容真实性与准确性分析{RESET_COLOR}")
        print(f"{DETAIL_COLOR}{'━' * 70}{RESET_COLOR}")
        
        # AI生成内容检测部分
        print(f"\n{SECTION_COLOR}1. AI生成内容检测:{RESET_COLOR}")
        if ai_content_data and isinstance(ai_content_data, dict):
            try:
                # 初始化ai_score变量
                ai_score = None
                
                # 计算平均分数
                detailed_scores = {
                    "表达模式": ai_content_data.get("expression_pattern", ai_content_data.get("表达模式", 0)),
                    "词汇多样性": ai_content_data.get("vocabulary_diversity", ai_content_data.get("词汇多样性", 0)),
                    "句子变化": ai_content_data.get("sentence_variation", ai_content_data.get("句子变化", 0)),
                    "上下文连贯性": ai_content_data.get("context_coherence", ai_content_data.get("上下文连贯性", 0)),
                    "人类特征": ai_content_data.get("human_traits", ai_content_data.get("人类特征", 0))
                }
                
                valid_scores = [score for score in detailed_scores.values() if isinstance(score, (int, float)) and 0 <= float(score) <= 1]
                if valid_scores:
                    avg_score = sum(valid_scores) / len(valid_scores)
                    ai_score = avg_score  # 设置ai_score
                    score_color = SUCCESS_COLOR if avg_score >= 0.8 else (WARNING_COLOR if avg_score >= 0.6 else ERROR_COLOR)
                    
                    print(f"{score_color}  • 人类写作特征评分: {avg_score:.2f} {get_progress_bar(avg_score)}{RESET_COLOR}")
                    print(f"{DETAIL_COLOR}    - {get_ai_content_description(avg_score)}{RESET_COLOR}")
                    
                    # 显示AI生成概率
                    ai_probability = max(0, min(1, 1 - avg_score))
                    ai_prob_color = SUCCESS_COLOR if ai_probability <= 0.3 else (WARNING_COLOR if ai_probability <= 0.5 else ERROR_COLOR)
                    print(f"{ai_prob_color}  • AI生成概率: {ai_probability:.2f} {get_progress_bar(ai_probability)}{RESET_COLOR}")
                    
                    # 显示详细特征评分
                    print(f"\n{SECTION_COLOR}  AI特征详细分析:{RESET_COLOR}")
                    for key, score in detailed_scores.items():
                        if isinstance(score, (int, float)) and 0 <= float(score) <= 1:
                            score_float = float(score)
                            score_color = SUCCESS_COLOR if score_float >= 0.7 else (WARNING_COLOR if score_float >= 0.5 else ERROR_COLOR)
                            print(f"{score_color}    • {key}: {score_float:.2f} {get_progress_bar(score_float)}{RESET_COLOR}")
            except Exception as e:
                logger.error(f"提取AI生成内容评分时出错: {str(e)}")
                ai_score = None
                
            # 如果没有找到，检查嵌套字典
            if ai_score is None:
                try:
                    for key, value in ai_content_data.items():
                        if isinstance(value, dict) and "score" in value:
                            ai_score = value["score"]
                            logger.info(f"从嵌套字典中找到AI生成内容评分，键路径: {key}.score")
                            break
                except Exception as e:
                    logger.error(f"从嵌套字典提取AI评分时出错: {str(e)}")
            
            # 如果还是没有找到，尝试找结论字段
            if ai_score is None:
                try:
                    conclusion = None
                    for key in ["conclusion", "summary", "结论", "分析结果"]:
                        if key in ai_content_data:
                            conclusion = ai_content_data[key]
                            logger.info(f"找到AI分析结论，键名: {key}")
                            break
                    
                    if conclusion:
                        # 从结论文本中提取可能的评分
                        if isinstance(conclusion, str):
                            import re
                            # 尝试找出类似 "0.7" 或 "70%" 的评分
                            score_match = re.search(r'(\d+(\.\d+)?)%?', conclusion)
                            if score_match:
                                try:
                                    potential_score = float(score_match.group(1))
                                    # 如果是百分比格式，转换为0-1范围
                                    if "%" in conclusion and potential_score > 1:
                                        potential_score /= 100
                                    # 确保在0-1范围内
                                    ai_score = max(0, min(1, potential_score))
                                    logger.info(f"从结论中提取AI生成内容评分: {ai_score}")
                                except ValueError:
                                    logger.warning(f"无法从结论中提取评分: {conclusion}")
                except Exception as e:
                    logger.error(f"处理AI分析结论时出错: {str(e)}")
                    
            if ai_score is not None:
                try:
                    ai_score_float = validate_score(ai_score, "AI生成内容评分")
                    # 注意：这里评分越高，表示越像人类写作，AI生成可能性越低
                    score_color = SUCCESS_COLOR if ai_score_float >= 0.7 else (WARNING_COLOR if ai_score_float >= 0.5 else ERROR_COLOR)
                    print(f"{score_color}  • 人类写作特征评分: {ai_score_float:.2f} {get_progress_bar(ai_score_float)}{RESET_COLOR}")
                    print(f"{DETAIL_COLOR}  • {get_ai_content_description(ai_score_float)}{RESET_COLOR}")
                    
                    # 添加AI生成概率
                    ai_probability = max(0, min(1, 1 - ai_score_float))
                    ai_prob_color = SUCCESS_COLOR if ai_probability <= 0.3 else (WARNING_COLOR if ai_probability <= 0.5 else ERROR_COLOR)
                    print(f"{ai_prob_color}  • AI生成概率: {ai_probability:.1%}{RESET_COLOR}")
                except ValueError:
                    logger.warning(f"AI生成内容评分无效: {ai_score}")
                    print(f"{ERROR_COLOR}  • AI生成内容评分无效{RESET_COLOR}")
            else:
                # 尝试从其他字段推断AI生成可能性
                conclusion = None
                try:
                    for key in ["conclusion", "summary", "结论", "分析结果"]:
                        if key in ai_content_data:
                            conclusion = ai_content_data[key]
                            logger.info(f"找到AI分析结论，键名: {key}")
                            break
                    
                    if conclusion:
                        print(f"{DETAIL_COLOR}  • AI分析结论: {conclusion}{RESET_COLOR}")
                        
                        # 尝试从结论中推断AI生成可能性
                        if isinstance(conclusion, str):
                            if any(term in conclusion.lower() for term in ["人工智能生成", "ai生成", "机器生成", "很可能是ai", "生成式ai"]):
                                print(f"{WARNING_COLOR}  • 推断结果: 文本很可能由AI生成{RESET_COLOR}")
                            elif any(term in conclusion.lower() for term in ["部分特征", "混合特征", "ai辅助"]):
                                print(f"{WARNING_COLOR}  • 推断结果: 文本可能是AI辅助创作{RESET_COLOR}")
                            elif any(term in conclusion.lower() for term in ["人类特征", "人工撰写", "真实作者"]):
                                print(f"{SUCCESS_COLOR}  • 推断结果: 文本具有较强的人类写作特征{RESET_COLOR}")
                    else:
                        print(f"{WARNING_COLOR}  • 未找到明确的AI生成内容评分或结论{RESET_COLOR}")
                        print(f"{DETAIL_COLOR}  • 以下为原始AI检测数据的关键字段:{RESET_COLOR}")
                        # 显示关键字段，帮助用户理解数据
                        key_fields = [k for k in ai_content_data.keys() if k not in ["raw_data", "detail_data"]][:5]
                        for k in key_fields:
                            print(f"{DETAIL_COLOR}    - {k}: {str(ai_content_data[k])[:50]}...{RESET_COLOR}")
                except Exception as e:
                    logger.error(f"处理AI分析结论推断时出错: {str(e)}")
                    print(f"{ERROR_COLOR}  • 处理AI分析结论时出错: {str(e)}{RESET_COLOR}")
                
                # 添加AI详细分析部分，放在if/else的外部，因为无论是否找到ai_score都应尝试分析详细特征
                try:
                    # 尝试提取详细的特征分析
                    detailed_scores = None
                    # 尝试从不同的可能字段名获取详细评分
                    for key in ["detailed_analysis", "deepseek_scores", "scores", "详细评分", "features", "分项评分"]:
                        if key in ai_content_data and ai_content_data[key]:
                            detailed_scores = ai_content_data[key]
                            logger.info(f"找到AI生成内容详细评分，键名: {key}")
                            break
                    
                    # 如果直接键没找到，尝试在嵌套字典中查找
                    if not detailed_scores:
                        for key, value in ai_content_data.items():
                            if isinstance(value, dict) and any(sk in value for sk in ["score", "expression_pattern", "vocabulary_diversity", "人类特征"]):
                                detailed_scores = value
                                logger.info(f"从嵌套字典中找到AI生成内容详细评分: {key}")
                                break
                    
                    # 如果找到了详细特征评分，但没有找到总体评分，则计算平均值作为总体评分
                    if detailed_scores and isinstance(detailed_scores, dict) and ai_score is None:
                        feature_scores = []
                        for key, value in detailed_scores.items():
                            try:
                                if isinstance(value, (int, float)) and 0 <= float(value) <= 1:
                                    feature_scores.append(float(value))
                            except:
                                pass
                        
                        if feature_scores:
                            # 计算平均值作为总体评分
                            avg_score = sum(feature_scores) / len(feature_scores)
                            ai_score = avg_score
                            logger.info(f"从详细特征评分计算出总体评分: {ai_score:.2f}")
                            
                            # 显示计算得出的总体评分
                            ai_score_float = avg_score
                            score_color = SUCCESS_COLOR if ai_score_float >= 0.7 else (WARNING_COLOR if ai_score_float >= 0.5 else ERROR_COLOR)
                            print(f"{score_color}  • 人类写作特征评分: {ai_score_float:.2f} {get_progress_bar(ai_score_float)}{RESET_COLOR}")
                            print(f"{DETAIL_COLOR}  • {get_ai_content_description(ai_score_float)}{RESET_COLOR}")
                            
                            # 添加AI生成概率
                            ai_probability = max(0, min(1, 1 - ai_score_float))
                            ai_prob_color = SUCCESS_COLOR if ai_probability <= 0.3 else (WARNING_COLOR if ai_probability <= 0.5 else ERROR_COLOR)
                            print(f"{ai_prob_color}  • AI生成概率: {ai_probability:.1%}{RESET_COLOR}")
                    
                    # 显示详细特征分析
                    if detailed_scores and isinstance(detailed_scores, dict):
                        print(f"\n{SECTION_COLOR}  AI特征详细分析:{RESET_COLOR}")
                        
                        # 定义常见评分项的描述
                        score_descriptions = {
                            "expression_pattern": "表达模式 (句式结构的人类特征)",
                            "vocabulary_diversity": "词汇多样性 (用词丰富度的人类特征)",
                            "sentence_variation": "句子变化 (句式变化多样性的人类特征)",
                            "context_coherence": "上下文连贯性 (逻辑流畅度的人类特征)",
                            "human_traits": "人类特征 (文本中的人类思维特征)",
                            "表达模式": "表达模式 (句式结构的人类特征)",
                            "词汇多样性": "词汇多样性 (用词丰富度的人类特征)",
                            "句子变化": "句子变化 (句式变化多样性的人类特征)",
                            "上下文连贯性": "上下文连贯性 (逻辑流畅度的人类特征)",
                            "人类特征": "人类特征 (文本中的人类思维特征)"
                        }
                        
                        # 计算有效评分项
                        valid_scores = 0
                        for key, value in detailed_scores.items():
                            try:
                                if isinstance(value, (int, float)) and 0 <= float(value) <= 1:
                                    valid_scores += 1
                            except:
                                pass
                        
                        if valid_scores > 0:
                            for key, value in detailed_scores.items():
                                try:
                                    if isinstance(value, (int, float)):
                                        score = validate_score(value, f"AI生成内容.{key}")
                                        score_color = SUCCESS_COLOR if score >= 0.7 else (WARNING_COLOR if score >= 0.5 else ERROR_COLOR)
                                        key_description = score_descriptions.get(key, key)
                                        print(f"{score_color}    • {key_description}: {score:.2f} {get_progress_bar(score)}{RESET_COLOR}")
                                except ValueError:
                                    logger.warning(f"AI生成内容详细评分'{key}'无效: {value}")
                        else:
                            print(f"{WARNING_COLOR}    • 未找到有效的详细评分项{RESET_COLOR}")
                    
                    # 尝试提取文本分析结论
                    text_analysis = None
                    for key in ["analysis", "deepseek_analysis", "text_analysis", "分析结论", "analysis_details", "检测结论", "结论说明"]:
                        if key in ai_content_data and ai_content_data[key]:
                            text_analysis = ai_content_data[key]
                            logger.info(f"找到AI生成内容文本分析，键名: {key}")
                            break
                    
                    if text_analysis:
                        print(f"\n{SECTION_COLOR}  分析结论:{RESET_COLOR}")
                        if isinstance(text_analysis, str):
                            print(f"{DETAIL_COLOR}    • {text_analysis}{RESET_COLOR}")
                        elif isinstance(text_analysis, list):
                            for point in text_analysis:
                                print(f"{DETAIL_COLOR}    • {point}{RESET_COLOR}")
                except Exception as e:
                    logger.error(f"处理AI生成内容检测数据时出错: {str(e)}")
                    print(f"{ERROR_COLOR}  • AI生成内容检测数据处理错误: {str(e)}{RESET_COLOR}")
                    # 尝试直接显示原始数据
                    try:
                        print(f"{DETAIL_COLOR}  • 原始AI生成内容数据: {str(ai_content_data)[:200]}...{RESET_COLOR}")
                    except:
                        pass
        else:
            # 尝试从deepseek_data中提取AI内容相关信息
            ai_related_info = {}
            if isinstance(deepseek_data, dict):
                # 搜索deepseek_data中可能与AI相关的键
                for key, value in deepseek_data.items():
                    if any(term in key.lower() for term in ["ai", "人工智能", "生成", "机器"]):
                        ai_related_info[key] = value
            
            if ai_related_info:
                print(f"{WARNING_COLOR}  • 未找到标准格式的AI生成内容检测数据，但发现相关信息{RESET_COLOR}")
                print(f"{DETAIL_COLOR}  • 相关信息: {str(ai_related_info)[:200]}...{RESET_COLOR}")
            else:
                print(f"{WARNING_COLOR}  • 未找到AI生成内容检测数据{RESET_COLOR}")
                print(f"{DETAIL_COLOR}  • 建议：启用AI生成内容检测功能以评估文本真实性{RESET_COLOR}")
        
        # 2. 安全获取和处理 DeepSeek 数据
        logger.debug("开始处理DeepSeek分析数据")
        deepseek_data = result.get("原始分析数据", {}).get("deepseek_full_response", {})
        if not isinstance(deepseek_data, dict):
            logger.warning("DeepSeek数据格式无效")
            deepseek_data = {}
        
        # 3. 处理主要评分
        logger.debug("开始处理主要评分指标")
        main_scores = {}
        
        # 首先尝试从评分详情中获取
        if isinstance(scoring_details, dict):
            for key, value in scoring_details.items():
                if key.startswith(("内容真实性", "信息准确性", "来源可靠性", "引用质量", "语言客观性", "逻辑连贯性")):
                    clean_key = key.split("_")[-1] if "_" in key else key
                    try:
                        main_scores[clean_key] = validate_score(value, f"评分详情.{key}")
                        logger.debug(f"从评分详情获取到{clean_key}评分: {main_scores[clean_key]}")
                    except ValueError:
                        logger.warning(f"评分详情中的{key}评分无效: {value}")
                        continue
        
        # 如果评分详情中没有找到，则从deepseek数据中获取
        if not main_scores:
            logger.debug("尝试从DeepSeek数据获取主要评分")
            main_scores = deepseek_data.get("各大类评分", {})
        
        if main_scores and isinstance(main_scores, dict):
            print(f"\n{SECTION_COLOR}2. 主要评分指标:{RESET_COLOR}")
            try:
                # 处理主要维度评分
                dimensions = {
                    "内容真实性": "新闻内容与事实的符合程度",
                    "信息准确性": "信息的精确性和完整性",
                    "来源可靠性": "信息来源的权威性和可信度",
                    "引用质量": "引用的准确性和相关性",
                    "语言客观性": "语言表达的中立性和客观性",
                    "逻辑连贯性": "内容的逻辑性和连贯性"
                }
                
                for dim, desc in dimensions.items():
                    score = main_scores.get(dim)
                    if score is not None:
                        try:
                            score_float = validate_score(score, f"主要评分.{dim}")
                            color = SUCCESS_COLOR if score_float >= 0.8 else (WARNING_COLOR if score_float >= 0.6 else ERROR_COLOR)
                            print(f"{color}  • {dim}: {score_float:.2f} {get_progress_bar(score_float)}{RESET_COLOR}")
                            print(f"{DETAIL_COLOR}    - {desc}{RESET_COLOR}")
                            logger.debug(f"{dim}评分: {score_float:.2f}")
                        except ValueError:
                            logger.warning(f"{dim}评分无效: {score}")
                            print(f"{ERROR_COLOR}  • {dim}: 数据无效{RESET_COLOR}")
            except Exception as e:
                logger.error(f"处理主要评分指标时出错: {str(e)}")
                print(f"{ERROR_COLOR}  • 评分数据处理错误{RESET_COLOR}")
        
        # 4. 处理细分评分
        logger.debug("开始处理细分评分指标")
        sub_scores = deepseek_data.get("细分点评分", {})
        if sub_scores and isinstance(sub_scores, dict):
            print(f"\n{SECTION_COLOR}3. 细分评分指标:{RESET_COLOR}")
            
            # 按类别组织细分评分
            categories = {
                "内容真实性": [],
                "信息准确性": [],
                "来源可靠性": [],
                "引用质量": [],
                "语言客观性": [],
                "逻辑连贯性": []
            }
            
            for key, value in sub_scores.items():
                for category in categories:
                    if key.startswith(f"{category}_"):
                        try:
                            score = validate_score(value, f"细分评分.{key}")
                            categories[category].append((key.split("_")[-1], score))
                            logger.debug(f"细分评分 {key}: {score:.2f}")
                        except ValueError:
                            logger.warning(f"细分评分{key}无效: {value}")
            
            # 显示细分评分
            for category, scores in categories.items():
                if scores:
                    print(f"{SUBHEADER_COLOR}  ▶ {category}相关指标:{RESET_COLOR}")
                    for name, score in scores:
                        color = SUCCESS_COLOR if score >= 0.8 else (WARNING_COLOR if score >= 0.6 else ERROR_COLOR)
                        print(f"{color}    • {name}: {score:.2f} {get_progress_bar(score)}{RESET_COLOR}")
        
        # 二、来源可靠性与引用分析
        print(f"\n{SUBHEADER_COLOR}二、来源可靠性与引用分析{RESET_COLOR}")
        print(f"{DETAIL_COLOR}{'━' * 70}{RESET_COLOR}")
        
        # 5. 处理引用分析
        logger.debug("开始处理引用分析")
        citation_data = result.get("citation_analysis", {})
        if citation_data and isinstance(citation_data, dict):
            print(f"{SECTION_COLOR}1. 引用统计:{RESET_COLOR}")
            try:
                # 基本引用统计
                total_citations = int(citation_data.get("total_citations", 0))
                verified_citations = int(citation_data.get("verified_citations", 0))
                authority_score = validate_score(citation_data.get("authority_score", 0), "引用权威性")
                diversity_score = validate_score(citation_data.get("diversity_score", 0), "引用多样性")
                
                verification_rate = verified_citations / total_citations if total_citations > 0 else 0
                logger.info(f"引用统计: 总数={total_citations}, 已验证={verified_citations}, 验证率={verification_rate:.1%}")
                
                # 根据验证率选择颜色
                verification_color = SUCCESS_COLOR if verification_rate >= 0.8 else (WARNING_COLOR if verification_rate >= 0.5 else ERROR_COLOR)
                authority_color = SUCCESS_COLOR if authority_score >= 0.8 else (WARNING_COLOR if authority_score >= 0.6 else ERROR_COLOR)
                diversity_color = SUCCESS_COLOR if diversity_score >= 0.8 else (WARNING_COLOR if diversity_score >= 0.6 else ERROR_COLOR)
                
                print(f"{DETAIL_COLOR}  • 引用总数: {total_citations} 处{RESET_COLOR}")
                print(f"{verification_color}  • 验证通过数: {verified_citations} 处 (验证率: {verification_rate:.1%}){RESET_COLOR}")
                print(f"{authority_color}  • 来源权威性: {authority_score:.2f} {get_progress_bar(authority_score)}{RESET_COLOR}")
                print(f"{diversity_color}  • 来源多样性: {diversity_score:.2f} {get_progress_bar(diversity_score)}{RESET_COLOR}")
                
                # 引用详情
                if "citation_details" in citation_data:
                    print(f"\n{SECTION_COLOR}引用详情:{RESET_COLOR}")
                    for i, cite in enumerate(citation_data["citation_details"], 1):
                        logger.debug(f"处理第{i}个引用: {cite}")
                        verified = cite.get('verified', False)
                        status_color = SUCCESS_COLOR if verified else WARNING_COLOR
                        print(f"{DETAIL_COLOR}  • 引用{i}:{RESET_COLOR}")
                        print(f"{DETAIL_COLOR}    - 内容: {cite.get('quote', '未知')[:100]}...{RESET_COLOR}")
                        print(f"{DETAIL_COLOR}    - 来源: {cite.get('source', '未知')}{RESET_COLOR}")
                        print(f"{status_color}    - 验证状态: {'✓ 已验证' if verified else '✗ 未验证'}{RESET_COLOR}")
                        if "verification_method" in cite:
                            print(f"{DETAIL_COLOR}    - 验证方法: {cite['verification_method']}{RESET_COLOR}")
                        if "confidence" in cite:
                            print(f"{DETAIL_COLOR}    - 置信度: {cite['confidence']:.2%}{RESET_COLOR}")
            except Exception as e:
                logger.error(f"处理引用分析时出错: {str(e)}")
                print(f"{ERROR_COLOR}  • 引用数据处理错误{RESET_COLOR}")
        else:
            print(f"{WARNING_COLOR}  • 未找到引用分析数据{RESET_COLOR}")
            print(f"{DETAIL_COLOR}  • 建议：进行引用分析以提高内容可信度评估{RESET_COLOR}")
        
        # 6. 处理来源评分
        print(f"\n{SECTION_COLOR}2. 来源评分与分析:{RESET_COLOR}")
        
        # 尝试从不同位置提取来源数据
        source_quality_data = None
        for key in ["source_quality", "来源质量", "domain_credibility", "域名可信度"]:
            if key in result and result[key]:
                source_quality_data = result[key]
                logger.info(f"找到来源质量数据，键名: {key}")
                break
        
        if main_scores and isinstance(main_scores, dict):
            try:
                source_reliability = float(main_scores.get("来源可靠性", 0))
                citation_quality = float(main_scores.get("引用质量", 0))
                
                source_color = SUCCESS_COLOR if source_reliability >= 0.8 else (WARNING_COLOR if source_reliability >= 0.6 else ERROR_COLOR)
                citation_color = SUCCESS_COLOR if citation_quality >= 0.8 else (WARNING_COLOR if citation_quality >= 0.6 else ERROR_COLOR)
                
                print(f"{source_color}  • 来源可靠性: {source_reliability:.2f} {get_progress_bar(source_reliability)}{RESET_COLOR}")
                print(f"{citation_color}  • 引用质量: {citation_quality:.2f} {get_progress_bar(citation_quality)}{RESET_COLOR}")
                
                # 解释评分含义
                if source_reliability >= 0.8:
                    print(f"{DETAIL_COLOR}    - 来源高度可靠，包含权威或官方信息{RESET_COLOR}")
                elif source_reliability >= 0.6:
                    print(f"{DETAIL_COLOR}    - 来源基本可靠，但可能包含部分未经验证信息{RESET_COLOR}")
                else:
                    print(f"{DETAIL_COLOR}    - 来源可靠性存疑，建议核实关键信息{RESET_COLOR}")
                
                if citation_quality >= 0.8:
                    print(f"{DETAIL_COLOR}    - 引用质量高，引用准确且来源可靠{RESET_COLOR}")
                elif citation_quality >= 0.6:
                    print(f"{DETAIL_COLOR}    - 引用质量一般，部分引用需要核实{RESET_COLOR}")
                else:
                    print(f"{DETAIL_COLOR}    - 引用质量差，多数引用无法验证{RESET_COLOR}")
            except (ValueError, TypeError):
                print(f"{ERROR_COLOR}  • 评分数据格式错误{RESET_COLOR}")
        
        # 显示详细的来源质量数据
        if source_quality_data and isinstance(source_quality_data, dict):
            print(f"\n{SECTION_COLOR}3. 详细来源分析:{RESET_COLOR}")
            
            # 域名信息
            domain_trust = source_quality_data.get("domain_trust", source_quality_data.get("trust_level", "未知"))
            if domain_trust != "未知":
                trust_color = SUCCESS_COLOR if "高" in domain_trust else (WARNING_COLOR if "中" in domain_trust else ERROR_COLOR)
                print(f"{trust_color}  • 域名可信度: {domain_trust}{RESET_COLOR}")
            
            # 来源统计
            source_count = source_quality_data.get("source_count", 0)
            if source_count > 0:
                count_color = SUCCESS_COLOR if source_count >= 5 else (WARNING_COLOR if source_count >= 2 else ERROR_COLOR)
                print(f"{count_color}  • 引用来源数量: {source_count} 个{RESET_COLOR}")
            
            # 权威来源
            authority_sources = source_quality_data.get("authority_sources", 0)
            if authority_sources > 0:
                auth_color = SUCCESS_COLOR if authority_sources >= 3 else (WARNING_COLOR if authority_sources >= 1 else ERROR_COLOR)
                print(f"{auth_color}  • 权威来源数量: {authority_sources} 个{RESET_COLOR}")
            
            # 直接引用
            direct_quotes = source_quality_data.get("direct_quotes", 0)
            if direct_quotes > 0:
                quote_color = SUCCESS_COLOR if direct_quotes >= 3 else (WARNING_COLOR if direct_quotes >= 1 else ERROR_COLOR)
                print(f"{quote_color}  • 直接引用数量: {direct_quotes} 个{RESET_COLOR}")
            
            # 来源列表
            source_list = source_quality_data.get("sources", source_quality_data.get("source_list", []))
            if source_list and isinstance(source_list, list) and len(source_list) > 0:
                print(f"\n{DETAIL_COLOR}  • 主要来源列表:{RESET_COLOR}")
                for i, source in enumerate(source_list[:5], 1):  # 最多显示5个来源
                    if isinstance(source, dict):
                        name = source.get("name", "未知来源")
                        reliability = source.get("reliability", 0)
                        rel_color = SUCCESS_COLOR if reliability >= 0.8 else (WARNING_COLOR if reliability >= 0.6 else ERROR_COLOR)
                        print(f"{DETAIL_COLOR}    {i}. {name}{RESET_COLOR}")
                        if reliability > 0:
                            print(f"{rel_color}       可信度: {reliability:.2f} {get_progress_bar(reliability)}{RESET_COLOR}")
                    else:
                        print(f"{DETAIL_COLOR}    {i}. {source}{RESET_COLOR}")
                
                if len(source_list) > 5:
                    print(f"{DETAIL_COLOR}    ... 等共 {len(source_list)} 个来源{RESET_COLOR}")
            
            # 域名信息
            if "domain_info" in source_quality_data:
                domain_info = source_quality_data["domain_info"]
                if isinstance(domain_info, dict) and domain_info:
                    print(f"\n{DETAIL_COLOR}  • 域名信息:{RESET_COLOR}")
                    if "registration_date" in domain_info:
                        print(f"{DETAIL_COLOR}    - 注册日期: {domain_info['registration_date']}{RESET_COLOR}")
                    if "reputation" in domain_info:
                        rep = domain_info["reputation"]
                        rep_color = SUCCESS_COLOR if rep >= 8 else (WARNING_COLOR if rep >= 5 else ERROR_COLOR)
                        print(f"{rep_color}    - 网站声誉评分: {rep}/10{RESET_COLOR}")
                    if "category" in domain_info:
                        print(f"{DETAIL_COLOR}    - 网站类别: {domain_info['category']}{RESET_COLOR}")
        
        # 如果没有任何来源数据
        if not source_quality_data and not (main_scores and isinstance(main_scores, dict) and ("来源可靠性" in main_scores or "引用质量" in main_scores)):
            print(f"{WARNING_COLOR}  • 未找到详细的来源分析数据{RESET_COLOR}")
            print(f"{DETAIL_COLOR}  • 建议：进行更详细的来源分析以提高评估准确性{RESET_COLOR}")
        
        # 三、语言分析
        print(f"\n{SUBHEADER_COLOR}三、语言分析{RESET_COLOR}")
        print(f"{DETAIL_COLOR}{'━' * 70}{RESET_COLOR}")
        
        # 7. 处理语言中立性
        logger.debug("开始处理语言中立性分析")
        neutrality = result.get("语言中立性", {})
        if neutrality and isinstance(neutrality, dict):
            print(f"{SECTION_COLOR}1. 语言中立性评分:{RESET_COLOR}")
            
            # 总体评分
            if "score" in neutrality:
                try:
                    overall_score = validate_score(neutrality["score"], "语言中立性总分")
                    score_color = SUCCESS_COLOR if overall_score >= 0.8 else (WARNING_COLOR if overall_score >= 0.6 else ERROR_COLOR)
                    print(f"{score_color}  • 总体评分: {overall_score:.2f} {get_progress_bar(overall_score)}{RESET_COLOR}")
                    logger.info(f"语言中立性总分: {overall_score:.2f}")
                except ValueError:
                    logger.warning("语言中立性总分无效")
            
            # DeepSeek详细评分
            scores = neutrality.get("deepseek_scores", {})
            if scores and isinstance(scores, dict):
                print(f"\n{SECTION_COLOR}2. 详细评分指标:{RESET_COLOR}")
                try:
                    score_descriptions = {
                        "情感词汇": "文本中情感色彩词汇的使用程度",
                        "情感平衡": "正面与负面情感的平衡程度",
                        "极端表述": "极端或绝对化表述的使用程度",
                        "煽动性表达": "可能引起强烈情感反应的表达",
                        "主观评价": "个人观点和主观判断的程度"
                    }
                    
                    for key, value in scores.items():
                        try:
                            score = validate_score(value, f"语言中立性.{key}")
                            score_color = SUCCESS_COLOR if score >= 0.8 else (WARNING_COLOR if score >= 0.6 else ERROR_COLOR)
                            print(f"{score_color}  • {key}: {score:.2f} {get_progress_bar(score)}{RESET_COLOR}")
                            if key in score_descriptions:
                                print(f"{DETAIL_COLOR}    - {score_descriptions[key]}{RESET_COLOR}")
                            logger.debug(f"语言中立性 {key}: {score:.2f}")
                        except ValueError:
                            logger.warning(f"语言中立性评分{key}无效: {value}")
                except Exception as e:
                    logger.error(f"处理语言中立性详细评分时出错: {str(e)}")
            
            # DeepSeek分析结果
            if "deepseek_analysis" in neutrality:
                print(f"\n{SECTION_COLOR}3. 详细分析:{RESET_COLOR}")
                analysis = neutrality["deepseek_analysis"]
                if isinstance(analysis, str):
                    print(f"{DETAIL_COLOR}  • {analysis}{RESET_COLOR}")
                elif isinstance(analysis, list):
                    for point in analysis:
                        print(f"{DETAIL_COLOR}  • {point}{RESET_COLOR}")
        
        # 8. 处理语言评分
        logger.debug("开始处理语言评分")
        if main_scores and isinstance(main_scores, dict):
            print(f"\n{SECTION_COLOR}语言表达评分:{RESET_COLOR}")
            try:
                language_scores = {
                    "语言客观性": "语言表达的客观中立程度",
                    "逻辑连贯性": "内容的逻辑性和连贯性",
                    "表达准确性": "用词和表达的准确程度",
                    "专业性": "专业术语和概念的使用准确性"
                }
                
                for key, desc in language_scores.items():
                    if key in main_scores:
                        try:
                            score = validate_score(main_scores[key], f"语言评分.{key}")
                            score_color = SUCCESS_COLOR if score >= 0.8 else (WARNING_COLOR if score >= 0.6 else ERROR_COLOR)
                            print(f"{score_color}  • {key}: {score:.2f} {get_progress_bar(score)}{RESET_COLOR}")
                            print(f"{DETAIL_COLOR}    - {desc}{RESET_COLOR}")
                            logger.debug(f"语言评分 {key}: {score:.2f}")
                        except ValueError:
                            logger.warning(f"语言评分{key}无效: {main_scores[key]}")
            except Exception as e:
                logger.error(f"处理语言评分时出错: {str(e)}")
        
        # 添加交叉验证部分
        print(f"\n{SUBHEADER_COLOR}四、交叉验证结果{RESET_COLOR}")
        print(f"{DETAIL_COLOR}{'━' * 70}{RESET_COLOR}")
        
        # 优化交叉验证数据的显示
        has_cv_data = False
        
        # 检查是否有标准格式的交叉验证数据
        if cross_validation_data and isinstance(cross_validation_data, dict):
            has_cv_data = True
            print(f"{SECTION_COLOR}交叉验证评估:{RESET_COLOR}")
            try:
                # 提取验证点
                verification_points = []
                # 尝试多个可能的键名
                for key in ["verification_points", "claims", "验证点", "关键声明", "points"]:
                    if key in cross_validation_data and cross_validation_data[key]:
                        verification_points = cross_validation_data[key]
                        logger.info(f"找到验证点数据，键名: {key}")
                        break
                
                # 提取来源信息
                sources = []
                for key in ["sources", "verified_sources", "相关来源", "related_sources"]:
                    if key in cross_validation_data and cross_validation_data[key]:
                        sources = cross_validation_data[key]
                        logger.info(f"找到来源数据，键名: {key}")
                        break
                
                # 显示验证点
                if verification_points:
                    print(f"\n{SECTION_COLOR}验证点分析:{RESET_COLOR}")
                    for i, point in enumerate(verification_points, 1):
                        if isinstance(point, dict):
                            # 检查是否包含key_points键，如果包含则说明是多个验证点的集合
                            if "key_points" in point and isinstance(point["key_points"], list):
                                for j, sub_point in enumerate(point["key_points"], 1):
                                    # 获取内容
                                    if isinstance(sub_point, dict) and "内容" in sub_point:
                                        content = sub_point["内容"]
                                        importance = sub_point.get("重要性", "中")
                                        score_color = SUCCESS_COLOR if "验证评分" in point and point["验证评分"] >= 0.7 else (WARNING_COLOR if "验证评分" in point and point["验证评分"] >= 0.5 else ERROR_COLOR)
                                        print(f"{score_color}  • 验证点 {i}.{j}: {content}{RESET_COLOR}")
                                        if "验证评分" in point:
                                            print(f"{score_color}    得分: {point['验证评分']:.2f} {get_progress_bar(point['验证评分'])}{RESET_COLOR}")
                                        
                                        # 显示重要性
                                        print(f"{DETAIL_COLOR}    重要性: {importance}{RESET_COLOR}")
                                        
                                        # 如果有验证结论，显示它
                                        if "验证结论" in point and point["验证结论"]:
                                            print(f"{DETAIL_COLOR}    结论: {point['验证结论']}{RESET_COLOR}")
                                continue
                            
                            # 获取内容，尝试多个可能的键名
                            content = None
                            for content_key in ["内容", "验证内容", "content", "claim", "statement"]:
                                if content_key in point and point[content_key]:
                                    content = point[content_key]
                                    break
                            
                            if not content:
                                content = "未知内容"
                                
                            # 获取分数，尝试多个可能的键名
                            score = None
                            for score_key in ["验证评分", "评分", "score", "confidence"]:
                                if score_key in point and point[score_key] is not None:
                                    try:
                                        score = float(point[score_key])
                                        break
                                    except (ValueError, TypeError):
                                        pass
                            
                            if score is None:
                                score = 0.5
                                
                            score_color = SUCCESS_COLOR if score >= 0.7 else (WARNING_COLOR if score >= 0.5 else ERROR_COLOR)
                            print(f"{score_color}  • 验证点 {i}: {content}{RESET_COLOR}")
                            print(f"{score_color}    得分: {score:.2f} {get_progress_bar(score)}{RESET_COLOR}")
                            
                            # 如果有验证结论，显示它
                            if "验证结论" in point and point["验证结论"]:
                                print(f"{DETAIL_COLOR}    结论: {point['验证结论']}{RESET_COLOR}")
                            
                            # 如果有搜索结果数量，显示它
                            if "搜索结果数量" in point:
                                result_count = point["搜索结果数量"]
                                if result_count == 0:
                                    print(f"{WARNING_COLOR}    搜索结果: 未找到相关内容{RESET_COLOR}")
                                else:
                                    print(f"{DETAIL_COLOR}    搜索结果: {result_count}个相关内容{RESET_COLOR}")
                                    
                            # 显示搜索结果链接和摘要
                            if "搜索结果摘要" in point and point["搜索结果摘要"]:
                                print(f"{DETAIL_COLOR}    相关信息摘要:{RESET_COLOR}")
                                for j, summary in enumerate(point["搜索结果摘要"], 1):
                                    if summary:
                                        # 摘要限制在100字符以内，显示为间断摘要
                                        if len(summary) > 100:
                                            formatted_summary = summary[:40] + "..." + summary[len(summary)-40:]
                                        else:
                                            formatted_summary = summary
                                        print(f"{DETAIL_COLOR}      {j}. {formatted_summary}{RESET_COLOR}")
                            
                            # 获取搜索结果链接
                            search_results = None
                            for results_key in ["search_results", "搜索结果", "results", "相关信息"]:
                                if results_key in point and point[results_key]:
                                    search_results = point[results_key]
                                    break
                            
                            # 如果找到了搜索结果链接，显示它们
                            if search_results and isinstance(search_results, list):
                                print(f"{DETAIL_COLOR}    相关链接:{RESET_COLOR}")
                                for j, result_item in enumerate(search_results[:3], 1):  # 限制显示3个链接
                                    if isinstance(result_item, dict):
                                        url = result_item.get("url", "")
                                        title = result_item.get("title", "未知标题")
                                        print(f"{DETAIL_COLOR}      {j}. {title}{RESET_COLOR}")
                                        print(f"{INFO_COLOR}         {url}{RESET_COLOR}")
                                        
                                        # 如果有内容摘要，显示间断摘要
                                        content = result_item.get("content", "")
                                        if content:
                                            if len(content) > 100:
                                                formatted_content = content[:40] + "..." + content[len(content)-40:]
                                            else:
                                                formatted_content = content
                                            print(f"{NEUTRAL_COLOR}         摘要: {formatted_content}{RESET_COLOR}")
                                    elif isinstance(result_item, str) and ("http://" in result_item or "https://" in result_item):
                                        print(f"{INFO_COLOR}      {j}. {result_item}{RESET_COLOR}")
                                
                                if len(search_results) > 3:
                                    print(f"{DETAIL_COLOR}      ... 等共 {len(search_results)} 个相关链接{RESET_COLOR}")
                else:
                    # 如果没有验证点但已通过测试验证了SearXNG可用，显示提示信息
                    print(f"\n{WARNING_COLOR}  • 未能成功提取验证点，但搜索服务正常{RESET_COLOR}")
                    print(f"{DETAIL_COLOR}  • 建议: 请检查文本是否包含可验证的事实陈述{RESET_COLOR}")
                
                # 显示来源信息
                if sources:
                    print(f"\n{SECTION_COLOR}相关来源分析:{RESET_COLOR}")
                    for i, source in enumerate(sources, 1):
                        if isinstance(source, dict):
                            url = source.get("url", "未知URL")
                            reliability = source.get("reliability", source.get("credibility", 0.5))
                            rel_color = SUCCESS_COLOR if reliability >= 0.7 else (WARNING_COLOR if reliability >= 0.5 else ERROR_COLOR)
                            print(f"{rel_color}  • 来源 {i}: {url}{RESET_COLOR}")
                            print(f"{rel_color}    可信度: {reliability:.2f} {get_progress_bar(reliability)}{RESET_COLOR}")
                
                # 显示整体评分
                cv_score = cross_validation_data.get("score", cross_validation_data.get("overall_score", cross_validation_data.get("总体可信度", 0.5)))
                score_color = SUCCESS_COLOR if cv_score >= 0.7 else (WARNING_COLOR if cv_score >= 0.5 else ERROR_COLOR)
                print(f"\n{score_color}  • 交叉验证总分: {cv_score:.2f} {get_progress_bar(cv_score)}{RESET_COLOR}")
                
                # 显示验证结论
                if "验证结论" in cross_validation_data and cross_validation_data["验证结论"]:
                    print(f"{DETAIL_COLOR}  • 验证结论: {cross_validation_data['验证结论']}{RESET_COLOR}")
                
                # 显示时效性
                timeliness = cross_validation_data.get("timeliness", cross_validation_data.get("时效性", "未知"))
                print(f"{DETAIL_COLOR}  • 时效性评估: {timeliness}{RESET_COLOR}")
                
                # 显示可信内容总结 (新增部分)
                if "可信内容总结" in cross_validation_data and cross_validation_data["可信内容总结"]:
                    print(f"\n{SECTION_COLOR}可信内容总结:{RESET_COLOR}")
                    summary = cross_validation_data["可信内容总结"]
                    # 使用醒目颜色显示总结
                    print(f"{SUCCESS_COLOR}  {summary}{RESET_COLOR}")
                
                # 显示问题点 - 修改此部分
                # 计算验证点中无结果的数量和来源数量
                no_result_count = 0
                source_count = 0
                search_results_count = 0
                
                # 首先尝试计算无结果的验证点
                if verification_points and isinstance(verification_points, list):
                    no_result_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("搜索结果数量", 0) == 0)
                    
                    # 同时尝试从验证点中获取搜索结果总数
                    for p in verification_points:
                        if isinstance(p, dict) and "搜索结果" in p and isinstance(p["搜索结果"], int):
                            search_results_count += p["搜索结果"]
                        elif isinstance(p, dict) and "搜索结果数量" in p and isinstance(p["搜索结果数量"], int):
                            search_results_count += p["搜索结果数量"]
                
                # 尝试获取来源数量
                # 直接使用来源列表长度
                if sources and isinstance(sources, list):
                    source_count = len(sources)
                # 尝试从交叉验证数据中获取来源数量
                else:
                    # 尝试多种可能的键名
                    for key in ["source_count", "sources_count", "搜索结果总数", "来源数量", "相关来源数"]:
                        if key in cross_validation_data and isinstance(cross_validation_data[key], (int, float, str)):
                            try:
                                source_count = int(cross_validation_data[key])
                                break
                            except (ValueError, TypeError):
                                pass
                
                # 如果搜索结果数大于0但来源计数为0，使用搜索结果数作为来源计数的估计
                if search_results_count > 0 and source_count == 0:
                    logger.info(f"使用搜索结果数量({search_results_count})作为来源数量估计")
                    source_count = search_results_count
                
                # 只有在确实有验证点但没有找到结果，或来源太少时才显示问题
                has_problems = False
                
                if verification_points:
                    # 只有当来源确实太少(小于2)且搜索结果也不足时才显示来源不足问题
                    if source_count < 2 and search_results_count < 3:
                        has_problems = True
                        print(f"\n{SECTION_COLOR}交叉验证问题:{RESET_COLOR}")
                        print(f"{WARNING_COLOR}  • 缺乏足够的交叉验证来源 (仅{source_count}个){RESET_COLOR}")
                        print(f"{DETAIL_COLOR}    - 建议：建议寻找更多独立来源验证信息{RESET_COLOR}")
                    
                    # 无论来源数量如何，如果有验证点没有找到结果，都显示这个问题
                    if no_result_count > 0:
                        if not has_problems:
                            has_problems = True
                            print(f"\n{SECTION_COLOR}交叉验证问题:{RESET_COLOR}")
                            
                        print(f"{WARNING_COLOR}  • {no_result_count}个验证点没有找到相关信息{RESET_COLOR}")
                        print(f"{DETAIL_COLOR}    - 这些验证点可能需要额外验证{RESET_COLOR}")
                        print(f"{DETAIL_COLOR}    - 建议：针对这些特定信息点进行额外验证{RESET_COLOR}")
                
            except Exception as e:
                logger.error(f"处理交叉验证数据时出错: {str(e)}")
                print(f"{ERROR_COLOR}  • 交叉验证数据处理错误: {str(e)}{RESET_COLOR}")
        
        # 检查权重中是否有交叉验证的贡献
        if not has_cv_data and "交叉验证" in weights:
            print(f"{SECTION_COLOR}交叉验证评估:{RESET_COLOR}")
            cv_weight = weights["交叉验证"]
            print(f"{DETAIL_COLOR}  • 交叉验证在总评分中的贡献比例: {cv_weight:.2f}{RESET_COLOR}")
            print(f"{WARNING_COLOR}  • 交叉验证详细数据不可用，但已纳入总评分计算{RESET_COLOR}")
            print(f"{DETAIL_COLOR}  • 默认交叉验证评分用于计算: 0.5{RESET_COLOR}")
            has_cv_data = True
        
        # 无交叉验证数据的情况
        if not has_cv_data:
            # 检查日志中是否记录了交叉验证信息
            if "validation" in str(result).lower() or "交叉验证" in str(result):
                print(f"{WARNING_COLOR}  • 发现交叉验证相关信息，但格式无法解析{RESET_COLOR}")
                print(f"{DETAIL_COLOR}  • 建议：查看日志获取更多交叉验证详情{RESET_COLOR}")
            else:
                print(f"{WARNING_COLOR}  • 没有交叉验证数据{RESET_COLOR}")
                print(f"{DETAIL_COLOR}  • 建议：考虑启用交叉验证功能以提高分析可靠性{RESET_COLOR}")
                # 创建一个默认的交叉验证数据结构供分析问题使用
                cross_validation_data = {"source_count": 0, "unique_sources": 0}
        
        # 分析问题
        problems = analyze_problems(result, total_score, main_scores, cross_validation_data)
        
        # 打印问题分析部分
        print(f"\n{SUBHEADER_COLOR}五、问题点分析{RESET_COLOR}")
        print(f"{DETAIL_COLOR}{'━' * 70}{RESET_COLOR}")
        
        if not problems:
            print(f"{SUCCESS_COLOR}  ✓ 未发现明显问题{RESET_COLOR}")
            print(f"{DETAIL_COLOR}  • 建议：保持批判性思维，关注信息更新{RESET_COLOR}")
        else:
            # 按严重程度排序（严重 > 中等）
            problems.sort(key=lambda x: 0 if x["severity"] == "严重" else 1)
            
            for i, problem in enumerate(problems, 1):
                color = problem["color"]
                print(f"\n{color}{i}. {problem['type']}问题:{RESET_COLOR}")
                print(f"{color}  ⚠️ 严重性：{problem['severity']}{RESET_COLOR}")
                print(f"{color}    - {problem['description']}{RESET_COLOR}")
                print(f"{color}    - 建议：{problem['suggestion']}{RESET_COLOR}")
        
        # 系统警告
        warnings = result.get("警告", [])
        if warnings and isinstance(warnings, list):
            print(f"\n{SUBHEADER_COLOR}六、系统警告{RESET_COLOR}")
            print(f"{DETAIL_COLOR}{'━' * 70}{RESET_COLOR}")
            for warning in warnings:
                if isinstance(warning, str):
                    logger.warning(f"系统警告: {warning}")
                    print(f"{WARNING_COLOR}  ⚠️ {warning}{RESET_COLOR}")
            
            # 添加交叉验证验证点统计信息
            if "交叉验证" in result and isinstance(result["交叉验证"], dict):
                if "验证点统计" in result["交叉验证"]:
                    stats = result["交叉验证"]["验证点统计"]
                    total_points = stats.get("总数", len(result["交叉验证"].get("验证点", [])))
                    success_count = stats.get("验证成功", 0)
                    fail_count = stats.get("验证失败", 0)
                    no_result_count = stats.get("无结果", 0)
                    
                    if total_points > 0:
                        print(f"{INFO_COLOR}  ℹ️ 交叉验证: 共有{total_points}个验证点，其中{success_count}个通过验证，{fail_count}个验证失败，{no_result_count}个未找到相关信息{RESET_COLOR}")
                elif "验证点" in result["交叉验证"]:
                    # 如果没有统计数据但有验证点，我们自己计算
                    verification_points = result["交叉验证"]["验证点"]
                    total_points = len(verification_points)
                    success_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("验证评分", 0) >= 0.7)
                    fail_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("验证评分", 0) < 0.4)
                    no_result_count = sum(1 for p in verification_points if isinstance(p, dict) and (p.get("搜索结果数量", 0) == 0 or (0.4 <= p.get("验证评分", 0) < 0.7)))
                    
                    if total_points > 0:
                        print(f"{INFO_COLOR}  ℹ️ 交叉验证: 共有{total_points}个验证点，其中{success_count}个通过验证，{fail_count}个验证失败，{no_result_count}个未找到相关信息{RESET_COLOR}")
        
        # 底部信息
        print(f"\n{HEADER_COLOR}{'=' * 70}{RESET_COLOR}")
        print(f"{HEADER_COLOR}{'分析完成 - 感谢使用新闻可信度分析工具':^70}{RESET_COLOR}")
        print(f"{HEADER_COLOR}{'=' * 70}{RESET_COLOR}")
        
        logger.info("分析报告生成完成")
        
    except Exception as e:
        logger.error(f"格式化结果时发生错误: {str(e)}")
        logger.error(f"错误详情:\n{traceback.format_exc()}")
        print(f"{ERROR_COLOR}格式化结果时发生错误: {str(e)}{RESET_COLOR}")
        print(f"{ERROR_COLOR}错误详情:\n{traceback.format_exc()}{RESET_COLOR}")
        # 尝试打印原始数据以便调试
        print(f"{ERROR_COLOR}原始数据:\n{result}{RESET_COLOR}")

def display_detailed_results(result: Dict[str, Any]) -> None:
    """显示详细的分析结果"""
    
    # AI生成内容检测
    print(f"\n{SECTION_COLOR}▶ AI生成内容检测{RESET_COLOR}")
    if "ai_content" in result:
        ai_content = result["ai_content"]
        print(f"• 综合评分: {format_score(ai_content.get('score', 0))}")
        
        # DeepSeek多维度评分
        if "deepseek_scores" in ai_content:
            print(f"• DeepSeek多维度评分 (AI生成内容):")
            scores = ai_content["deepseek_scores"]
            print(f"  - 表达模式: {format_score(scores.get('expression_pattern', 0))}")
            print(f"  - 词汇多样性: {format_score(scores.get('vocabulary_diversity', 0))}")
            print(f"  - 句子变化: {format_score(scores.get('sentence_variation', 0))}")
            print(f"  - 上下文连贯性: {format_score(scores.get('context_coherence', 0))}")
            print(f"  - 人类特征: {format_score(scores.get('human_traits', 0))}")
        
        # DeepSeek分析
        if "deepseek_analysis" in ai_content:
            print(f"\n• DeepSeek分析: {ai_content['deepseek_analysis']}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取AI生成内容检测数据{RESET_COLOR}")

    # 语言中立性
    print(f"\n{SECTION_COLOR}▶ 语言中立性{RESET_COLOR}")
    if "语言中立性" in result:
        neutrality = result["语言中立性"]
        print(f"• 综合评分: {format_score(neutrality.get('score', 0))}")
        
        # DeepSeek多维度评分
        if "deepseek_scores" in neutrality:
            print(f"• DeepSeek多维度评分 (语言中立性):")
            scores = neutrality["deepseek_scores"]
            print(f"  - 情感词汇: {format_score(scores.get('emotional_words', 0))}")
            print(f"  - 情感平衡: {format_score(scores.get('sentiment_balance', 0))}")
            print(f"  - 极端表述: {format_score(scores.get('extreme_expressions', 0))}")
            print(f"  - 煽动性表达: {format_score(scores.get('inflammatory_expressions', 0))}")
            print(f"  - 主观评价: {format_score(scores.get('subjective_evaluation', 0))}")
        
        # DeepSeek分析
        if "deepseek_analysis" in neutrality:
            print(f"\n• DeepSeek分析: {neutrality['deepseek_analysis']}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取语言中立性分析数据{RESET_COLOR}")

    # 来源质量
    print(f"\n{SECTION_COLOR}▶ 来源质量{RESET_COLOR}")
    if "source_quality" in result:
        source = result["source_quality"]
        if "domain_trust" in source:
            print(f"• {source['domain_trust']}")
        if "source_count" in source:
            print(f"• 引用了{get_source_level(source['source_count'])}的来源 ({source['source_count']}个)")
        if "authority_sources" in source:
            print(f"• {'发现' if source['authority_sources'] > 0 else '未发现'}权威来源引用")
        if "direct_quotes" in source:
            print(f"• 包含{'多个' if source['direct_quotes'] > 3 else '少量'}直接引用 ({source['direct_quotes']}个)")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取来源质量分析数据{RESET_COLOR}")

    # 域名可信度
    print(f"\n{SECTION_COLOR}▶ 域名可信度{RESET_COLOR}")
    if "domain_credibility" in result:
        domain = result["domain_credibility"]
        if "trust_level" in domain:
            print(f"• {domain['trust_level']}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取域名可信度数据{RESET_COLOR}")

    # 引用有效性
    print(f"\n{SECTION_COLOR}▶ 引用有效性{RESET_COLOR}")
    if "citation_validity" in result:
        validity = result["citation_validity"]
        print(f"• 引用数量: {get_citation_status(validity.get('citation_count', 0))}")
        print(f"• 引用准确性: {validity.get('accuracy_assessment', '无法评估')}")
        print(f"• 引用内容的真实性评估：{validity.get('authenticity_assessment', '无法评估')}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取引用有效性数据{RESET_COLOR}")

    # 引用质量
    print(f"\n{SECTION_COLOR}▶ 引用质量{RESET_COLOR}")
    if "citation_quality" in result:
        quality = result["citation_quality"]
        print(f"• 引用数量: {get_quantity_level(quality.get('total_citations', 0))} (直接引语: {quality.get('direct_quotes', 0)}, 间接引用: {quality.get('indirect_quotes', 0)})")
        print(f"• 引用来源多样性: {get_diversity_assessment(quality.get('unique_sources', 0))} (检测到{quality.get('unique_sources', 0)}个不同来源)")
        print(f"• 引用来源权威性: {get_authority_level(quality.get('authority_sources', 0))} (检测到{quality.get('authority_sources', 0)}个权威来源)")
        print(f"• 引用质量评估：{quality.get('overall_assessment', '无法评估')}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取引用质量数据{RESET_COLOR}")

    # 本地新闻验证
    print(f"\n{SECTION_COLOR}▶ 本地新闻验证{RESET_COLOR}")
    if "local_verification" in result:
        local = result["local_verification"]
        print(f"• {local.get('assessment', '未发现明显的本地相关性指标')}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取本地新闻验证数据{RESET_COLOR}")

    # 逻辑分析
    print(f"\n{SECTION_COLOR}▶ 逻辑分析{RESET_COLOR}")
    if "logic_analysis" in result:
        logic = result["logic_analysis"]
        for point in logic.get("points", []):
            print(f"• {point}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取逻辑分析数据{RESET_COLOR}")

    # 交叉验证
    print(f"\n{SECTION_COLOR}▶ 交叉验证{RESET_COLOR}")
    if "cross_validation" in result:
        cross = result["cross_validation"]
        if "source_count" in cross:
            print(f"• 搜索到了{cross['unique_sources']}个不同来源的{cross['source_count']}篇报道")
        if "timeliness" in cross:
            print(f"• {cross['timeliness']}")
        if "source_credibility" in cross:
            print(f"• {cross['source_credibility']}")
    else:
        print(f"{ERROR_COLOR}  • 错误：无法获取交叉验证数据{RESET_COLOR}")

def get_source_level(count: int) -> str:
    if count == 0:
        return "无"
    elif count < 3:
        return "有限"
    elif count < 5:
        return "适量"
    else:
        return "充足"

def get_citation_status(count: int) -> str:
    if count == 0:
        return "无明确引用"
    elif count < 3:
        return f"较少 ({count}个)"
    elif count < 5:
        return f"适量 ({count}个)"
    else:
        return f"充足 ({count}个)"

def get_quantity_level(count: int) -> str:
    if count == 0:
        return "无"
    elif count < 3:
        return "较少"
    elif count < 5:
        return "适量"
    else:
        return "充足"

def get_diversity_assessment(count: int) -> str:
    if count == 0:
        return "无法评估"
    elif count < 2:
        return "单一"
    elif count < 4:
        return "一般"
    else:
        return "多样"

def get_authority_level(count: int) -> str:
    if count == 0:
        return "低"
    elif count < 2:
        return "一般"
    elif count < 4:
        return "较高"
    else:
        return "高" 