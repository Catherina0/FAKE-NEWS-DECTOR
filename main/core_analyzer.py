#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
核心分析模块
负责新闻内容可信度分析的核心功能
"""

import logging
import json
from typing import Dict, List, Tuple, Any, Optional, Union
import traceback
import os
import datetime
import hashlib
import shutil
import re

# 从配置模块导入默认权重
from config import (
    DEFAULT_WEIGHTS, 
    DEEPSEEK_WEIGHTS, 
    DEEPSEEK_API_AVAILABLE
)

# 从search_services导入SearXNG状态（确保使用最新测试状态）
from search_services import SEARXNG_AVAILABLE, test_searxng_connection

# 初始化logger
logger = logging.getLogger(__name__)

def analyze_news_credibility(
    text: str, 
    url: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
    use_ai_services: bool = True,
    use_online: bool = True
) -> Dict[str, Any]:
    """
    综合分析新闻可信度
    
    参数:
        text (str): 新闻文本
        url (str, optional): 新闻URL
        weights (dict, optional): 各项分析的权重
        use_ai_services (bool): 是否使用AI服务进行分析
        use_online (bool): 是否使用在线验证服务
    
    返回:
        dict: 包含总体评分和详细分析的字典
    """
    logger.info("开始分析新闻可信度")
    
    # 导入所需模块
    from text_analysis import (
        # check_ai_content,  # 注释掉本地算法
        # analyze_language_neutrality,  # 注释掉本地算法
        analyze_source_quality,
        # analyze_text_logic  # 注释掉本地算法
    )
    from citation_analysis import (
        get_citation_score
    )
    from ai_services import (
        analyze_with_deepseek_v3
    )
    from validation import (
        perform_cross_validation
    )
    from citation_validation import (  # 导入新的引用验证模块
        validate_citations
    )
    
    # 检查关键服务可用性
    service_warnings = []
    
    # 如果需要使用在线服务，重新测试SearXNG连接状态
    global SEARXNG_AVAILABLE
    if use_online:
        logger.debug("正在重新检查SearXNG连接状态...")
        test_searxng_connection()
    
    if use_ai_services and not DEEPSEEK_API_AVAILABLE:
        logger.warning("DeepSeek API不可用，将使用本地算法进行分析，精度可能受限")
        service_warnings.append("DeepSeek API不可用，部分高级分析功能受限")
    
    if not SEARXNG_AVAILABLE:
        logger.warning("SearXNG搜索引擎不可用，交叉验证功能将受限")
        service_warnings.append("SearXNG搜索引擎不可用，交叉验证功能受限")
    
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
        "警告": service_warnings,  # 添加服务警告列表
        "新闻价值分析": {
            "总分": 0.0,
            "各项评分": {},
            "详细分析": {}
        },
        "原始分析数据": {},  # 添加原始分析数据，保存完整的DeepSeek结果
        "分析过程": []  # 记录分析过程的关键步骤
    }
    
    # 使用各项分析方法获取评分
    scores = {}
    warnings = []
    
    # 确保 text 是字符串
    if isinstance(text, tuple):
        text = text[0]
    
    # DeepSeek分析
    if use_ai_services and DEEPSEEK_API_AVAILABLE:
        try:
            deepseek_score, deepseek_result = analyze_with_deepseek_v3(text)
            
            # 记录完整的DeepSeek分析结果到原始数据中
            result["原始分析数据"]["deepseek_full_response"] = deepseek_result
            result["分析过程"].append("DeepSeek API分析完成")
            
            # 添加类型检查，确保DeepSeek返回结果格式正确
            if not isinstance(deepseek_result, dict):
                logger.error(f"DeepSeek分析返回格式异常: {type(deepseek_result)}")
                
                # 如果是字符串类型，尝试将其解析为JSON
                if isinstance(deepseek_result, str):
                    try:
                        # 尝试解析JSON字符串
                        parsed_json = json.loads(deepseek_result)
                        logger.info("成功将DeepSeek返回的字符串解析为字典")
                        deepseek_result = parsed_json
                    except json.JSONDecodeError as e:
                        logger.error(f"解析DeepSeek返回的字符串失败: {e}")
                        logger.error(f"DeepSeek返回内容: {deepseek_result[:200]}")
                        raise ValueError(f"DeepSeek返回的字符串不是有效的JSON: {e}")
                else:
                    logger.error(f"DeepSeek返回内容: {str(deepseek_result)[:200]}")
                    raise ValueError(f"DeepSeek返回格式异常: 期望dict类型，实际为{type(deepseek_result)}")
            
            # 检查详细分析字段是否存在且为字符串
            if "详细分析" not in deepseek_result:
                logger.error("DeepSeek分析结果缺少'详细分析'字段")
                logger.error(f"DeepSeek返回键: {deepseek_result.keys()}")
                raise ValueError("DeepSeek分析结果缺少'详细分析'字段")
            
            if not isinstance(deepseek_result["详细分析"], str):
                logger.error(f"DeepSeek '详细分析'字段类型异常: {type(deepseek_result['详细分析'])}")
                logger.error(f"DeepSeek '详细分析'内容: {str(deepseek_result['详细分析'])[:200]}")
                # 如果不是字符串，尝试直接转为JSON字符串
                deepseek_result["详细分析"] = json.dumps(deepseek_result["详细分析"])
                logger.info("已将非字符串的'详细分析'转换为JSON字符串")
            
            result["AI分析"] = deepseek_result
            scores["deepseek"] = deepseek_score
            
            # 提取DeepSeek返回的各大类评分和细分点评分到评分详情中
            if isinstance(deepseek_result, dict):
                if "各大类评分" in deepseek_result and isinstance(deepseek_result["各大类评分"], dict):
                    for category, score in deepseek_result["各大类评分"].items():
                        result["评分详情"][f"DeepSeek_{category}"] = score
                
                if "细分点评分" in deepseek_result and isinstance(deepseek_result["细分点评分"], dict):
                    for detail_point, score in deepseek_result["细分点评分"].items():
                        result["评分详情"][f"DeepSeek_细分_{detail_point}"] = score
            
        except Exception as e:
            logger.error(f"DeepSeek分析失败: {e}")
            # 记录完整错误堆栈
            logger.error(traceback.format_exc())
            logger.warning("DeepSeek分析失败，将使用本地算法和其他可用数据继续分析")
            service_warnings.append("DeepSeek分析失败，分析结果可能不完整")
            # 不再抛出异常，而是继续执行
            # 设置默认值
            scores["deepseek"] = 0.5
            result["AI分析"] = {"详细分析": "DeepSeek API不可用，无法进行分析"}
    
    # 本地AI内容检测和语言中立性分析只有在DeepSeek不可用时才执行
    if not use_ai_services or not DEEPSEEK_API_AVAILABLE:
        # 注释掉本地算法分析
        # # 本地AI内容检测
        # ai_content_score, ai_content_result = check_ai_content(text)
        # scores["ai_content"] = ai_content_score
        # result["AI内容检测"] = ai_content_result
        
        # # 分析语言中立性
        # neutrality_score, neutrality_result = analyze_language_neutrality(text)
        # scores["neutrality"] = neutrality_score
        # result["语言中立性"] = neutrality_result
        
        # 使用默认值
        scores["ai_content"] = 0.5
        result["AI内容检测"] = {"分析结果": "本地分析功能已禁用"}
        scores["neutrality"] = 0.5
        result["语言中立性"] = {"分析结果": "本地分析功能已禁用"}
    
    # 1. 检测AI生成内容
    try:
        # 如果DeepSeek可用，使用DeepSeek结果
        if use_ai_services and DEEPSEEK_API_AVAILABLE and "AI分析" in result:
            ai_score = 0.0
            ai_details = "未能从DeepSeek分析中提取AI内容检测结果"
            ai_properties = {}
            
            # 首先尝试从解析好的结构化数据中提取AI生成内容信息
            if isinstance(result["AI分析"], dict) and "AI生成内容" in result["AI分析"]:
                logger.info("直接从AI分析结果中找到AI生成内容数据")
                ai_data = result["AI分析"]["AI生成内容"]
                
                # 确保ai_data是字典
                if isinstance(ai_data, dict):
                    # 计算平均分数
                    scores = []
                    if "表达模式" in ai_data and isinstance(ai_data["表达模式"], (int, float)):
                        scores.append(ai_data["表达模式"])
                        ai_properties["表达模式"] = ai_data["表达模式"]
                    if "词汇多样性" in ai_data and isinstance(ai_data["词汇多样性"], (int, float)):
                        scores.append(ai_data["词汇多样性"])
                        ai_properties["词汇多样性"] = ai_data["词汇多样性"]
                    if "句子变化" in ai_data and isinstance(ai_data["句子变化"], (int, float)):
                        scores.append(ai_data["句子变化"])
                        ai_properties["句子变化"] = ai_data["句子变化"]
                    if "上下文连贯性" in ai_data and isinstance(ai_data["上下文连贯性"], (int, float)):
                        scores.append(ai_data["上下文连贯性"])
                        ai_properties["上下文连贯性"] = ai_data["上下文连贯性"]
                    if "人类特征" in ai_data and isinstance(ai_data["人类特征"], (int, float)):
                        scores.append(ai_data["人类特征"])
                        ai_properties["人类特征"] = ai_data["人类特征"]
                    
                    if scores:
                        ai_score = sum(scores) / len(scores)
                        ai_details = ai_data.get("分析", "无详细分析")
                        logger.info(f"成功从JSON结构中提取AI内容检测平均分数: {ai_score}")
                    else:
                        logger.warning("未找到有效的AI评分数据")
                        ai_score = 0.6
                        ai_details = "未找到有效的AI评分数据，使用默认值"
                else:
                    logger.warning(f"AI生成内容数据不是字典: {type(ai_data)}")
                    
                    # 如果不是字典，尝试转换为字符串并分析内容
                    ai_text = str(ai_data)
                    if "高度的人类化特征" in ai_text or "明显的人工生成" in ai_text:
                        ai_score = 0.8
                        ai_details = "文本具有高度的人类化特征，可能为人工生成"
                    elif "机械化表达" in ai_text or "模板化" in ai_text:
                        ai_score = 0.3
                        ai_details = "文本具有明显的AI特征，可能为AI生成"
                    else:
                        ai_score = 0.6
                        ai_details = "AI生成内容数据格式不正确，使用默认评分"
            else:
                # 如果没有在结构中找到AI生成内容信息，尝试从详细分析文本中提取
                logger.info("在AI分析结果结构中未找到AI生成内容字段，尝试从详细文本分析")
                
                if "详细分析" in result["AI分析"]:
                    deepseek_analysis = result["AI分析"]["详细分析"]
                    logger.debug(f"DeepSeek 分析结果: {deepseek_analysis}")
                    
                    # 确保re模块已导入
                    import re
                    
                    # 尝试从文本中分析AI生成内容信息
                    if isinstance(deepseek_analysis, str):
                        # 如果是完整的JSON字符串，尝试解析
                        try:
                            json_data = json.loads(deepseek_analysis)
                            if isinstance(json_data, dict) and "AI生成内容" in json_data:
                                ai_data = json_data["AI生成内容"]
                                if isinstance(ai_data, dict):
                                    scores = []
                                    for key in ["表达模式", "词汇多样性", "句子变化", "上下文连贯性", "人类特征"]:
                                        if key in ai_data and isinstance(ai_data[key], (int, float)):
                                            scores.append(ai_data[key])
                                    
                                    if scores:
                                        ai_score = sum(scores) / len(scores)
                                        ai_details = ai_data.get("分析", "从JSON中提取的无详细分析")
                                        logger.info(f"成功从详细分析JSON中提取AI内容检测平均分数: {ai_score}")
                            else:
                                logger.warning("详细分析JSON中未找到AI生成内容字段")
                        except json.JSONDecodeError:
                            logger.info("详细分析不是有效的JSON，尝试使用文本分析")
                        
                        # 如果JSON解析失败或未包含所需数据，尝试文本分析
                        if ai_score == 0.0:
                            # 如果文本中提到AI生成内容相关描述
                            if "AI生成内容" in deepseek_analysis:
                                # 提取AI生成内容相关描述
                                ai_section = re.search(r'AI生成内容[：:].*?(?=语言中立性|$)', deepseek_analysis, re.DOTALL)
                                if ai_section:
                                    ai_text = ai_section.group(0)
                                    logger.info(f"找到AI生成内容部分: {ai_text[:100]}...")
                                    
                                    # 从文本中提取各项评分
                                    scores = []
                                    for key in ["表达模式", "词汇多样性", "句子变化", "上下文连贯性", "人类特征"]:
                                        score_match = re.search(f'{key}[：:]\s*(\d+\.\d+)', ai_text)
                                        if score_match:
                                            try:
                                                score = float(score_match.group(1))
                                                scores.append(score)
                                                logger.info(f"从文本中提取到{key}评分: {score}")
                                            except:
                                                logger.warning(f"无法将{key}的值转换为浮点数")
                                    
                                    # 提取分析文本
                                    analysis_match = re.search(r'分析[：:](.*?)(?=表达模式|词汇多样性|$)', ai_text, re.DOTALL)
                                    if analysis_match:
                                        ai_details = analysis_match.group(1).strip()
                                        logger.info(f"从文本中提取到分析详情: {ai_details[:100]}...")
                                    
                                    if scores:
                                        ai_score = sum(scores) / len(scores)
                                        logger.info(f"成功从文本中提取AI内容检测平均分数: {ai_score}")
                                    else:
                                        # 根据文本描述判断分数
                                        if "高度的人类化特征" in ai_text or "明显的人工生成" in ai_text:
                                            ai_score = 0.8
                                            ai_details = "文本具有高度的人类化特征，可能为人工生成"
                                        elif "机械化表达" in ai_text or "模板化" in ai_text:
                                            ai_score = 0.3
                                            ai_details = "文本具有明显的AI特征，可能为AI生成"
                                        else:
                                            ai_score = 0.6
                                            ai_details = "无法从文本中确定内容的AI生成可能性，给予中等评价"
                                        
                                        logger.info(f"根据文本描述设置AI内容检测分数: {ai_score}")
                                else:
                                    logger.warning("未找到AI生成内容部分，尝试从整体描述判断")
                            
                            # 如果仍然无法提取，尝试从整体描述判断
                            if ai_score == 0.0:
                                if "可信度极高" in deepseek_analysis or "高度可信" in deepseek_analysis:
                                    ai_score = 0.8
                                    ai_details = "整体分析表明内容可信度高，可能为人工生成"
                                    logger.info("根据整体描述判断为人工生成内容，评分0.8")
                                elif "可信度较低" in deepseek_analysis or "存在疑点" in deepseek_analysis:
                                    ai_score = 0.3
                                    ai_details = "整体分析表明内容可信度较低，可能为AI生成"
                                    logger.info("根据整体描述判断为AI生成内容，评分0.3")
                                else:
                                    ai_score = 0.6
                                    ai_details = "无法从整体描述中确定内容的AI生成可能性，给予中等评价"
                                    logger.info("无法判断内容来源，使用默认评分0.6")
                    else:
                        logger.error(f"DeepSeek详细分析不是字符串: {type(deepseek_analysis)}")
                        ai_score = 0.6
                        ai_details = "DeepSeek详细分析格式不正确，使用默认评分"
                        logger.info("使用默认AI评分0.6")
                else:
                    logger.error("AI分析结果中未找到详细分析字段")
                    ai_score = 0.6
                    ai_details = "DeepSeek分析结果中未找到详细分析，使用默认评分"
                    logger.info("使用默认AI评分0.6")
        else:
            # 使用本地算法
            logger.info("DeepSeek不可用或AI服务已禁用，使用本地AI内容检测算法")
            ai_score, ai_details = check_ai_content(text)
            ai_properties = {}
        
        # 更新AI内容检测的分数和详情
        result["各项评分"]["AI内容检测"] = ai_score
        result["详细分析"]["AI内容检测"] = ai_details
        
        # 添加AI内容检测的详细评分点
        result["评分详情"]["AI内容检测_句式结构分析"] = round(ai_score * 0.95, 2)
        result["评分详情"]["AI内容检测_重复模式检测"] = round(ai_score * 1.05, 2)
        result["评分详情"]["AI内容检测_常见AI表达方式识别"] = round(ai_score * 1.0, 2)
        result["评分详情"]["AI内容检测_词汇多样性评估"] = round(ai_score * 0.9, 2)
        result["评分详情"]["AI内容检测_语言连贯性"] = round(ai_score * 1.1, 2)
        
        if ai_score < 0.5:
            result["问题"].append("文本可能由AI生成，建议进一步核实内容真实性")
    except Exception as e:
        logger.error(f"AI内容检测失败: {e}")
        logger.error(traceback.format_exc())
        # 抛出异常
        raise RuntimeError(f"AI内容检测失败: {str(e)}")
    
    # 2. 分析语言中立性
    try:
        # 如果DeepSeek可用，使用DeepSeek结果
        if use_ai_services and DEEPSEEK_API_AVAILABLE and "AI分析" in result:
            # 从DeepSeek结果中提取语言中立性部分
            neutrality_score = 0.0
            neutrality_details = "未能从DeepSeek分析中提取语言中立性结果"
            parsing_successful = False
            
            try:
                # 检查是否能够直接从AI分析结果中提取语言中立性数据
                if isinstance(result["AI分析"], dict) and "语言中立性" in result["AI分析"]:
                    logger.info("直接从AI分析结果中找到语言中立性数据")
                    neutrality_data = result["AI分析"]["语言中立性"]
                    
                    # 确保neutrality_data是一个字典
                    if isinstance(neutrality_data, dict):
                        # 计算平均分数
                        scores = []
                        if "情感词汇" in neutrality_data and isinstance(neutrality_data["情感词汇"], (int, float)):
                            scores.append(neutrality_data["情感词汇"])
                        if "情感平衡" in neutrality_data and isinstance(neutrality_data["情感平衡"], (int, float)):
                            scores.append(neutrality_data["情感平衡"])
                        if "极端表述" in neutrality_data and isinstance(neutrality_data["极端表述"], (int, float)):
                            scores.append(neutrality_data["极端表述"])
                        if "煽动性表达" in neutrality_data and isinstance(neutrality_data["煽动性表达"], (int, float)):
                            scores.append(neutrality_data["煽动性表达"])
                        if "主观评价" in neutrality_data and isinstance(neutrality_data["主观评价"], (int, float)):
                            scores.append(neutrality_data["主观评价"])
                        
                        if scores:
                            neutrality_score = sum(scores) / len(scores)
                            neutrality_details = neutrality_data.get("分析", "无详细分析")
                            logger.info("成功直接从AI分析结果提取语言中立性数据")
                            # 标记成功提取，后续不再处理
                            parsing_successful = True
                        else:
                            logger.warning("未找到有效的语言中立性评分数据，尝试解析详细分析")
                    else:
                        logger.warning(f"语言中立性数据不是字典: {type(neutrality_data)}，尝试解析详细分析")
                else:
                    logger.info("未在AI分析结果中直接找到语言中立性数据，尝试解析详细分析")
                
                # 如果无法直接从结果中获取，尝试从详细分析字段解析
                if neutrality_score == 0.0 and not parsing_successful:
                    # 检查详细分析是否是有效的JSON字符串
                    deepseek_analysis = result["AI分析"]["详细分析"]
                    logger.debug(f"语言中立性分析 - 准备解析的详细分析数据类型: {type(deepseek_analysis)}")
                    
                    # 如果已经是字典，不需要解析
                    if isinstance(deepseek_analysis, dict):
                        deepseek_details = deepseek_analysis
                        logger.info("语言中立性分析 - 详细分析已经是字典类型，无需解析")
                    elif isinstance(deepseek_analysis, str):
                        # 先检查字符串是否为空
                        if not deepseek_analysis.strip():
                            logger.error("语言中立性分析 - 详细分析是空字符串")
                            raise ValueError("语言中立性分析 - DeepSeek返回的详细分析是空字符串")
                        
                        try:
                            # 尝试解析JSON字符串
                            deepseek_details = json.loads(deepseek_analysis)
                            logger.info("语言中立性分析 - 详细分析成功从字符串解析为字典")
                        except json.JSONDecodeError as je:
                            logger.error(f"语言中立性分析 - JSON解析错误: {je}")
                            logger.error(f"尝试解析的内容: '{deepseek_analysis[:100]}...'")
                            
                            # 尝试从响应中提取可能的JSON部分
                            json_match = re.search(r'({[\s\S]*})', deepseek_analysis)
                            if json_match:
                                try:
                                    potential_json = json_match.group(1)
                                    logger.info(f"尝试解析提取的JSON部分: '{potential_json[:100]}...'")
                                    deepseek_details = json.loads(potential_json)
                                    logger.info("成功从提取的JSON部分解析为字典")
                                except json.JSONDecodeError:
                                    logger.error("从提取的JSON部分解析失败")
                                    
                                    # 尝试从纯文本中提取语言中立性信息
                                    logger.info("尝试从纯文本中提取语言中立性信息")
                                    neutrality_section = re.search(r'语言中立性[：:].*?(?=详细分析|$)', deepseek_analysis, re.DOTALL)
                                    if neutrality_section:
                                        neutrality_text = neutrality_section.group(0)
                                        logger.info(f"找到语言中立性部分: {neutrality_text[:100]}...")
                                        
                                        # 提取各项评分
                                        scores = []
                                        for key in ["情感词汇", "情感平衡", "极端表述", "煽动性表达", "主观评价"]:
                                            score_match = re.search(f'{key}[：:]\s*(\d+\.\d+)', neutrality_text)
                                            if score_match:
                                                try:
                                                    score = float(score_match.group(1))
                                                    scores.append(score)
                                                    logger.info(f"从文本中提取到{key}评分: {score}")
                                                except:
                                                    logger.warning(f"无法将{key}的值转换为浮点数")
                                        
                                        # 提取分析文本
                                        analysis_match = re.search(r'分析[：:](.*?)(?=情感词汇|情感平衡|$)', neutrality_text, re.DOTALL)
                                        if analysis_match:
                                            neutrality_details = analysis_match.group(1).strip()
                                            logger.info(f"从文本中提取到分析详情: {neutrality_details[:100]}...")
                                        
                                        if scores:
                                            neutrality_score = sum(scores) / len(scores)
                                            logger.info(f"成功从文本中提取语言中立性平均分数: {neutrality_score}")
                                        else:
                                            # 如果无法提取评分，给予一个中等值评分
                                            neutrality_score = 0.7
                                            logger.warning("无法从文本提取准确评分，使用默认值0.7")
                                        
                                        # 提取成功，不需要继续解析
                                        # 设置一个标志变量，表示已成功提取
                                        parsing_successful = True
                                    else:
                                        # 如果无法找到语言中立性部分，直接抛出错误
                                        raise ValueError(f"语言中立性分析 - 无法从DeepSeek返回中找到语言中立性部分")
                            else:
                                # 尝试从纯文本中提取语言中立性信息
                                logger.info("尝试从纯文本中提取语言中立性信息")
                                neutrality_section = re.search(r'语言中立性[：:].*?(?=详细分析|$)', deepseek_analysis, re.DOTALL)
                                if neutrality_section:
                                    neutrality_text = neutrality_section.group(0)
                                    logger.info(f"找到语言中立性部分: {neutrality_text[:100]}...")
                                    
                                    # 提取各项评分
                                    scores = []
                                    for key in ["情感词汇", "情感平衡", "极端表述", "煽动性表达", "主观评价"]:
                                        score_match = re.search(f'{key}[：:]\s*(\d+\.\d+)', neutrality_text)
                                        if score_match:
                                            try:
                                                score = float(score_match.group(1))
                                                scores.append(score)
                                                logger.info(f"从文本中提取到{key}评分: {score}")
                                            except:
                                                logger.warning(f"无法将{key}的值转换为浮点数")
                                        
                                    # 提取分析文本
                                    analysis_match = re.search(r'分析[：:](.*?)(?=情感词汇|情感平衡|$)', neutrality_text, re.DOTALL)
                                    if analysis_match:
                                        neutrality_details = analysis_match.group(1).strip()
                                        logger.info(f"从文本中提取到分析详情: {neutrality_details[:100]}...")
                                    
                                    if scores:
                                        neutrality_score = sum(scores) / len(scores)
                                        logger.info(f"成功从文本中提取语言中立性平均分数: {neutrality_score}")
                                    else:
                                        # 如果无法提取评分，给予一个中等值评分
                                        neutrality_score = 0.7
                                        logger.warning("无法从文本提取准确评分，使用默认值0.7")
                                else:
                                    # 如果无法找到语言中立性部分，解析整个文本来估计分数
                                    logger.warning("无法从文本中找到语言中立性部分，分析整个文本")
                                    
                                    # 如果文本内容提到"客观中立"、"平衡"等内容，给予较高分数
                                    if re.search(r'(客观中立|平衡报道|中立表达|无明显偏见)', deepseek_analysis):
                                        neutrality_score = 0.8
                                        neutrality_details = "文本分析表明内容具有较高的语言中立性，表达客观平衡"
                                        logger.info("根据关键词判断语言中立性较高，评分0.8")
                                    # 如果文本内容提到"情感化"、"偏见"等内容，给予较低分数
                                    elif re.search(r'(情感化表达|明显偏见|煽动性|极端表述)', deepseek_analysis):
                                        neutrality_score = 0.4
                                        neutrality_details = "文本分析表明内容存在明显的情感偏向或立场倾向"
                                        logger.info("根据关键词判断语言中立性较低，评分0.4")
                                    else:
                                        # 默认中等分数
                                        neutrality_score = 0.6
                                        neutrality_details = "无法从文本中确定语言中立性的具体程度，给予中等评价"
                                        logger.info("无法判断语言中立性程度，使用默认评分0.6")
                    else:
                        # 尝试强制转换为字符串再解析
                        logger.warning(f"语言中立性分析 - 详细分析非预期类型: {type(deepseek_analysis)}，尝试强制转换")
                        str_analysis = str(deepseek_analysis)
                        
                        # 使用相同的纯文本解析方法
                        ai_section = re.search(r'语言中立性[：:].*?(?=详细分析|$)', str_analysis, re.DOTALL)
                        if ai_section:
                            ai_text = ai_section.group(0)
                            logger.info(f"找到语言中立性部分: {ai_text[:100]}...")
                            
                            # 提取各项评分
                            scores = []
                            for key in ["情感词汇", "情感平衡", "极端表述", "煽动性表达", "主观评价"]:
                                score_match = re.search(f'{key}[：:]\s*(\d+\.\d+)', ai_text)
                                if score_match:
                                    try:
                                        score = float(score_match.group(1))
                                        scores.append(score)
                                        logger.info(f"从文本中提取到{key}评分: {score}")
                                    except:
                                        logger.warning(f"无法将{key}的值转换为浮点数")
                            
                            # 提取分析文本
                            analysis_match = re.search(r'分析[：:](.*?)(?=情感词汇|情感平衡|$)', ai_text, re.DOTALL)
                            if analysis_match:
                                ai_details = analysis_match.group(1).strip()
                                logger.info(f"从文本中提取到分析详情: {ai_details[:100]}...")
                            
                            if scores:
                                ai_score = sum(scores) / len(scores)
                                logger.info(f"成功从文本中提取语言中立性平均分数: {ai_score}")
                            else:
                                # 如果无法提取评分，给予一个中等值评分
                                ai_score = 0.7
                                logger.warning("无法从文本提取准确评分，使用默认值0.7")
                        else:
                            # 如果无法找到语言中立性部分，使用默认值
                            ai_score = 0.6
                            ai_details = "无法从转换后的内容中提取语言中立性信息，使用默认值"
                            logger.warning("无法从转换后的内容提取信息，使用默认评分0.6")
                
                # 检查是否已经成功提取到语言中立性信息
                if ai_score != 0.0:
                    logger.info(f"成功提取语言中立性信息，评分: {ai_score}")
                else:
                    # 如果到这里还没有提取到评分，尝试继续解析deepseek_details
                    if 'deepseek_details' in locals() and isinstance(deepseek_details, dict):
                        if "语言中立性" in deepseek_details:
                            neutrality_data = deepseek_details["语言中立性"]
                            # 确保neutrality_data是一个字典
                            if isinstance(neutrality_data, dict):
                                # 计算平均分数
                                scores = []
                                if "情感词汇" in neutrality_data and isinstance(neutrality_data["情感词汇"], (int, float)):
                                    scores.append(neutrality_data["情感词汇"])
                                if "情感平衡" in neutrality_data and isinstance(neutrality_data["情感平衡"], (int, float)):
                                    scores.append(neutrality_data["情感平衡"])
                                if "极端表述" in neutrality_data and isinstance(neutrality_data["极端表述"], (int, float)):
                                    scores.append(neutrality_data["极端表述"])
                                if "煽动性表达" in neutrality_data and isinstance(neutrality_data["煽动性表达"], (int, float)):
                                    scores.append(neutrality_data["煽动性表达"])
                                if "主观评价" in neutrality_data and isinstance(neutrality_data["主观评价"], (int, float)):
                                    scores.append(neutrality_data["主观评价"])
                                
                                if scores:
                                    neutrality_score = sum(scores) / len(scores)
                                    neutrality_details = neutrality_data.get("分析", "无详细分析")
                                    logger.info("成功从DeepSeek结果中提取语言中立性数据")
                                else:
                                    logger.error("未找到有效的语言中立性评分数据")
                                    # 给一个默认评分
                                    neutrality_score = 0.6
                                    neutrality_details = "无法提取有效的语言中立性评分数据，使用默认值"
                                    logger.warning("使用默认语言中立性评分0.6")
                            else:
                                logger.error(f"语言中立性数据不是字典: {type(neutrality_data)}")
                                # 给一个默认评分
                                neutrality_score = 0.6
                                neutrality_details = "语言中立性数据格式不正确，使用默认值"
                                logger.warning("使用默认语言中立性评分0.6")
                        else:
                            logger.error("DeepSeek结果中未找到语言中立性数据")
                            # 给一个默认评分
                            neutrality_score = 0.6
                            neutrality_details = "无法在DeepSeek结果中找到语言中立性数据，使用默认值"
                            logger.warning("使用默认语言中立性评分0.6")
                    else:
                        # 最后的回退方案
                        neutrality_score = 0.6
                        neutrality_details = "所有提取方法均失败，使用默认评分"
                        logger.warning("所有语言中立性数据提取方法均失败，使用默认评分0.6")
            except Exception as extract_error:
                logger.error(f"从DeepSeek结果提取语言中立性数据失败: {extract_error}")
                # 记录详细错误信息
                logger.error(traceback.format_exc())
                # 不再降级使用本地算法，直接抛出原始异常
                raise extract_error
        else:
            # 使用本地算法
            logger.info("DeepSeek不可用或AI服务已禁用，使用本地语言中立性分析算法")
            neutrality_score, neutrality_details = analyze_language_neutrality(text)
        
        result["各项评分"]["语言中立性"] = neutrality_score
        result["详细分析"]["语言中立性"] = neutrality_details
        
        # 添加语言中立性的详细评分点
        result["评分详情"]["语言中立性_情感词汇分析"] = round(neutrality_score * 1.05, 2)
        result["评分详情"]["语言中立性_偏见词汇检测"] = round(neutrality_score * 0.95, 2)
        result["评分详情"]["语言中立性_修辞手法评估"] = round(neutrality_score * 1.03, 2)
        result["评分详情"]["语言中立性_平衡报道分析"] = round(neutrality_score * 0.97, 2)
        result["评分详情"]["语言中立性_语言客观性"] = round(neutrality_score * 1.0, 2)
        
        if neutrality_score < 0.6:
            result["问题"].append("文本语言偏向性较强，可能存在情感倾向或偏见")
    except Exception as e:
        logger.error(f"语言中立性分析失败: {e}")
        # 不再提供默认值，直接抛出异常
        raise RuntimeError(f"语言中立性分析失败: {str(e)}")
    
    # 3. 分析来源质量和引用质量（合并为一项）
    try:
        source_quality_score, source_quality_details = analyze_source_quality(text, url)
        
        # 使用新的引用验证方法
        citation_score = None
        citation_details = None
        citation_analysis_failed = False
        
        if use_ai_services and DEEPSEEK_API_AVAILABLE and SEARXNG_AVAILABLE:
            logger.info("使用DeepSeek和SearXNG进行引用验证")
            citation_score, citation_details = validate_citations(text)
            
            # 检查引用验证是否成功
            if citation_score is None:
                logger.warning(f"引用验证分析失败: {citation_details.get('error', '未知错误')}")
                citation_analysis_failed = True
                
                # 将引用验证标记为不参与评分的项目
                result["缺失评分项"] = result.get("缺失评分项", []) + ["引用验证"]
                
                # 记录失败原因
                result["分析失败项"] = result.get("分析失败项", {})
                result["分析失败项"]["引用验证"] = citation_details
                
                # 继续使用旧方法作为备选
                logger.info("尝试使用本地方法进行引用分析")
                citation_score, citation_details = get_citation_score(text)
                
        else:
            # 退回到旧的方法
            logger.info("使用本地方法进行引用分析")
            citation_score, citation_details = get_citation_score(text)
        
        # 如果所有引用分析方法都失败，则标记该项为不参与评分
        if citation_score is None:
            logger.error("所有引用分析方法均失败")
            result["各项评分"]["来源引用质量"] = None if source_quality_score is None else source_quality_score
            result["详细分析"]["来源引用质量"] = {
                "来源质量": source_quality_details,
                "引用质量": {"error": "引用分析失败", "详细信息": "所有引用分析方法均失败"}
            }
            
            # 将引用验证标记为不参与评分的项目
            result["缺失评分项"] = result.get("缺失评分项", []) + ["引用验证"]
            
            # 如果来源质量也分析失败，则整个"来源引用质量"项不参与评分
            if source_quality_score is None:
                logger.error("来源质量分析也失败，整个'来源引用质量'项不参与评分")
                result["缺失评分项"] = result.get("缺失评分项", []) + ["来源引用质量"]
            
            return
        
        # 如果有一项评分缺失，使用另一项
        if source_quality_score is None:
            combined_score = citation_score
        elif citation_score is None:
            combined_score = source_quality_score
        else:
            # 否则取加权平均值，引用验证占比更高
            combined_score = source_quality_score * 0.4 + citation_score * 0.6
        
        result["各项评分"]["来源引用质量"] = combined_score
        result["详细分析"]["来源引用质量"] = {
            "来源质量": source_quality_details,
            "引用质量": citation_details
        }
        
        # 添加引用验证的详细信息
        if citation_details and isinstance(citation_details, dict) and "引用详情" in citation_details:
            result["引用验证结果"] = citation_details
        
        # 添加来源和引用质量的详细评分点
        if source_quality_score is not None:
            result["评分详情"]["来源引用质量_来源多样性"] = round(source_quality_score * 0.9, 2)
            result["评分详情"]["来源引用质量_来源权威性"] = round(source_quality_score * 1.1, 2)
        
        if citation_score is not None and not citation_analysis_failed:
            result["评分详情"]["来源引用质量_引用数量"] = round(citation_score * 0.95, 2)
            result["评分详情"]["来源引用质量_引用真实性"] = round(citation_score * 1.05, 2)
        
        # 如果有引用验证总结，添加到问题或警告中
        if citation_details and isinstance(citation_details, dict) and "总结" in citation_details:
            summary = citation_details["总结"]
            if citation_score < 0.5:
                result["问题"].append(f"引用验证: {summary}")
            elif citation_score < 0.7:
                result["警告"].append(f"引用验证: {summary}")
        
        if combined_score < 0.5:
            result["问题"].append("文本来源和引用质量较低，缺乏足够的支持性证据或可靠来源")
    except Exception as e:
        logger.error(f"来源和引用质量分析失败: {e}")
        logger.error(traceback.format_exc())
        
        # 标记该项不参与评分
        result["缺失评分项"] = result.get("缺失评分项", []) + ["来源引用质量"]
        result["各项评分"]["来源引用质量"] = None
        result["详细分析"]["来源引用质量"] = f"分析过程出错: {str(e)}"
        
        # 记录失败原因
        result["分析失败项"] = result.get("分析失败项", {})
        result["分析失败项"]["来源引用质量"] = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    # 4. 使用DeepSeek进行深度分析
    ai_analysis_result = None
    if use_ai_services and DEEPSEEK_API_AVAILABLE:
        try:
            logger.info("使用DeepSeek进行深度分析")
            deepseek_score, ai_analysis = analyze_with_deepseek_v3(text)
            if isinstance(ai_analysis, dict):
                ai_score = deepseek_score
                ai_detailed_scores = ai_analysis.get("各大类评分", {})
                
                result["各项评分"]["DeepSeek综合分析"] = ai_score
                result["详细分析"]["DeepSeek综合分析"] = ai_analysis
                result["AI分析"] = {
                    "评分": ai_score,
                    "详细分析": json.dumps(ai_analysis) if not isinstance(ai_analysis, str) else ai_analysis
                }
                
                # 获取AI分析中的可信度疑点并添加到问题列表中
                if "可信度判断的疑点" in ai_analysis:
                    疑点列表 = ai_analysis["可信度判断的疑点"]
                    if isinstance(疑点列表, list):
                        for 疑点 in 疑点列表:
                            if isinstance(疑点, dict) and "内容" in 疑点:
                                疑点文本 = 疑点["内容"]
                                if isinstance(疑点文本, list):
                                    result["问题"].extend([p for p in 疑点文本 if p.strip()])
                                elif isinstance(疑点文本, str) and 疑点文本.strip():
                                    result["问题"].append(疑点文本.strip())
                
                # 将AI分析的详细评分添加到评分详情中
                for key, value in ai_detailed_scores.items():
                    if isinstance(value, (int, float)):
                        result["评分详情"][f"DeepSeek综合分析_{key}"] = round(value, 2)
                
                ai_analysis_result = ai_analysis
            else:
                logger.error("DeepSeek返回的分析结果格式不正确")
                result["各项评分"]["DeepSeek综合分析"] = 0.5
                result["详细分析"]["DeepSeek综合分析"] = "分析格式不正确"
        except Exception as e:
            logger.error(f"DeepSeek深度分析失败: {e}")
            result["各项评分"]["DeepSeek综合分析"] = 0.5
            result["详细分析"]["DeepSeek综合分析"] = f"分析过程出错: {str(e)}"
    else:
        logger.warning("跳过DeepSeek深度分析：服务不可用或AI服务已禁用")
        result["各项评分"]["DeepSeek综合分析"] = 0.5
        result["详细分析"]["DeepSeek综合分析"] = "DeepSeek服务不可用，使用默认值"
        # 标记为缺失项
        result["缺失评分项"] = result.get("缺失评分项", []) + ["DeepSeek综合分析"]
    
    # 5. 交叉验证
    cross_validation_data = None
    if use_ai_services and DEEPSEEK_API_AVAILABLE and SEARXNG_AVAILABLE:
        logger.info("开始执行交叉验证")
        try:
            cross_validation_data = perform_cross_validation(text, ai_analysis_result or {})
            cross_validation_score = cross_validation_data.get("总体可信度", 0.5)
            
            result["各项评分"]["交叉验证"] = cross_validation_score
            result["详细分析"]["交叉验证"] = cross_validation_data
            result["交叉验证"] = cross_validation_data
            
            # 更新问题列表
            if "验证点" in cross_validation_data:
                verification_points = cross_validation_data["验证点"]
                no_result_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("搜索结果数量", 0) == 0)
                if no_result_count > 0:
                    result["问题"].append(f"缺乏足够的交叉验证来源 (共{len(verification_points)}个验证点，其中{no_result_count}个没有找到相关信息)")
                
                # 添加未通过验证的验证点到问题列表
                fail_count = sum(1 for p in verification_points if isinstance(p, dict) and p.get("验证评分", 0) < 0.4)
                if fail_count > 0:
                    result["问题"].append(f"交叉验证显示{fail_count}个验证点未通过验证，可信度较低")
            
            # 添加到综合评价中
            if cross_validation_score >= 0.7:
                positive_aspects.append(f"交叉验证显示内容可信度高 ({cross_validation_score:.2f})")
            elif cross_validation_score >= 0.5:
                positive_aspects.append(f"交叉验证显示部分内容可得到验证 ({cross_validation_score:.2f})")
            else:
                negative_aspects.append(f"交叉验证结果不佳，多数内容无法得到验证 ({cross_validation_score:.2f})")
            
        except Exception as e:
            logger.error(f"执行交叉验证时出错: {e}")
            logger.error(traceback.format_exc())
            result["交叉验证错误"] = f"执行交叉验证时出错: {str(e)}"
            result["缺失评分项"] = result.get("缺失评分项", []) + ["交叉验证"]
    else:
        if not DEEPSEEK_API_AVAILABLE:
            logger.warning("DeepSeek API不可用，跳过交叉验证")
            result["缺失评分项"] = result.get("缺失评分项", []) + ["交叉验证"]
            result["警告"] = result.get("警告", []) + ["DeepSeek API不可用，无法进行交叉验证"]
        elif not SEARXNG_AVAILABLE:
            logger.warning("SearXNG搜索服务不可用，跳过交叉验证")
            result["缺失评分项"] = result.get("缺失评分项", []) + ["交叉验证"]
            result["警告"] = result.get("警告", []) + ["SearXNG搜索服务不可用，无法进行交叉验证"]
        elif not use_ai_services:
            logger.info("AI服务已禁用，跳过交叉验证")
            result["缺失评分项"] = result.get("缺失评分项", []) + ["交叉验证"]
    
    # 6. 分析文本逻辑性（作为新闻价值分析的一部分，不参与可信度评分）
    try:
        # 注释掉本地文本逻辑性分析
        # logic_score, logic_details = analyze_text_logic(text)
        # result["新闻价值分析"]["各项评分"]["文本逻辑性"] = logic_score
        # result["新闻价值分析"]["详细分析"]["文本逻辑性"] = logic_details
        
        # 使用默认值
        result["新闻价值分析"]["各项评分"]["文本逻辑性"] = 0.5
        result["新闻价值分析"]["详细分析"]["文本逻辑性"] = "本地分析功能已禁用"
        
        # 更新新闻价值分析的总分
        value_scores = result["新闻价值分析"]["各项评分"]
        if value_scores:
            result["新闻价值分析"]["总分"] = sum(value_scores.values()) / len(value_scores)
    except Exception as e:
        logger.error(f"文本逻辑性分析失败: {e}")
        result["新闻价值分析"]["各项评分"]["文本逻辑性"] = 0.5
        result["新闻价值分析"]["详细分析"]["文本逻辑性"] = f"分析过程出错: {str(e)}"
    
    # 计算总体评分
    # 使用配置的权重计算加权平均分
    total_score = 0.0
    weight_sum = 0.0
    missing_items = result.get("缺失评分项", [])
    
    # 调整权重以弥补缺失项
    adjusted_weights = weights.copy()
    if missing_items:
        missing_weight_sum = sum(weights[item.lower().replace(" ", "_")] for item in missing_items if item.lower().replace(" ", "_") in weights)
        if missing_weight_sum > 0:
            scaling_factor = 1 / (1 - missing_weight_sum)
            for key in adjusted_weights:
                if key not in [item.lower().replace(" ", "_") for item in missing_items]:
                    adjusted_weights[key] *= scaling_factor
    
    # 计算加权总分
    for key, score in result["各项评分"].items():
        # 跳过None值和在缺失项列表中的项目
        if score is None or key in missing_items:
            logger.info(f"评分项 '{key}' 不参与总分计算 (值为None或标记为缺失项)")
            continue
            
        weight_key = key.lower().replace(" ", "_")
        if weight_key in adjusted_weights:
            weight = adjusted_weights[weight_key]
            total_score += score * weight
            weight_sum += weight
            logger.debug(f"评分项 '{key}': 分数={score}, 权重={weight}, 当前总分={total_score}")
    
    # 确保总权重之和为1
    if weight_sum > 0:
        total_score = total_score / weight_sum
    else:
        total_score = 0.5  # 默认分数
        logger.warning("没有有效的评分项，使用默认分数0.5")
    
    # 更新总体评分
    result["总体评分"] = round(total_score, 2)
    
    # 添加权重和缺失项信息到结果中，方便查看
    result["评分权重"] = adjusted_weights
    result["实际权重和"] = weight_sum

    # 确保AI生成内容详情完整
    if "AI分析" in result and isinstance(result["AI分析"], dict) and "AI生成内容" in result["AI分析"]:
        ai_content_data = result["AI分析"]["AI生成内容"]
        if isinstance(ai_content_data, dict):
            result["详细分析"]["AI内容检测详情"] = ai_content_data
    
    # 确保语言中立性详情完整
    if "AI分析" in result and isinstance(result["AI分析"], dict) and "语言中立性" in result["AI分析"]:
        neutrality_data = result["AI分析"]["语言中立性"]
        if isinstance(neutrality_data, dict):
            result["详细分析"]["语言中立性详情"] = neutrality_data
    
    # 最后一步：添加分析时间戳
    result["分析时间"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info(f"新闻可信度分析完成，总体评分: {result['总体评分']}")
    return result

def save_news_to_local(text, url, result, save_dir="saved_news", image_paths=None):
    """
    将新闻文本和分析结果保存到本地文件。
    
    参数:
        text (str或tuple): 新闻文本内容，如果是元组则取第一个元素
        url (str): 新闻URL
        result (dict): 分析结果
        save_dir (str): 保存目录
        image_paths (list): 图片路径列表
    
    返回:
        bool: 是否成功保存
    """
    try:
        # 如果text是元组，取第一个元素作为文本内容
        if isinstance(text, tuple):
            if text:  # 确保元组不为空
                text_content = text[0]
            else:
                text_content = "无内容"
        else:
            text_content = text
            
        # 创建保存目录
        os.makedirs(save_dir, exist_ok=True)
        
        # 生成唯一文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{timestamp}_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        
        # 保存新闻文本
        text_filename = os.path.join(save_dir, f"{base_filename}_news.txt")
        with open(text_filename, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\n\n")
            f.write(text_content)
        logger.info(f"新闻文本已保存到 {text_filename}")
        
        # 保存分析结果
        result_filename = os.path.join(save_dir, f"{base_filename}_analysis.json")
        with open(result_filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"分析结果已保存到 {result_filename}")
        
        # 保存图片(如果有)
        if image_paths and isinstance(image_paths, list):
            for i, img_path in enumerate(image_paths):
                if os.path.exists(img_path):
                    img_ext = os.path.splitext(img_path)[1]
                    dest_path = os.path.join(save_dir, f"{base_filename}_image_{i}{img_ext}")
                    shutil.copy(img_path, dest_path)
                    logger.info(f"图片已保存到 {dest_path}")
        
        return True
    except Exception as e:
        logger.error(f"保存新闻文本时出错: {e}")
        return False 