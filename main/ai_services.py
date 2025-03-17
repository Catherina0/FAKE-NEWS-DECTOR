#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

# 全局变量，用于标记API是否可用 - 必须默认为True
DEEPSEEK_API_AVAILABLE = True

def test_deepseek_connection():
    """
    测试DeepSeek API连接是否正常
    
    返回:
        bool: 连接是否成功
    """
    global DEEPSEEK_API_AVAILABLE
    
    # 重置API状态为True，确保测试可以进行
    DEEPSEEK_API_AVAILABLE = True
    
    logger.info("测试DeepSeek API连接...")
    
    # 获取API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("未设置DEEPSEEK_API_KEY环境变量")
        DEEPSEEK_API_AVAILABLE = False
        return False
    
    print(f"开始测试DeepSeek API连接，API密钥长度：{len(api_key)}")
    
    # API端点
    api_url = "https://api.deepseek.com/v1/chat/completions"
    
    # 请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 请求数据 - 使用更简单的提示词减少响应大小
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "回复'OK'两个字母"
            }
        ],
        "max_tokens": 5,
        "temperature": 0.1  # 使用低温度获得确定性回答
    }
    
    # 重试参数
    max_retries = 3
    base_timeout = 15  # 增加基础超时时间
    
    # 重试逻辑
    for attempt in range(max_retries):
        try:
            current_timeout = base_timeout * (attempt + 1)  # 逐次增加超时时间
            print(f"发送测试请求到DeepSeek API... (尝试 {attempt+1}/{max_retries}, 超时: {current_timeout}秒)")
            
            # 创建新的会话对象
            session = requests.Session()
            
            response = session.post(
                api_url, 
                headers=headers, 
                json=data, 
                timeout=current_timeout
            )
            
            # 关闭会话
            session.close()
            
            if response.status_code == 200:
                try:
                    # 尝试解析JSON响应
                    response_data = response.json()
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        logger.info("DeepSeek API连接测试成功")
                        print("DeepSeek API连接测试成功")
                        DEEPSEEK_API_AVAILABLE = True
                        return True
                    else:
                        logger.warning("DeepSeek API响应格式不正确")
                        print("DeepSeek API响应格式不正确")
                except json.JSONDecodeError:
                    logger.warning("DeepSeek API响应不是有效的JSON格式")
                    print("DeepSeek API响应不是有效的JSON格式")
                    
                # 即使JSON解析失败，如果状态码是200，仍然认为连接成功
                logger.info("DeepSeek API连接测试成功（基于HTTP状态码）")
                print("DeepSeek API连接测试成功（基于HTTP状态码）")
                DEEPSEEK_API_AVAILABLE = True
                return True
            elif response.status_code == 429:
                error_msg = f"DeepSeek API请求频率限制 (HTTP {response.status_code})"
                logger.warning(error_msg)
                print(error_msg)
                
                # 如果不是最后一次尝试，等待更长时间后重试
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5  # 指数退避，基础等待时间更长
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            else:
                error_msg = f"DeepSeek API连接测试失败: HTTP {response.status_code}, {response.text}"
                logger.error(error_msg)
                print(error_msg)
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        except requests.exceptions.Timeout:
            logger.error(f"DeepSeek API连接超时 (尝试 {attempt+1}/{max_retries})")
            print(f"DeepSeek API连接超时 (尝试 {attempt+1}/{max_retries})")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"DeepSeek API连接错误: {e}")
            print(f"DeepSeek API连接错误: {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        except Exception as e:
            error_msg = f"DeepSeek API连接测试失败: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            logger.error(traceback.format_exc())
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
    
    # 如果所有尝试都失败
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
    
    # DeepSeek API端点
    api_url = "https://api.deepseek.com/v1/chat/completions"
    
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
        "max_tokens": 4000
    }
    
    # 只有当提示词中包含 "json" 时才添加 response_format 参数
    if "json" in prompt.lower():
        data["response_format"] = {"type": "json_object"}
        logger.debug("启用 JSON 响应格式")
    
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

def analyze_with_deepseek_v3(text, api_key=None):
    """
    使用DeepSeek API分析文本可信度
    
    参数:
        text (str): 要分析的文本
        api_key (str, optional): DeepSeek API密钥
    
    返回:
        tuple: (分数, 详细信息)
    """
    # 检查API是否可用
    global DEEPSEEK_API_AVAILABLE
    if not DEEPSEEK_API_AVAILABLE:
        logging.warning("DeepSeek API不可用，跳过分析")
        return 0.5, "DeepSeek API不可用，无法进行分析"
    
    # 限制文本长度，避免超出API限制
    max_text_length = 2000
    if len(text) > max_text_length:
        logging.warning(f"文本长度超过{max_text_length}字符，将被截断")
        text = text[:max_text_length] + "...(文本已截断)"
    
    # 构建提示词
    prompt = f"""请分析以下新闻文本的可信度，并给出详细评分和分析。评分范围从0到1，其中0表示完全不可信，1表示完全可信。

请先仔细阅读文本，然后逐步思考以下各个方面的评分标准，对每个细分点进行独立评分，最后再综合得出总体评分。

请从以下几个方面进行详细评分和分析：

1. 内容真实性（总分值占比25%）：
   a. 事实核查：文本中的主要事实是否可被验证（0-1分）
   b. 虚构成分：是否存在明显编造或夸大的内容（0-1分）
   c. 时间准确性：事件发生时间是否准确描述（0-1分）
   d. 地点准确性：地理位置和场景描述是否准确（0-1分）
   e. 人物真实性：涉及人物是否真实存在且描述准确（0-1分）

2. 信息准确性（总分值占比20%）：
   a. 数据准确性：数字、统计数据是否准确（0-1分）
   b. 细节一致性：文本内部细节是否一致，无矛盾（0-1分）
   c. 专业术语：专业术语使用是否恰当准确（0-1分）
   d. 背景信息：背景和上下文信息是否准确（0-1分）

3. 来源可靠性（总分值占比15%）：
   a. 信息来源：是否明确标注信息来源（0-1分）
   b. 来源权威性：来源是否具有权威性和专业性（0-1分）
   c. 多源验证：是否有多个独立来源佐证（0-1分）
   d. 引用规范：引用方式是否规范、准确（0-1分）

4. 语言客观性（总分值占比15%）：
   a. 情感色彩：语言是否避免过度情绪化表达（0-1分）
   b. 偏见检测：是否存在明显的立场偏见（0-1分）
   c. 平衡报道：是否呈现多方观点（0-1分）
   d. 修辞使用：修辞手法是否恰当，不误导读者（0-1分）

5. 逻辑连贯性（总分值占比15%）：
   a. 因果关系：因果关系是否合理建立（0-1分）
   b. 论证完整性：论证是否完整，无明显跳跃（0-1分）
   c. 结构清晰：文本结构是否清晰有序（0-1分）
   d. 推理合理：推理过程是否合理（0-1分）

6. 引用质量（总分值占比10%）：
   a. 引用多样性：是否引用多样化的资料（0-1分）
   b. 引用时效性：引用资料是否具有时效性（0-1分）
   c. 引用相关性：引用是否与主题高度相关（0-1分）

请对每个细分点进行思考和评分，然后计算各大类的加权平均分，最后得出总体评分。

请以JSON格式返回结果，包含总体评分、各大类评分、各细分点评分，以及详细分析。格式如下：
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
  "详细分析": "这里是详细分析...",
  "可信度判断的疑点": "这里是影响文本可信度存在的疑点..."
}}

新闻文本：
{text}
"""
    
    try:
        # 调用DeepSeek API
        response = query_deepseek(prompt)
        if not response:
            logging.warning("DeepSeek API返回空响应")
            return 0.5, "DeepSeek API返回空响应，无法进行分析"
        
        logging.debug(f"DeepSeek API响应: {response}")
        
        # 尝试解析JSON
        try:
            import json
            import re
            
            # 记录原始响应以便调试
            logging.debug(f"尝试解析的原始响应: {response[:500]}...")
            
            # 尝试从响应中提取JSON部分
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                json_str = json_match.group(1)
                try:
                    data = json.loads(json_str)
                    
                    # 提取总体评分
                    overall_score = data.get("总体评分", 0.5)
                    
                    # 格式化详细信息
                    detailed_info = json.dumps(data, ensure_ascii=False, indent=2)
                    
                    return overall_score, detailed_info
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
                        return overall_score, json.dumps(data, ensure_ascii=False, indent=2)
                    except Exception as fix_error:
                        logging.error(f"修复JSON失败: {fix_error}")
                        
                        # 如果修复失败，尝试使用更宽松的方式解析
                        try:
                            import ast
                            # 尝试使用ast模块解析Python字典
                            dict_str = json_str.replace('null', 'None').replace('true', 'True').replace('false', 'False')
                            data = ast.literal_eval(dict_str)
                            overall_score = data.get("总体评分", 0.5)
                            return overall_score, json.dumps(data, ensure_ascii=False, indent=2)
                        except Exception as ast_error:
                            logging.error(f"使用ast解析失败: {ast_error}")
            
            # 如果无法提取JSON，尝试从文本中提取评分
            score_match = re.search(r'总体评分[：:]\s*(\d+\.\d+)', response)
            if score_match:
                score = float(score_match.group(1))
                return score, response
            else:
                # 尝试提取数字评分
                number_match = re.search(r'(\d+\.\d+)\s*/\s*1', response)
                if number_match:
                    score = float(number_match.group(1))
                    return score, response
                
                # 如果无法提取评分，返回默认值和原始响应
                logging.warning("无法从响应中提取评分，使用默认值0.5")
                return 0.5, response
        except Exception as e:
            logging.error(f"解析DeepSeek响应时出错: {e}")
            logging.error(traceback.format_exc())
            return 0.5, response
    except Exception as e:
        logging.error(f"调用DeepSeek API时出错: {e}")
        return 0.5, f"调用DeepSeek API时出错: {e}"

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