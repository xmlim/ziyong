import re
import requests
import logging
from collections import OrderedDict
from datetime import datetime
import config
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import asyncio
from aiohttp import ClientTimeout
from functools import partial

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler("function.log", "w", encoding="utf-8"), logging.StreamHandler()])

def parse_template(template_file):
    template_channels = OrderedDict()
    current_category = None

    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    template_channels[current_category] = []
                elif current_category:
                    channel_name = line.split(",")[0].strip()
                    template_channels[current_category].append(channel_name)

    return template_channels

def fetch_channels(url):
    channels = OrderedDict()

    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8'
        lines = response.text.split("\n")
        current_category = None
        is_m3u = any("#EXTINF" in line for line in lines[:15])
        source_type = "m3u" if is_m3u else "txt"
        logging.info(f"url: {url} 获取成功，判断为{source_type}格式")

        if is_m3u:
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    match = re.search(r'group-title="(.*?)",(.*)', line)
                    if match:
                        current_category = match.group(1).strip()
                        channel_name = match.group(2).strip()
                        if current_category not in channels:
                            channels[current_category] = []
                elif line and not line.startswith("#"):
                    channel_url = line.strip()
                    if current_category and channel_name:
                        channels[current_category].append((channel_name, channel_url))
        else:
            for line in lines:
                line = line.strip()
                if "#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    channels[current_category] = []
                elif current_category:
                    match = re.match(r"^(.*?),(.*?)$", line)
                    if match:
                        channel_name = match.group(1).strip()
                        channel_url = match.group(2).strip()
                        channels[current_category].append((channel_name, channel_url))
                    elif line:
                        channels[current_category].append((line, ''))
        if channels:
            categories = ", ".join(channels.keys())
            logging.info(f"url: {url} 爬取成功✅，包含频道分类: {categories}")
    except requests.RequestException as e:
        logging.error(f"url: {url} 爬取失败❌, Error: {e}")

    return channels

def match_channels(template_channels, all_channels):
    matched_channels = OrderedDict()

    for category, channel_list in template_channels.items():
        matched_channels[category] = OrderedDict()
        for channel_name in channel_list:
            for online_category, online_channel_list in all_channels.items():
                for online_channel_name, online_channel_url in online_channel_list:
                    if channel_name == online_channel_name:
                        matched_channels[category].setdefault(channel_name, []).append(online_channel_url)

    return matched_channels

def filter_source_urls(template_file):
    template_channels = parse_template(template_file)
    source_urls = config.source_urls

    all_channels = OrderedDict()
    for url in source_urls:
        fetched_channels = fetch_channels(url)
        for category, channel_list in fetched_channels.items():
            if category in all_channels:
                all_channels[category].extend(channel_list)
            else:
                all_channels[category] = channel_list

    matched_channels = match_channels(template_channels, all_channels)

    return matched_channels, template_channels

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def updateChannelUrlsM3U(channels, template_channels):
    written_urls = set()
    written_urls_ipv6 = set()

    current_date = datetime.now().strftime("%Y-%m-%d")
    for group in config.announcements:
        for announcement in group['entries']:
            if announcement['name'] is None:
                announcement['name'] = current_date

    with open("live.m3u", "w", encoding="utf-8") as f_m3u, \
         open("live.txt", "w", encoding="utf-8") as f_txt, \
         open("live_ipv6.m3u", "w", encoding="utf-8") as f_m3u_ipv6, \
         open("live_ipv6.txt", "w", encoding="utf-8") as f_txt_ipv6:
        
        m3u_header = f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n"""
        f_m3u.write(m3u_header)
        f_m3u_ipv6.write(m3u_header)

        for group in config.announcements:
            f_txt.write(f"{group['channel']},#genre#\n")
            f_txt_ipv6.write(f"{group['channel']},#genre#\n")
            for announcement in group['entries']:
                announcement_line = f"""#EXTINF:-1 tvg-id="1" tvg-name="{announcement['name']}" tvg-logo="{announcement['logo']}" group-title="{group['channel']}",{announcement['name']}\n"""
                f_m3u.write(announcement_line)
                f_m3u.write(f"{announcement['url']}\n")
                f_m3u_ipv6.write(announcement_line)
                f_m3u_ipv6.write(f"{announcement['url']}\n")
                f_txt.write(f"{announcement['name']},{announcement['url']}\n")
                f_txt_ipv6.write(f"{announcement['name']},{announcement['url']}\n")

        for category, channel_list in template_channels.items():
            f_txt.write(f"{category},#genre#\n")
            f_txt_ipv6.write(f"{category},#genre#\n")
            
            if category in channels:
                for channel_name in channel_list:
                    if channel_name in channels[category]:
                        urls = channels[category][channel_name]
                        
                        ipv4_urls = [url for url in urls if not is_ipv6(url) and not any(blacklist in url for blacklist in config.url_blacklist)]
                        ipv6_urls = [url for url in urls if is_ipv6(url) and not any(blacklist in url for blacklist in config.url_blacklist)]
                        
                        for index, url in enumerate(ipv4_urls[:10], start=1):
                            if url not in written_urls:
                                written_urls.add(url)
                                url_suffix = f"$LR•IPV4" if len(ipv4_urls) == 1 else f"$LR•IPV4『线路{index}』"
                                new_url = f"{url}{url_suffix}"
                                
                                f_m3u.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/{channel_name}.png\" group-title=\"{category}\",{channel_name}\n")
                                f_m3u.write(new_url + "\n")
                                f_txt.write(f"{channel_name},{new_url}\n")
                        
                        for index, url in enumerate(ipv6_urls[:10], start=1):
                            if url not in written_urls_ipv6:
                                written_urls_ipv6.add(url)
                                url_suffix = f"$LR•IPV6" if len(ipv6_urls) == 1 else f"$LR•IPV6『线路{index}』"
                                new_url = f"{url}{url_suffix}"
                                
                                f_m3u_ipv6.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/{channel_name}.png\" group-title=\"{category}\",{channel_name}\n")
                                f_m3u_ipv6.write(new_url + "\n")
                                f_txt_ipv6.write(f"{channel_name},{new_url}\n")

        f_txt.write("\n")
        f_txt_ipv6.write("\n")

async def check_link_quality(session, link):
    timeout = ClientTimeout(total=2)  # 设置2秒超时
    try:
        start_time = time.time()
        async with session.head(link, timeout=timeout, allow_redirects=True) as response:
            response_time = time.time() - start_time
            if response.status == 200:
                return response_time
            return float('inf')
    except:
        return float('inf')

async def check_links_batch(urls):
    conn = aiohttp.TCPConnector(limit=100)  # 允许100个并发连接
    timeout = ClientTimeout(total=2)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        tasks = [check_link_quality(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

def process_channel_links(channel_links):
    sorted_channels = {}
    
    for category, channel_dict in channel_links.items():
        sorted_channels[category] = OrderedDict()
        
        for channel_name, urls in channel_dict.items():
            if urls:
                # 运行异步检查
                results = asyncio.run(check_links_batch(urls))
                
                # 将结果和URL配对并排序
                url_qualities = list(zip(urls, results))
                sorted_urls = [url for url, _ in sorted(url_qualities, key=lambda x: float('inf') if isinstance(x[1], Exception) else x[1])]
                sorted_channels[category][channel_name] = sorted_urls
            else:
                sorted_channels[category][channel_name] = []
    
    return sorted_channels

if __name__ == "__main__":
    template_file = "demo.txt"
    channels, template_channels = filter_source_urls(template_file)
    sorted_channels = process_channel_links(channels)
    updateChannelUrlsM3U(sorted_channels, template_channels)