import requests
import logging
import subprocess
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
import json
import os
import glob
from datetime import datetime

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

def check_stream_quality(url: str) -> dict:
    try:
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            url
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                'resolution': f"{data['streams'][0].get('width', '未知')}x{data['streams'][0].get('height', '未知')}",
                'bitrate': data['format'].get('bit_rate', '未知'),
                'format': data['format'].get('format_name', '未知')
            }
    except Exception as e:
        logging.error(f"Error checking quality for {url}: {e}")
    return {'resolution': '未知', 'bitrate': '未知', 'format': '未知'}

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
        
        # 去重
        valid_lines = remove_duplicates(valid_lines)
        
        # 分类
        categorized_streams = categorize_streams(valid_lines)
        
        # 生成统计
        stats = generate_stats(valid_lines)
        
        # 保存分类结果
        for category, streams in categorized_streams.items():
            with open(f'live_ipv4_{category}.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(streams))
        
        # 保存主文件
        with open('live_ipv4.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_lines))
        
        # 创建备份
        backup_sources(valid_lines)
        
        # 保存统计信息
        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logging.info(f"处理完成，共有 {stats['total_sources']} 个有效源")

def categorize_streams(lines: List[str]) -> dict:
    categories = {
        '央视': [],
        '卫视': [],
        '地方': [],
        '港澳台': [],
        '其他': []
    }
    
    for line in lines:
        if 'CCTV' in line.upper():
            categories['央视'].append(line)
        elif '卫视' in line:
            categories['卫视'].append(line)
        elif any(x in line for x in ['香港', '澳门', '台湾']):
            categories['港澳台'].append(line)
        elif any(x in line for x in ['北京', '上海', '广东']):  # 添加更多地方台关键词
            categories['地方'].append(line)
        else:
            categories['其他'].append(line)
    
    return categories

def remove_duplicates(lines: List[str]) -> List[str]:
    seen_urls = set()
    unique_lines = []
    
    for line in lines:
        if line.startswith('http'):
            url = line.split()[0]
            if url not in seen_urls:
                seen_urls.add(url)
                unique_lines.append(line)
        else:
            unique_lines.append(line)
    
    return unique_lines

def backup_sources(valid_lines: List[str]):
    # 创建备份目录
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'live_ipv4_{timestamp}.txt')
    
    # 保存备份
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(valid_lines))
    
    # 只保留最近7天的备份
    backup_files = sorted(glob.glob(os.path.join(backup_dir, 'live_ipv4_*.txt')))
    if len(backup_files) > 7:
        for old_file in backup_files[:-7]:
            os.remove(old_file)

def generate_stats(valid_lines: List[str]) -> dict:
    stats = {
        'total_sources': len(valid_lines),
        'categories': {},
        'quality_distribution': {
            'HD': 0,
            'SD': 0,
            'Unknown': 0
        }
    }
    
    # 统计分类
    categories = categorize_streams(valid_lines)
    for category, items in categories.items():
        stats['categories'][category] = len(items)
    
    return stats

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
        'https://live.fanmingming.com/tv/m3u/ipv6.m3u',
        'https://aktv.top/live.m3u',
        'http://aktv.top/live.txt'
    ]
    
    asyncio.run(process_urls(urls))