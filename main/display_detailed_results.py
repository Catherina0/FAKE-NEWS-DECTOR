#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
显示引用验证详细结果
"""

from typing import Dict, Any, List

def display_citation_validation_results(citation_validation_data: Dict[str, Any]) -> None:
    """
    显示引用验证的详细结果
    
    参数:
        citation_validation_data (Dict[str, Any]): 引用验证结果数据
    """
    if not citation_validation_data:
        print("未找到引用验证数据。")
        return
    
    print("\n引用验证结果:")
    
    # 显示总体评分
    overall_score = citation_validation_data.get("总体评分", 0)
    print(f"总体评分: {overall_score:.2f}")
    
    # 显示验证总结
    if "验证总结" in citation_validation_data:
        print(f"验证总结: {citation_validation_data['验证总结']}")
    
    # 显示验证陈述
    verification_results = citation_validation_data.get("verification_results", [])
    if verification_results:
        print(f"\n共验证{len(verification_results)}个陈述:")
        
        # 统计验证状态
        verified_count = len([r for r in verification_results if r.get("验证评分", 0) >= 0.7])
        unverified_count = len([r for r in verification_results if r.get("验证评分", 0) < 0.5])
        partial_count = len(verification_results) - verified_count - unverified_count
        
        print(f"- 已验证: {verified_count}个")
        print(f"- 部分验证: {partial_count}个")
        print(f"- 无法验证: {unverified_count}个")
        
        # 显示各个陈述的详细信息
        print("\n陈述详情:")
        for i, result_item in enumerate(verification_results, 1):
            content = result_item.get("内容", result_item.get("验证内容", "未知内容"))
            importance = result_item.get("重要性", "中")
            score = result_item.get("验证评分", 0.5)
            status = result_item.get("验证状态", "")
            
            print(f"\n{i}. {content}")
            print(f"   重要性: {importance}")
            print(f"   评分: {score:.2f}")
            
            if status:
                print(f"   状态: {status}")
            
            if "验证原因" in result_item:
                print(f"   原因: {result_item['验证原因']}")
            
            if "搜索结果摘要" in result_item and result_item["搜索结果摘要"]:
                print(f"   相关摘要:")
                for j, summary in enumerate(result_item["搜索结果摘要"][:2], 1):
                    if summary:
                        print(f"     {j}. {summary[:100]}..." if len(summary) > 100 else f"     {j}. {summary}")
            
            if "搜索结果" in result_item and isinstance(result_item["搜索结果"], list):
                print(f"   相关链接:")
                for j, search_result in enumerate(result_item["搜索结果"][:2], 1):
                    if isinstance(search_result, dict):
                        url = search_result.get("url", "")
                        title = search_result.get("title", "未知标题")
                        print(f"     {j}. {title}")
                        print(f"        {url}")
    else:
        print("未找到验证陈述数据。")

if __name__ == "__main__":
    # 测试数据
    test_data = {
        "总体评分": 0.75,
        "验证总结": "内容基本可信，主要陈述得到了验证。",
        "verification_results": [
            {
                "内容": "中国科学家在量子计算领域取得重大突破。",
                "重要性": "高",
                "验证评分": 0.85,
                "验证状态": "已验证",
                "验证原因": "多个可靠来源证实了这一成就",
                "搜索结果摘要": ["中国科学家团队在量子计算领域取得突破性进展，研发出新型量子芯片。", "Science杂志报道了中国科学家的量子计算突破。"]
            },
            {
                "内容": "美国物理学家约翰逊质疑这一成果的实际应用价值。",
                "重要性": "中",
                "验证评分": 0.60,
                "验证状态": "部分验证",
                "验证原因": "发现了相关评论，但缺乏完整的上下文",
                "搜索结果摘要": ["美国物理学家对中国量子计算研究提出了一些疑问。"]
            }
        ]
    }
    
    display_citation_validation_results(test_data) 