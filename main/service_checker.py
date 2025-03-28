#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务检查模块
负责检查各项服务的可用性和状态报告
"""

import logging
from typing import Dict, Any, List
from config import (
    colorama_available, Fore, Style,
    SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR,
    RESET_COLOR, HEADER_COLOR, SUBHEADER_COLOR
)

# 初始化logger
logger = logging.getLogger(__name__)

def initialize_services():
    """
    初始化各项服务，测试连接状态
    
    返回:
        dict: 各服务可用状态和受影响的功能列表
    """
    # 导入需要的模块
    from ai_services import test_deepseek_connection, DEEPSEEK_API_AVAILABLE
    from search_services import test_searxng_connection, SEARXNG_AVAILABLE
    
    services_status = {
        "deepseek_api": False,
        "searxng": False,
        "affected_features": []
    }
    
    # 测试DeepSeek API连接
    try:
        if test_deepseek_connection():
            services_status["deepseek_api"] = True
            logger.info("DeepSeek API连接测试成功")
        else:
            services_status["affected_features"].append({
                "service": "DeepSeek API",
                "status": "不可用",
                "affected_features": [
                    "引用真实性判断(judge_citation_truthfulness)",
                    "引用验证(validate_citations)",
                    "引用质量评估(get_citation_score)",
                    "深度新闻分析(analyze_with_deepseek_v3)",
                    "交叉验证(perform_cross_validation)",
                    "验证点提取(extract_verification_points_with_deepseek)",
                    "搜索结果验证(verify_search_results_with_deepseek)"
                ]
            })
            logger.warning("DeepSeek API连接测试失败 - 将使用本地算法进行分析，精度可能受限")
    except Exception as e:
        services_status["affected_features"].append({
            "service": "DeepSeek API",
            "status": f"连接错误: {str(e)}",
            "affected_features": [
                "引用真实性判断(judge_citation_truthfulness)",
                "引用验证(validate_citations)",
                "引用质量评估(get_citation_score)",
                "深度新闻分析(analyze_with_deepseek_v3)",
                "交叉验证(perform_cross_validation)",
                "验证点提取(extract_verification_points_with_deepseek)",
                "搜索结果验证(verify_search_results_with_deepseek)"
            ]
        })
        logger.error(f"测试DeepSeek API连接时出错: {e}")
    
    # 测试SearXNG连接
    try:
        if test_searxng_connection():
            services_status["searxng"] = True
            logger.info("SearXNG连接测试成功")
        else:
            services_status["affected_features"].append({
                "service": "SearXNG搜索引擎",
                "status": "不可用",
                "affected_features": [
                    "交叉验证(perform_cross_validation)",
                    "搜索验证(search_with_searxng)",
                    "引用验证(verify_citation_with_searxng)"
                ]
            })
            logger.warning("SearXNG连接测试失败 - 交叉验证功能将受限")
    except Exception as e:
        services_status["affected_features"].append({
            "service": "SearXNG搜索引擎",
            "status": f"连接错误: {str(e)}",
            "affected_features": [
                "交叉验证(perform_cross_validation)",
                "搜索验证(search_with_searxng)",
                "引用验证(verify_citation_with_searxng)"
            ]
        })
        logger.error(f"测试SearXNG连接时出错: {e}")
    
    return services_status

def print_service_status(services_status):
    """
    打印服务状态和受影响的功能
    
    参数:
        services_status (dict): 服务状态字典
    """
    print("\n" + "="*80)
    print(f"{HEADER_COLOR}【系统自检】{RESET_COLOR}")
    print("-"*80)
    
    if services_status["deepseek_api"]:
        print(f"{SUCCESS_COLOR}✓ DeepSeek API 可用{RESET_COLOR}")
    else:
        print(f"{ERROR_COLOR}✗ DeepSeek API 不可用{RESET_COLOR}")
        print(f"  {WARNING_COLOR}● 将使用本地算法进行分析，精度可能受限{RESET_COLOR}")
    
    if services_status["searxng"]:
        print(f"{SUCCESS_COLOR}✓ SearXNG 搜索引擎可用{RESET_COLOR}")
    else:
        print(f"{ERROR_COLOR}✗ SearXNG 搜索引擎不可用{RESET_COLOR}")
        print(f"  {WARNING_COLOR}● 交叉验证功能将受限{RESET_COLOR}")
    
    affected_features = services_status.get("affected_features", [])
    if affected_features:
        print("\n" + "-"*80)
        print(f"{WARNING_COLOR}【受影响的功能】{RESET_COLOR}")
        for service in affected_features:
            print(f"\n{ERROR_COLOR}● {service['service']} - {service['status']}{RESET_COLOR}")
            print(f"  {WARNING_COLOR}以下功能将无法使用或性能下降:{RESET_COLOR}")
            for feature in service['affected_features']:
                print(f"  {WARNING_COLOR}→ {feature}{RESET_COLOR}")
    
    print("="*80 + "\n") 