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
from aiohttp import ClientTimeout, TCPConnector
import os
from urllib.parse import urlparse
import backoff

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("function.log", "w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IPTV_Processor")

class IPTVProcessor:
    def __init__(self, template_file="demo.txt"):
        self.template_file = template_file
        self.session = None
        self.timeout = getattr(config, 'request_timeout', 10)
        self.max_workers = getattr(config, 'max_workers', 50)
        self.link_check_timeout = getattr(config, 'performance_config', {}).get('link_check_timeout', 3)
        self.max_concurrent_checks = getattr(config, 'performance_config', {}).get('max_concurrent_checks', 50)
        self.skip_check_patterns = getattr(config, 'skip_check_patterns', [])
        
    async def __aenter__(self):
        await self.setup_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
        
    async def setup_session(self):
        """创建aiohttp会话"""
        connector = TCPConnector(limit=self.max_workers, limit_per_host=10)
        timeout = ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
    async def close_session(self):
        """关闭会话"""
        if self.session:
            await self.session.close()

    def parse_template(self, template_file):
        """解析模板文件"""
        template_channels = OrderedDict()
        current_category = None

        try:
            with open(template_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                        
                    if "#genre#" in line:
                        current_category = line.split(",")[0].strip()
                        template_channels[current_category] = []
                        logger.info(f"找到分类: {current_category}")
                    elif current_category:
                        channel_name = line.split(",")[0].strip()
                        if channel_name:  # 确保频道名不为空
                            template_channels[current_category].append(channel_name)
                            
            logger.info(f"模板解析完成，共 {len(template_channels)} 个分类")
            return template_channels
            
        except Exception as e:
            logger.error(f"解析模板文件失败: {e}")
            raise

    @backoff.on_exception(backoff.expo, (requests.RequestException,), max_tries=3)
    def fetch_channels(self, url):
        """获取频道数据，支持重试机制和无group-title的M3U格式"""
        channels = OrderedDict()

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            lines = response.text.split("\n")
            
            is_m3u = any("#EXTINF" in line for line in lines[:10])
            source_type = "m3u" if is_m3u else "txt"
            logger.info(f"URL: {url} 获取成功，格式: {source_type}")

            current_category = "默认分类"  # 为无分类的频道设置默认分类
            channel_name = None

            if is_m3u:
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith("#EXTINF"):
                        # 尝试多种格式的解析
                        match = re.search(r'group-title="([^"]*)"\s*,\s*(.+)', line)
                        if match:
                            # 标准格式：有group-title
                            current_category = match.group(1).strip() or "未分类"
                            channel_name = match.group(2).strip()
                            logger.debug(f"找到标准格式频道: {channel_name}, 分类: {current_category}")
                        else:
                            # 无group-title格式：直接提取频道名
                            match_simple = re.search(r'#EXTINF:.*?,(.+)', line)
                            if match_simple:
                                channel_name = match_simple.group(1).strip()
                                current_category = "默认分类"  # 使用默认分类
                                logger.debug(f"找到简单格式频道: {channel_name}, 分类: {current_category}")
                            else:
                                # 备用解析方式
                                current_category = "默认分类"
                                channel_name = line.split(',')[-1].strip() if ',' in line else f"频道_{i}"
                                logger.debug(f"使用备用解析频道: {channel_name}, 分类: {current_category}")
                        
                        if current_category not in channels:
                            channels[current_category] = []
                            
                    elif line and not line.startswith("#") and channel_name:
                        channel_url = line.strip()
                        if channel_url.startswith(('http://', 'https://')):
                            channels[current_category].append((channel_name, channel_url))
                            logger.debug(f"添加频道: {channel_name}, URL: {channel_url}")
                            channel_name = None  # 重置频道名
            else:
                # TXT格式处理 - 修复bug
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if "#genre#" in line:
                        current_category = line.split(",")[0].strip()
                        # 确保分类在channels字典中
                        if current_category not in channels:
                            channels[current_category] = []
                        logger.debug(f"找到分类: {current_category}")
                    elif current_category:  # 确保有当前分类
                        if ',' in line:
                            parts = line.split(',', 1)
                            if len(parts) == 2:
                                channel_name = parts[0].strip()
                                channel_url = parts[1].strip()
                                if channel_url.startswith(('http://', 'https://')):
                                    # 确保分类存在
                                    if current_category not in channels:
                                        channels[current_category] = []
                                    channels[current_category].append((channel_name, channel_url))
                                    logger.debug(f"添加频道到分类 {current_category}: {channel_name}")
                        else:
                            # 处理没有URL的情况
                            channel_name = line.strip()
                            if channel_name:
                                if current_category not in channels:
                                    channels[current_category] = []
                                channels[current_category].append((channel_name, ''))
                                logger.debug(f"添加无URL频道到分类 {current_category}: {channel_name}")

            if channels:
                total_channels = sum(len(channel_list) for channel_list in channels.values())
                categories = list(channels.keys())
                logger.info(f"URL: {url} 处理完成，分类数: {len(categories)}, 频道总数: {total_channels}")
            else:
                logger.warning(f"URL: {url} 未找到有效频道")
                
            return channels

        except requests.RequestException as e:
            logger.error(f"URL: {url} 获取失败: {e}")
            return OrderedDict()

    def match_channels(self, template_channels, all_channels):
        """匹配模板频道和在线频道"""
        matched_channels = OrderedDict()
        match_count = 0

        for category, channel_list in template_channels.items():
            matched_channels[category] = OrderedDict()
            
            for channel_name in channel_list:
                found = False
                for online_category, online_channel_list in all_channels.items():
                    for online_channel_name, online_channel_url in online_channel_list:
                        # 使用更宽松的匹配方式
                        if self.is_channel_match(channel_name, online_channel_name):
                            if channel_name not in matched_channels[category]:
                                matched_channels[category][channel_name] = []
                            matched_channels[category][channel_name].append(online_channel_url)
                            found = True
                            match_count += 1
                
                if not found:
                    logger.debug(f"未找到匹配频道: {channel_name}")
                    matched_channels[category][channel_name] = []

        logger.info(f"频道匹配完成，共匹配 {match_count} 个频道")
        return matched_channels

    def is_channel_match(self, template_name, online_name):
        """判断频道是否匹配"""
        # 精确匹配
        if template_name == online_name:
            return True
            
        # 清理名称后进行匹配
        clean_template = self.clean_channel_name(template_name)
        clean_online = self.clean_channel_name(online_name)
        
        return clean_template == clean_online

    def clean_channel_name(self, name):
        """清理频道名称"""
        # 移除常见的修饰词
        patterns = [
            r'★\s*', r'☆\s*', r'●\s*', r'○\s*', r'◆\s*', r'◇\s*',
            r'\[\d+\]', r'【\d+】', r'\(.*?\)', r'\[.*?\]', r'（.*?）', r'【.*?】'
        ]
        cleaned = name
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned)
        return cleaned.strip()

    def filter_source_urls(self):
        """过滤源URL"""
        template_channels = self.parse_template(self.template_file)
        source_urls = getattr(config, 'source_urls', [])
        
        if not source_urls:
            logger.error("未找到源URL配置")
            return OrderedDict(), template_channels

        all_channels = OrderedDict()
        
        # 使用线程池并行获取
        with ThreadPoolExecutor(max_workers=min(10, len(source_urls))) as executor:
            futures = {executor.submit(self.fetch_channels, url): url for url in source_urls}
            
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    fetched_channels = future.result()
                    for category, channel_list in fetched_channels.items():
                        if category in all_channels:
                            all_channels[category].extend(channel_list)
                        else:
                            all_channels[category] = channel_list
                except Exception as e:
                    logger.error(f"处理URL {url} 时出错: {e}")

        matched_channels = self.match_channels(template_channels, all_channels)
        return matched_channels, template_channels

    def is_ipv6(self, url):
        """判断是否为IPv6地址"""
        return re.match(r'^https?://\[[0-9a-fA-F:]+\]', url) is not None

    def is_url_blacklisted(self, url):
        """检查URL是否在黑名单中"""
        blacklist = getattr(config, 'url_blacklist', [])
        return any(blacklisted in url for blacklisted in blacklist)
    
    def should_skip_check(self, url):
        """检查是否应该跳过链接检查"""
        return any(pattern in url for pattern in self.skip_check_patterns)

    async def check_link_quality(self, url):
        """检查链接质量 - 优化版本"""
        if not self.session:
            await self.setup_session()
        
        # 跳过已知稳定的源
        if self.should_skip_check(url):
            return 0.1  # 返回一个很小的响应时间，表示稳定
        
        # 减少超时时间
        timeout = ClientTimeout(total=self.link_check_timeout)
        
        try:
            start_time = time.time()
            # 使用更快的检查方法，只等待状态码
            async with self.session.get(url, timeout=timeout, allow_redirects=True) as response:
                # 只读取前几个字节来确认连接
                await response.content.read(1024)
                response_time = time.time() - start_time
                
                if response.status == 200:
                    return response_time
                return float('inf')
        except asyncio.TimeoutError:
            logger.debug(f"链接检查超时: {url}")
            return float('inf')
        except Exception as e:
            logger.debug(f"链接检查失败 {url}: {e}")
            return float('inf')

    async def check_links_batch(self, urls):
        """批量检查链接质量 - 优化版本"""
        if not urls:
            return []
        
        # 限制并发数量，避免过多请求
        semaphore = asyncio.Semaphore(self.max_concurrent_checks)
        
        async def bounded_check(url):
            async with semaphore:
                return await self.check_link_quality(url)
        
        tasks = [bounded_check(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(float('inf'))
            else:
                processed_results.append(result)
                
        return processed_results

    async def process_channel_links(self, channel_links):
        """处理频道链接并排序"""
        sorted_channels = OrderedDict()
        total_channels = sum(len(channels) for channels in channel_links.values())
        processed = 0

        for category, channel_dict in channel_links.items():
            sorted_channels[category] = OrderedDict()
            
            for channel_name, urls in channel_dict.items():
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"处理进度: {processed}/{total_channels}")
                    
                if urls:
                    # 过滤黑名单URL
                    filtered_urls = [url for url in urls if not self.is_url_blacklisted(url)]
                    
                    if filtered_urls:
                        results = await self.check_links_batch(filtered_urls)
                        
                        # 配对URL和质量结果并排序
                        url_qualities = list(zip(filtered_urls, results))
                        sorted_urls = [
                            url for url, quality in sorted(
                                url_qualities, 
                                key=lambda x: x[1] if x[1] != float('inf') else float('inf')
                            )
                        ]
                        sorted_channels[category][channel_name] = sorted_urls
                    else:
                        sorted_channels[category][channel_name] = []
                else:
                    sorted_channels[category][channel_name] = []
                    
        logger.info("频道链接处理完成")
        return sorted_channels

    def update_channel_urls_m3u(self, channels, template_channels):
        """更新频道URL到M3U和TXT文件"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # 更新公告日期
            announcements = getattr(config, 'announcements', [])
            for group in announcements:
                for announcement in group.get('entries', []):
                    if announcement.get('name') is None:
                        announcement['name'] = current_date

            # 创建输出目录
            output_dir = getattr(config, 'output_config', {}).get('output_dir', 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取输出文件配置
            output_files = getattr(config, 'output_config', {}).get('files', {})
            ipv4_files = output_files.get('ipv4', {})
            ipv6_files = output_files.get('ipv6', {})
            
            m3u_file = os.path.join(output_dir, ipv4_files.get('m3u', 'live.m3u'))
            txt_file = os.path.join(output_dir, ipv4_files.get('txt', 'live.txt'))
            m3u_ipv6_file = os.path.join(output_dir, ipv6_files.get('m3u', 'live_ipv6.m3u'))
            txt_ipv6_file = os.path.join(output_dir, ipv6_files.get('txt', 'live_ipv6.txt'))
            
            with open(m3u_file, "w", encoding="utf-8") as f_m3u, \
                 open(txt_file, "w", encoding="utf-8") as f_txt, \
                 open(m3u_ipv6_file, "w", encoding="utf-8") as f_m3u_ipv6, \
                 open(txt_ipv6_file, "w", encoding="utf-8") as f_txt_ipv6:
                
                # 写入M3U头
                epg_urls = getattr(config, 'epg_urls', [])
                m3u_header = f"""#EXTM3U x-tvg-url="{','.join(epg_urls)}"\n"""
                f_m3u.write(m3u_header)
                f_m3u_ipv6.write(m3u_header)

                # 写入公告频道
                for group in announcements:
                    group_title = group.get('channel', '公告')
                    f_txt.write(f"{group_title},#genre#\n")
                    f_txt_ipv6.write(f"{group_title},#genre#\n")
                    
                    for announcement in group.get('entries', []):
                        name = announcement.get('name', '')
                        logo = announcement.get('logo', '')
                        url = announcement.get('url', '')
                        
                        announcement_line = f"""#EXTINF:-1 tvg-id="1" tvg-name="{name}" tvg-logo="{logo}" group-title="{group_title}",{name}\n"""
                        f_m3u.write(announcement_line)
                        f_m3u.write(f"{url}\n")
                        f_m3u_ipv6.write(announcement_line)
                        f_m3u_ipv6.write(f"{url}\n")
                        f_txt.write(f"{name},{url}\n")
                        f_txt_ipv6.write(f"{name},{url}\n")

                # 写入频道数据
                written_channels = set()  # 跟踪已写入的频道
                
                for category, channel_list in template_channels.items():
                    f_txt.write(f"{category},#genre#\n")
                    f_txt_ipv6.write(f"{category},#genre#\n")
                    
                    if category in channels:
                        for channel_name in channel_list:
                            if channel_name in channels[category] and channel_name not in written_channels:
                                urls = channels[category][channel_name]
                                
                                # 分离IPv4和IPv6
                                ipv4_urls = [url for url in urls if not self.is_ipv6(url)]
                                ipv6_urls = [url for url in urls if self.is_ipv6(url)]
                                
                                # 写入IPv4
                                for index, url in enumerate(ipv4_urls[:10], start=1):
                                    url_suffix = "$LR•IPV4" if len(ipv4_urls) == 1 else f"$LR•IPV4『线路{index}』"
                                    new_url = f"{url}{url_suffix}"
                                    logo_url = getattr(config, 'logo_base_url', 'https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/') + f"{channel_name}.png"
                                    
                                    f_m3u.write(f'#EXTINF:-1 tvg-id="{index}" tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{category}",{channel_name}\n')
                                    f_m3u.write(new_url + "\n")
                                    f_txt.write(f"{channel_name},{new_url}\n")
                                
                                # 写入IPv6
                                for index, url in enumerate(ipv6_urls[:10], start=1):
                                    url_suffix = "$LR•IPV6" if len(ipv6_urls) == 1 else f"$LR•IPV6『线路{index}』"
                                    new_url = f"{url}{url_suffix}"
                                    logo_url = getattr(config, 'logo_base_url', 'https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/') + f"{channel_name}.png"
                                    
                                    f_m3u_ipv6.write(f'#EXTINF:-1 tvg-id="{index}" tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{category}",{channel_name}\n')
                                    f_m3u_ipv6.write(new_url + "\n")
                                    f_txt_ipv6.write(f"{channel_name},{new_url}\n")
                                
                                written_channels.add(channel_name)  # 标记为已写入

                logger.info(f"文件生成完成: {m3u_file}, {txt_file}, {m3u_ipv6_file}, {txt_ipv6_file}")
                
        except Exception as e:
            logger.error(f"生成文件失败: {e}")
            raise

async def main():
    """主函数"""
    processor = IPTVProcessor("demo.txt")
    
    try:
        # 获取频道数据
        channels, template_channels = processor.filter_source_urls()
        
        # 处理频道链接
        async with processor:
            sorted_channels = await processor.process_channel_links(channels)
        
        # 生成输出文件
        processor.update_channel_urls_m3u(sorted_channels, template_channels)
        
        logger.info("IPTV处理完成")
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())