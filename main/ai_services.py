#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI服务模块
负责与外部AI API交互
"""

import logging
import os
import requests
import json
import re
import time
import random
import traceback
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Tuple, Optional, List, Union

# 确保加载.env文件
# 尝试在当前目录和父目录查找.env文件
print("正在加载.env文件...")
for env_path in ['.env', '../.env', '../../.env']:
    if Path(env_path).exists():
        print(f"找到并加载.env文件: {env_path}")
        load_dotenv(env_path)
        break

# 直接检查和打印环境变量状态
api_key = os.getenv('DEEPSEEK_API_KEY')
print(f"DEEPSEEK_API_KEY设置状态: {'已设置' if api_key else '未设置'}")

logger = logging.getLogger(__name__)

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_AVAILABLE = False  # 默认为False，会在初始化时检查

# 检查API密钥是否设置
if not DEEPSEEK_API_KEY:
    logger.warning("未设置DEEPSEEK_API_KEY环境变量")
    DEEPSEEK_API_AVAILABLE = False

def test_deepseek_connection():
    """
    测试DeepSeek连接

    返回:
        bool: 连接是否可用
    """
    global DEEPSEEK_API_AVAILABLE
    
    try:
        logger.info("测试DeepSeek API连接...")
        from config import DEEPSEEK_API_KEY
        
        # 使用模块中定义的API URL
        api_url = DEEPSEEK_API_URL
                
        # 确保API密钥已设置
        if not DEEPSEEK_API_KEY:
            logger.error("DeepSeek API密钥未设置")
            DEEPSEEK_API_AVAILABLE = False
            return False
            
        # 简单的测试查询
        prompt = "请简单回复'连接正常'测试连接"
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # 设置请求数据
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 50
        }
        
        # 发送请求
        response = requests.post(api_url, headers=headers, json=data, timeout=15)
        
        # 判断响应状态
        if response.status_code != 200:
            logger.error(f"DeepSeek API测试请求失败，状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")
            DEEPSEEK_API_AVAILABLE = False
            return False
            
        # 尝试解析响应
        response_data = response.json()
        if "choices" in response_data and len(response_data["choices"]) > 0:
            content = response_data["choices"][0].get("message", {}).get("content", "")
            logger.info(f"DeepSeek API测试响应: {content}")
            DEEPSEEK_API_AVAILABLE = True
            return True
        else:
            logger.error("DeepSeek API响应格式不正确")
            logger.debug(f"响应内容: {response_data}")
            DEEPSEEK_API_AVAILABLE = False
            return False
            
    except ImportError as e:
        logger.warning(f"从config导入时出错: {e}，使用环境变量")
        # 使用环境变量或默认API密钥
        api_key = os.getenv("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)
        api_url = DEEPSEEK_API_URL
        
        if not api_key:
            logger.error("DeepSeek API密钥未设置")
            DEEPSEEK_API_AVAILABLE = False
            return False
            
        # 剩余代码与上面相同，但使用环境变量
        try:
            prompt = "请简单回复'连接正常'测试连接"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 50
            }
            response = requests.post(api_url, headers=headers, json=data, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"DeepSeek API测试请求失败，状态码: {response.status_code}")
                DEEPSEEK_API_AVAILABLE = False
                return False
                
            response_data = response.json()
            if "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0].get("message", {}).get("content", "")
                logger.info(f"DeepSeek API测试响应: {content}")
                DEEPSEEK_API_AVAILABLE = True
                return True
            else:
                logger.error("DeepSeek API响应格式不正确")
                DEEPSEEK_API_AVAILABLE = False
                return False
        except Exception as inner_e:
            logger.error(f"使用环境变量测试DeepSeek API连接时出错: {inner_e}")
            DEEPSEEK_API_AVAILABLE = False
            return False
    except requests.exceptions.ConnectionError:
        logger.error("DeepSeek API连接错误")
        DEEPSEEK_API_AVAILABLE = False
        return False
    except requests.exceptions.Timeout:
        logger.error("DeepSeek API请求超时")
        DEEPSEEK_API_AVAILABLE = False
        return False
    except Exception as e:
        logger.error(f"测试DeepSeek API连接时出错: {e}")
        logger.error(traceback.format_exc())
        DEEPSEEK_API_AVAILABLE = False
        return False

def query_deepseek(prompt, max_retries=3):
    """
    向DeepSeek API发送查询请求
    
    参数:
        prompt (str): 提示词
        max_retries (int): 最大重试次数
    
    返回:
        (str): API返回的内容
    """
    if os.environ.get('DISABLE_AI', 'false').lower() == 'true':
        logger.warning("AI服务已禁用，无法使用DeepSeek API")
        return "AI服务已禁用，无法使用DeepSeek API"
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        logger.error("未设置DEEPSEEK_API_KEY环境变量")
        return "未设置DEEPSEEK_API_KEY环境变量"
    
    logger.info(f"准备向DeepSeek API发送请求")
    logger.debug(f"提示词长度: {len(prompt)} 字符")
    logger.debug(f"提示词前100字符: {prompt[:100]}...")
    
    # 使用全局变量中定义的API URL
    api_url = DEEPSEEK_API_URL
    
    # 请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 请求数据
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,  # 降低温度以获得更确定性的回答
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}  # 始终要求返回JSON格式
    }
    
    # 移除原来的条件判断代码，始终使用JSON格式
    logger.debug("始终启用 JSON 响应格式")
    
    logger.debug(f"DeepSeek API请求URL: {api_url}")
    logger.debug(f"DeepSeek API请求数据: {data}")
    
    # 基础超时时间
    base_timeout = 30  # 增加基础超时时间
    
    for attempt in range(max_retries + 1):
        try:
            current_timeout = base_timeout * (attempt + 1)  # 逐次增加超时时间
            logger.info(f"DeepSeek API请求尝试 {attempt+1}/{max_retries+1} (超时: {current_timeout}秒)")
            
            # 创建新的会话对象，避免连接池问题
            session = requests.Session()
            
            response = session.post(
                api_url,
                headers=headers,
                json=data,
                timeout=current_timeout
            )
            
            logger.debug(f"DeepSeek API响应状态码: {response.status_code}")
            logger.debug(f"DeepSeek API响应头: {response.headers}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    content = response_data['choices'][0]['message']['content']
                    logger.info("DeepSeek API请求成功")
                    logger.debug(f"响应长度: {len(content)} 字符")
                    logger.debug(f"响应前100字符: {content[:100]}...")
                    return content
                except (KeyError, IndexError) as e:
                    logger.error(f"DeepSeek API响应格式不正确: {e}")
                    logger.error(f"响应内容: {response.text[:500]}...")
                    
                    # 尝试直接返回响应文本
                    if response.text and len(response.text) > 0:
                        logger.info("尝试直接使用响应文本")
                        return response.text
                except json.JSONDecodeError as e:
                    logger.error(f"解析DeepSeek API响应JSON时出错: {e}")
                    logger.error(f"响应内容: {response.text[:500]}...")
                    
                    # 尝试直接返回响应文本
                    if response.text and len(response.text) > 0:
                        logger.info("尝试直接使用响应文本")
                        return response.text
            elif response.status_code == 429:
                logger.warning("DeepSeek API请求频率限制，等待后重试")
                # 如果不是最后一次尝试，等待更长时间后重试
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 5  # 指数退避，基础等待时间更长
                    logger.info(f"等待 {wait_time} 秒后重试DeepSeek API请求")
                    time.sleep(wait_time)
                    continue
            else:
                logger.error(f"DeepSeek API请求失败，状态码: {response.status_code}")
                logger.error(f"错误响应: {response.text[:500]}...")
        
        except requests.exceptions.Timeout:
            logger.error(f"DeepSeek API请求超时 (尝试 {attempt+1}/{max_retries+1}, 超时: {current_timeout}秒)")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"DeepSeek API连接错误: {e}")
        except Exception as e:
            logger.error(f"DeepSeek API请求出错: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
        
        # 如果不是最后一次尝试，等待一段时间后重试
        if attempt < max_retries:
            wait_time = 2 ** attempt  # 指数退避
            logger.info(f"等待 {wait_time} 秒后重试DeepSeek API请求")
            time.sleep(wait_time)
        else:
            # 最后一次尝试也失败，设置全局变量
            global DEEPSEEK_API_AVAILABLE
            DEEPSEEK_API_AVAILABLE = False
    
    logger.error("所有DeepSeek API请求尝试均失败")
    return "DeepSeek API请求失败，请检查网络连接或稍后再试"

def analyze_with_deepseek_v3(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    使用DeepSeek API分析文本可信度
    
    参数:
        text (str): 要分析的文本
    
    返回:
        Tuple[float, Dict[str, Any]]: (分数, 详细信息对象)
        
    异常:
        ValueError: 当API不可用或返回无效响应时
        RuntimeError: 当API调用失败时
    """
    # 检查API是否可用
    global DEEPSEEK_API_AVAILABLE
    if not DEEPSEEK_API_AVAILABLE:
        raise ValueError("DeepSeek API不可用，无法进行分析")
    
    # 限制文本长度，避免超出API限制
    max_text_length = 2000
    if len(text) > max_text_length:
        logging.warning(f"文本长度超过{max_text_length}字符，将被截断")
        text = text[:max_text_length] + "...(文本已截断)"
    
    # 构建提示词，要求以JSON格式返回分析结果
    prompt = f"""
你是一个专业的新闻可信度分析专家，请分析以下新闻内容的可信度，并按要求以JSON格式返回评分和分析。

请按照以下详细标准从六个主要维度进行深入分析，每个维度的评分从0到1（1表示完全符合该维度的标准）：

1. 内容真实性（评估新闻事实的真实程度）：
   - 事实核查：文本中的关键事实是否有确切来源或可被验证？是否与已知事实相符？
   - 虚构成分：是否存在夸大、编造或未经证实的内容？
   - 时间准确性：事件发生的时间描述是否准确、完整？
   - 地点准确性：地理位置和场景描述是否符合实际情况？
   - 人物真实性：涉及的人物是否真实存在，其言行是否准确描述？

2. 信息准确性（评估数据和信息的精确度）：
   - 数据准确性：数字、统计数据和百分比是否精确？来源是否可靠？
   - 细节一致性：文章内部信息是否自洽，不存在相互矛盾的说法？
   - 专业术语：专业名词和术语使用是否准确、恰当？是否存在误用或滥用？
   - 背景信息：上下文和背景信息是否完整、准确，有助于理解事件？

3. 来源可靠性（评估信息来源的质量）：
   - 信息来源：是否明确标注信息的来源？来源是否可追溯和验证？
   - 来源权威性：引用的来源是否具有相关领域的专业性和权威性？
   - 多源验证：重要信息是否有多个独立来源佐证？不同来源是否一致？
   - 引用规范：引用方式是否规范、准确，避免断章取义或曲解原意？

4. 语言客观性（评估表达是否客观公正）：
   - 情感色彩：语言是否过度情绪化？是否使用煽动性或夸张性词汇？
   - 偏见检测：是否存在明显的立场偏向、刻板印象或歧视性表达？
   - 平衡报道：是否呈现多方观点，特别是在争议话题上？
   - 修辞使用：修辞手法是否恰当，不会误导读者或强化特定立场？

5. 逻辑连贯性（评估文本的逻辑性和结构）：
   - 因果关系：因果关系是否合理建立，避免跳跃式推断？
   - 论证完整性：论证是否完整，有足够的证据支持结论？
   - 结构清晰：文本结构是否清晰有序，阐述是否连贯？
   - 推理合理：推理过程是否合理，避免逻辑谬误？

6. 引用质量（评估引用的质量和相关性）：
   - 引用多样性：是否引用多元化、不同类型的资料和观点？
   - 引用时效性：引用的资料是否具有时效性，反映最新研究或情况？
   - 引用相关性：引用内容是否与主题高度相关，有效支持论点？

此外，请对以下两个特定方面进行更深入的分析：

A. AI生成内容（评估文本是否由AI生成）：
   - 表达模式：是否存在AI特有的表达模式和句式结构？（0表示高度机械化，1表示自然人类化）
   - 词汇多样性：词汇使用是否多样且自然，避免过于规整或重复？（0表示词汇单一，1表示丰富多样）
   - 句子变化：句子长度和结构是否有自然变化？（0表示高度一致，1表示变化自然）
   - 上下文连贯性：段落间过渡是否自然，上下文是否连贯？（0表示连贯性过于完美，1表示自然流畅）
   - 人类特征：是否包含人类特有的表达方式、情感或思考角度？（0表示缺乏人类特征，1表示富有人类特质）

B. 语言中立性（评估语言的客观中立程度）：
   - 情感词汇：使用情感词汇的频率和强度如何？（0表示情感词汇过多，1表示使用恰当）
   - 情感平衡：对不同观点的情感表达是否平衡？（0表示严重不平衡，1表示完全平衡）
   - 极端表述：是否使用极端化、绝对化表述？（0表示大量使用，1表示几乎不使用）
   - 煽动性表达：是否含有煽动情绪或引导立场的表达？（0表示高度煽动，1表示完全中立）
   - 主观评价：是否混入作者个人评价和判断？（0表示大量主观评价，1表示客观陈述）

请进行全面、详细的分析，确保每个维度都有深入的考量。特别注意捕捉可能影响可信度的细微问题。

注意：你的回复必须且只能是一个标准的JSON对象，开头是{{，结尾是}}，没有其他任何文本或说明。不要在JSON前后添加任何解释或格式化字符。不要使用Markdown或代码块语法。直接以原始JSON格式响应。

必须严格按照以下JSON格式输出，确保JSON格式是有效且可解析的：
{{
  "总体评分": 0.*,
  "各大类评分": {{
    "内容真实性": 0.*,
    "信息准确性": 0.*,
    "来源可靠性": 0.*,
    "语言客观性": 0.*,
    "逻辑连贯性": 0.*,
    "引用质量": 0.*
  }},
  "细分点评分": {{
    "内容真实性_事实核查": 0.*,
    "内容真实性_虚构成分": 0.*,
    "内容真实性_时间准确性": 0.*,
    "内容真实性_地点准确性": 0.*,
    "内容真实性_人物真实性": 0.*,
    "信息准确性_数据准确性": 0.*,
    "信息准确性_细节一致性": 0.*,
    "信息准确性_专业术语": 0.*,
    "信息准确性_背景信息": 0.*,
    "来源可靠性_信息来源": 0.*,
    "来源可靠性_来源权威性": 0.*,
    "来源可靠性_多源验证": 0.*,
    "来源可靠性_引用规范": 0.*,
    "语言客观性_情感色彩": 0.*,
    "语言客观性_偏见检测": 0.*,
    "语言客观性_平衡报道": 0.*,
    "语言客观性_修辞使用": 0.*,
    "逻辑连贯性_因果关系": 0.*,
    "逻辑连贯性_论证完整性": 0.*,
    "逻辑连贯性_结构清晰": 0.*,
    "逻辑连贯性_推理合理": 0.*,
    "引用质量_引用多样性": 0.*,
    "引用质量_引用时效性": 0.*,
    "引用质量_引用相关性": 0.*
  }},
  "AI生成内容": {{
    "表达模式": 0.*,
    "词汇多样性": 0.*,
    "句子变化": 0.*,
    "上下文连贯性": 0.*,
    "人类特征": 0.*,
    "分析": "详细分析AI生成内容特征的具体表现，提供文本中的例证"
  }},
  "语言中立性": {{
    "情感词汇": 0.*,
    "情感平衡": 0.*,
    "极端表述": 0.*,
    "煽动性表达": 0.*,
    "主观评价": 0.*,
    "分析": "详细分析语言中立性问题的具体表现，提供文本中的例证"
  }},
  "详细分析": "对整体可信度的深入分析，包含各维度之间的相互影响和总体评价",
  "可信度判断的疑点": ["具体列出可能降低可信度的问题点1", "问题点2", "问题点3"]
}}

新闻文本：
{text}
"""
    
    try:
        # 调用DeepSeek API - 只调用一次，减少重复分析
        response = query_deepseek(prompt)
        if not response:
            raise ValueError("DeepSeek API返回空响应，无法进行分析")
        
        logging.debug(f"DeepSeek API响应: {response[:500]}...")
        
        # 解析API响应
        try:
            import json
            import re
            import traceback
            
            # 记录原始响应以便调试
            logging.debug(f"尝试解析的原始响应: {response[:500]}...")
            
            # 先尝试直接解析整个响应
            try:
                data = json.loads(response)
                overall_score = data.get("总体评分", 0.5)
                normalized_data = validate_and_normalize_analysis(data)
                logging.info("成功直接将响应解析为JSON")
                return overall_score, normalized_data
            except json.JSONDecodeError:
                logging.warning("整个响应不是有效的JSON，尝试提取JSON部分")
            
            # 尝试从响应中提取JSON部分
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                json_str = json_match.group(1)
                try:
                    data = json.loads(json_str)
                    
                    # 提取总体评分
                    overall_score = data.get("总体评分", 0.5)
                    
                    # 验证和标准化数据
                    normalized_data = validate_and_normalize_analysis(data)
                    logging.info("成功从响应中提取并解析JSON部分")
                    
                    return overall_score, normalized_data
                    
                except json.JSONDecodeError as e:
                    logging.error(f"JSON解析错误: {e}, 原始JSON: {json_str[:200]}...")
                    
                    # 尝试修复常见的JSON格式问题
                    try:
                        # 替换单引号为双引号
                        fixed_json = json_str.replace("'", '"')
                        # 替换中文冒号为英文冒号
                        fixed_json = fixed_json.replace("：", ":")
                        # 修复可能的尾部逗号问题
                        fixed_json = re.sub(r',\s*}', '}', fixed_json)
                        fixed_json = re.sub(r',\s*]', ']', fixed_json)
                        # 修复键值对格式问题
                        fixed_json = re.sub(r'([^"{\[,])\s*:\s*', r'"\1": ', fixed_json)
                        # 修复键名没有引号的问题
                        fixed_json = re.sub(r'{\s*([^"{\[,][^:]*)\s*:', r'{"\\1":', fixed_json)
                        fixed_json = re.sub(r',\s*([^"{\[,][^:]*)\s*:', r',"\1":', fixed_json)
                        
                        logging.debug(f"尝试修复后的JSON: {fixed_json[:200]}...")
                        
                        data = json.loads(fixed_json)
                        overall_score = data.get("总体评分", 0.5)
                        normalized_data = validate_and_normalize_analysis(data)
                        logging.info("成功修复并解析JSON")
                        return overall_score, normalized_data
                    except Exception as fix_error:
                        logging.error(f"修复JSON失败: {fix_error}")
                        
                        # 如果修复失败，尝试使用更宽松的方式解析
                        try:
                            import ast
                            # 尝试使用ast模块解析Python字典
                            dict_str = json_str.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                            data = ast.literal_eval(dict_str)
                            overall_score = data.get("总体评分", 0.5)
                            normalized_data = validate_and_normalize_analysis(data)
                            logging.info("使用AST成功解析数据")
                            return overall_score, normalized_data
                        except Exception as ast_error:
                            logging.error(f"使用ast解析失败: {ast_error}")
            
            # 如果以上所有方法都失败，尝试从纯文本响应中提取结构化数据
            logging.warning("所有JSON解析方法均失败，尝试从纯文本解析结构化数据")
            structured_data = parse_structured_text(response)
            overall_score = structured_data.get("总体评分", 0.5)
            normalized_data = validate_and_normalize_analysis(structured_data)
            logging.info("从纯文本成功提取结构化数据")
            return overall_score, normalized_data
            
        except Exception as e:
            logging.error(f"解析DeepSeek响应时出错: {e}")
            logging.error(traceback.format_exc())
            
            # 所有解析方法都失败，抛出错误
            # 不再返回默认值，而是抛出错误
            raise ValueError(f"解析DeepSeek响应失败，无法提取有效数据: {str(e)}")
    except Exception as e:
        logging.error(f"调用DeepSeek API时出错: {e}")
        logging.error(traceback.format_exc())
        # 抛出错误而不是返回默认值
        raise RuntimeError(f"调用DeepSeek API失败: {str(e)}")

def parse_structured_text(response: str) -> Dict[str, Any]:
    """
    当JSON解析失败时，尝试从结构化文本中提取信息
    
    参数:
        response: DeepSeek返回的文本
    
    返回:
        Dict: 提取的数据
    """
    logging.debug("尝试从结构化文本解析")
    result = {
        "总体评分": 0.5,
        "各大类评分": {},
        "细分点评分": {},
        "AI生成内容": {
            "表达模式": 0.5,
            "词汇多样性": 0.5,
            "句子变化": 0.5,
            "上下文连贯性": 0.5,
            "人类特征": 0.5,
            "分析": "无法从响应中提取分析"
        },
        "语言中立性": {
            "情感词汇": 0.5,
            "情感平衡": 0.5,
            "极端表述": 0.5,
            "煽动性表达": 0.5,
            "主观评价": 0.5,
            "分析": "无法从响应中提取分析"
        },
        "详细分析": response,  # 保存原始响应作为详细分析
        "可信度判断的疑点": []
    }
    
    # 尝试提取总体评分
    score_match = re.search(r'总体评分[：:]\s*(\d+\.\d+)', response)
    if score_match:
        try:
            result["总体评分"] = float(score_match.group(1))
        except:
            pass
    
    # 尝试提取各维度评分
    dimensions = ["内容真实性", "信息准确性", "来源可靠性", "语言客观性", "逻辑连贯性", "引用质量"]
    for dim in dimensions:
        score_match = re.search(f'{dim}[：:]\s*(\d+\.\d+)', response)
        if score_match:
            try:
                result["各大类评分"][dim] = float(score_match.group(1))
            except:
                result["各大类评分"][dim] = 0.5
    
    # 尝试提取AI生成内容评分
    ai_section = re.search(r'AI生成内容[：:].*?(?=语言中立性|$)', response, re.DOTALL)
    if ai_section:
        ai_text = ai_section.group(0)
        for key in ["表达模式", "词汇多样性", "句子变化", "上下文连贯性", "人类特征"]:
            score_match = re.search(f'{key}[：:]\s*(\d+\.\d+)', ai_text)
            if score_match:
                try:
                    result["AI生成内容"][key] = float(score_match.group(1))
                except:
                    pass
        
        # 提取分析
        analysis_match = re.search(r'分析[：:](.*?)(?=表达模式|词汇多样性|$)', ai_text, re.DOTALL)
        if analysis_match:
            result["AI生成内容"]["分析"] = analysis_match.group(1).strip()
    
    # 尝试提取语言中立性评分
    neutrality_section = re.search(r'语言中立性[：:].*?(?=详细分析|$)', response, re.DOTALL)
    if neutrality_section:
        neutrality_text = neutrality_section.group(0)
        for key in ["情感词汇", "情感平衡", "极端表述", "煽动性表达", "主观评价"]:
            score_match = re.search(f'{key}[：:]\s*(\d+\.\d+)', neutrality_text)
            if score_match:
                try:
                    result["语言中立性"][key] = float(score_match.group(1))
                except:
                    pass
        
        # 提取分析
        analysis_match = re.search(r'分析[：:](.*?)(?=情感词汇|情感平衡|$)', neutrality_text, re.DOTALL)
        if analysis_match:
            result["语言中立性"]["分析"] = analysis_match.group(1).strip()
    
    # 尝试提取疑点
    doubts_section = re.search(r'可信度判断的疑点[：:](.+?)(?=总体评分|$)', response, re.DOTALL)
    if doubts_section:
        doubts_text = doubts_section.group(1)
        # 分割为单独的疑点
        doubts = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', doubts_text, re.DOTALL)
        if doubts:
            result["可信度判断的疑点"] = [d.strip() for d in doubts if d.strip()]
        else:
            # 如果没有找到编号的疑点，尝试按行分割
            lines = [line.strip() for line in doubts_text.split('\n') if line.strip()]
            if lines:
                result["可信度判断的疑点"] = lines
    
    return result

def generate_default_analysis_result(original_response: str) -> Dict[str, Any]:
    """
    生成默认的分析结果结构
    
    参数:
        original_response: 原始响应文本
    
    返回:
        Dict: 默认的分析结果
    """
    return {
        "总体评分": 0.5,
        "各大类评分": {
            "内容真实性": 0.5,
            "信息准确性": 0.5,
            "来源可靠性": 0.5,
            "语言客观性": 0.5,
            "逻辑连贯性": 0.5,
            "引用质量": 0.5
        },
        "AI生成内容": {
            "表达模式": 0.5,
            "词汇多样性": 0.5,
            "句子变化": 0.5,
            "上下文连贯性": 0.5,
            "人类特征": 0.5,
            "分析": "无法解析DeepSeek响应，使用默认值。"
        },
        "语言中立性": {
            "情感词汇": 0.5,
            "情感平衡": 0.5,
            "极端表述": 0.5,
            "煽动性表达": 0.5,
            "主观评价": 0.5,
            "分析": "无法解析DeepSeek响应，使用默认值。"
        },
        "详细分析": "无法解析DeepSeek响应格式，使用默认分析结果。原始响应: " + original_response[:500] + "...",
        "可信度判断的疑点": ["无法从DeepSeek响应中提取疑点"]
    }

def validate_and_normalize_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证和规范化分析结果，确保所有必要字段存在
    
    参数:
        data: 解析的数据
    
    返回:
        Dict: 规范化后的数据
    """
    # 创建基础结构
    result = {
        "总体评分": 0.5,
        "各大类评分": {},
        "细分点评分": {},
        "AI生成内容": {},
        "语言中立性": {},
        "详细分析": "",
        "可信度判断的疑点": []
    }
    
    # 复制总体评分，确保是有效数值
    if "总体评分" in data and isinstance(data["总体评分"], (int, float)):
        result["总体评分"] = float(data["总体评分"])
    
    # 复制各大类评分
    if "各大类评分" in data and isinstance(data["各大类评分"], dict):
        result["各大类评分"] = data["各大类评分"]
    
    # 复制细分点评分
    if "细分点评分" in data and isinstance(data["细分点评分"], dict):
        result["细分点评分"] = data["细分点评分"]
    
    # 处理AI生成内容
    ai_content = {"表达模式": 0.5, "词汇多样性": 0.5, "句子变化": 0.5, "上下文连贯性": 0.5, "人类特征": 0.5, "分析": ""}
    
    if "AI生成内容" in data and isinstance(data["AI生成内容"], dict):
        for key in ai_content:
            if key in data["AI生成内容"]:
                if key == "分析":
                    ai_content[key] = str(data["AI生成内容"][key])
                elif isinstance(data["AI生成内容"][key], (int, float)):
                    ai_content[key] = float(data["AI生成内容"][key])
    
    result["AI生成内容"] = ai_content
    
    # 处理语言中立性
    neutrality = {"情感词汇": 0.5, "情感平衡": 0.5, "极端表述": 0.5, "煽动性表达": 0.5, "主观评价": 0.5, "分析": ""}
    
    if "语言中立性" in data and isinstance(data["语言中立性"], dict):
        for key in neutrality:
            if key in data["语言中立性"]:
                if key == "分析":
                    neutrality[key] = str(data["语言中立性"][key])
                elif isinstance(data["语言中立性"][key], (int, float)):
                    neutrality[key] = float(data["语言中立性"][key])
    
    result["语言中立性"] = neutrality
    
    # 复制详细分析
    if "详细分析" in data:
        result["详细分析"] = str(data["详细分析"])
    
    # 处理可信度判断的疑点
    if "可信度判断的疑点" in data:
        if isinstance(data["可信度判断的疑点"], list):
            result["可信度判断的疑点"] = data["可信度判断的疑点"]
        elif isinstance(data["可信度判断的疑点"], str):
            # 尝试分割字符串为列表
            lines = data["可信度判断的疑点"].strip().split('\n')
            result["可信度判断的疑点"] = [line.strip() for line in lines if line.strip()]
    
    return result

def identify_citations_with_deepseek(text):
    """
    使用DeepSeek识别文本中的引用内容
    
    参数:
        text (str): 新闻文本
    
    返回:
        List[Dict[str, Any]]: 引用内容列表，每项包含引用内容、位置和置信度
    """
    global DEEPSEEK_API_AVAILABLE
    
    if not DEEPSEEK_API_AVAILABLE:
        logger.warning("DeepSeek API不可用，无法识别引用内容")
        return []
    
    logger.info("使用DeepSeek识别引用内容")
    
    prompt = f"""
请分析以下新闻文本，识别其中所有的引用内容。引用内容可能包括直接引用（使用引号）或间接引用（如"据某某报道"）。
对于每个识别的引用，请提供以下信息：
1. 引用内容：具体被引用的文本
2. 引用来源：引用的来源（如有提及）
3. 置信度：你认为这确实是一个引用的置信度（0-1）

以JSON格式返回，格式为：
{{
    "citations": [
        {{
            "content": "引用内容",
            "source": "引用来源（如果有）",
            "confidence": 0.95,
            "type": "直接引用/间接引用"
        }}
    ]
}}

新闻文本：
{text}
"""
    
    try:
        response = query_deepseek(prompt)
        # 解析JSON响应
        try:
            # 尝试直接解析完整的JSON
            data = json.loads(response)
            return data.get("citations", [])
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            logger.warning("DeepSeek返回的不是有效JSON，尝试提取JSON部分")
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    return data.get("citations", [])
                except json.JSONDecodeError:
                    logger.error("无法从DeepSeek响应中提取有效JSON")
            logger.error("从DeepSeek响应中提取引用失败")
            return []
    except Exception as e:
        logger.error(f"调用DeepSeek识别引用时出错: {e}")
        logger.error(traceback.format_exc())
        return []

def verify_citations_with_deepseek(citations, search_results):
    """
    使用DeepSeek验证引用内容与搜索结果的一致性
    
    参数:
        citations (list): 引用内容列表
        search_results (dict): 搜索结果
    
    返回:
        List[Dict[str, Any]]: 验证结果列表
    """
    global DEEPSEEK_API_AVAILABLE
    
    if not DEEPSEEK_API_AVAILABLE:
        logger.warning("DeepSeek API不可用，无法验证引用内容")
        return []
    
    logger.info("使用DeepSeek验证引用内容")
    
    all_results = []
    
    for citation in citations:
        citation_content = citation.get("content", "")
        
        # 如果没有搜索结果，则跳过
        if not search_results or not search_results.get("results"):
            all_results.append({
                "citation": citation_content,
                "verified": False,
                "score": 0.0,
                "reason": "未找到搜索结果"
            })
            continue
        
        # 格式化搜索结果为文本
        search_texts = []
        for result in search_results.get("results", []):
            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")
            search_texts.append(f"标题: {title}\n内容: {content}\n链接: {url}")
        
        search_text = "\n\n".join(search_texts)
        
        prompt = f"""
请评估下面引用内容与搜索结果的一致性，判断引用内容是否真实可信。

引用内容：
"{citation_content}"

搜索结果：
{search_text}

请回答以下问题，并以JSON格式返回：
1. 引用内容与搜索结果是否一致？
2. 一致性评分（0-1，其中1代表完全一致）
3. 简要说明理由

格式如下：
{{
    "verified": true/false,
    "score": 0.95,
    "reason": "简要说明引用内容与搜索结果一致或不一致的原因"
}}
"""
        
        try:
            response = query_deepseek(prompt)
            # 解析JSON响应
            try:
                # 尝试直接解析完整的JSON
                data = json.loads(response)
                result = {
                    "citation": citation_content,
                    "verified": data.get("verified", False),
                    "score": data.get("score", 0.0),
                    "reason": data.get("reason", "")
                }
                all_results.append(result)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON部分
                logger.warning("DeepSeek返回的不是有效JSON，尝试提取JSON部分")
                json_match = re.search(r'({[\s\S]*})', response)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        result = {
                            "citation": citation_content,
                            "verified": data.get("verified", False),
                            "score": data.get("score", 0.0),
                            "reason": data.get("reason", "")
                        }
                        all_results.append(result)
                    except json.JSONDecodeError:
                        logger.error("无法从DeepSeek响应中提取有效JSON")
                        all_results.append({
                            "citation": citation_content,
                            "verified": False,
                            "score": 0.0,
                            "reason": "处理DeepSeek响应时出错"
                        })
                else:
                    logger.error("从DeepSeek响应中提取验证结果失败")
                    all_results.append({
                        "citation": citation_content,
                        "verified": False,
                        "score": 0.0,
                        "reason": "无法解析DeepSeek响应"
                    })
        except Exception as e:
            logger.error(f"调用DeepSeek验证引用时出错: {e}")
            logger.error(traceback.format_exc())
            all_results.append({
                "citation": citation_content,
                "verified": False,
                "score": 0.0,
                "reason": f"验证过程出错: {str(e)}"
            })
    
    return all_results

def judge_citation_with_deepseek(citation, api_key=None):
    """
    使用DeepSeek API判断引用内容的真实性
    
    参数:
        citation (Dict[str, Any]): 引用信息，包含内容、来源等
        api_key (str, optional): DeepSeek API密钥
    
    返回:
        Dict[str, Any]: 包含评分和分析的字典
    """
    logger.info("使用DeepSeek API判断引用真实性")
    
    # 提取引用内容和来源
    content = citation.get("内容", "")
    source = citation.get("来源", "未知来源")
    context = citation.get("上下文", "")
    
    if not content:
        logger.warning("引用内容为空，无法判断真实性")
        return {
            "score": 0.5,
            "reasoning": "引用内容为空，无法判断真实性",
            "conclusion": "无效引用"
        }
    
    # 构建提示
    prompt = f"""
请判断以下引用内容的真实性，评分范围0-1（0表示完全虚假，1表示完全真实）：

引用内容：{content}
来源：{source}
引用上下文：{context}

请基于以下几点进行评估：
1. 内容的具体性和细节程度
2. 表述的极端程度（过于绝对的表述往往可信度较低）
3. 引用来源的可靠性
4. 内容的常识性和逻辑性

请按以下格式返回结果：
{{"score": 0.X, "reasoning": "你的分析理由", "conclusion": "简短结论"}}
"""

    try:
        # 调用DeepSeek API
        response = query_deepseek(prompt)
        
        # 尝试解析返回的JSON
        try:
            # 从响应文本中提取JSON
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_str = match.group(0)
                result = json.loads(json_str)
                
                if "score" in result:
                    score = float(result["score"])
                    logger.info(f"DeepSeek引用真实性评分: {score}")
                    return result
            
            # 如果没有找到JSON或解析失败，尝试直接从文本中提取评分
            score_match = re.search(r'score"?\s*:\s*(\d+\.\d+)', response)
            if score_match:
                score = float(score_match.group(1))
                logger.info(f"从文本提取的引用真实性评分: {score}")
                return {
                    "score": score,
                    "reasoning": "无法完全解析DeepSeek响应，但成功提取了评分",
                    "conclusion": "评分可信但详细分析缺失"
                }
            
            # 最后手段：根据DeepSeek的文本响应进行简单分类
            if any(word in response.lower() for word in ["真实", "可信", "reliable", "trustworthy", "true"]):
                score = 0.8
                reason = "DeepSeek评估为高度可信"
            elif any(word in response.lower() for word in ["部分真实", "partially", "somewhat"]):
                score = 0.6
                reason = "DeepSeek评估为部分可信"
            elif any(word in response.lower() for word in ["虚假", "不可信", "false", "unreliable", "fake"]):
                score = 0.2
                reason = "DeepSeek评估为可能虚假"
            else:
                score = 0.5
                reason = "DeepSeek无法确定真实性"
                
            return {
                "score": score,
                "reasoning": reason,
                "conclusion": reason
            }
                
        except Exception as e:
            logger.error(f"解析DeepSeek引用真实性响应失败: {str(e)}")
            return {
                "score": 0.5,
                "reasoning": f"解析DeepSeek响应失败: {str(e)}",
                "conclusion": "分析失败，使用默认评分"
            }
            
    except Exception as e:
        logger.error(f"调用DeepSeek判断引用真实性失败: {str(e)}")
        return {
            "score": 0.5,
            "reasoning": f"调用DeepSeek API失败: {str(e)}",
            "conclusion": "API调用失败，使用默认评分"
        }

def analyze_citation_validity_with_deepseek(text: str, citations: list, api_key=None):
    """
    使用DeepSeek API分析引用内容的有效性和相关性
    
    参数:
        text (str): 新闻全文
        citations (list): 提取的引用列表
        api_key (str, optional): DeepSeek API密钥
    
    返回:
        Tuple[float, Dict[str, Any]]: (有效性评分, 详细分析结果)
    """
    logger.info("使用DeepSeek API分析引用有效性")
    
    if not citations:
        return 0.5, {
            "引用数量": 0,
            "引用有效性": 0.5,
            "详细分析": ["文本中未检测到引用内容"],
            "总结": "未检测到引用内容，无法评估有效性"
        }
    
    # 构建引用列表字符串
    citations_text = ""
    for i, citation in enumerate(citations):
        content = citation.get("内容", "")
        source = citation.get("来源", "未知来源")
        citations_text += f"\n引用 {i+1}: {content}\n来源: {source}\n\n"
    
    # 构建提示
    prompt = f"""请分析以下新闻文本中的引用内容的有效性和相关性。评估每个引用是否与文章主题相关、是否具体、是否提供了有价值的信息。

新闻全文:
{text[:1500]}...  # 限制长度，避免超出API限制

引用列表:
{citations_text}

请分析每个引用的有效性，并评分（0-1分）。然后给出总体评分和分析结论。
请以JSON格式返回结果，包括:
1. 总体有效性评分
2. 每个引用的评分和分析
3. 总结性结论

返回格式示例:
{{
  "总体评分": 0.X,
  "引用分析": [
    {{
      "引用序号": 1,
      "内容": "引用内容...",
      "评分": 0.X,
      "分析": "这个引用..."
    }},
    ...
  ],
  "总结": "总体来看，这些引用..."
}}
"""

    try:
        # 调用DeepSeek API
        response = query_deepseek(prompt)
        
        # 尝试解析返回的JSON
        try:
            # 从响应文本中提取JSON
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_str = match.group(0)
                # 清理可能导致JSON解析错误的字符
                clean_json = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'', json_str)
                result = json.loads(clean_json)
                
                # 提取总体评分
                overall_score = result.get("总体评分", 0.5)
                
                # 提取引用分析
                citation_analyses = result.get("引用分析", [])
                
                # 提取总结
                summary = result.get("总结", "DeepSeek未提供有效总结")
                
                # 构建返回结果
                final_result = {
                    "引用数量": len(citations),
                    "引用有效性": overall_score,
                    "详细分析": citation_analyses,
                    "总结": summary
                }
                
                logger.info(f"DeepSeek引用有效性分析完成，总评分: {overall_score}")
                return overall_score, final_result
                
            # 如果JSON解析失败，尝试从文本中提取评分
            score_match = re.search(r'总体评分"?\s*:\s*(\d+\.\d+)', response)
            if score_match:
                score = float(score_match.group(1))
                
                # 构建简化的返回结果
                result = {
                    "引用数量": len(citations),
                    "引用有效性": score,
                    "详细分析": ["DeepSeek分析结果格式不正确，无法提取详细分析"],
                    "总结": "无法从DeepSeek响应中提取完整分析结果"
                }
                
                logger.info(f"从文本提取的引用有效性评分: {score}")
                return score, result
                
            # 如果无法提取评分，返回默认值
            logger.warning("无法从DeepSeek响应中提取引用有效性分析结果")
            return 0.5, {
                "引用数量": len(citations),
                "引用有效性": 0.5,
                "详细分析": ["无法从DeepSeek响应中提取分析结果"],
                "总结": "DeepSeek分析失败，使用默认评分"
            }
            
        except Exception as e:
            logger.error(f"解析DeepSeek引用有效性响应失败: {str(e)}")
            return 0.5, {
                "引用数量": len(citations),
                "引用有效性": 0.5,
                "详细分析": [f"解析DeepSeek响应失败: {str(e)}"],
                "总结": "DeepSeek响应解析失败，使用默认评分"
            }
            
    except Exception as e:
        logger.error(f"调用DeepSeek分析引用有效性失败: {str(e)}")
        return 0.5, {
            "引用数量": len(citations),
            "引用有效性": 0.5,
            "详细分析": [f"调用DeepSeek API失败: {str(e)}"],
            "总结": "DeepSeek API调用失败，使用默认评分"
        }

def analyze_suspicious_points_with_deepseek(text: str) -> Dict[str, Any]:
    """
    使用DeepSeek API分析新闻文本中的可疑点
    
    参数:
        text (str): 要分析的新闻文本
    
    返回:
        Dict[str, Any]: 包含可疑点分析结果的字典
    """
    logger.info("开始使用DeepSeek分析可疑点")
    
    # 限制文本长度
    max_text_length = 2000
    if len(text) > max_text_length:
        text = text[:max_text_length] + "...(文本已截断)"
    
    prompt = """
请对以下新闻文本进行深入的可疑点分析。重点关注以下方面：

1. 内容真实性问题：
   - 事实陈述是否有明确来源
   - 数据和统计是否准确
   - 是否存在夸大或虚构内容
   
2. 信息准确性问题：
   - 细节是否前后矛盾
   - 时间地点是否模糊
   - 专业术语使用是否准确
   
3. 来源可靠性问题：
   - 引用来源是否可靠
   - 是否存在匿名或不明确的消息来源
   - 多个来源之间是否存在矛盾
   
4. 语言表达问题：
   - 是否存在明显的偏见或倾向性
   - 是否使用煽动性或极端化语言
   - 是否混入过多主观评价
   
5. 逻辑推理问题：
   - 因果关系是否合理
   - 论证是否完整
   - 结论是否过于武断

请以JSON格式返回分析结果：
{
    "主要疑点": [
        {
            "问题": "具体的可疑点描述",
            "类型": "问题类型（如：内容真实性/信息准确性等）",
            "严重程度": "高/中/低",
            "理由": "为什么这是一个问题",
            "建议": "如何验证或解决该问题"
        }
    ],
    "总体评估": "对新闻整体可信度的简要评估",
    "建议": [
        "针对发现的问题给出的具体建议"
    ]
}

新闻文本：
{text}
"""
    
    try:
        # 调用DeepSeek API
        response = query_deepseek(prompt)
        
        # 解析响应
        try:
            # 尝试直接解析JSON
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            # 尝试从响应中提取JSON部分
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                try:
                    json_str = json_match.group(1)
                    # 清理可能导致解析错误的字符
                    clean_json = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'', json_str)
                    return json.loads(clean_json)
                except json.JSONDecodeError:
                    logger.error("无法从DeepSeek响应中提取有效JSON")
            
            # 如果无法解析JSON，返回基本结构
            return {
                "主要疑点": [],
                "总体评估": "无法从DeepSeek响应中提取有效分析结果",
                "建议": ["建议进行人工审查以确认新闻可信度"]
            }
            
    except Exception as e:
        logger.error(f"调用DeepSeek分析可疑点时出错: {e}")
        logger.error(traceback.format_exc())
        return {
            "主要疑点": [],
            "总体评估": f"分析过程出错: {str(e)}",
            "建议": ["建议进行人工审查以确认新闻可信度"]
        }

# 如果直接运行此模块，执行简单测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("开始测试ai_services模块...")
    
    # 打印环境变量状态
    api_key = os.getenv('DEEPSEEK_API_KEY')
    print(f"DEEPSEEK_API_KEY设置状态: {'已设置' if api_key else '未设置'}")
    
    # 测试API连接
    print(f"测试前DEEPSEEK_API_AVAILABLE={DEEPSEEK_API_AVAILABLE}")
    connection_ok = test_deepseek_connection()
    print(f"测试后DEEPSEEK_API_AVAILABLE={DEEPSEEK_API_AVAILABLE}")
    print(f"DeepSeek API连接测试: {'成功' if connection_ok else '失败'}")
    
    if connection_ok:
        # 测试分析功能
        test_text = "据专家称，植物油比动物油更健康。"
        score, analysis = analyze_with_deepseek_v3(test_text)
        print(f"分析结果 - 评分: {score}")
        print(f"详细分析: {analysis[:200]}...") 