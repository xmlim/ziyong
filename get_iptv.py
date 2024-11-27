import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from googlesearch import search
from typing import Optional, Dict, List
import random
import logging
import os
from datetime import datetime, timedelta
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('iptv_collector.log'),
        logging.StreamHandler()
    ]
)

# 配置重试策略
def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

# 代理列表（建议使用您自己的代理）
PROXIES = [
    None,  # 无代理
    # 添加您的代理列表
    # {'http': 'http://proxy1:port1', 'https': 'https://proxy1:port1'},
    # {'http': 'http://proxy2:port2', 'https': 'https://proxy2:port2'},
]

def get_random_proxy():
    return random.choice(PROXIES)

# 获取请求IP的地理位置
def get_location_by_ip(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=10)
        response.raise_for_status()  # 检查HTTP错误
        data = response.json()
        if data.get('status') == 'fail':
            return None
        return data
    except (requests.RequestException, ValueError) as e:
        print(f"获取IP地理位置时出错: {e}")
        return None

# 使用搜索引擎查找当地的IPTV直播源
def search_iptv_sources(location: Dict) -> List[str]:
    sources = set()  # 使用集合去重
    queries = [
        f"IPTV {location['city']} {location['country']} m3u",
        f"IPTV {location['country']} playlist m3u",
        f"{location['country']} free iptv m3u8"
    ]
    
    for query in queries:
        try:
            for url in search(query, num=10, stop=10, pause=random.uniform(2.0, 5.0)):
                if any(url.lower().endswith(ext) for ext in ['.m3u', '.m3u8']):
                    sources.add(url)
        except Exception as e:
            print(f"搜索查询 '{query}' 时出错: {e}")
            continue
    
    return list(sources)

# 验证直播源的有效性
def validate_iptv_source(source_url: str) -> bool:
    session = create_session()
    try:
        response = session.get(source_url, timeout=15, proxies=get_random_proxy())
        response.raise_for_status()
        content = response.text.strip()
        
        # 基本格式检查
        if not content.startswith("#EXTM3U"):
            return False
            
        # 检查是否包含有效的频道
        if "#EXTINF" not in content:
            return False
            
        # 检查内容长度
        if len(content.splitlines()) < 3:  # 至少需要有M3U头部、一个EXTINF行和一个URL行
            return False
            
        return True
    except Exception as e:
        print(f"验证源 {source_url} 时出错: {e}")
        return False

# 获取直播源内容
def get_iptv_stream(source_url):
    response = requests.get(source_url)
    if response.status_code == 200:
        return response.text
    return None

# 保存IPTV数据
def save_iptv_data(stream: str, location: Dict, valid_sources: List[str]) -> None:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        # 创建备份目录
        os.makedirs('backups', exist_ok=True)
        
        # 保存当前文件
        with open("iptv_stream.m3u", "w", encoding='utf-8') as file:
            file.write(stream)
            
        # ���建备份
        backup_path = f'backups/iptv_stream_{timestamp}.m3u'
        with open(backup_path, "w", encoding='utf-8') as file:
            file.write(stream)
            
        # 保存详细信息
        with open("moyun.txt", "w", encoding='utf-8') as file:
            file.write(f"# IPTV直播源列表 (更新时间: {timestamp})\n")
            file.write(f"地理位置: {location['city']}, {location['country']}\n")
            file.write(f"IP: {location['query']}\n\n")
            file.write("有效直播源:\n")
            for idx, source in enumerate(valid_sources, 1):
                file.write(f"{idx}. {source}\n")
            file.write("\n完整直播源内容:\n")
            file.write(stream)
            
        logging.info("所有文件保存成功")
    except Exception as e:
        logging.error(f"保存文件时出错: {e}")
        raise

# 添加缓存相关的常量
CACHE_DIR = "iptv_cache"
CACHE_INDEX_FILE = os.path.join(CACHE_DIR, "cache_index.json")
SOURCES_DIR = os.path.join(CACHE_DIR, "sources")

# 初始化缓存目录
def init_cache_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(SOURCES_DIR, exist_ok=True)
    if not os.path.exists(CACHE_INDEX_FILE):
        with open(CACHE_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

def get_cache_key(location):
    """生成缓存键"""
    return f"{location['country']}_{location['region']}_{location['city']}".lower()

def save_to_cache(location, sources, stream):
    """保存直播源到缓存"""
    cache_key = get_cache_key(location)
    timestamp = datetime.now().isoformat()
    
    # 保存源文件
    source_file = os.path.join(SOURCES_DIR, f"{cache_key}.m3u")
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(stream)
    
    # 更新索引
    with open(CACHE_INDEX_FILE, 'r+', encoding='utf-8') as f:
        index = json.load(f)
        index[cache_key] = {
            'location': location,
            'sources': sources,
            'file_path': source_file,
            'updated_at': timestamp
        }
        f.seek(0)
        json.dump(index, f, indent=2)
        f.truncate()

def get_from_cache(location, max_age_hours=24):
    """从缓存获取直播源"""
    cache_key = get_cache_key(location)
    
    try:
        with open(CACHE_INDEX_FILE, 'r', encoding='utf-8') as f:
            index = json.load(f)
            
        if cache_key in index:
            cache_data = index[cache_key]
            updated_at = datetime.fromisoformat(cache_data['updated_at'])
            
            # 检查缓��是否过期
            if datetime.now() - updated_at < timedelta(hours=max_age_hours):
                # 读取缓存的源文件
                with open(cache_data['file_path'], 'r', encoding='utf-8') as f:
                    stream = f.read()
                return cache_data['sources'], stream
    except Exception as e:
        logging.error(f"读取缓存时出错: {e}")
    
    return None, None

# 主函数
def main():
    logging.info("开始运行IPTV源收集器")
    
    # 初始化缓存目录
    init_cache_dirs()
    
    ip = "8.8.8.8"
    logging.info(f"使用IP地址: {ip}")
    
    location = get_location_by_ip(ip)
    if not location:
        logging.error("无法获取地理位置信息")
        return
    
    logging.info(f"获取到地理位置: {location['city']}, {location['country']}")
    
    # 尝试从缓存获取
    cached_sources, cached_stream = get_from_cache(location)
    if cached_sources and cached_stream:
        logging.info("使用缓存的直播源")
        save_iptv_data(cached_stream, location, cached_sources)
        return
    
    # 如果缓存不存在或已过期，重新获取
    sources = search_iptv_sources(location)
    if not sources:
        logging.error("未找到IPTV直播源")
        return

    valid_sources = [source for source in sources if validate_iptv_source(source)]
    if not valid_sources:
        logging.error("未找到有效的IPTV直播源")
        return

    stream = get_iptv_stream(valid_sources[0])
    if not stream:
        logging.error("无法获取直播源内容")
        return

    # 保存到缓存
    save_to_cache(location, valid_sources, stream)
    
    # 保存直播源内容到文件
    try:
        save_iptv_data(stream, location, valid_sources)
    except Exception as e:
        logging.error(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()