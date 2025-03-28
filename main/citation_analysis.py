#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
引用分析模块
负责分析新闻文本中的引用质量
"""

import logging
import re
from typing import Tuple, Dict, List, Any, Optional

# 初始化logger
logger = logging.getLogger(__name__)

def extract_citations(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取引用
    
    参数:
        text (str): 新闻文本
    
    返回:
        List[Dict[str, Any]]: 提取的引用列表，每项包含引用内容和上下文
    """
    logger.info("开始从文本中提取引用")
    
    # 初始化引用列表
    citations = []
    
    # 提取直接引用（使用引号）
    quote_patterns = [
        (r'"([^"]+)"', "英文双引号"),
        (r"'([^']+)'", "英文单引号"),
        (r"「([^」]+)」", "中文单引号"),
        (r"『([^』]+)』", "中文双引号"),
        (r"【([^】]+)】", "中文方括号"),
        (r"《([^》]+)》", "中文书名号")
    ]
    
    for pattern, quote_type in quote_patterns:
        for match in re.finditer(pattern, text):
            quote = match.group(1).strip()
            if len(quote) > 5:  # 只考虑长度大于5的引用
                # 提取引用上下文（前后各50个字符）
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # 尝试提取引用来源
                source = extract_citation_source(context)
                
                citations.append({
                    "内容": quote,
                    "类型": quote_type,
                    "上下文": context,
                    "来源": source,
                    "位置": (match.start(), match.end())
                })
    
    # 提取间接引用（使用引用指示词）
    citation_indicators = [
        "据.*?称", "据.*?表示", "据.*?介绍", "据.*?透露",
        "根据.*?的说法", "引述.*?的话", "引用.*?的说法",
        "according to", "said by", "stated by", "reported by",
        "as.*?mentioned", "as.*?stated", "as.*?reported"
    ]
    
    for indicator in citation_indicators:
        for match in re.finditer(indicator, text):
            # 提取可能的引用内容（匹配词后的100个字符）
            start = match.end()
            end = min(len(text), start + 100)
            
            # 尝试找到引用内容的结束位置（句号、感叹号、问号）
            content_text = text[start:end]
            end_match = re.search(r'[。！？.!?]', content_text)
            if end_match:
                content_text = content_text[:end_match.end()]
            
            # 提取引用来源
            indicator_text = text[match.start():match.end()]
            source = extract_source_from_indicator(indicator_text)
            
            if len(content_text.strip()) > 10:  # 只考虑长够长的内容
                citations.append({
                    "内容": content_text.strip(),
                    "类型": "间接引用",
                    "上下文": text[max(0, match.start() - 20):min(len(text), match.end() + 100)],
                    "来源": source,
                    "位置": (start, start + len(content_text))
                })
    
    logger.info(f"从文本中提取了{len(citations)}个引用")
    return citations

def extract_citation_source(context: str) -> str:
    """
    从引用上下文中提取可能的来源
    
    参数:
        context (str): 引用上下文
    
    返回:
        str: 提取的来源，如果没有找到则返回空字符串
    """
    source_patterns = [
        r'据(.*?)(?:称|表示|介绍|透露|说)',
        r'(?:据|根据|来自)(.*?)的(?:报道|消息|通报|公告|声明|说法)',
        r'(.*?)(?:称|表示|说|透露)',
        r'according to (.*?)[,.]',
        r'(.*?) (?:said|reported|stated|mentioned|claimed)',
        r'(?:source|information) from (.*?)[,.]'
    ]
    
    for pattern in source_patterns:
        match = re.search(pattern, context)
        if match:
            source = match.group(1).strip()
            # 过滤掉太长或太短的来源
            if 2 <= len(source) <= 30:
                return source
    
    return ""

def extract_source_from_indicator(indicator_text: str) -> str:
    """
    从引用指示词中提取来源
    
    参数:
        indicator_text (str): 引用指示词文本，如"据专家称"
    
    返回:
        str: 提取的来源
    """
    # 提取"据XXX称"中的XXX
    match = re.search(r'据(.*?)(?:称|表示|介绍|透露|说)', indicator_text)
    if match:
        return match.group(1).strip()
    
    # 提取"根据XXX的"中的XXX
    match = re.search(r'(?:据|根据|来自)(.*?)的', indicator_text)
    if match:
        return match.group(1).strip()
    
    # 提取"according to XXX"中的XXX
    match = re.search(r'according to (.*?)$', indicator_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return ""

def analyze_citation_quality(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    分析引用质量
    
    参数:
        citations (List[Dict[str, Any]]): 提取的引用列表
    
    返回:
        Dict[str, Any]: 引用质量分析结果
    """
    logger.info("开始分析引用质量")
    
    if not citations:
        return {
            "引用数量": 0,
            "引用分布": "无引用",
            "引用多样性": 0,
            "来源可靠性": 0,
            "总评": "文本中没有检测到引用内容，可信度较低。",
            "详细分析": ["未检测到任何引用内容，无法评估引用质量。"]
        }
    
    # 计算引用数量和密度
    citation_count = len(citations)
    
    # 分析引用来源的多样性
    unique_sources = set()
    for citation in citations:
        if citation["来源"]:
            unique_sources.add(citation["来源"])
    
    source_diversity = len(unique_sources) / citation_count if citation_count > 0 else 0
    
    # 分析引用的分布
    if citation_count == 0:
        distribution = "无引用"
    elif citation_count == 1:
        distribution = "单一引用"
    elif citation_count <= 3:
        distribution = "少量引用"
    elif citation_count <= 7:
        distribution = "适量引用"
    else:
        distribution = "丰富引用"
    
    # 初步评估来源可靠性（实际应用中可以连接外部数据库进行评估）
    known_reliable_sources = [
        "央视", "中央电视台", "新华社", "人民日报", "中国日报",
        "路透社", "法新社", "美联社", "BBC", "CNN",
        "纽约时报", "华盛顿邮报", "卫报", "金融时报",
        "科学", "自然", "柳叶刀", "新英格兰医学杂志",
        "哈佛大学", "牛津大学", "剑桥大学", "麻省理工学院",
        "中国科学院", "中国社会科学院"
    ]
    
    source_reliability = 0
    reliable_source_count = 0
    
    for source in unique_sources:
        for known_source in known_reliable_sources:
            if known_source in source:
                reliable_source_count += 1
                break
    
    if unique_sources:
        source_reliability = reliable_source_count / len(unique_sources)
    
    # 计算最终评分
    quality_score = 0.0
    quality_details = []
    
    # 引用数量评分（0-0.3）
    if citation_count == 0:
        count_score = 0.0
        quality_details.append("引用数量：无引用 (0分)")
    elif citation_count <= 2:
        count_score = 0.1
        quality_details.append(f"引用数量：较少 ({citation_count}个) (0.1分)")
    elif citation_count <= 5:
        count_score = 0.2
        quality_details.append(f"引用数量：适中 ({citation_count}个) (0.2分)")
    else:
        count_score = 0.3
        quality_details.append(f"引用数量：丰富 ({citation_count}个) (0.3分)")
    
    quality_score += count_score
    
    # 来源多样性评分（0-0.3）
    if source_diversity == 0:
        diversity_score = 0.0
        quality_details.append("来源多样性：无可识别来源 (0分)")
    elif source_diversity < 0.3:
        diversity_score = 0.1
        quality_details.append(f"来源多样性：低 ({len(unique_sources)}个不同来源) (0.1分)")
    elif source_diversity < 0.6:
        diversity_score = 0.2
        quality_details.append(f"来源多样性：中 ({len(unique_sources)}个不同来源) (0.2分)")
    else:
        diversity_score = 0.3
        quality_details.append(f"来源多样性：高 ({len(unique_sources)}个不同来源) (0.3分)")
    
    quality_score += diversity_score
    
    # 来源可靠性评分（0-0.4）
    if source_reliability == 0:
        reliability_score = 0.0
        quality_details.append("来源可靠性：无法验证来源可靠性 (0分)")
    elif source_reliability < 0.3:
        reliability_score = 0.1
        quality_details.append(f"来源可靠性：较低 ({reliable_source_count}个可靠来源) (0.1分)")
    elif source_reliability < 0.6:
        reliability_score = 0.2
        quality_details.append(f"来源可靠性：中等 ({reliable_source_count}个可靠来源) (0.2分)")
    elif source_reliability < 0.9:
        reliability_score = 0.3
        quality_details.append(f"来源可靠性：较高 ({reliable_source_count}个可靠来源) (0.3分)")
    else:
        reliability_score = 0.4
        quality_details.append(f"来源可靠性：高 ({reliable_source_count}个可靠来源) (0.4分)")
    
    quality_score += reliability_score
    
    # 总体评估
    if quality_score >= 0.8:
        overall_assessment = "引用质量优秀，内容来源可靠且多样。"
    elif quality_score >= 0.6:
        overall_assessment = "引用质量良好，有一定数量的可靠来源。"
    elif quality_score >= 0.4:
        overall_assessment = "引用质量一般，来源有限或可靠性不足。"
    elif quality_score >= 0.2:
        overall_assessment = "引用质量较差，缺乏足够的可靠来源。"
    else:
        overall_assessment = "引用质量极差，几乎没有可验证的来源。"
    
    result = {
        "引用数量": citation_count,
        "引用分布": distribution,
        "引用多样性": source_diversity,
        "来源可靠性": source_reliability,
        "总评": overall_assessment,
        "详细分析": quality_details
    }
    
    logger.info(f"引用质量分析完成，总评分: {quality_score:.2f}")
    return result

def judge_citation_truthfulness(citation):
    """
    判断引用内容的真实性
    (使用DeepSeek API实现，如果不可用使用本地方法)
    
    参数:
        citation: 引用信息，可以是字符串或字典
    
    返回:
        float | dict: 真实性评分（0-1）或包含评分的字典
    """
    # 处理输入参数
    if isinstance(citation, str):
        # 如果输入是字符串，创建一个虚拟引用字典
        citation_dict = {
            "内容": citation,
            "来源": "未知来源",
            "上下文": citation
        }
    else:
        citation_dict = citation
    
    # 尝试使用DeepSeek API
    from config import DEEPSEEK_API_AVAILABLE
    
    if DEEPSEEK_API_AVAILABLE:
        from ai_services import judge_citation_with_deepseek
        try:
            return judge_citation_with_deepseek(citation_dict)
        except Exception as e:
            logger.warning(f"使用DeepSeek判断引用真实性失败: {e}，将使用本地方法")
    
    # 使用本地方法作为备选
    # 这里是一个简单的实现，实际应用中可以更复杂
    
    # 检查引用内容的特征
    content = citation_dict.get("内容", "")
    
    # 初始分数
    score = 0.5
    
    # 检查是否包含具体细节（数字、日期、地点等）
    has_specifics = bool(re.search(r'\d+|星期[一二三四五六日]|周[一二三四五六日]|[一二三四五六七八九十]月|[东南西北]|具体|详细', content))
    if has_specifics:
        score += 0.1
    
    # 检查是否包含极端用词
    extreme_words = ["绝对", "肯定", "一定", "必然", "全部", "所有", "完全", "从不", "永远"]
    has_extreme_words = any(word in content for word in extreme_words)
    if has_extreme_words:
        score -= 0.1
    
    # 检查来源可靠性
    source = citation_dict.get("来源", "")
    reliable_sources = ["央视", "新华社", "人民日报", "中国日报", "路透社", "法新社", "美联社", "BBC", "CNN"]
    if source and any(rs in source for rs in reliable_sources):
        score += 0.2
    
    # 限制评分范围
    score = min(1.0, max(0.0, score))
    
    # 为了兼容测试，如果是字符串输入，返回元组(分数, 详情)，否则返回分数
    if isinstance(citation, str):
        return score, {
            "score": score,
            "analysis": "基于本地算法的简单分析"
        }
    
    return score

def get_citation_score(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    获取文本的引用质量总评分
    
    参数:
        text (str): 新闻文本
    
    返回:
        Tuple[float, Dict[str, Any]]: (评分, 详细分析结果)
    """
    logger.info("开始评估引用质量")
    
    # 提取引用
    citations = extract_citations(text)
    
    # 分析引用质量
    quality_result = analyze_citation_quality(citations)
    
    # 如果启用DeepSeek，评估引用真实性
    from config import DEEPSEEK_API_AVAILABLE
    
    truthfulness_scores = []
    if DEEPSEEK_API_AVAILABLE and citations:
        logger.info("开始使用DeepSeek评估引用真实性")
        for citation in citations:
            result = judge_citation_truthfulness(citation)
            # 处理返回值可能是元组(分数, 详情)或单独分数的情况
            if isinstance(result, tuple):
                score, details = result
                truthfulness_scores.append(score)
                citation["真实性评分"] = score
                citation["真实性分析"] = details
            else:
                # 如果返回的是字典
                if isinstance(result, dict) and "score" in result:
                    score = result["score"]
                    truthfulness_scores.append(score)
                    citation["真实性评分"] = score
                    citation["真实性分析"] = result
                # 如果返回的是分数
                else:
                    truthfulness_scores.append(result)
                    citation["真实性评分"] = result
    
    # 计算最终引用评分
    # 默认引用评分
    final_score = 0.5
    
    # 检查"总评"字段是否存在
    if "总评" in quality_result and quality_result["总评"] is not None:
        # 这里我们只需将总评字段作为信息保留，不用于评分计算
        # 引用数量评分作为基础分数
        quality_score = 0.0
        if citations:
            if len(citations) <= 2:
                quality_score = 0.4
            elif len(citations) <= 5:
                quality_score = 0.6
            else:
                quality_score = 0.8
            
            # 如果有真实性评分，结合质量评分和真实性评分
            if truthfulness_scores:
                # 确保所有值都是数值类型
                numeric_scores = [s for s in truthfulness_scores if isinstance(s, (int, float))]
                if numeric_scores:
                    avg_truthfulness = sum(numeric_scores) / len(numeric_scores)
                    final_score = 0.7 * quality_score + 0.3 * avg_truthfulness
                    quality_result["真实性评分"] = avg_truthfulness
                else:
                    final_score = quality_score
            else:
                final_score = quality_score
    else:
        final_score = 0.5  # 默认中等评分
    
    # 确保评分在0-1范围内
    final_score = max(0.0, min(1.0, final_score))
    
    # 添加引用详情
    quality_result["引用详情"] = citations
    
    logger.info(f"引用质量评估完成，总评分: {final_score:.2f}")
    
    return final_score, quality_result

def analyze_citation_validity(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    分析引用内容的有效性
    使用DeepSeek API或本地方法评估引用的有效性和相关性
    
    参数:
        text (str): 新闻文本
    
    返回:
        Tuple[float, Dict[str, Any]]: (有效性评分, 详细分析结果)
    """
    logger.info("开始分析引用内容的有效性")
    
    # 提取引用
    citations = extract_citations(text)
    
    if not citations:
        return 0.5, {
            "引用数量": 0,
            "引用有效性": 0.5,
            "详细分析": ["文本中未检测到引用内容"],
            "总结": "未检测到引用内容，无法评估有效性"
        }
    
    from config import DEEPSEEK_API_AVAILABLE
    
    # 如果DeepSeek API可用，使用AI进行评估
    if DEEPSEEK_API_AVAILABLE:
        try:
            from ai_services import analyze_citation_validity_with_deepseek
            return analyze_citation_validity_with_deepseek(text, citations)
        except Exception as e:
            logger.warning(f"使用DeepSeek分析引用有效性失败: {e}，将使用本地方法")
    
    # 使用本地方法分析引用有效性
    total_validity_score = 0.0
    validity_details = []
    
    for citation in citations:
        # 检查引用与上下文的相关性
        context = citation.get("上下文", "")
        content = citation.get("内容", "")
        source = citation.get("来源", "未知来源")
        
        # 初始有效性评分
        validity_score = 0.5
        detail = {"引用内容": content[:50] + ("..." if len(content) > 50 else "")}
        
        # 检查1: 引用内容是否与上下文相关
        if context and content:
            # 简单相关性检查 - 检查关键词重叠
            context_words = set(re.findall(r'\w+', context.lower()))
            content_words = set(re.findall(r'\w+', content.lower()))
            common_words = context_words.intersection(content_words)
            
            relevance = len(common_words) / max(len(content_words), 1) if content_words else 0
            if relevance > 0.3:
                validity_score += 0.2
                detail["相关性"] = "高"
            elif relevance > 0.1:
                validity_score += 0.1
                detail["相关性"] = "中"
            else:
                validity_score -= 0.1
                detail["相关性"] = "低"
        
        # 检查2: 引用内容是否具体
        if len(content) > 100:
            validity_score += 0.1
            detail["具体性"] = "高"
        elif len(content) > 50:
            validity_score += 0.05
            detail["具体性"] = "中"
        else:
            detail["具体性"] = "低"
        
        # 检查3: 引用是否有明确来源
        if source and source != "未知来源":
            validity_score += 0.1
            detail["来源明确性"] = "高"
        else:
            detail["来源明确性"] = "低"
        
        # 检查4: 引用内容是否含有具体数据或事实
        has_facts = bool(re.search(r'\d+年|\d+月|\d+日|\d+%|\d+人|\d+元|\d+美元|\d+次', content))
        if has_facts:
            validity_score += 0.1
            detail["事实含量"] = "高"
        else:
            detail["事实含量"] = "低"
        
        # 限制评分范围
        validity_score = min(1.0, max(0.0, validity_score))
        
        # 评估结论
        if validity_score > 0.7:
            detail["评估"] = "高度有效"
        elif validity_score > 0.5:
            detail["评估"] = "有效"
        elif validity_score > 0.3:
            detail["评估"] = "部分有效"
        else:
            detail["评估"] = "低效或无效"
        
        detail["评分"] = validity_score
        validity_details.append(detail)
        total_validity_score += validity_score
    
    # 计算平均有效性评分
    avg_validity_score = total_validity_score / len(citations) if citations else 0.5
    
    # 生成总结
    if avg_validity_score > 0.7:
        summary = "引用内容高度有效，与文章主题紧密相关，且有具体事实支持"
    elif avg_validity_score > 0.5:
        summary = "引用内容基本有效，但部分引用相关性或具体性不足"
    elif avg_validity_score > 0.3:
        summary = "引用内容有效性一般，多数引用缺乏具体性或相关性"
    else:
        summary = "引用内容有效性较低，可能与文章主题关系不大或过于笼统"
    
    result = {
        "引用数量": len(citations),
        "引用有效性": avg_validity_score,
        "详细分析": validity_details,
        "总结": summary
    }
    
    logger.info(f"引用有效性分析完成，评分: {avg_validity_score:.2f}")
    return avg_validity_score, result 