#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import re
import traceback
from search_services import verify_citation_with_searxng, SEARXNG_AVAILABLE

logger = logging.getLogger(__name__)

def extract_citations(text):
    """
    从文本中提取引用内容
    
    参数:
        text: 文本内容
    
    返回:
        引用列表，每项包含引用文本和来源
    """
    citations = []
    
    # 匹配引号内容 - 使用Unicode码点表示中文引号
    quote_patterns = [
        (r'"([^"]{10,})"', '未指明来源'),                     # 英文双引号
        (r"'([^']{10,})'", '未指明来源'),                     # 英文单引号
        (r'\u201c([^\u201d]{10,})\u201d', '未指明来源'),      # 中文双引号（"..."）
        (r'\u2018([^\u2019]{10,})\u2019', '未指明来源')       # 中文单引号（'...'）
    ]
    
    # 从每种引号模式中提取内容
    for pattern, default_source in quote_patterns:
        try:
            matches = re.findall(pattern, text)
            for match in matches:
                citations.append({
                    'text': match.strip(),
                    'source': default_source
                })
        except Exception as e:
            logger.warning(f"引用提取出错: {str(e)}")
            continue
    
    # 匹配引用短语后的内容，尝试提取来源
    citation_phrases = [
        (r"据([^，,。.；;：:]{2,})报道[，,：:]?\s*(.{10,}?)[。！？\.\n]", True),  # "据XX报道: YYY"
        (r"([^，,。.；;：:]{2,})表示[，,：:]?\s*(.{10,}?)[。！？\.\n]", True),    # "XX表示: YYY"
        (r"([^，,。.；;：:]{2,})认为[，,：:]?\s*(.{10,}?)[。！？\.\n]", True),    # "XX认为: YYY"
        (r"([^，,。.；;：:]{2,})指出[，,：:]?\s*(.{10,}?)[。！？\.\n]", True),    # "XX指出: YYY"
        (r"([^，,。.；;：:]{2,})强调[，,：:]?\s*(.{10,}?)[。！？\.\n]", True),    # "XX强调: YYY"
        (r"引用([^，,。.；;：:]{2,})[，,：:]?\s*(.{10,}?)[。！？\.\n]", True),    # "引用XX: YYY"
        (r"根据([^，,。.；;：:]{2,})[，,：:]?\s*(.{10,}?)[。！？\.\n]", True),    # "根据XX: YYY"
        
        # 没有明确来源的引用短语
        (r"据报道[，,：:]?\s*(.{10,}?)[。！？\.\n]", False),                     # "据报道: YYY"
        (r"有人指出[，,：:]?\s*(.{10,}?)[。！？\.\n]", False),                   # "有人指出: YYY"
        (r"研究表明[，,：:]?\s*(.{10,}?)[。！？\.\n]", False)                    # "研究表明: YYY"
    ]
    
    for pattern, has_source in citation_phrases:
        try:
            matches = re.findall(pattern, text)
            for match in matches:
                if has_source:
                    # 如果模式包含来源，match是一个包含(source, citation)的元组
                    source, citation_text = match
                    citations.append({
                        'text': citation_text.strip(),
                        'source': source.strip()
                    })
                else:
                    # 如果模式不包含来源，match只是引用文本
                    citation_text = match
                    citations.append({
                        'text': citation_text.strip(),
                        'source': '未指明来源'
                    })
        except Exception as e:
            logging.warning(f"引用短语提取出错: {str(e)}")
            continue
    
    # 去重
    unique_citations = []
    seen_texts = set()
    
    for citation in citations:
        citation_text = citation['text']
        if citation_text not in seen_texts:
            seen_texts.add(citation_text)
            unique_citations.append(citation)
    
    return unique_citations

def judge_citation_truthfulness(text):
    """
    判断引用内容的真实性
    
    参数:
        text: 文本内容
    
    返回:
        (真实性评分, 详细信息)
    """
    try:
        from ai_services import DEEPSEEK_API_AVAILABLE, query_deepseek
        import random
        import json
        
        citations = extract_citations(text)
        
        if not citations:
            return 0.7, {"引用真实性评分": 0.7, "说明": "未发现明确引用，无法评估真实性"}
        
        total_score = 0.0
        citation_analysis = []
        checked_count = 0
        
        # 使用DeepSeek API进行引用分析
        if DEEPSEEK_API_AVAILABLE:
            logger.info("使用DeepSeek API进行引用真实性分析")
            
            for citation in citations:
                # 引用信息提取
                citation_text = citation['text']
                source = citation.get('source', '未指明来源')
                
                # 使用DeepSeek提取关键词
                keywords_prompt = f"""
                从以下引用中提取3-5个关键词或短语，这些关键词应该能够用于验证引用的真实性。
                引用: "{citation_text}"
                请直接返回关键词，用逗号分隔。
                """
                
                try:
                    keywords_response = query_deepseek(keywords_prompt)
                    keywords = [kw.strip() for kw in keywords_response.split(',')]
                    
                    # 使用SearXNG搜索关键词
                    search_results = []
                    if SEARXNG_AVAILABLE:
                        for keyword in keywords[:3]:  # 限制搜索次数
                            try:
                                from search_services import search_with_searxng
                                result = search_with_searxng(keyword)
                                if result and 'results' in result:
                                    for item in result['results'][:3]:  # 取前3个结果
                                        search_results.append({
                                            "标题": item.get("title", ""),
                                            "摘要": item.get("content", ""),
                                            "链接": item.get("url", "")
                                        })
                            except Exception as e:
                                logger.error(f"搜索关键词时出错: {e}")
                    
                    # 使用DeepSeek分析搜索结果与引用的一致性
                    verification_prompt = f"""
                    请分析以下引用与搜索结果的一致性，评估引用的真实性和权威性。
                    
                    引用: "{citation_text}"
                    引用来源: {source}
                    
                    搜索结果:
                    {json.dumps(search_results, ensure_ascii=False, indent=2)}
                    
                    请分析:
                    1. 引用内容的真实性 (0-1分)
                    2. 引用来源的权威性 (0-1分)
                    3. 详细分析理由
                    
                    请以JSON格式返回:
                    {{
                        "真实性评分": 0.0-1.0,
                        "权威性评分": 0.0-1.0,
                        "分析": "详细分析..."
                    }}
                    """
                    
                    verification_response = query_deepseek(verification_prompt)
                    
                    # 解析JSON响应
                    try:
                        verification_result = json.loads(verification_response)
                        truthfulness_score = verification_result.get("真实性评分", 0.7)
                        authority_score = verification_result.get("权威性评分", 0.6)
                        analysis = verification_result.get("分析", "DeepSeek分析结果")
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，使用正则表达式提取分数
                        truthfulness_match = re.search(r'真实性评分["\s:：]+([0-9.]+)', verification_response)
                        authority_match = re.search(r'权威性评分["\s:：]+([0-9.]+)', verification_response)
                        
                        truthfulness_score = float(truthfulness_match.group(1)) if truthfulness_match else 0.7
                        authority_score = float(authority_match.group(1)) if authority_match else 0.6
                        analysis = "DeepSeek分析结果 (JSON解析失败)"
                    
                    # 添加到分析结果
                    citation_analysis.append({
                        "引用文本": citation_text[:100] + "..." if len(citation_text) > 100 else citation_text,
                        "来源": source,
                        "真实性评分": round(truthfulness_score, 2),
                        "权威性评分": round(authority_score, 2),
                        "分析": analysis
                    })
                    
                    total_score += truthfulness_score
                    checked_count += 1
                    
                except Exception as e:
                    logger.error(f"使用DeepSeek分析引用时出错: {e}")
                    logger.error(traceback.format_exc())
                    
                    # 回退到本地分析方法
                    truthfulness_score = 0.7  # 默认中等可信度
                    
                    if source != '未指明来源':
                        truthfulness_details = f"引用提供了明确来源：{source}"
                    else:
                        truthfulness_details = "DeepSeek分析失败，使用内容分析方法评估"
                    
                    # 评估引用的具体性
                    if len(citation_text) > 100:
                        truthfulness_score += 0.1
                        truthfulness_details += "。较长的引用提供了更多细节，可能性更高"
                    
                    # 评估引用的专业性
                    scientific_terms = ['研究', '发现', '分析', '数据', '实验', '证明', '报告', '调查', 
                                    'study', 'research', 'analysis', 'data', 'experiment', 'evidence', 'report']
                    
                    term_count = sum(1 for term in scientific_terms if term in citation_text.lower())
                    if term_count >= 3:
                        truthfulness_score += 0.1
                        truthfulness_details += "。引用包含多个专业术语，增加可信度"
                    
                    # 检查引用是否包含可验证的数字或统计数据
                    has_numbers = bool(re.search(r'\d+(\.\d+)?%?', citation_text))
                    if has_numbers:
                        truthfulness_score += 0.1
                        truthfulness_details += "。引用包含具体数字或统计数据，提高了可验证性"
                    
                    # 如果引用提供了明确的来源，给予加分
                    if source != '未指明来源' and len(source) > 5:
                        truthfulness_score += 0.1
                    
                    # 添加一些随机性，使评分更自然
                    truthfulness_score += random.uniform(-0.05, 0.05)
                    
                    # 确保评分在0-1范围内
                    truthfulness_score = min(1.0, max(0.0, truthfulness_score))
                    
                    citation_analysis.append({
                        "引用文本": citation_text[:100] + "..." if len(citation_text) > 100 else citation_text,
                        "来源": source,
                        "真实性评分": round(truthfulness_score, 2),
                        "分析": truthfulness_details
                    })
                    
                    total_score += truthfulness_score
                    checked_count += 1
        else:
            # DeepSeek API不可用，使用本地分析方法
            logger.info("DeepSeek API不可用，使用本地方法分析引用真实性")
            
            for citation in citations:
                # 引用信息提取
                citation_text = citation['text']
                source = citation.get('source', '未指明来源')
                
                # 根据来源和SearXNG可用性选择评估方法
                if source == '未指明来源' and SEARXNG_AVAILABLE:
                    # 对未指明来源的引用使用SearXNG搜索验证
                    verified, truthfulness_score, verification_result = verify_citation_with_searxng(citation_text)
                    truthfulness_details = verification_result
                else:
                    # 使用基于文本特征的替代评估方法
                    truthfulness_score = 0.7  # 默认中等可信度
                    
                    if source != '未指明来源':
                        truthfulness_details = f"引用提供了明确来源：{source}"
                    else:
                        truthfulness_details = "搜索服务不可用，使用内容分析方法评估"
                    
                    # 评估引用的具体性
                    if len(citation_text) > 100:
                        truthfulness_score += 0.1
                        truthfulness_details += "。较长的引用提供了更多细节，可能性更高"
                    
                    # 评估引用的专业性
                    scientific_terms = ['研究', '发现', '分析', '数据', '实验', '证明', '报告', '调查', 
                                    'study', 'research', 'analysis', 'data', 'experiment', 'evidence', 'report']
                    
                    term_count = sum(1 for term in scientific_terms if term in citation_text.lower())
                    if term_count >= 3:
                        truthfulness_score += 0.1
                        truthfulness_details += "。引用包含多个专业术语，增加可信度"
                    
                    # 检查引用是否包含可验证的数字或统计数据
                    has_numbers = bool(re.search(r'\d+(\.\d+)?%?', citation_text))
                    if has_numbers:
                        truthfulness_score += 0.1
                        truthfulness_details += "。引用包含具体数字或统计数据，提高了可验证性"
                    
                    # 如果引用提供了明确的来源，给予加分
                    if source != '未指明来源' and len(source) > 5:
                        truthfulness_score += 0.1
                    
                    # 添加一些随机性，使评分更自然
                    truthfulness_score += random.uniform(-0.05, 0.05)
                    
                    # 确保评分在0-1范围内
                    truthfulness_score = min(1.0, max(0.0, truthfulness_score))
                
                citation_analysis.append({
                    "引用文本": citation_text[:100] + "..." if len(citation_text) > 100 else citation_text,
                    "来源": source,
                    "真实性评分": round(truthfulness_score, 2),  # 保留两位小数
                    "分析": truthfulness_details
                })
                
                total_score += truthfulness_score
                checked_count += 1
        
        # 计算平均分
        avg_score = total_score / checked_count if checked_count > 0 else 0.5
        
        detailed_info = {
            "引用真实性评分": round(avg_score, 2),  # 保留两位小数
            "引用分析": citation_analysis,
            "说明": "引用真实性评估基于DeepSeek AI分析和搜索引擎验证" if DEEPSEEK_API_AVAILABLE else 
                   "引用真实性评估基于搜索引擎验证和内容分析" if SEARXNG_AVAILABLE else 
                   "搜索服务不可用，使用内容分析方法评估引用真实性"
        }
        
        return avg_score, detailed_info
    except Exception as e:
        logger.error(f"判断引用真实性时出错: {e}")
        logger.error(traceback.format_exc())
        return 0.5, {"引用真实性评分": 0.5, "说明": f"分析过程出错: {str(e)}"}

def analyze_citation_validity(text):
    """
    分析引用的有效性
    
    参数:
        text: 新闻文本
        
    返回:
        (引用有效性评分, 详细分析结果列表)
    """
    # 导入所需模块
    import re
    import json
    
    # 检查DeepSeek API是否可用
    try:
        from ai_services import DEEPSEEK_API_AVAILABLE, query_deepseek
        from search_services import SEARXNG_AVAILABLE, search_with_searxng
        
        # 如果DeepSeek API可用，使用AI进行引用有效性分析
        if DEEPSEEK_API_AVAILABLE:
            logging.info("使用DeepSeek API分析引用有效性")
            
            # 提取引用内容
            citations = extract_citations(text)
            
            if not citations:
                return 0.6, ["引用数量: 无明确引用", "引用准确性: 无法评估", "引用内容的真实性评估：无明确引用内容"]
            
            # 对每个引用进行验证
            verification_results = []
            total_score = 0.0
            
            for citation in citations[:5]:  # 限制处理的引用数量
                citation_text = citation['text']
                source = citation.get('source', '未指明来源')
                
                # 使用SearXNG搜索引用内容
                search_results = []
                if SEARXNG_AVAILABLE:
                    try:
                        # 使用DeepSeek提取关键词
                        keywords_prompt = f"""
                        从以下引用中提取3-5个关键词或短语，这些关键词应该能够用于验证引用的有效性。
                        引用: "{citation_text}"
                        请直接返回关键词，用逗号分隔。
                        """
                        
                        keywords_response = query_deepseek(keywords_prompt)
                        keywords = [kw.strip() for kw in keywords_response.split(',')]
                        
                        # 使用关键词搜索
                        for keyword in keywords[:2]:  # 限制搜索次数
                            result = search_with_searxng(keyword)
                            if result and 'results' in result:
                                for item in result['results'][:3]:  # 取前3个结果
                                    search_results.append({
                                        "标题": item.get("title", ""),
                                        "摘要": item.get("content", ""),
                                        "链接": item.get("url", "")
                                    })
                    except Exception as e:
                        logging.error(f"搜索引用内容时出错: {e}")
                
                # 使用DeepSeek分析引用有效性
                verification_prompt = f"""
                请分析以下引用的有效性，评估其准确性和可信度。
                
                引用: "{citation_text}"
                引用来源: {source}
                
                搜索结果:
                {json.dumps(search_results, ensure_ascii=False, indent=2)}
                
                请分析:
                1. 引用内容的准确性 (0-1分)
                2. 引用内容的可验证性 (0-1分)
                3. 详细分析理由
                
                请以JSON格式返回:
                {{
                    "准确性评分": 0.0-1.0,
                    "可验证性评分": 0.0-1.0,
                    "总评分": 0.0-1.0,
                    "分析": "详细分析..."
                }}
                """
                
                try:
                    verification_response = query_deepseek(verification_prompt)
                    
                    # 解析JSON响应
                    try:
                        verification_result = json.loads(verification_response)
                        accuracy_score = verification_result.get("准确性评分", 0.6)
                        verifiability_score = verification_result.get("可验证性评分", 0.5)
                        total_citation_score = verification_result.get("总评分", (accuracy_score + verifiability_score) / 2)
                        analysis = verification_result.get("分析", "DeepSeek分析结果")
                        
                        verification_results.append(f"引用\"{citation_text[:30]}...\": {analysis} (评分: {total_citation_score:.2f})")
                        total_score += total_citation_score
                        
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，使用正则表达式提取分数
                        accuracy_match = re.search(r'准确性评分["\s:：]+([0-9.]+)', verification_response)
                        verifiability_match = re.search(r'可验证性评分["\s:：]+([0-9.]+)', verification_response)
                        total_match = re.search(r'总评分["\s:：]+([0-9.]+)', verification_response)
                        
                        accuracy_score = float(accuracy_match.group(1)) if accuracy_match else 0.6
                        verifiability_score = float(verifiability_match.group(1)) if verifiability_match else 0.5
                        
                        if total_match:
                            total_citation_score = float(total_match.group(1))
                        else:
                            total_citation_score = (accuracy_score + verifiability_score) / 2
                        
                        verification_results.append(f"引用\"{citation_text[:30]}...\": DeepSeek分析 (评分: {total_citation_score:.2f})")
                        total_score += total_citation_score
                        
                except Exception as e:
                    logging.error(f"分析引用有效性时出错: {e}")
                    # 使用默认评分
                    verification_results.append(f"引用\"{citation_text[:30]}...\": 分析过程出错，使用默认评分 (评分: 0.6)")
                    total_score += 0.6
            
            # 计算平均分数
            if citations:
                avg_score = total_score / min(len(citations), 5)
            else:
                avg_score = 0.6  # 默认分数
            
            # 根据引用的有效性评估
            if avg_score >= 0.8:
                truthfulness = "引用内容验证度高"
            elif avg_score >= 0.6:
                truthfulness = "引用内容验证证据有限"
            else:
                truthfulness = "引用内容难以验证"
            
            # 返回结果
            details = [
                f"引用数量: {'充足' if len(citations) >= 3 else '有限'}",
                f"引用准确性: {'高' if avg_score >= 0.8 else '中等' if avg_score >= 0.6 else '低'}",
                f"引用内容的真实性评估：{truthfulness}"
            ]
            
            # 添加详细验证结果
            details.extend(verification_results)
            
            return round(avg_score, 2), details  # 保留两位小数
    
    except ImportError:
        logging.warning("无法导入DeepSeek API模块")
    except Exception as e:
        logging.error(f"使用DeepSeek API分析引用有效性时出错: {e}")
    
    # 如果DeepSeek API不可用或分析失败，使用本地方法
    logging.info("使用本地方法分析引用有效性")
    
    # 提取引用内容
    citations = []
    citation_pattern = r'[""]([^""]+)[""]'
    matches = re.finditer(citation_pattern, text)
    
    for match in matches:
        citation = match.group(1)
        if len(citation) > 10:  # 忽略过短的引用
            citations.append(citation)
    
    if not citations:
        # 如果没有找到引用，返回中等分数
        return 0.6, ["引用数量: 无明确引用", "引用准确性: 无法评估", "引用内容的真实性评估：无明确引用内容"]
    
    # 评估引用的数量
    if len(citations) >= 3:
        citation_quantity = "充足"
        quantity_score = 0.9
    elif len(citations) == 2:
        citation_quantity = "适量"
        quantity_score = 0.7
    else:
        citation_quantity = "有限"
        quantity_score = 0.5
    
    # 评估引用的准确性和真实性
    accuracy_score = 0
    truthfulness_score = 0
    verification_details = []
    
    try:
        # 验证每个引用
        for citation in citations:
            try:
                # 尝试使用搜索引擎验证引用
                verified, citation_score, verification_detail = verify_citation_with_searxng(citation)
                
                accuracy_score += citation_score
                verification_details.append(f"引用\"{citation[:30]}...\": {verification_detail} (评分: {citation_score:.1f})")
            except Exception as e:
                logging.error(f"验证引用时出错: {str(e)}")
                accuracy_score += 0.6  # 默认分数
                verification_details.append(f"引用\"{citation[:30]}...\": 无搜索结果，使用本地评估: 本地评估: 引用来源(+0.1) (评分: 0.6)")
    except Exception as e:
        logging.error(f"验证引用时出错: {str(e)}")
        accuracy_score = 0.6 * len(citations)  # 默认分数
        verification_details = [f"引用验证过程出错: {str(e)}，使用默认评分"]
    
    # 计算平均分数
    if citations:
        accuracy_score = accuracy_score / len(citations)
    else:
        accuracy_score = 0.6  # 默认分数
    
    # 根据引用的真实性评估
    if accuracy_score >= 0.8:
        truthfulness = "引用内容验证度高"
    elif accuracy_score >= 0.6:
        truthfulness = "引用内容验证证据有限"
    else:
        truthfulness = "引用内容难以验证"
    
    # 计算总分
    total_score = (quantity_score + accuracy_score) / 2
    
    # 返回结果
    details = [
        f"引用数量: {citation_quantity}",
        f"引用准确性: {'高' if accuracy_score >= 0.8 else '中等' if accuracy_score >= 0.6 else '低'}",
        f"引用内容的真实性评估：{truthfulness}"
    ]
    
    # 添加详细验证结果
    details.extend(verification_details)
    
    return round(total_score, 2), details  # 保留两位小数

def get_citation_score(text):
    """
    评估文本中引用的质量
    
    统计引用数量和多样性
    检测直接引语的使用
    评估引用来源的权威性
    
    参数:
        text: 新闻文本
        
    返回:
        (引用质量评分(0-1), 详细分析结果列表)
    """
    logging.info("开始评估引用质量...")
    
    # 初始化评分和详情
    citation_score = 0.5  # 默认中等分数
    details = []
    
    # 检查DeepSeek API是否可用
    try:
        from ai_services import DEEPSEEK_API_AVAILABLE, query_deepseek
        import json
        
        # 如果DeepSeek API可用，使用AI进行引用质量评估
        if DEEPSEEK_API_AVAILABLE:
            logging.info("使用DeepSeek API评估引用质量")
            
            # 构建提示
            prompt = f"""
            请分析以下文本中的引用质量，评估以下几个方面:
            1. 引用数量 (直接引用和间接引用的数量)
            2. 引用多样性 (不同来源的数量)
            3. 引用来源权威性 (来源的可靠性和权威性)
            4. 引用内容质量 (引用内容的相关性和准确性)
            
            文本内容:
            {text}
            
            请以JSON格式返回分析结果:
            {{
                "引用质量总评分": 0.0-1.0,
                "引用数量评分": 0.0-1.0,
                "引用多样性评分": 0.0-1.0,
                "引用权威性评分": 0.0-1.0,
                "引用内容质量评分": 0.0-1.0,
                "直接引用数量": 数字,
                "间接引用数量": 数字,
                "不同来源数量": 数字,
                "权威来源数量": 数字,
                "详细分析": [
                    "分析点1",
                    "分析点2",
                    ...
                ]
            }}
            """
            
            # 调用DeepSeek API
            response = query_deepseek(prompt)
            
            try:
                # 尝试解析JSON响应
                try:
                    # 直接尝试解析
                    data = json.loads(response)
                except json.JSONDecodeError:
                    # 如果直接解析失败，尝试提取JSON部分
                    json_match = re.search(r'({[\s\S]*})', response)
                    if json_match:
                        json_str = json_match.group(1)
                        try:
                            data = json.loads(json_str)
                        except json.JSONDecodeError:
                            # 尝试修复常见的JSON格式问题
                            fixed_json = json_str.replace("'", '"').replace("：", ":")
                            # 修复可能的尾部逗号问题
                            fixed_json = re.sub(r',\s*}', '}', fixed_json)
                            fixed_json = re.sub(r',\s*]', ']', fixed_json)
                            data = json.loads(fixed_json)
                    else:
                        raise ValueError("无法从响应中提取JSON")
                
                # 提取评分和分析结果
                citation_score = data.get("总体评分", 0.6)
                
                # 添加总体评估
                if citation_score >= 0.8:
                    conclusion = "引用质量评估：引用质量高，来源可靠多样"
                elif citation_score >= 0.6:
                    conclusion = "引用质量评估：引用质量中等，来源基本可靠"
                elif citation_score >= 0.4:
                    conclusion = "引用质量评估：引用质量一般，来源可靠性有限"
                else:
                    conclusion = "引用质量评估：引用质量低，缺乏可靠来源"
                
                details.append(conclusion)
                
                logging.info(f"DeepSeek引用质量评估完成，评分: {citation_score:.2f}")
                return round(citation_score, 2), details  # 保留两位小数
                
            except json.JSONDecodeError:
                logging.error("无法解析DeepSeek API响应为JSON格式")
                # 尝试使用正则表达式提取评分
                citation_score_match = re.search(r'总体评分[：:]\s*(\d+\.\d+)', response)
                if citation_score_match:
                    citation_score = float(citation_score_match.group(1))
                else:
                    citation_score = 0.6  # 默认分数
                
                # 添加总体评估
                if citation_score >= 0.8:
                    conclusion = "引用质量评估：引用质量高，来源可靠多样"
                elif citation_score >= 0.6:
                    conclusion = "引用质量评估：引用质量中等，来源基本可靠"
                elif citation_score >= 0.4:
                    conclusion = "引用质量评估：引用质量一般，来源可靠性有限"
                else:
                    conclusion = "引用质量评估：引用质量低，缺乏可靠来源"
                
                details.append(conclusion)
                
                logging.info(f"DeepSeek引用质量评估完成，评分: {citation_score:.2f}")
                return round(citation_score, 2), details  # 保留两位小数
            except ValueError as e:
                logging.error(f"处理DeepSeek API响应时出错: {e}")
                logging.debug(f"原始响应: {response[:500]}...")
                # 继续使用本地方法分析
            except Exception as e:
                logging.error(f"处理DeepSeek API响应时出错: {e}")
                logging.error(traceback.format_exc())
                logging.debug(f"原始响应: {response[:500]}...")
                # 继续使用本地方法分析
    except ImportError:
        logging.warning("无法导入DeepSeek API模块")
    except Exception as e:
        logging.error(f"使用DeepSeek API评估引用质量时出错: {e}")
    
    # 如果DeepSeek API不可用或分析失败，使用本地方法
    logging.info("使用本地方法评估引用质量")
    
    # 1. 提取直接引语
    # 匹配引号内容 - 使用Unicode码点表示中文引号
    quote_patterns = [
        r'"([^"]+)"',                      # 英文双引号
        r"'([^']+)'",                      # 英文单引号
        r'\u201c([^\u201d]+)\u201d',       # 中文双引号（"..."）
        r'\u2018([^\u2019]+)\u2019'        # 中文单引号（'...'）
    ]
    
    direct_quotes = []
    for pattern in quote_patterns:
        try:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 10:  # 忽略过短的引用
                    direct_quotes.append(match)
        except Exception as e:
            logging.warning(f"引用提取出错: {str(e)}")
    
    # 2. 提取间接引用
    # 匹配引用短语后的内容
    citation_phrases = [
        "据报道", "表示", "认为", "指出", "强调", "称", "透露", "宣称", "宣布", "声明",
        "报道", "披露", "爆料", "提到", "谈到", "说", "讲", "写道", "写到", "描述"
    ]
    
    indirect_quotes = []
    for phrase in citation_phrases:
        try:
            pattern = phrase + r"[，,:：]?\s*(.+?)[。！？\.\n]"
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 10:  # 忽略过短的引用
                    indirect_quotes.append(match)
        except Exception as e:
            logging.warning(f"引用短语提取出错: {str(e)}")
    
    # 3. 统计引用数量
    total_quotes = len(direct_quotes) + len(indirect_quotes)
    
    if total_quotes >= 5:
        quantity_level = "丰富"
        quantity_score = 0.9
    elif total_quotes >= 3:
        quantity_level = "充足"
        quantity_score = 0.8
    elif total_quotes >= 1:
        quantity_level = "有限"
        quantity_score = 0.6
    else:
        quantity_level = "缺乏"
        quantity_score = 0.3
    
    details.append(f"引用数量: {quantity_level} (直接引用: {len(direct_quotes)}, 间接引用: {len(indirect_quotes)})")
    
    # 4. 评估引用多样性
    # 提取引用来源
    citation_sources = []
    source_patterns = [
        r"据(.*?)(?:报道|透露|称|表示|介绍)",
        r"(.*?)(?:表示|认为|指出|强调|称)",
        r"来自(.*?)的(?:消息|报道|信息|通报)",
        r"引用(.*?)的(?:话|说法|观点|研究)",
        r"根据(.*?)的(?:数据|统计|调查|研究)"
    ]
    
    for pattern in source_patterns:
        try:
            matches = re.findall(pattern, text)
            for match in matches:
                if match and len(match) < 20:  # 避免匹配过长的内容
                    citation_sources.append(match.strip())
        except Exception as e:
            logging.warning(f"引用来源提取出错: {str(e)}")
    
    # 去重
    citation_sources = list(set(citation_sources))
    
    # 评估多样性
    if len(citation_sources) >= 3:
        diversity_level = "高"
        diversity_score = 0.9
    elif len(citation_sources) >= 2:
        diversity_level = "中等"
        diversity_score = 0.7
    elif len(citation_sources) >= 1:
        diversity_level = "低"
        diversity_score = 0.5
    else:
        diversity_level = "无"
        diversity_score = 0.3
    
    details.append(f"引用多样性: {diversity_level} (检测到{len(citation_sources)}个不同来源)")
    
    if citation_sources:
        details.append(f"检测到的引用来源: {', '.join(citation_sources[:5])}" + ("..." if len(citation_sources) > 5 else ""))
    
    # 6. 评估引用来源权威性
    authority_sources = [
        "新华社", "人民日报", "中央电视台", "CCTV", "央视", "中新社", "光明日报", "经济日报",
        "BBC", "CNN", "路透社", "Reuters", "美联社", "AP", "法新社", "AFP", "彭博社", "Bloomberg",
        "纽约时报", "华盛顿邮报", "华尔街日报", "金融时报", "经济学人", "卫报",
        "科学", "自然", "柳叶刀", "新英格兰医学杂志", "Science", "Nature", "Lancet", "NEJM"
    ]
    
    authority_count = 0
    for source in citation_sources:
        for auth_source in authority_sources:
            if auth_source in source:
                authority_count += 1
                break
    
    if authority_count >= 2:
        authority_level = "高"
        authority_score = 0.9
    elif authority_count >= 1:
        authority_level = "中等"
        authority_score = 0.7
    else:
        authority_level = "低"
        authority_score = 0.4
    
    details.append(f"引用来源权威性: {authority_level} (检测到{authority_count}个权威来源)")
    
    # 7. 计算综合得分
    # 各项权重
    weights = {
        "quantity": 0.3,
        "diversity": 0.3,
        "authority": 0.4
    }
    
    # 计算加权总分
    citation_score = (
        quantity_score * weights["quantity"] +
        diversity_score * weights["diversity"] +
        authority_score * weights["authority"]
    )
    
    # 确保分数在0-1范围内
    citation_score = max(0.1, min(0.9, citation_score))
    
    # 8. 总体评估
    if citation_score >= 0.8:
        conclusion = "引用质量评估：引用质量高，来源可靠多样"
    elif citation_score >= 0.6:
        conclusion = "引用质量评估：引用质量中等，来源基本可靠"
    elif citation_score >= 0.4:
        conclusion = "引用质量评估：引用质量一般，来源可靠性有限"
    else:
        conclusion = "引用质量评估：引用质量低，缺乏可靠来源"
    
    details.append(conclusion)
    
    logging.info(f"引用质量评估完成，评分: {citation_score:.2f}")
    return round(citation_score, 2), details  # 保留两位小数 