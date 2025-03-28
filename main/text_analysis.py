#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文本分析模块
负责对新闻文本进行各种分析（其实是毫无意义的claude3.7生成的凑数用的本地算法）
"""

import logging
import re
import traceback
from typing import Tuple, Dict, Any, List, Optional
from utils import find_common_substrings

# 初始化logger
logger = logging.getLogger(__name__)

def check_ai_content(text: str) -> Tuple[float, List[str]]:
    """
    检测文本是否由AI生成
    
    使用多种方法检测AI生成内容的特征:
    1. 句式结构分析
    2. 重复模式检测
    3. 常见AI表达方式识别
    4. 词汇多样性评估
    
    参数:
        text (str): 要分析的文本
        
    返回:
        Tuple[float, List[str]]: (人类撰写可能性评分(0-1), 详细分析结果列表)
    """
    logger.info("本地AI内容检测功能已禁用")
    return 0.5, ["本地分析功能已禁用"]

    '''
    logger.info("开始进行AI内容检测...")
    
    # 初始化评分和详情
    ai_indicators = []
    human_indicators = []
    
    # 1. 句式结构分析
    # 检测过于规整的句式结构
    sentences = re.split(r'[。！？.!?]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    
    if not sentences:
        return 0.5, ["无法提取有效句子进行分析，使用默认评分"]
    
    # 计算句子长度的标准差 - AI生成文本句子长度往往更均匀
    sentence_lengths = [len(s) for s in sentences]
    avg_length = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((length - avg_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
    std_dev = variance ** 0.5
    
    # 句子长度变化评估
    if std_dev < 10 and len(sentences) > 5:
        ai_indicators.append("句子长度变化小，结构过于规整")
    else:
        human_indicators.append("句子长度变化自然")
    
    # 2. 重复模式检测
    # 检查重复的短语和表达
    phrases = []
    for i in range(len(sentences) - 1):
        for j in range(i + 1, len(sentences)):
            common_substrings = find_common_substrings(sentences[i], sentences[j], min_length=5)
            phrases.extend(common_substrings)
    
    # 统计重复短语
    phrase_counts = {}
    for phrase in phrases:
        if phrase in phrase_counts:
            phrase_counts[phrase] += 1
        else:
            phrase_counts[phrase] = 1
    
    # 过滤掉常见短语
    common_phrases = ["因此", "所以", "然而", "但是", "此外", "另外", "总之", "总的来说", "最后"]
    filtered_phrases = {k: v for k, v in phrase_counts.items() if k not in common_phrases and v > 2}
    
    if filtered_phrases:
        ai_indicators.append(f"检测到重复表达模式: {len(filtered_phrases)}个短语重复出现")
    else:
        human_indicators.append("未检测到明显重复表达模式")
    
    # 3. 常见AI表达方式识别
    ai_patterns = [
        r"首先.*其次.*最后",
        r"一方面.*另一方面",
        r"不仅.*而且",
        r"总的来说",
        r"总而言之",
        r"综上所述"
    ]
    
    ai_pattern_matches = 0
    for pattern in ai_patterns:
        if re.search(pattern, text, re.DOTALL):
            ai_pattern_matches += 1
    
    if ai_pattern_matches >= 3:
        ai_indicators.append("检测到多个AI常用表达模式")
    elif ai_pattern_matches > 0:
        ai_indicators.append(f"检测到{ai_pattern_matches}个AI常用表达模式")
    else:
        human_indicators.append("未检测到明显的AI表达模式")
    
    # 4. 词汇多样性评估
    words = re.findall(r'\w+', text.lower())
    unique_words = set(words)
    
    if len(words) > 0:
        diversity_ratio = len(unique_words) / len(words)
        
        if diversity_ratio < 0.4:
            ai_indicators.append("词汇多样性较低")
        elif diversity_ratio > 0.6:
            human_indicators.append("词汇多样性较高")
    
    # 5. 计算最终评分
    # 根据人类和AI指标的数量计算评分
    total_indicators = len(ai_indicators) + len(human_indicators)
    if total_indicators == 0:
        score = 0.5  # 默认中等分数
    else:
        score = len(human_indicators) / total_indicators
    
    # 调整评分范围，避免极端值
    score = 0.2 + score * 0.6
    
    # 准备详细结果
    if score >= 0.7:
        conclusion = "人类撰写概率较高"
    elif score >= 0.5:
        conclusion = "可能为人类撰写，但有AI辅助痕迹"
    elif score >= 0.3:
        conclusion = "可能为AI生成，有人工编辑痕迹"
    else:
        conclusion = "AI生成概率较高"
    
    details = [f"AI内容检测结果：{conclusion} (评分: {score:.2f})"]
    
    # 添加详细指标
    if ai_indicators:
        details.append("AI特征:")
        for indicator in ai_indicators:
            details.append(f"- {indicator}")
    
    if human_indicators:
        details.append("人类撰写特征:")
        for indicator in human_indicators:
            details.append(f"- {indicator}")
    
    logger.info(f"AI内容检测完成，评分: {score:.2f}")
    return score, details
    '''

def analyze_language_neutrality(text: str) -> Tuple[float, List[str]]:
    """
    分析文本的语言中立性
    
    使用预定义词汇列表检测情感词和偏见表达
    计算正面/负面/中性词汇比例
    识别夸张、煽动性语言和主观表达
    
    参数:
        text: 新闻文本
        
    返回:
        Tuple[float, List[str]]: (中立性评分(0-1), 详细分析结果列表)
    """
    logger.info("本地语言中立性分析功能已禁用")
    return 0.5, ["本地分析功能已禁用"]

    '''
    logger.info("开始分析语言中立性...")
    
    # 1. 情感词汇检测
    # 正面情感词汇
    positive_words = [
        "优秀", "杰出", "卓越", "伟大", "成功", "突破", "胜利", "进步", "发展", "提升",
        "创新", "优化", "改善", "增强", "促进", "鼓励", "支持", "赞赏", "肯定", "表扬",
        "excellent", "outstanding", "great", "successful", "breakthrough", "victory", "progress"
    ]
    
    # 负面情感词汇
    negative_words = [
        "失败", "糟糕", "恶劣", "危机", "灾难", "崩溃", "衰退", "下滑", "恶化", "破坏",
        "威胁", "打击", "损害", "削弱", "阻碍", "批评", "指责", "谴责", "否定", "质疑",
        "failure", "terrible", "crisis", "disaster", "collapse", "recession", "deteriorate"
    ]
    
    # 极端情感词汇
    extreme_words = [
        "震惊", "愤怒", "恐怖", "可怕", "悲剧", "惊人", "极端", "疯狂", "荒谬", "惊骇",
        "惨不忍睹", "令人发指", "骇人听闻", "触目惊心", "不可思议", "难以置信", "史无前例",
        "shocking", "outrageous", "horrific", "terrifying", "tragic", "extreme", "crazy"
    ]
    
    # 煽动性词汇
    inflammatory_words = [
        "必须", "绝对", "一定", "永远", "从不", "全部", "所有", "没有一个", "完全", "彻底",
        "毫无疑问", "毫无例外", "无可争辩", "无可辩驳", "无可置疑", "无可非议", "无可厚非",
        "must", "absolute", "definitely", "always", "never", "all", "none", "completely"
    ]
    
    # 主观表达
    subjective_phrases = [
        "我认为", "我相信", "我觉得", "我想", "我希望", "我担心", "我怀疑", "我期待",
        "据我所知", "依我看", "在我看来", "以我之见", "我个人认为", "我的看法是",
        "I think", "I believe", "I feel", "I hope", "I worry", "I doubt", "I expect"
    ]
    
    # 统计各类词汇出现次数
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    extreme_count = sum(1 for word in extreme_words if word in text)
    inflammatory_count = sum(1 for word in inflammatory_words if word in text)
    subjective_count = sum(1 for phrase in subjective_phrases if phrase in text)
    
    # 计算总情感词数量
    total_emotional_words = positive_count + negative_count + extreme_count
    
    # 计算情感词比例
    text_length = len(text)
    emotional_ratio = total_emotional_words / (text_length / 100)  # 每100字的情感词数量
    
    # 计算正负面情感平衡度
    if positive_count + negative_count > 0:
        sentiment_balance = abs(positive_count - negative_count) / (positive_count + negative_count)
    else:
        sentiment_balance = 0
    
    # 2. 计算各项得分
    # 情感词密度得分 (越低越中立)
    emotional_density_score = max(0, 1 - (emotional_ratio / 5))  # 假设每100字5个情感词为阈值
    
    # 情感平衡得分 (越平衡越中立)
    balance_score = 1 - sentiment_balance
    
    # 极端词汇得分 (越少越中立)
    extreme_score = max(0, 1 - (extreme_count / 5))  # 假设5个极端词为阈值
    
    # 煽动性词汇得分 (越少越中立)
    inflammatory_score = max(0, 1 - (inflammatory_count / 5))  # 假设5个煽动词为阈值
    
    # 主观表达得分 (越少越中立)
    subjective_score = max(0, 1 - (subjective_count / 3))
    
    # 3. 计算综合得分
    # 各项权重
    weights = {
        "emotional_density": 0.25,
        "balance": 0.15,
        "extreme": 0.25,
        "inflammatory": 0.2,
        "subjective": 0.15
    }
    
    # 计算加权总分
    neutrality_score = (
        emotional_density_score * weights["emotional_density"] +
        balance_score * weights["balance"] +
        extreme_score * weights["extreme"] +
        inflammatory_score * weights["inflammatory"] +
        subjective_score * weights["subjective"]
    )
    
    # 确保分数在0-1范围内
    neutrality_score = max(0, min(1, neutrality_score))
    
    # 4. 准备详细结果
    # 评估情感词水平
    if emotional_ratio < 1:
        emotional_level = "较少"
    elif emotional_ratio < 3:
        emotional_level = "适量"
    else:
        emotional_level = "较多"
    
    # 评估情感平衡度
    if sentiment_balance < 0.3:
        balance_level = "平衡"
    elif sentiment_balance < 0.7:
        balance_level = "偏向"
    else:
        balance_level = "强烈偏向"
    
    # 评估极端表述
    if extreme_count == 0:
        extreme_level = "无"
    elif extreme_count < 3:
        extreme_level = "少量"
    else:
        extreme_level = "较多"
    
    # 评估煽动性表述
    if inflammatory_count == 0:
        inflammatory_level = "无"
    elif inflammatory_count < 3:
        inflammatory_level = "少量"
    else:
        inflammatory_level = "较多"
    
    # 评估主观表达
    if subjective_count == 0:
        subjective_level = "无"
    elif subjective_count < 2:
        subjective_level = "少量"
    else:
        subjective_level = "较多"
    
    # 总体评估结论
    if neutrality_score >= 0.8:
        conclusion = "语言中立性分析：表述相对客观"
    elif neutrality_score >= 0.6:
        conclusion = "语言中立性分析：表述基本客观，存在一定情绪化内容"
    elif neutrality_score >= 0.4:
        conclusion = "语言中立性分析：表述情绪化明显，中立性一般"
    else:
        conclusion = "语言中立性分析：表述情绪化严重，缺乏客观性"
    
    # 准备详细结果
    details = [
        f"情感词汇: {emotional_level} (正面: {positive_count}, 负面: {negative_count})",
        f"情感平衡: {balance_level}",
        f"极端表述: {extreme_level} (数量: {extreme_count})",
        f"煽动性表述: {inflammatory_level} (数量: {inflammatory_count})",
        f"主观表达: {subjective_level} (数量: {subjective_count})",
        conclusion
    ]
    
    logger.info(f"语言中立性分析完成，评分: {neutrality_score:.2f}")
    return neutrality_score, details
    '''

def analyze_source_quality(text: str, url: Optional[str] = None) -> Tuple[float, List[str]]:
    """
    分析新闻来源的质量
    
    参数:
        text (str): 新闻文本
        url (str, optional): 新闻URL，用于评估域名可信度
        
    返回:
        tuple: (来源质量分数, 详情列表)
    """
    from web_utils import evaluate_domain_trust
    
    logger.info("开始分析来源质量")
    
    # 初始化
    score = 0.5  # 默认中等质量
    details = []
    
    # 如果提供了URL，评估域名可信度
    if url:
        domain_score, domain_details = evaluate_domain_trust(url)
        # 域名评估占40%权重
        score = 0.4 * domain_score + 0.6 * score
        details.append(domain_details)
    
    # 提取可能的来源指示词
    source_indicators = [
        "据.*?报道", "来自.*?的消息", "根据.*?的数据", "引用.*?的话",
        "参考.*?的研究", "援引.*?的说法", "来源于.*?", "出自.*?",
        "记者.*?报道", "通讯员.*?报道", "特约记者.*?", "本报记者.*?",
        "报道称", "消息称", "消息人士称", "知情人士透露",
        "according to", "reported by", "cited by", "quoted by",
        "sources said", "officials said", "experts said", "researchers found"
    ]
    
    # 提取所有可能的来源
    sources = []
    for indicator in source_indicators:
        matches = re.finditer(indicator, text)
        for match in matches:
            # 提取匹配后的内容，最多30个字符
            start = match.end()
            end = min(start + 30, len(text))
            source_text = text[start:end].strip()
            # 如果有标点符号，截断到第一个标点
            for i, char in enumerate(source_text):
                if char in "。，,.:;!?；，。！？":
                    source_text = source_text[:i]
                    break
            if source_text and len(source_text) > 1:
                sources.append(source_text)
    
    # 提取引号中的内容作为可能的引用
    quotes = []
    quote_patterns = [
        r'"([^"]+)"',                      # 英文双引号
        r"'([^']+)'",                      # 英文单引号
        r"「([^」]+)」",                    # 中文单引号
        r"『([^』]+)』",                    # 中文双引号
        r"【([^】]+)】",                    # 中文方括号
        r"《([^》]+)》"                     # 中文书名号
    ]
    
    for pattern in quote_patterns:
        for match in re.finditer(pattern, text):
            quote = match.group(1).strip()
            if len(quote) > 5:  # 只考虑长度大于5的引用
                quotes.append(quote)
    
    # 根据来源和引用数量评估质量
    if len(sources) >= 3:
        score += 0.2
        details.append(f"检测到多个信息来源指示 ({len(sources)}个)")
    elif len(sources) > 0:
        score += 0.1
        details.append(f"检测到一些信息来源指示 ({len(sources)}个)")
    else:
        score -= 0.1
        details.append("未检测到明确的信息来源指示")
    
    if len(quotes) >= 3:
        score += 0.2
        details.append(f"包含多个引用内容 ({len(quotes)}个)")
    elif len(quotes) > 0:
        score += 0.1
        details.append(f"包含一些引用内容 ({len(quotes)}个)")
    else:
        details.append("未检测到引用内容")
    
    # 检查是否包含数据和统计信息
    data_patterns = [
        r'\d+(?:\.\d+)?%',                 # 百分比
        r'\d+(?:\.\d+)?\s*(?:亿|万|千|百)',  # 中文数量单位
        r'\d+(?:\.\d+)?\s*(?:million|billion|thousand)', # 英文数量单位
        r'增长\s*\d+(?:\.\d+)?%',           # 增长率
        r'下降\s*\d+(?:\.\d+)?%',           # 下降率
        r'上升\s*\d+(?:\.\d+)?%'            # 上升率
    ]
    
    data_count = 0
    for pattern in data_patterns:
        data_count += len(re.findall(pattern, text))
    
    if data_count >= 5:
        score += 0.1
        details.append(f"包含丰富的数据和统计信息 ({data_count}处)")
    elif data_count > 0:
        score += 0.05
        details.append(f"包含一些数据和统计信息 ({data_count}处)")
    
    # 确保分数在0-1范围内
    score = max(0, min(1, score))
    
    # 总体评估
    if score >= 0.8:
        details.append("来源质量评估：高质量来源，包含多个可验证的信息来源和引用")
    elif score >= 0.6:
        details.append("来源质量评估：良好来源，包含一些可验证的信息")
    elif score >= 0.4:
        details.append("来源质量评估：一般来源，信息来源有限")
    else:
        details.append("来源质量评估：低质量来源，缺乏可验证的信息来源")
    
    logger.info(f"来源质量分析完成，评分: {score:.2f}")
    return score, details

def analyze_text_logic(text: str) -> Tuple[float, str]:
    """
    分析文本的逻辑性
    
    参数:
        text (str): 文本内容
    
    返回:
        tuple: (分数, 详细信息)
    """
    logger.info("分析文本逻辑性")
    
    # 使用基本逻辑分析
    logger.info("使用基本逻辑分析")
    return basic_logic_analysis(text)

def basic_logic_analysis(text: str) -> Tuple[float, str]:
    """
    基本的文本逻辑分析
    
    参数:
        text (str): 要分析的文本
    
    返回:
        tuple: (分数, 详细信息)
    """
    # 初始分数
    score = 0.5
    details = []
    
    # 文本长度分析
    if len(text) < 100:
        score -= 0.1
        details.append("文本过短，难以进行深入逻辑分析")
    elif len(text) > 500:
        score += 0.1
        details.append("文本较长，基本分析显示有一定的逻辑结构和论述深度")
    
    # 逻辑连接词分析
    logic_connectors = [
        "因为", "所以", "因此", "由于", "如果", "那么", "但是", "然而",
        "虽然", "尽管", "不过", "否则", "除非", "只有", "首先", "其次",
        "最后", "总之", "换言之", "例如", "比如", "特别是", "尤其是"
    ]
    
    connector_count = sum(1 for connector in logic_connectors if connector in text)
    connector_density = connector_count / (len(text) / 100)  # 每100字的连接词数量
    
    if connector_density > 2:
        score += 0.2
        details.append("文本包含充足的逻辑连接词，逻辑结构清晰")
    elif connector_density > 1:
        score += 0.1
        details.append("文本包含一定的逻辑连接词，逻辑结构基本清晰")
    else:
        score -= 0.1
        details.append("文本缺乏足够的逻辑连接词，逻辑组织可能不够清晰")
    
    # 段落结构分析
    paragraphs = text.split('\n\n')
    if len(paragraphs) > 3:
        score += 0.1
        details.append("文本分为多个段落，结构较为完整")
    
    # 矛盾词分析
    contradiction_pairs = [
        ("增加", "减少"), ("上升", "下降"), ("提高", "降低"),
        ("加强", "减弱"), ("扩大", "缩小"), ("加速", "减速"),
        ("肯定", "否定"), ("支持", "反对"), ("赞成", "反对")
    ]
    
    contradiction_count = 0
    for pair in contradiction_pairs:
        if pair[0] in text and pair[1] in text:
            contradiction_count += 1
    
    if contradiction_count > 2:
        score -= 0.2
        details.append(f"检测到可能的逻辑矛盾：文本中同时出现了{contradiction_count}对矛盾词汇")
    
    # 最终评分
    score = max(0, min(1, score))  # 确保分数在0-1之间
    
    return score, " ".join(details)

def local_news_validation(text: str) -> Tuple[float, str]:
    """
    本地新闻验证
    
    参数:
        text (str): 新闻文本
    
    返回:
        tuple: (分数, 详细信息)
    """
    # 简单的本地验证，实际应用中可以扩展
    score = 0.5
    details = "本地新闻验证：使用基本验证方法，无法确定真实性，建议结合其他方法进行综合评估"
    
    return score, details 