#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
交叉验证模块
负责执行对新闻内容的交叉验证功能
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import traceback

# 初始化logger
logger = logging.getLogger(__name__)

def perform_cross_validation(text: str, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行交叉验证
    
    参数:
        text (str): 新闻文本
        ai_analysis (Dict[str, Any]): DeepSeek AI分析结果
    
    返回:
        Dict[str, Any]: 交叉验证结果
    """
    from config import DEEPSEEK_API_AVAILABLE
    from search_services import SEARXNG_AVAILABLE, search_with_searxng, test_searxng_connection
    
    logger.info("开始执行交叉验证")
    
    # 初始化结果
    result = {
        "总体可信度": 0.5,  # 默认值
        "验证点": [],
        "验证结论": "无法进行交叉验证，必要服务不可用。",
        "服务状态": {}
    }
    
    # 重新测试SearXNG连接状态
    logger.debug("重新检查SearXNG连接状态...")
    if not test_searxng_connection():
        result["服务状态"]["searxng"] = "不可用"
        logger.warning("SearXNG不可用，无法执行网络搜索验证")
        result["验证结论"] = "SearXNG搜索服务不可用，无法进行交叉验证。"
        return result
    else:
        result["服务状态"]["searxng"] = "可用"
    
    # 检查必要的服务是否可用
    if not DEEPSEEK_API_AVAILABLE:
        result["服务状态"]["deepseek"] = "不可用"
        logger.warning("DeepSeek API不可用，无法执行完整的交叉验证")
        result["验证结论"] = "DeepSeek API不可用，无法执行完整的交叉验证。"
        return result
    else:
        result["服务状态"]["deepseek"] = "可用"
    
    # 提取需要验证的关键点
    try:
        logger.info("使用DeepSeek提取需要验证的关键点")
        verification_points = extract_verification_points_with_deepseek(text)
        
        if not verification_points:
            logger.warning("DeepSeek未能提取到有效的验证点")
            result["验证结论"] = "DeepSeek未能从文本中提取有效的验证点，无法进行交叉验证。"
            # 添加一个空的验证点示例，以便显示
            result["验证点"] = [{
                "内容": "DeepSeek未能提取验证点",
                "重要性": "中",
                "搜索结果数量": 0,
                "验证评分": 0.5,
                "验证结论": "deepseek错误，无法验证"
            }]
            return result
        
        logger.info(f"成功提取了{len(verification_points)}个验证点")
        logger.debug(f"验证点内容: {verification_points}")
        
        # 初始化验证结果
        verified_results = []
        total_score = 0
        verified_count = 0
        
        # 对每个验证点进行验证
        for i, point in enumerate(verification_points):
            logger.info(f"验证点 {i+1}: {point['内容']}")
            
            # 构建搜索查询
            search_query = point["搜索关键词"] if "搜索关键词" in point and point["搜索关键词"] else point["内容"]
            logger.info(f"使用搜索查询: {search_query}")
            
            # 再次确认SearXNG仍然可用
            if not test_searxng_connection():
                logger.warning("SearXNG连接状态变为不可用，中止验证")
                # 使用已经验证的点计算部分结果
                if verified_count > 0:
                    result["总体可信度"] = total_score / verified_count
                result["验证结论"] = "验证过程中SearXNG连接中断，结果可能不完整。"
                result["验证点"] = verified_results
                return result
                
            # 使用SearXNG进行搜索
            search_results = search_with_searxng(search_query)
            logger.debug(f"搜索结果: {search_results}")
            
            if not search_results or not search_results.get("results", []):
                logger.warning(f"没有找到与验证点相关的搜索结果: {search_query}")
                verified_point = {
                    "验证内容": point["内容"],
                    "重要性": point.get("重要性", "中"),
                    "搜索结果数量": 0,
                    "验证评分": 0.4,
                    "验证结论": "未找到相关信息，无法验证。"
                }
            else:
                # 使用DeepSeek AI判断搜索结果与验证点的一致性
                verification_result = verify_search_results_with_deepseek(
                    content=text,
                    doubt_point=point["内容"],
                    search_results=search_results
                )
                
                verified_point = {
                    "验证内容": point["内容"],
                    "重要性": point.get("重要性", "中"),
                    "搜索结果数量": len(search_results.get("results", [])),
                    "搜索结果摘要": [r.get("content", "") for r in search_results.get("results", [])[:2]],
                    "验证评分": verification_result.get("评分", 0.5),
                    "验证结论": verification_result.get("结论", "无法确定")
                }
                
                # 累加评分
                importance_weight = 1.0
                if point.get("重要性", "中") == "高":
                    importance_weight = 1.5
                elif point.get("重要性", "中") == "低":
                    importance_weight = 0.5
                    
                total_score += verified_point["验证评分"] * importance_weight
                verified_count += 1
            
            verified_results.append(verified_point)
        
        # 计算总体评分
        if verified_results:
            overall_score = total_score / sum(
                1.5 if r["重要性"] == "高" else (0.5 if r["重要性"] == "低" else 1.0)
                for r in verified_results
            )
            
            # 根据总体评分生成结论
            if overall_score >= 0.8:
                conclusion = "高度可信：交叉验证结果表明新闻内容与多个可靠来源的信息一致。"
            elif overall_score >= 0.6:
                conclusion = "基本可信：交叉验证结果表明大部分内容可被其他来源证实，但存在少量不一致。"
            elif overall_score >= 0.4:
                conclusion = "部分可信：交叉验证结果表明部分内容可被证实，但也存在较多无法验证或不一致的信息。"
            else:
                conclusion = "低度可信：交叉验证结果表明大部分内容无法通过其他来源证实，或与其他来源信息存在较大冲突。"
                
            result = {
                "总体可信度": overall_score,
                "验证点": verified_results,
                "验证结论": conclusion,
                "服务状态": {
                    "deepseek": "可用",
                    "searxng": "可用"
                }
            }
            
            # 添加验证点统计
            success_count = sum(1 for r in verified_results if r.get("验证评分", 0) >= 0.7)
            fail_count = sum(1 for r in verified_results if r.get("验证评分", 0) < 0.4)
            no_result_count = sum(1 for r in verified_results if r.get("搜索结果数量", 0) == 0 or (0.4 <= r.get("验证评分", 0) < 0.7))
            
            result["验证点统计"] = {
                "验证成功": success_count,
                "验证失败": fail_count,
                "无结果": no_result_count,
                "总数": len(verified_results)
            }
            
            # 添加总体评估
            if overall_score >= 0.8:
                result["总体评估"] = "高度可信：交叉验证结果表明新闻内容与多个可靠来源的信息一致"
            elif overall_score >= 0.6:
                result["总体评估"] = "基本可信：交叉验证结果表明大部分内容可被其他来源证实，但存在少量不一致"
            elif overall_score >= 0.4:
                result["总体评估"] = "部分可信：交叉验证结果表明部分内容可被证实，但也存在较多无法验证或不一致的信息"
            else:
                result["总体评估"] = "低度可信：交叉验证结果表明大部分内容无法通过其他来源证实，或与其他来源信息存在较大冲突"
        else:
            result["验证结论"] = "交叉验证失败，未能验证任何关键点。"
    except Exception as e:
        logger.error(f"执行交叉验证时出错: {e}")
        result["验证结论"] = f"交叉验证过程中出错: {str(e)}"
    
    logger.info(f"交叉验证完成，总体可信度: {result['总体可信度']}")
    return result

def extract_verification_points_with_deepseek(text: str) -> List[Dict[str, Any]]:
    """
    使用DeepSeek从文本中提取需要验证的关键点
    
    参数:
        text (str): 新闻文本
    
    返回:
        List[Dict[str, Any]]: 需要验证的关键点列表
    """
    from ai_services import query_deepseek
    
    logger.info("使用DeepSeek提取需要验证的关键点")
    
    # 构建提取验证点的提示
    prompt = f"""
    请从以下新闻文本中提取5个需要进行事实验证的关键点。
    这些关键点应该是新闻中的具体事实陈述，而非观点或修饰性内容。
    请确保每个关键点是足够具体的短句子，便于搜索引擎查询验证。
    
    新闻文本:
    {text}
    
    对于每个关键点，请提供以下信息:
    1. 内容: 需要验证的具体事实陈述
    2. 重要性: 高/中/低
    3. 搜索关键词: 用于网络搜索验证的关键点（这些关键短句将直接被搜索并返回结果）
    请以JSON格式返回，格式如下:
    [
      {{
        "内容": "关键点1的内容",
        "重要性": "高",
        "搜索关键词": "搜索关键词1"
      }},
      ...
    ]
    
    只返回JSON格式的内容，不要有其他文字说明。
    """
    
    try:
        # 调用DeepSeek API提取验证点
        response = query_deepseek(prompt)
        
        # 记录原始响应用于调试
        logger.debug(f"DeepSeek原始响应(前200字符): {response[:200]}")
        
        # 尝试解析JSON响应
        verification_points = []
        
        # 多种方式尝试解析JSON
        json_extraction_methods = [
            # 方法1: 直接解析整个响应
            lambda r: json.loads(r),
            
            # 方法2: 使用正则表达式查找JSON数组
            lambda r: json.loads(re.search(r'\[\s*\{.*\}\s*\]', r, re.DOTALL).group(0)) 
                if re.search(r'\[\s*\{.*\}\s*\]', r, re.DOTALL) else None,
            
            # 方法3: 查找大括号包围的内容(可能是对象而非数组)
            lambda r: json.loads(re.search(r'\{.*\}', r, re.DOTALL).group(0))
                if re.search(r'\{.*\}', r, re.DOTALL) else None,
                
            # 方法4: 尝试修复JSON格式问题后解析
            lambda r: json.loads(r.replace("'", '"').replace("，", ",").replace("：", ":"))
        ]
        
        # 尝试所有解析方法
        for method_idx, extraction_method in enumerate(json_extraction_methods):
            try:
                extracted_data = extraction_method(response)
                logger.debug(f"方法{method_idx+1}成功解析JSON")
                
                # 检查提取的数据类型并相应处理
                if isinstance(extracted_data, list):
                    verification_points = extracted_data
                    break
                elif isinstance(extracted_data, dict):
                    # 如果是字典，检查是否有包含验证点的字段
                    for key in ["验证点", "points", "关键点", "verification_points", "result", "结果"]:
                        if key in extracted_data and isinstance(extracted_data[key], list):
                            verification_points = extracted_data[key]
                            break
                    # 如果找到了验证点，跳出外层循环
                    if verification_points:
                        break
                    
                    # 如果字典中没有找到验证点，将其转换为验证点列表
                    logger.warning("DeepSeek返回了字典而非列表，尝试转换为验证点")
                    verification_points = [{"内容": str(extracted_data), "重要性": "中", "搜索关键词": text[:50]}]
                    break
                else:
                    logger.warning(f"方法{method_idx+1}提取的数据不是列表或字典: {type(extracted_data)}")
            except Exception as e:
                logger.debug(f"方法{method_idx+1}解析失败: {e}")
                continue
        
        # 如果所有方法都失败，尝试直接从响应文本中提取结构化内容
        if not verification_points:
            logger.warning("所有JSON解析方法均失败，尝试从响应文本中提取结构化内容")
            
            # 查找格式化的验证点(查找数字+内容模式)
            point_matches = re.findall(r'(\d+)[\.、:：]?\s*(.+?)(?=\d+[\.、:：]|\Z)', response, re.DOTALL)
            if point_matches:
                logger.debug(f"从响应文本中找到了{len(point_matches)}个可能的验证点")
                for _, content in point_matches:
                    content = content.strip()
                    if len(content) > 10:  # 验证点至少应有10个字符
                        verification_points.append({
                            "内容": content,
                            "重要性": "中",
                            "搜索关键词": " ".join(content.split()[:5])  # 使用前5个词作为搜索关键词
                        })
            
            # 也可以尝试查找"关键点/验证点"这样的格式
            if not verification_points:
                point_sections = re.split(r'关键点|验证点|重要陈述|事实陈述', response)
                if len(point_sections) > 1:
                    for section in point_sections[1:]:  # 跳过第一部分(可能是前导文本)
                        clean_section = section.strip()
                        if len(clean_section) > 10:
                            # 提取第一句作为验证点
                            first_sentence = re.split(r'[.!?。！？]', clean_section)[0].strip()
                            if len(first_sentence) > 10:
                                verification_points.append({
                                    "内容": first_sentence,
                                    "重要性": "中", 
                                    "搜索关键词": " ".join(first_sentence.split()[:5])
                                })
                                if len(verification_points) >= 5:
                                    break
        
        # 验证返回的格式是否正确
        if not isinstance(verification_points, list):
            logger.error(f"最终的验证点不是列表格式: {type(verification_points)}")
            logger.warning("DeepSeek未能提取有效验证点")
            return []
        
        if not verification_points:
            logger.error("DeepSeek未能提取任何验证点")
            return []
        
        # 过滤掉格式不正确的项并规范化
        valid_points = []
        for point in verification_points:
            # 如果point不是字典，尝试转换为字典
            if not isinstance(point, dict):
                if isinstance(point, str) and len(point.strip()) > 0:
                    point = {"内容": point.strip()}
                else:
                    continue
            
            # 确保内容字段存在且有值
            if "内容" not in point or not point["内容"] or len(str(point["内容"]).strip()) == 0:
                continue
                
            # 确保所有必要字段都存在，如果不存在，使用默认值
            if "重要性" not in point or not point["重要性"]:
                point["重要性"] = "中"
            if "搜索关键词" not in point or not point["搜索关键词"]:
                content = str(point["内容"])
                point["搜索关键词"] = " ".join(content.split()[:5])
            
            # 规范化字段值
            importance = str(point["重要性"]).strip().lower()
            if importance in ["高", "high", "h", "重要"]:
                point["重要性"] = "高"
            elif importance in ["低", "low", "l", "次要"]:
                point["重要性"] = "低"
            else:
                point["重要性"] = "中"
                
            valid_points.append(point)
        
        if not valid_points:
            logger.warning("过滤后没有有效的验证点")
            return []
        
        # 限制返回的验证点数量(最多5个)
        return valid_points[:5]
    
    except Exception as e:
        logger.error(f"从文本中提取验证点时出错: {e}")
        logger.error(traceback.format_exc())
        return []

def generate_default_verification_points(text: str) -> List[Dict[str, Any]]:
    """
    当DeepSeek API失败时，生成一些基本的默认验证点
    
    参数:
        text (str): 新闻文本
    
    返回:
        List[Dict[str, Any]]: 默认的验证点列表
    """
    # 先替换掉换行符
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # 使用正则表达式拆分中英文混合句子
    pattern = r'([^.!?。！？]+[.!?。！？])'
    sentence_matches = re.findall(pattern, text)
    
    logger.info(f"正则表达式找到 {len(sentence_matches)} 个句子")
    
    valid_sentences = []
    for sentence in sentence_matches:
        clean_text = sentence.strip()
        if len(clean_text) > 15:  # 减少最小长度阈值
            valid_sentences.append(clean_text)
    
    # 如果正则表达式没找到足够句子，尝试直接按标点分割
    if len(valid_sentences) < 2:
        logger.warning("正则表达式未找到足够句子，尝试按标点分割")
        # 直接按句末标点分割
        sentences = []
        for end_mark in ['。', '！', '？', '.', '!', '?']:
            parts = text.split(end_mark)
            for part in parts[:-1]:  # 忽略最后一个可能不完整的部分
                if part.strip() and len(part.strip()) > 15:
                    sentences.append(part.strip() + end_mark)
        
        if sentences:
            valid_sentences = sentences
    
    logger.info(f"为文本生成默认验证点，找到 {len(valid_sentences)} 个可用句子")
    
    default_points = []
    for i, sentence in enumerate(valid_sentences[:5]):  # 最多取5个句子
        # 提取更有意义的搜索关键词
        search_keywords = sentence[:100] if len(sentence) > 100 else sentence
        
        default_points.append({
            "内容": sentence,
            "重要性": "中",
            "搜索关键词": search_keywords
        })
        logger.debug(f"生成默认验证点 {i+1}: {sentence[:50]}...")
    
    # 如果还是没有验证点，创建一个直接包含文本前200字符的验证点
    if not default_points:
        logger.warning("无法从文本中提取有效句子，创建基本验证点")
        
        # 如果文本不为空，则添加到验证点
        if text.strip():
            first_chunk = text.strip()[:200]
            default_points.append({
                "内容": first_chunk,
                "重要性": "中",
                "搜索关键词": first_chunk[:100] if len(first_chunk) > 100 else first_chunk
            })
        else:
            # 如果文本为空，添加一个明确的错误信息
            default_points.append({
                "内容": "无有效内容可验证",
                "重要性": "低",
                "搜索关键词": "无效内容"
            })
    
    return default_points

def verify_search_results_with_deepseek(content: str, doubt_point: str, search_results: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    使用DeepSeek判断搜索结果与验证点的一致性
    
    参数:
        content (str): 原始新闻内容
        doubt_point (str): 需要验证的关键点
        search_results (List[Dict[str, str]]): 搜索结果列表
    
    返回:
        Dict[str, Any]: 验证结果，包含评分和结论
    """
    from ai_services import query_deepseek
    
    logger.info(f"使用DeepSeek验证关键点: {doubt_point[:50]}..." if len(doubt_point) > 50 else f"使用DeepSeek验证关键点: {doubt_point}")
    
    # 构建验证提示
    snippets = []
    if isinstance(search_results, dict) and "results" in search_results:
        search_results_list = search_results.get("results", [])
        for result in search_results_list[:5]:  # 只取前5个结果
            if isinstance(result, dict):
                snippet = result.get("content", result.get("snippet", ""))
                if snippet:
                    snippets.append(snippet)
    elif isinstance(search_results, list):
        for result in search_results[:5]:
            if isinstance(result, dict):
                snippet = result.get("content", result.get("snippet", ""))
                if snippet:
                    snippets.append(snippet)
    
    if not snippets:
        logger.warning("搜索结果中没有可用的摘要信息")
        return {
            "评分": 0.4,
            "结论": "未能找到足够的相关信息进行验证"
        }
    
    # 构建搜索结果文本
    search_results_text = ""
    for i, snippet in enumerate(snippets):
        search_results_text += f"[{i+1}] {snippet}\n\n"
    
    # 构建提示
    prompt = f"""
    我需要你判断以下新闻中的一个关键陈述点是否可以通过搜索结果得到验证。
    
    新闻原文: 
    {content[:1000] if len(content) > 1000 else content}
    
    需要验证的关键点: 
    {doubt_point}
    
    搜索结果:
    {search_results_text}
    
    请根据上述搜索结果，判断关键点的可信度，并给出0-1之间的评分（1表示完全一致，0表示完全不一致）。
    
    请以JSON格式返回，格式如下:
    {{
      "评分": 0.x,
      "结论": "你的判断结论"
    }}
    """
    
    try:
        # 调用DeepSeek API进行验证
        response = query_deepseek(prompt)
        
        # 尝试解析JSON响应
        verification_result = None
        try:
            verification_result = json.loads(response)
        except json.JSONDecodeError:
            # 如果解析失败，尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    verification_result = json.loads(json_match.group(0))
                except:
                    logger.error("无法解析DeepSeek返回的JSON格式验证结果")
                    return generate_default_verification_result(doubt_point, snippets)
            else:
                logger.error("DeepSeek响应中未找到JSON格式的验证结果")
                return generate_default_verification_result(doubt_point, snippets)
        
        # 验证返回的格式是否正确
        if not isinstance(verification_result, dict):
            logger.error("DeepSeek返回的验证结果不是字典格式")
            return generate_default_verification_result(doubt_point, snippets)
        
        if "评分" not in verification_result:
            logger.error("DeepSeek返回的验证结果中缺少'评分'字段")
            verification_result["评分"] = 0.5
            
        if "结论" not in verification_result:
            logger.error("DeepSeek返回的验证结果中缺少'结论'字段")
            verification_result["结论"] = "AI未能提供结论，无法判断"
        
        # 确保评分在0-1之间
        score = verification_result.get("评分", 0.5)
        if isinstance(score, str):
            try:
                score = float(score)
            except:
                score = 0.5
        
        score = max(0.0, min(1.0, score))
        verification_result["评分"] = score
        
        return verification_result
    except Exception as e:
        logger.error(f"验证搜索结果时出错: {e}")
        logger.error(traceback.format_exc())
        return generate_default_verification_result(doubt_point, snippets)

def generate_default_verification_result(doubt_point: str, snippets: List[str]) -> Dict[str, Any]:
    """
    当DeepSeek API验证失败时，生成默认验证结果
    
    参数:
        doubt_point (str): 需要验证的关键点
        snippets (List[str]): 搜索结果摘要列表
    
    返回:
        Dict[str, Any]: 默认验证结果
    """
    # 如果有搜索结果，但API调用失败，给一个中等分数
    if snippets:
        # 执行一个简单的关键词匹配
        doubt_words = set(re.findall(r'\b\w+\b', doubt_point.lower()))
        match_count = 0
        for snippet in snippets:
            snippet_words = set(re.findall(r'\b\w+\b', snippet.lower()))
            intersection = doubt_words.intersection(snippet_words)
            match_count += len(intersection) / len(doubt_words) if doubt_words else 0
        
        match_score = min(1.0, match_count / len(snippets)) if snippets else 0.5
        
        return {
            "评分": max(0.4, match_score),
            "结论": "系统通过简单关键词匹配进行评估，结果可能不够精确"
        }
    else:
        return {
            "评分": 0.3,
            "结论": "未找到足够的相关信息进行验证，且AI验证失败"
        } 