import requests
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
import time
from collections import defaultdict
import os

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_url_validity(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.head(url, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logging.error(f"URL {url} failed after {max_retries} attempts: {e}")
                return False
            time.sleep(1)  # 重试前等待

def fetch_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content.decode('utf-8-sig')
    except:
        return None

def filter_content(content):
    if content is None:
        return []
    keywords = ["㊙VIP测试", "关注公众号", "天微科技", "获取测试密码", "更新时间", "♥聚玩盒子", "🌹防失联","📡  更新日期","👉",]
    return [line for line in content.splitlines() if 'ipv6' not in line.lower() and not any(keyword in line for keyword in keywords)]

def check_stream_quality(url):
    """检查流的质量并返回一个质量分数"""
    try:
        command = ['ffmpeg', '-i', url, '-t', '10', '-f', 'null', '-']
        start_time = time.time()
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        duration = time.time() - start_time
        
        if result.returncode == 0:
            # 基础分数 100
            score = 100
            # 响应时间越短越好，每超过1秒扣1分，最多扣20分
            score -= min(20, int(duration))
            # 检查ffmpeg输出中的错误和警告数量
            stderr = result.stderr.decode('utf-8')
            errors = stderr.count('Error') * 5  # 每个错误扣5分
            warnings = stderr.count('Warning') * 2  # 每个警告扣2分
            score -= (errors + warnings)
            return max(0, score)  # 确保分数不小于0
        return 0
    except:
        return 0

def fetch_and_filter(urls):
    filtered_lines = []
    
    # 调整URL获取的并发数，设置为CPU核心数的2倍
    max_fetch_workers = min(32, os.cpu_count() * 2 or 4)
    with ThreadPoolExecutor(max_workers=max_fetch_workers) as executor:
        valid_urls = [url for url in urls if check_url_validity(url)]
        results = list(executor.map(fetch_content, valid_urls))
    
    for content in results:
        filtered_lines.extend(filter_content(content))
    
    # 用于存储按频道分组的URL
    channel_groups = defaultdict(list)
    current_genre = None
    
    # 首先按频道分组
    for line in filtered_lines:
        if line.startswith('#genre#'):
            current_genre = line
            channel_groups[current_genre].append(line)
        elif line.startswith('http'):
            if current_genre:
                url_parts = line.split(',', 1)
                if len(url_parts) == 2:
                    url, channel_name = url_parts
                    channel_groups[channel_name].append(line)
        else:
            if current_genre:
                channel_groups[current_genre].append(line)
    
    # 调整流媒体质量检测的并发数
    # 流媒体检测比较耗资源，所以设置较小的并发数
    max_stream_workers = min(5, os.cpu_count() or 2)
    valid_lines = []
    with ThreadPoolExecutor(max_workers=max_stream_workers) as executor:
        for channel, urls in channel_groups.items():
            if channel.startswith('#genre#'):
                valid_lines.extend(urls)
                continue
            
            # 批量提交检测任务，但控制同时运行的任务数
            url_scores = []
            batch_size = max_stream_workers  # 每批处理的URL数量
            
            for i in range(0, len(urls), batch_size):
                batch_urls = urls[i:i + batch_size]
                batch_scores = []
                
                for url_line in batch_urls:
                    if url_line.startswith('http'):
                        url = url_line.split(',')[0]
                        score = executor.submit(check_stream_quality, url)
                        batch_scores.append((url_line, score))
                
                # 等待当前批次完成
                for url_line, score in batch_scores:
                    try:
                        quality_score = score.result(timeout=30)  # 设置超时时间
                        if quality_score > 0:
                            url_scores.append((url_line, quality_score))
                    except Exception as e:
                        logging.error(f"Error checking quality for {url_line}: {e}")
            
            # 对当前频道的所有URL进行排序
            sorted_urls = sorted(url_scores, key=lambda x: x[1], reverse=True)
            valid_lines.extend(url_line for url_line, score in sorted_urls)
    
    # 保存结果
    with open('live_ipv4.txt', 'w', encoding='utf-8') as file:
        file.write('\n'.join(valid_lines))
    logging.info("Filtered and sorted content saved to live_ipv4.txt")

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
    fetch_and_filter(urls)