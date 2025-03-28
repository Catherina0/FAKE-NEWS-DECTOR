#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
引用验证模块
负责使用DeepSeek识别引用，并使用SearXNG验证引用内容的真实性
"""

import logging
import json
import re
import time
from typing import Dict, List, Any, Tuple, Optional
import traceback

# 初始化logger
logger = logging.getLogger(__name__)

def validate_citations(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    使用DeepSeek和SearXNG验证引用内容的真实性
    
    流程:
    1. 使用DeepSeek识别文本中的引用内容
    2. 对每个识别出的引用，使用SearXNG进行搜索
    3. 将搜索结果传回DeepSeek进行验证
    4. 返回综合评分和详细结果
    
    参数:
        text (str): 新闻文本
    
    返回:
        Tuple[float, Dict[str, Any]]: (引用可信度评分, 详细验证结果) 或 (None, 错误信息) 如果无法完成分析
    """
    from config import DEEPSEEK_API_AVAILABLE, SEARXNG_AVAILABLE
    from ai_services import identify_citations_with_deepseek, verify_citations_with_deepseek
    from search_services import search_with_searxng, test_searxng_connection
    
    logger.info("开始验证引用内容")
    
    # 检查服务可用性
    if not DEEPSEEK_API_AVAILABLE:
        logger.warning("DeepSeek API不可用，无法执行完整的引用验证")
        return None, {
            "error": "DeepSeek API不可用，无法执行完整的引用验证",
            "分析状态": "失败",
            "详细信息": "缺少DeepSeek API服务，该项不参与评分"
        }
    
    # 使用DeepSeek识别引用内容
    try:
        citations = identify_citations_with_deepseek(text)
    except Exception as e:
        logger.error(f"DeepSeek识别引用内容失败: {e}")
        return None, {
            "error": f"DeepSeek识别引用内容失败: {str(e)}",
            "分析状态": "失败",
            "详细信息": "引用识别过程出错，该项不参与评分"
        }
    
    if not citations:
        logger.info("未识别到引用内容")
        return 0.7, {
            "引用验证评分": 0.7,
            "引用详情": [],
            "总结": "未识别到明确的引用内容，无需验证",
            "分析状态": "成功"
        }
    
    logger.info(f"DeepSeek识别到 {len(citations)} 个引用")
    
    # 重新测试SearXNG连接状态，确保状态是最新的
    logger.debug("重新检查SearXNG连接状态...")
    if not test_searxng_connection():
        logger.warning("SearXNG不可用，无法执行完整的引用验证")
        return None, {
            "warning": "SearXNG不可用，引用验证无法完成",
            "引用详情": citations,
            "总结": "由于SearXNG搜索服务不可用，无法验证引用内容的真实性",
            "分析状态": "失败",
            "详细信息": "缺少SearXNG搜索服务，该项不参与评分"
        }
    
    # 对每个引用进行验证
    try:
        verification_results = []
        total_score = 0.0
        verified_count = 0
        connection_lost = False
        
        for citation in citations:
            citation_content = citation.get("content", "")
            citation_confidence = citation.get("confidence", 0.5)
            
            logger.info(f"验证引用: {citation_content[:50]}...")
            
            # 再次确认SearXNG仍然可用
            if not test_searxng_connection():
                logger.warning("SearXNG连接状态变为不可用，中止验证过程")
                connection_lost = True
                break
            
            # 使用SearXNG搜索验证引用内容
            clean_text = re.sub(r'\s+', ' ', citation_content).strip()
            
            # 如果文本太短，不进行验证
            if len(clean_text) < 10:
                verification_results.append({
                    "引用内容": citation_content,
                    "验证状态": "跳过",
                    "验证评分": citation_confidence,
                    "验证详情": "引用文本太短，无法进行有效验证"
                })
                total_score += citation_confidence
                verified_count += 1
                continue
            
            # 如果文本太长，截取前100个字符进行搜索
            search_text = clean_text[:100] if len(clean_text) > 100 else clean_text
            
            try:
                # 使用SearXNG搜索
                logger.info(f"使用SearXNG搜索: {search_text}")
                search_results = search_with_searxng(f'"{search_text}"', num_results=5)
                
                if not search_results or not search_results.get("results"):
                    logger.warning("SearXNG搜索未返回结果")
                    verification_results.append({
                        "引用内容": citation_content,
                        "验证状态": "未验证",
                        "验证评分": citation_confidence * 0.8, # 降低评分
                        "验证详情": "未找到相关搜索结果"
                    })
                    total_score += citation_confidence * 0.8
                    verified_count += 1
                    continue
                
                # 使用DeepSeek验证搜索结果
                deepseek_verification = verify_citations_with_deepseek([citation], search_results)
                
                if deepseek_verification and len(deepseek_verification) > 0:
                    verification = deepseek_verification[0]
                    verified = verification.get("verified", False)
                    score = verification.get("score", 0.0)
                    reason = verification.get("reason", "")
                    
                    verification_results.append({
                        "引用内容": citation_content,
                        "验证状态": "已验证" if verified else "验证失败",
                        "验证评分": score,
                        "验证详情": reason
                    })
                    
                    total_score += score
                    verified_count += 1
                else:
                    logger.warning("DeepSeek验证返回空结果")
                    verification_results.append({
                        "引用内容": citation_content,
                        "验证状态": "验证出错",
                        "验证评分": citation_confidence * 0.7, # 降低评分
                        "验证详情": "DeepSeek验证过程出错"
                    })
                    total_score += citation_confidence * 0.7
                    verified_count += 1
            
            except Exception as e:
                logger.error(f"验证引用时出错: {e}")
                verification_results.append({
                    "引用内容": citation_content,
                    "验证状态": "验证出错",
                    "验证评分": citation_confidence * 0.6, # 显著降低评分
                    "验证详情": f"验证过程出错: {str(e)}"
                })
                total_score += citation_confidence * 0.6
                verified_count += 1
        
        # 处理连接中断但有部分验证结果的情况
        if connection_lost and verified_count > 0:
            logger.warning("SearXNG连接中断，但已完成部分验证")
            avg_score = total_score / verified_count
            final_score = max(0.0, min(1.0, avg_score))
            
            summary = f"引用验证过程中SearXNG连接中断，仅完成了{verified_count}/{len(citations)}个引用的验证。"
            result = {
                "引用验证评分": final_score,
                "引用详情": verification_results,
                "总结": summary,
                "分析状态": "部分成功",
                "警告": "SearXNG连接中断，结果不完整"
            }
            
            logger.info(f"引用验证部分完成，总评分: {final_score:.2f}")
            return final_score, result
        
        # 如果没有成功验证任何引用，返回失败状态
        if verified_count == 0:
            return None, {
                "error": "所有引用验证均失败",
                "分析状态": "失败",
                "详细信息": "无法完成任何引用的验证，该项不参与评分"
            }
            
        # 计算平均评分
        avg_score = total_score / verified_count if verified_count > 0 else 0.5
        
        # 限制评分范围
        final_score = max(0.0, min(1.0, avg_score))
        
        # 生成总结
        summary = generate_validation_summary(verification_results, final_score)
        
        result = {
            "引用验证评分": final_score,
            "引用详情": verification_results,
            "总结": summary,
            "分析状态": "成功"
        }
        
        logger.info(f"引用验证完成，总评分: {final_score:.2f}")
        return final_score, result
    
    except Exception as e:
        logger.error(f"引用验证过程失败: {e}")
        logger.error(traceback.format_exc())
        return None, {
            "error": f"引用验证过程失败: {str(e)}",
            "分析状态": "失败",
            "详细信息": "验证过程出错，该项不参与评分"
        }

def generate_validation_summary(verification_results: List[Dict[str, Any]], score: float) -> str:
    """
    生成引用验证总结
    
    参数:
        verification_results (List[Dict[str, Any]]): 验证结果列表
        score (float): 总体评分
    
    返回:
        str: 总结文本
    """
    verified_count = len([r for r in verification_results if r.get("验证状态") == "已验证"])
    total_count = len(verification_results)
    
    if total_count == 0:
        return "未检测到任何引用内容"
    
    # 更准确地计算验证通过的数量
    verified_count = len([r for r in verification_results if r.get("验证状态") == "已验证" or r.get("验证评分", 0) >= 0.7])
    verification_ratio = verified_count / total_count
    
    if score >= 0.8:
        if verification_ratio >= 0.8:
            return f"引用内容高度可信。共有{total_count}处引用，其中{verified_count}处通过了验证。"
        else:
            return f"引用内容整体可信，但部分引用无法完全验证。共有{total_count}处引用，其中{verified_count}处通过了验证。"
    elif score >= 0.6:
        return f"引用内容基本可信，但有一些疑点。共有{total_count}处引用，其中{verified_count}处通过了验证。"
    elif score >= 0.4:
        return f"引用内容可信度较低，多数引用无法验证。共有{total_count}处引用，仅有{verified_count}处通过了验证。"
    else:
        return f"引用内容可信度极低，几乎所有引用都无法验证。共有{total_count}处引用，仅有{verified_count}处通过了验证。"

# 如果直接运行此模块，执行简单测试
if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 加载环境变量
    load_dotenv()
    
    # 设置API可用性
    from config import DEEPSEEK_API_AVAILABLE, SEARXNG_AVAILABLE
    
    if not DEEPSEEK_API_AVAILABLE:
        print("警告: DeepSeek API 不可用，测试将受限")
    
    if not SEARXNG_AVAILABLE:
        print("警告: SearXNG 不可用，测试将受限")
    
    # 测试文本
    test_text = """
    据新华社报道，中国科学家近期在量子计算领域取得重大突破。
    研究团队负责人李教授表示："我们的成果将极大推动量子计算的实用化进程。"
    但有国外专家质疑这一成果的实际应用价值，CNN引述美国物理学家约翰逊的话："中国的量子研究虽然进展迅速，但距离实用化还有很长的路要走。"
    根据科技部发布的数据，中国在量子计算领域的投入已超过100亿元人民币。
    """
    
    print("开始测试引用验证模块...")
    score, details = validate_citations(test_text)
    
    print(f"引用验证评分: {score:.2f}")
    print("验证详情:")
    print(json.dumps(details, ensure_ascii=False, indent=2))
    
    print("测试完成") 