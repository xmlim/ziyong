import requests
import logging
import subprocess
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('stream_check.log')  # 添加文件日志
    ]
)

async def check_url_validity(session: aiohttp.ClientSession, url: str) -> bool:
    try:
        async with session.head(url, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        logging.error(f"URL {url} is invalid or unreachable: {e}")
        return False

async def fetch_content(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        logging.info(f"Fetching content from {url}")
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                return await response.text(encoding='utf-8-sig')
            logging.error(f"Failed to fetch {url}, status code: {response.status}")
            return None
    except Exception as e:
        logging.error(f"Failed to fetch content from {url}: {e}")
        return None

def filter_content(content: Optional[str]) -> List[str]:
    if not content:
        return []
    
    keywords = [
        "㊙VIP测试", "关注公众号", "天微科技", "获取测试密码",
        "更新时间", "♥聚玩盒子", "🌹防失联", "📡  更新日期",
    ]
    
    filtered_lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line or 'ipv6' in line.lower():
            continue
        if any(keyword in line for keyword in keywords):
            continue
        filtered_lines.append(line)
    
    return filtered_lines

def check_stream_validity(url: str) -> bool:
    try:
        command = [
            'ffmpeg',
            '-v', 'quiet',  # 减少输出
            '-i', url,
            '-t', '5',      # 缩短检查时间到5秒
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logging.error(f"Stream {url} check timed out")
        return False
    except Exception as e:
        logging.error(f"Error checking stream {url}: {e}")
        return False

async def process_urls(urls: List[str]):
    async with aiohttp.ClientSession() as session:
        # 并发检查URL有效性
        tasks = [check_url_validity(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        valid_urls = [url for url, is_valid in zip(urls, results) if is_valid]
        
        # 获取内容
        tasks = [fetch_content(session, url) for url in valid_urls]
        contents = await asyncio.gather(*tasks)
        
        # 过滤内容
        all_filtered_lines = []
        for content in contents:
            all_filtered_lines.extend(filter_content(content))
        
        # 检查流的有效性
        valid_lines = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for line in all_filtered_lines:
                if line.startswith('http'):
                    url = line.split()[0]
                    futures.append((line, executor.submit(check_stream_validity, url)))
                else:
                    valid_lines.append(line)
            
            for line, future in futures:
                if future.result():
                    valid_lines.append(line)
                else:
                    logging.warning(f"Skipping unplayable stream: {line.split()[0]}")
        
        # 保存结果
        with open('live_ipv4.txt', 'w', encoding='utf-8') as file:
            file.write('\n'.join(valid_lines))
        logging.info(f"Saved {len(valid_lines)} valid streams to live_ipv4.txt")

if __name__ == "__main__":
    urls = [
        'https://raw.githubusercontent.com/leiyou-li/IPTV4/refs/heads/main/live.txt',
        'https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.txt',
        'http://xhztv.top/zbc.txt',
        'http://ww.weidonglong.com/dsj.txt',
        'https://tv.youdu.fan:666/live/',
        'https://live.zhoujie218.top/tv/iptv6.txt',
        'http://tipu.xjqxz.top/live1213.txt',
        'https://tv.iill.top/m3u/Live',
        'http://www.lyyytv.cn/yt/zhibo/1.txt',
        'http://live.nctv.top/x.txt',
        'http://www.lyyytv.cn/yt/zhibo/1.txt',
        'https://github.moeyy.xyz/https://raw.githubusercontent.com/Ftindy/IPTV-URL/main/huyayqk.m3u',
        'https://ghp.ci/raw.githubusercontent.com/MemoryCollection/IPTV/refs/heads/main/itvlist.m3u',
        'https://live.fanmingming.com/tv/m3u/ipv6.m3u'
    ]
    
    asyncio.run(process_urls(urls))