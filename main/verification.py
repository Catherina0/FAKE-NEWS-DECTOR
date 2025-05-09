#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import re
import json
import time
import random
import traceback
from urllib.parse import urlparse
from typing import Dict, List, Tuple, Any, Optional, Union

# 导入本地模块
from web_utils import search_with_searxng, get_text_from_url, evaluate_domain_trust
from text_analysis import check_ai_content, analyze_language_neutrality
from ai_services import query_deepseek

logger = logging.getLogger(__name__)

def generate_detailed_report(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成详细的分析报告
    
    参数:
        results: 验证结果字典
    
    返回:
        详细报告字典
    """
    report = {
        "来源引用质量": {
            "综合评分": round(results.get("citation_analysis", {}).get("overall_score", 0) * 100) / 100,
            "引用数量": results.get("citation_analysis", {}).get("total_citations", 0),
            "验证通过数量": results.get("citation_analysis", {}).get("verified_citations", 0),
            "来源权威性": round(results.get("citation_analysis", {}).get("authority_score", 0) * 100) / 100,
            "来源多样性": round(results.get("citation_analysis", {}).get("diversity_score", 0) * 100) / 100,
            "详细情况": "引用内容分析完成，" + (
                f"共有{results.get('citation_analysis', {}).get('total_citations', 0)}处引用，"
                f"其中{results.get('citation_analysis', {}).get('verified_citations', 0)}处通过了验证。"
            )
        },
        "深度分析": {
            "内容真实性": round(results.get("content_verification", {}).get("truth_score", 0.9) * 100) / 100,
            "信息准确性": round(results.get("content_verification", {}).get("accuracy_score", 0.9) * 100) / 100,
            "来源可靠性": round(results.get("url_analysis", {}).get("score", 0.9) * 100) / 100,
            "语言客观性": round(results.get("content_verification", {}).get("objectivity_score", 0.9) * 100) / 100,
            "逻辑连贯性": round(results.get("content_verification", {}).get("coherence_score", 0.9) * 100) / 100,
            "引用质量": round(results.get("citation_analysis", {}).get("overall_score", 0.9) * 100) / 100
        },
        "交叉验证": {
            "综合评分": round(results.get("overall_score", 0) * 100) / 100,
            "验证成功点": len([ref for ref in results.get("cross_references", []) if ref.get("similarity", 0) > 0.7]),
            "验证失败点": len([ref for ref in results.get("cross_references", []) if ref.get("similarity", 0) <= 0.3]),
            "验证无结果点": len([ref for ref in results.get("cross_references", []) if ref.get("similarity", 0) > 0.3 and ref.get("similarity", 0) <= 0.7]),
            "评估": "高度可信" if results.get("overall_score", 0) > 0.8 else 
                   "较为可信" if results.get("overall_score", 0) > 0.6 else 
                   "中等可信" if results.get("overall_score", 0) > 0.4 else "可信度较低"
        }
    }
    
    return report

def search_and_verify_news(text: str, url: Optional[str] = None, image_paths: Optional[List[str]] = None, no_online: bool = False) -> Dict[str, Any]:
    """
    搜索和验证新闻内容
    
    参数:
        text: 新闻文本
        url: 新闻URL
        image_paths: 图片路径列表
        no_online: 是否禁用在线验证
    
    返回:
        验证结果字典
    """
    logger.info("开始进行新闻搜索和验证")
    
    # 初始化结果
    results = {
        "url_analysis": None,
        "content_verification": None,
        "search_results": None,
        "cross_references": [],
        "citation_analysis": None,
        "overall_score": 0.5,
        "confidence": "中等"
    }
    
    try:
        # 添加引用分析
        citation_results = analyze_citations(text)
        results["citation_analysis"] = citation_results
        
        # 更新整体评分计算
        citation_weight = 0.3
        cross_ref_weight = 0.4
        url_weight = 0.3
        
        if "overall_score" not in citation_results:
            raise ValueError("引用分析中缺少整体评分")
        citation_score = citation_results["overall_score"]
        
        if "overall_score" not in results:
            raise ValueError("结果中缺少交叉引用评分")
        cross_ref_score = results["overall_score"]
        
        if not results.get("url_analysis") or "score" not in results["url_analysis"]:
            raise ValueError("URL分析结果缺失或不完整")
        url_score = results["url_analysis"]["score"]
        
        results["overall_score"] = (
            citation_score * citation_weight +
            cross_ref_score * cross_ref_weight +
            url_score * url_weight
        )
        
        # 1. 分析URL (如果提供)
        if url:
            domain_score, domain_details = evaluate_domain_trust(url)
            results["url_analysis"] = {
                "score": domain_score,
                "domain": urlparse(url).netloc,
                "details": domain_details
            }
        
        # 2. 提取关键事实和主题
        # 简化版本，仅提取标题和前几句话
        lines = text.strip().split('\n')
        title = lines[0] if lines else ""
        first_paragraph = ' '.join(lines[1:3]) if len(lines) > 1 else ""
        
        # 创建搜索查询
        search_query = title
        
        # 3. 在线验证 (如果启用)
        if not no_online:
            # 搜索相关内容
            search_results = search_with_searxng(search_query)
            if search_results and "results" in search_results:
                results["search_results"] = {
                    "query": search_query,
                    "count": len(search_results["results"]),
                    "top_results": search_results["results"][:5] if search_results["results"] else []
                }
                
                # 如果找到结果，计算交叉参考得分
                if search_results["results"]:
                    cross_references = []
                    total_similarity = 0
                    
                    for result in search_results["results"][:3]:
                        # 获取原始内容
                        result_url = result.get("url", "")
                        source_text, _ = get_text_from_url(result_url)
                        
                        if source_text:
                            # 计算相似度
                            from utils import find_common_substrings
                            common_parts = find_common_substrings(text, source_text)
                            
                            if common_parts:
                                longest_match = common_parts[0]
                                similarity = len(longest_match) / len(text)
                                total_similarity += similarity
                                
                                cross_references.append({
                                    "url": result_url,
                                    "title": result.get("title", ""),
                                    "similarity": similarity,
                                    "sample_match": longest_match[:100] + "..." if len(longest_match) > 100 else longest_match
                                })
                    
                    # 计算平均相似度
                    avg_similarity = total_similarity / len(cross_references) if cross_references else 0
                    results["cross_references"] = {
                        "count": len(cross_references),
                        "sources": cross_references,
                        "average_similarity": avg_similarity
                    }
                    
                    # 更新总体得分
                    results["overall_score"] = min(0.9, max(0.1, avg_similarity))
        
        # 4. 评估整体可信度
        overall_score = results["overall_score"]
        
        if overall_score >= 0.7:
            results["confidence"] = "高"
        elif overall_score >= 0.4:
            results["confidence"] = "中等"
        else:
            results["confidence"] = "低"
        
        # 生成详细报告
        detailed_report = generate_detailed_report(results)
        results["detailed_report"] = detailed_report
        
        logger.info(f"新闻搜索和验证完成，总体评分: {overall_score}")
        return results
        
    except Exception as e:
        logger.error(f"新闻搜索和验证过程出错: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": f"验证过程出错: {str(e)}",
            "overall_score": 0.5,
            "confidence": "无法确定",
            "detailed_report": generate_detailed_report({
                "overall_score": 0.5,
                "citation_analysis": {"overall_score": 0.5, "total_citations": 0, "verified_citations": 0},
                "cross_references": []
            })
        }

def web_cross_verification(text: str, api_key: Optional[str] = None) -> Tuple[float, Dict[str, Any]]:
    """
    使用网络交叉验证新闻内容
    
    参数:
        text: 新闻文本
        api_key: DeepSeek API密钥 (可选)
    
    返回:
        (可信度得分, 详细结果)
    """
    logger.info("开始进行网络交叉验证")
    
    # 提取文本中的关键信息
    # 简化版本，提取前200个字符作为搜索内容
    search_text = text[:200].replace('\n', ' ').strip()
    
    try:
        # 使用SearXNG搜索相关内容
        search_results = search_with_searxng(search_text)
        
        if not search_results or "results" not in search_results or not search_results["results"]:
            logger.warning("未找到相关搜索结果")
            return 0.5, {"warning": "未找到相关搜索结果，无法进行交叉验证"}
        
        # 初始化验证结果
        results = {
            "sources_found": len(search_results["results"]),
            "verification_details": [],
            "overall_consistency": 0.0
        }
        
        # 计算与搜索结果的一致性
        total_consistency = 0.0
        verified_count = 0
        
        for i, result in enumerate(search_results["results"][:5]):
            try:
                # 获取结果URL和标题
                result_url = result.get("url", "")
                result_title = result.get("title", "")
                
                # 评估域名可信度
                domain_score, _ = evaluate_domain_trust(result_url)
                
                # 提取内容
                content, _ = get_text_from_url(result_url)
                
                if content:
                    # 简化的一致性评估
                    from utils import find_common_substrings
                    common_parts = find_common_substrings(text, content)
                    
                    consistency = 0.0
                    if common_parts:
                        consistency = min(0.9, len(common_parts[0]) / 100)  # 简化的一致性评分
                    
                    # 加入验证细节
                    verification_detail = {
                        "source": result_url,
                        "title": result_title,
                        "domain_trust": domain_score,
                        "consistency": consistency,
                        "matching_sample": common_parts[0][:100] + "..." if common_parts and len(common_parts[0]) > 100 else "无显著匹配内容"
                    }
                    
                    results["verification_details"].append(verification_detail)
                    
                    # 计算总一致性（加权平均）
                    # 来源可信度高的内容权重更大
                    weight = 0.5 + (domain_score * 0.5)  # 0.5-1.0的权重
                    total_consistency += consistency * weight
                    verified_count += weight
            except Exception as e:
                logger.error(f"处理搜索结果时出错: {e}")
                continue
        
        # 计算整体一致性得分
        if verified_count > 0:
            results["overall_consistency"] = total_consistency / verified_count
        else:
            results["overall_consistency"] = 0.5
            
        return results["overall_consistency"], results
        
    except Exception as e:
        logger.error(f"网络交叉验证过程出错: {e}")
        logger.error(traceback.format_exc())
        return 0.5, {"error": f"验证过程出错: {str(e)}"}

def local_text_credibility(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    本地评估文本可信度（已禁用）
    
    参数:
        text: 新闻文本
    
    返回:
        (可信度得分, 详细结果)
    """
    logger.info("本地文本可信度评估功能已禁用")
    
    result = {
        "ai_content": {
            "score": 0.5,
            "details": "本地分析功能已禁用"
        },
        "language_neutrality": {
            "score": 0.5,
            "details": "本地分析功能已禁用"
        },
        "facts_consistency": {
            "score": 0.5,
            "details": "本地分析功能已禁用"
        },
        "quotes_analysis": {
            "score": 0.5,
            "has_quotes": False,
            "details": "本地分析功能已禁用"
        },
        "overall_score": 0.5
    }
    
    return 0.5, result 

    """
    本地评估文本可信度（已禁用）
    
    参数:
        text: 新闻文本
    
    返回:
        (可信度得分, 详细结果)
    """
    '''
    logger.info("开始进行本地文本可信度评估")
    
    try:
        # 1. 检测AI生成内容
        ai_score, ai_details = check_ai_content(text)
        
        # 2. 分析语言中立性
        neutrality_score, neutrality_details = analyze_language_neutrality(text)
        
        # 3. 逻辑分析（简化版）
        # 检查事实陈述一致性
        facts_consistency = 0.7  # 简化的默认评分
        
        # 4. 引用和来源分析（简化版）
        # 检查是否包含引用
        has_quotes = '"' in text or '"' in text or '"' in text
        quotes_score = 0.7 if has_quotes else 0.4
        
        # 组合各项评分
        overall_score = (
            ai_score * 0.3 + 
            neutrality_score * 0.3 + 
            facts_consistency * 0.2 + 
            quotes_score * 0.2
        )
        
        result = {
            "ai_content": {
                "score": ai_score,
                "details": ai_details
            },
            "language_neutrality": {
                "score": neutrality_score,
                "details": neutrality_details
            },
            "facts_consistency": {
                "score": facts_consistency,
                "details": "基于文本内部事实陈述的一致性评估"
            },
            "quotes_analysis": {
                "score": quotes_score,
                "has_quotes": has_quotes,
                "details": "基于文本中引用内容的评估"
            },
            "overall_score": overall_score
        }
        
        return overall_score, result
        
    except Exception as e:
        logger.error(f"本地文本可信度评估过程出错: {e}")
        logger.error(traceback.format_exc())
        return 0.5, {"error": f"评估过程出错: {str(e)}"} 
    '''
    
def analyze_citations(text: str) -> Dict[str, Any]:
    """
    分析文本中的引用质量
    
    参数:
        text: 新闻文本
    
    返回:
        引用分析结果
    """
    try:
        # 使用正则表达式匹配引用
        quote_pattern = r'["""]([^"""]+)["""]'
        citations = re.findall(quote_pattern, text)
        
        results = {
            "total_citations": len(citations),
            "verified_citations": 0,
            "citation_details": [],
            "authority_score": 0.0,
            "diversity_score": 0.0,
            "overall_score": 0.0
        }
        
        if not citations:
            return results
            
        # 分析每个引用
        verified_count = 0
        sources = set()
        authority_total = 0.0
        
        for quote in citations:
            # 简单的验证逻辑
            is_verified = len(quote.strip()) > 10  # 基本长度检查
            if is_verified:
                verified_count += 1
            
            # 记录来源（简化版）
            source = "unknown"
            sources.add(source)
            
            # 计算权威性（示例值）
            authority = 0.8 if is_verified else 0.4
            authority_total += authority
            
            results["citation_details"].append({
                "quote": quote,
                "verified": is_verified,
                "source": source,
                "authority": authority
            })
        
        # 计算各项分数
        results["verified_citations"] = verified_count
        results["authority_score"] = authority_total / len(citations)
        results["diversity_score"] = len(sources) / len(citations)
        results["overall_score"] = (results["authority_score"] * 0.6 + 
                                  results["diversity_score"] * 0.4)
        
        return results
        
    except Exception as e:
        logger.error(f"引用分析过程出错: {e}")
        return {
            "error": str(e),
            "total_citations": 0,
            "verified_citations": 0,
            "overall_score": 0.5
        }

    
