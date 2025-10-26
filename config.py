# IPTV配置文​​件

# IP版本优先级 (ipv4/ipv6/both)
ip_version_priority = "both"

# 请求超时时间（秒）
request_timeout = 10

# 最大工作线程数
max_workers = 50

# 最大并发连接数
max_connections = 100

# 每个主机的最大连接数
max_connections_per_host = 10

# 链接质量检查超时（秒）
link_check_timeout = 5

# 每个频道最大保留的URL数量
max_urls_per_channel = 10

# 源URL列表
source_urls = [
    "https://gitee.com/xiaranxiaran/tv/raw/master/1.txt",
    "https://raw.githubusercontent.com/xmlim/ziyong/main/FJTELE.m3u",
    "https://raw.githubusercontent.com/xmlim/ziyong/main/FJCMCC.m3u",
    # 备用源（注释的源可以作为备用）
    # "https://live.hacks.tools/tv/iptv6.txt",
    # "http://aktv.top/live.txt",
    # "https://live.fanmingming.com/tv/m3u/ipv6.m3u",
    # "https://raw.githubusercontent.com/yuanzl77/IPTV/main/直播/央视频道.txt",
    # "http://120.79.4.185/new/mdlive.txt",
    # "https://raw.githubusercontent.com/Fairy8o/IPTV/main/PDX-V4.txt",
    # "https://raw.githubusercontent.com/Fairy8o/IPTV/main/PDX-V6.txt",
    # "https://live.zhoujie218.top/tv/iptv6.txt",
    # "https://live.zhoujie218.top/tv/iptv4.txt",
    # "https://www.mytvsuper.xyz/m3u/Live.m3u",
    # "https://tv.youdu.fan:666/live/",
    # "http://ww.weidonglong.com/dsj.txt",
    # "http://xhztv.top/zbc.txt",
    # "https://raw.githubusercontent.com/qingwen07/awesome-iptv/main/tvbox_live_all.txt",
    # "https://raw.githubusercontent.com/Guovin/TV/gd/output/result.txt",
    # "http://home.jundie.top:81/Cat/tv/live.txt",
    # "https://raw.githubusercontent.com/vbskycn/iptv/master/tv/hd.txt",
    # "https://cdn.jsdelivr.net/gh/YueChan/live@main/IPTV.m3u",
    # "https://raw.githubusercontent.com/cymz6/AutoIPTV-Hotel/main/lives.txt",
    # "https://raw.githubusercontent.com/PizazzGY/TVBox_warehouse/main/live.txt",
    # "https://fm1077.serv00.net/SmartTV.m3u",
    # "https://raw.githubusercontent.com/ssili126/tv/main/itvlist.txt",
    # "https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.txt",
    # "https://ghp.ci/raw.githubusercontent.com/MemoryCollection/IPTV/refs/heads/main/itvlist.m3u",
    # "https://github.moeyy.xyz/https://raw.githubusercontent.com/Ftindy/IPTV-URL/main/huyayqk.m3u",
    # "http://www.lyyytv.cn/yt/zhibo/1.txt",
    # "http://live.nctv.top/x.txt",
    # "https://tv.iill.top/m3u/Live",
    # "http://tipu.xjqxz.top/live1213.txt"
]

# URL黑名单（包含这些字符串的URL将被过滤）
url_blacklist = [
    "epg.pw/stream/",
    "103.40.13.71:12390",
    "[2409:8087:1a01:df::4077]/PLTV/",
    "8.210.140.75:68",
    "154.12.50.54",
    "yinhe.live_hls.zte.com",
    "8.137.59.151",
    "[2409:8087:7000:20:1000::22]:6060",
    "histar.zapi.us.kg",
    "www.tfiplaytv.vip",
    "dp.sxtv.top",
    "111.230.30.193",
    "148.135.93.213:81",
    "live.goodiptv.club",
    "iptv.luas.edu.cn",
    "[2409:8087:2001:20:2800:0:df6e:eb22]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb23]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb1d]/ott.mobaibox.com/",
    "[2409:8087:2001:20:2800:0:df6e:eb1d]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb24]",
    "2409:8087:2001:20:2800:0:df6e:eb25]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb27]",
    # 添加更多常见无效域名
    "example.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0"
]

# 域名白名单（可选，如果设置则只允许这些域名的URL）
domain_whitelist = [
    # "example.com",
    # "live.example.com"
]

# 公告频道配置
announcements = [
    {
        "channel": "LINTCL更新日期",
        "entries": [
            {
                "name": None,  # 自动设置为当前日期
                "url": "https://gitlab.com/lr77/IPTV/-/raw/main/%E8%B5%B7%E9%A3%8E%E4%BA%86.mp4", 
                "logo": "http://175.178.251.183:6689/LR.jpg"
            }
        ]
    }
]

# EPG源URL列表
epg_urls = [
    "https://live.fanmingming.com/e.xml",
    "http://epg.51zmt.top:8000/e.xml",
    "http://epg.aptvapp.com/xml",
    "https://epg.pw/xmltv/epg_CN.xml",
    "https://epg.pw/xmltv/epg_HK.xml",
    "https://epg.pw/xmltv/epg_TW.xml"
]

# 频道Logo基础URL
logo_base_url = "https://gcore.jsdelivr.net/gh/yuanzl77/TVlogo@master/png/"

# 输出文件配置
output_config = {
    "output_dir": "output",
    "files": {
        "ipv4": {
            "m3u": "live.m3u",
            "txt": "live.txt"
        },
        "ipv6": {
            "m3u": "live_ipv6.m3u", 
            "txt": "live_ipv6.txt"
        }
    }
}

# 日志配置
log_config = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    "filename": "function.log",
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# 重试配置
retry_config = {
    "max_retries": 3,
    "backoff_factor": 1,
    "status_forcelist": [500, 502, 503, 504]
}

# 用户代理配置
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]