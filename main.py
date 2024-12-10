import re
import requests
import logging
from collections import OrderedDict
from datetime import datetime
import config
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler("function.log", "w", encoding="utf-8"), logging.StreamHandler()])

def parse_template(template_file):
    template_channels = OrderedDict()
    current_category = None
    
    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            if "#genre#" in line:
                current_category = line.split(",")[0].strip()
                template_channels[current_category] = []
            elif current_category and ',' not in line:  # 修改这里，处理没有逗号的频道名称行
                channel_name = line.strip()
                if channel_name:  # 确保不是空行
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
            matched_urls = []
            for online_category, online_channel_list in all_channels.items():
                for online_channel_name, online_channel_url in online_channel_list:
                    if channel_name == online_channel_name:
                        matched_urls.append(online_channel_url)
            if matched_urls:  # 只有当找到匹配的URL时才添加到结果中
                matched_channels[category][channel_name] = matched_urls
    
    return matched_channels

def filter_source_urls(template_file):
    template_channels = parse_template(template_file)
    source_urls = config.source_urls
    
    all_channels = OrderedDict()
    for url in source_urls:
        try:
            fetched_channels = fetch_channels(url)
            for category, channel_list in fetched_channels.items():
                if category in all_channels:
                    all_channels[category].extend(channel_list)
                else:
                    all_channels[category] = channel_list
        except Exception as e:
            logging.error(f"处理源URL出错 {url}: {str(e)}")
    
    matched_channels = match_channels(template_channels, all_channels)
    
    # 打印调试信息
    for category, channels in matched_channels.items():
        logging.info(f"分类 {category} 包含 {len(channels)} 个频道")
        for channel, urls in channels.items():
            logging.info(f"  频道 {channel} 有 {len(urls)} 个链接")
    
    return matched_channels, template_channels

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def updateChannelUrlsM3U(channels, template_channels):
    try:
        written_urls = set()
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        logging.info("开始更新频道列表...")
        
        # 读取原始的demo.txt内容，保留频道分类结构
        with open('demo.txt', 'r', encoding='utf-8') as f:
            original_content = f.read()
            original_lines = original_content.split('\n')
        
        # 提取所有分类标题
        categories = []
        for line in original_lines:
            if line.strip().endswith('#genre#'):
                categories.append(line.strip())
        
        # 处理公告
        for group in config.announcements:
            for announcement in group['entries']:
                if announcement['name'] is None:
                    announcement['name'] = current_date
        
        # 打开文件
        with open("live.m3u", "w", encoding="utf-8") as f_m3u, \
             open("live.txt", "w", encoding="utf-8") as f_txt:
            
            # 写入M3U头部
            f_m3u.write(f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n""")
            
            # 处理公告
            for group in config.announcements:
                logging.info(f"处理分类: {group['channel']}")
                f_txt.write(f"{group['channel']},#genre#\n")
                for announcement in group['entries']:
                    f_m3u.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{announcement['name']}" tvg-logo="{announcement['logo']}" group-title="{group['channel']}",{announcement['name']}\n""")
                    f_m3u.write(f"{announcement['url']}\n")
                    f_txt.write(f"{announcement['name']},{announcement['url']}\n")
            
            # 按原始分类顺序处理频道
            current_category = None
            current_channels = []
            
            for line in original_lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.endswith('#genre#'):
                    # 写入前一个分类的内容
                    if current_category and current_channels:
                        for channel_name in current_channels:
                            if current_category in channels and channel_name in channels[current_category]:
                                try:
                                    # 获取并过滤URL
                                    channel_urls = channels[current_category][channel_name]
                                    filtered_urls = []
                                    for url in channel_urls:
                                        if url and url not in written_urls and not any(blacklist in url for blacklist in config.url_blacklist):
                                            filtered_urls.append(url)
                                            written_urls.add(url)
                                    
                                    # 使用新的筛选功能选择最佳链接
                                    filtered_urls = filter_best_urls(channel_name, filtered_urls)
                                    
                                    # 写入链接
                                    total_urls = len(filtered_urls)
                                    for index, url in enumerate(filtered_urls, start=1):
                                        if is_ipv6(url):
                                            url_suffix = f"$LR•IPV6" if total_urls == 1 else f"$LR•IPV6『线路{index}』"
                                        else:
                                            url_suffix = f"$LR•IPV4" if total_urls == 1 else f"$LR•IPV4『线路{index}』"
                                        
                                        base_url = url.split('$', 1)[0] if '$' in url else url
                                        new_url = f"{base_url}{url_suffix}"
                                        
                                        f_m3u.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/{channel_name}.png\" group-title=\"{current_category}\",{channel_name}\n")
                                        f_m3u.write(new_url + "\n")
                                        f_txt.write(f"{channel_name},{new_url}\n")
                                except Exception as e:
                                    logging.error(f"处理频道出错: {channel_name}: {str(e)}")
                    
                    # 开始新分类
                    current_category = line.split(',')[0].strip()
                    current_channels = []
                    f_txt.write(f"{line}\n")
                elif ',' not in line:
                    # 这是一个频道名称
                    current_channels.append(line.strip())
            
            # 处理最后一个分类
            if current_category and current_channels:
                for channel_name in current_channels:
                    if current_category in channels and channel_name in channels[current_category]:
                        try:
                            channel_urls = channels[current_category][channel_name]
                            filtered_urls = []
                            for url in channel_urls:
                                if url and url not in written_urls and not any(blacklist in url for blacklist in config.url_blacklist):
                                    filtered_urls.append(url)
                                    written_urls.add(url)
                            
                            filtered_urls = filter_best_urls(channel_name, filtered_urls)
                            
                            total_urls = len(filtered_urls)
                            for index, url in enumerate(filtered_urls, start=1):
                                if is_ipv6(url):
                                    url_suffix = f"$LR•IPV6" if total_urls == 1 else f"$LR•IPV6『线路{index}』"
                                else:
                                    url_suffix = f"$LR•IPV4" if total_urls == 1 else f"$LR•IPV4『线路{index}』"
                                
                                base_url = url.split('$', 1)[0] if '$' in url else url
                                new_url = f"{base_url}{url_suffix}"
                                
                                f_m3u.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/{channel_name}.png\" group-title=\"{current_category}\",{channel_name}\n")
                                f_m3u.write(new_url + "\n")
                                f_txt.write(f"{channel_name},{new_url}\n")
                        except Exception as e:
                            logging.error(f"处理频道出错: {channel_name}: {str(e)}")
        
        logging.info("频道列表更新完成")
        
    except Exception as e:
        logging.error(f"更新频道列表时出错: {str(e)}")
        raise

def score_url(url: str) -> int:
    """
    对URL进行质量评分
    """
    score = 0
    url_lower = url.lower()
    
    # 根据关键词评分
    for keyword, points in config.QUALITY_KEYWORDS.items():
        if keyword in url_lower:
            score += points
    
    # 额外的评分规则
    if 'http' in url_lower:  # 有效的URL
        score += 10
    if '.m3u8' in url_lower:  # m3u8格式通常更稳定
        score += 5
    
    return score

def filter_best_urls(channel_name: str, urls: List[str]) -> List[str]:
    """
    筛选最佳的URL链接
    """
    if not urls:
        return []
    
    # 如果链接数量小于等于最大保留数，直接返回
    if len(urls) <= config.MAX_LINKS:
        return urls
    
    # 对URLs进行评分并排序
    scored_urls: List[Tuple[int, str]] = [(score_url(url), url) for url in urls]
    scored_urls.sort(reverse=True)  # 按分数从高到低排序
    
    # 只保留分数最高的MAX_LINKS个链接
    best_urls = [url for score, url in scored_urls[:config.MAX_LINKS]]
    
    return best_urls

def process_channel_content(content: str) -> str:
    """
    处理频道内容，对多链接进行筛选
    """
    lines = content.split('\n')
    processed_lines = []
    current_channel = None
    current_urls = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.endswith('#genre#'):  # 分类行
            processed_lines.append(line)
        elif ',' not in line:  # 频道名称行
            # 处理前一个频道的URLs
            if current_channel and current_urls:
                best_urls = filter_best_urls(current_channel, current_urls)
                for url in best_urls:
                    processed_lines.append(f"{current_channel},{url}")
            
            current_channel = line
            current_urls = []
        else:  # URL行
            channel, url = line.split(',', 1)
            if channel == current_channel:
                current_urls.append(url)
            else:
                # 处理新频道
                if current_channel and current_urls:
                    best_urls = filter_best_urls(current_channel, current_urls)
                    for url in best_urls:
                        processed_lines.append(f"{current_channel},{url}")
                current_channel = channel
                current_urls = [url]
    
    # 处理最后一个频道
    if current_channel and current_urls:
        best_urls = filter_best_urls(current_channel, current_urls)
        for url in best_urls:
            processed_lines.append(f"{current_channel},{url}")
    
    return '\n'.join(processed_lines)

def main():
    try:
        # 读取原始文件
        with open('demo.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 处理内容
        processed_content = process_channel_content(content)
        
        # 写入处理后的内容
        with open('demo.txt', 'w', encoding='utf-8') as f:
            f.write(processed_content)
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    try:
        logging.info("开始执行程序...")
        template_file = "demo.txt"
        
        logging.info("获取频道列表...")
        channels, template_channels = filter_source_urls(template_file)
        
        logging.info("更新频道列表...")
        updateChannelUrlsM3U(channels, template_channels)
        
        logging.info("程序执行完成")
    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}")
        raise
