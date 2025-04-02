import logging
from urllib.parse import urlparse
from main.config import SEARXNG_URL, SEARCH_TIMEOUT
import requests
import traceback
# 初始化logger
logger = logging.getLogger(__name__)

# 全局变量，标记SearXNG API是否可用
SEARXNG_AVAILABLE = False

# 删除公共SearXNG实例相关代码

# SearXNG参数
SEARXNG_PARAMS = {
    'categories': 'general',
    'language': 'zh-CN,zh,en',
    'format': 'json',
    'headers': {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    'time_range': '',  # 空字符串表示所有时间
    'safesearch': 0,
    'engines': 'bing,google,brave,qwant,wikipedia'
}

def test_searxng_connection(verify_search: bool = True) -> bool:
    """
    测试与SearXNG的连接状态
    
    参数:
        verify_search (bool): 是否验证搜索功能
    
    返回:
        bool: 连接是否成功
    """
    global SEARXNG_AVAILABLE
    
    logger.info("测试SearXNG连接...")
    print(f"使用的SearXNG URL: {SEARXNG_URL}")
    
    # 检查基础URL设置
    if not SEARXNG_URL:
        logger.error("SearXNG URL未配置")
        SEARXNG_AVAILABLE = False
        return False
    
    try:
        # 解析API URL
        parsed_url = urlparse(SEARXNG_URL)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # 测试基础连接
        logger.info(f"测试SearXNG基础连接 {base_url}")
        
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        print(f"使用的User-Agent: {headers['User-Agent']}")
        
        response = requests.get(
            base_url,
            timeout=SEARCH_TIMEOUT,
            headers=headers
        )
        
        print(f"基础连接状态码: {response.status_code}")
        
        if response.status_code != 200:
            logger.warning(f"SearXNG连接失败: 状态码 {response.status_code}")
            SEARXNG_AVAILABLE = False
            return False
        
        # 如果需要验证搜索功能
        if verify_search:
            logger.info("测试SearXNG搜索功能")
            
            # 使用简单查询测试
            test_query = "test"
            search_url = f"{base_url}/search?q={test_query}&format=json"
            print(f"搜索请求URL: {search_url}")
            
            response = requests.get(
                search_url,
                timeout=SEARCH_TIMEOUT,
                headers=headers
            )
            
            print(f"搜索请求状态码: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"SearXNG搜索测试失败: 状态码 {response.status_code}")
                SEARXNG_AVAILABLE = False
                return False
            
            try:
                results = response.json()
                if 'results' not in results:
                    logger.warning("SearXNG搜索测试失败: 响应格式无效")
                    print(f"响应内容: {response.text[:500]}")
                    SEARXNG_AVAILABLE = False
                    return False
                else:
                    print(f"搜索结果数量: {len(results.get('results', []))}")
            except Exception as e:
                logger.warning(f"SearXNG搜索测试失败: 无法解析JSON响应 - {str(e)}")
                print(f"响应内容: {response.text[:500]}")
                SEARXNG_AVAILABLE = False
                return False
        
        logger.info("SearXNG连接测试成功")
        SEARXNG_AVAILABLE = True
        return True
        
    except Exception as e:
        logger.warning(f"SearXNG连接测试失败: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"测试SearXNG连接时出错: {str(e)}")
        SEARXNG_AVAILABLE = False
        return False 