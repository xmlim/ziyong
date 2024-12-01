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
    lines = []
    current_category = None
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
            
        # 处理分类标记
        if ',' in line and line.endswith('#genre#'):
            current_category = line
            lines.append(line)
            continue
            
        # 处理URL行
        if line.startswith('http'):
            if ',' in line:  # 如果URL行包含频道名
                url, name = line.split(',', 1)
                if current_category and not any(keyword in line for keyword in keywords):
                    lines.append(f"{url},{name}")
            else:  # 如果URL行没有频道名
                if current_category and not any(keyword in line for keyword in keywords):
                    lines.append(f"{line},未命名频道")
        else:
            # 保留其他非URL的描述性文本
            if not any(keyword in line for keyword in keywords):
                lines.append(line)
                
    return lines

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
    
    # 调整URL获取的并发数
    max_fetch_workers = min(32, os.cpu_count() * 2 or 4)
    with ThreadPoolExecutor(max_workers=max_fetch_workers) as executor:
        valid_urls = [url for url in urls if check_url_validity(url)]
        results = list(executor.map(fetch_content, valid_urls))
    
    for content in results:
        filtered_lines.extend(filter_content(content))
    
    # 用于存储按频道分组的URL
    channel_groups = defaultdict(list)
    current_category = None
    
    # 按频道分组
    for line in filtered_lines:
        if line.endswith('#genre#'):
            current_category = line
            channel_groups[current_category] = [line]
        elif current_category:
            channel_groups[current_category].append(line)
    
    # 调整流媒体质量检测的并发数
    max_stream_workers = min(5, os.cpu_count() or 2)
    final_lines = []
    
    with ThreadPoolExecutor(max_workers=max_stream_workers) as executor:
        for category, items in channel_groups.items():
            # 添加分类标记
            final_lines.append(category)
            
            # 收集当前分类下的URL
            url_scores = []
            for item in items:
                if item.startswith('http'):
                    url = item.split(',')[0]
                    try:
                        score = executor.submit(check_stream_quality, url)
                        url_scores.append((item, score))
                    except Exception as e:
                        logging.error(f"Error checking {url}: {e}")
            
            # 等待质量检测完成并排序
            valid_urls = []
            for item, score in url_scores:
                try:
                    quality = score.result(timeout=30)
                    if quality > 0:
                        valid_urls.append((item, quality))
                except Exception as e:
                    logging.error(f"Error getting result for {item}: {e}")
            
            # 按质量排序并添加到结果中
            sorted_urls = sorted(valid_urls, key=lambda x: x[1], reverse=True)
            final_lines.extend(url for url, _ in sorted_urls)
    
    # 保存结果
    if final_lines:
        with open('live_ipv4.txt', 'w', encoding='utf-8') as file:
            file.write('\n'.join(final_lines))
        logging.info(f"成功写入 {len(final_lines)} 行")
    else:
        logging.warning("没有找到有效的直播源")

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