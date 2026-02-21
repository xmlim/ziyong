# IPTV配置文件

# 源URL列表
source_urls = [
    "https://raw.githubusercontent.com/xmlim/1/main/FJCUCC.M3U",
    "https://raw.githubusercontent.com/xmlim/ziyong/main/FJTELE.m3u",
    "https://raw.githubusercontent.com/xmlim/ziyong/main/FJCMCC.m3u",
    # 台湾频道源（示例，请测试可用性）
    #"https://raw.githubusercontent.com/iptv-org/iptv/master/countries/tw.m3u",
    #"https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/global.m3u",
    #"https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u",
]

# URL黑名单
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

# 公告频道配置
announcements = [
    {
        "channel": "LINTCL更新日期",
        "entries": [
            {"name": None, "url": "
https://open.spotify.com/track/3ewRVZ2EolQkDrdkpDODR9?si=374cfded7827454e", "logo": "http://175.178.251.183:6689/LR.jpg"}
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
}

# 性能优化配置
performance_config = {
    "link_check_timeout": 3,
    "max_concurrent_checks": 50,
}

# 跳过检查的URL模式（已知稳定的源）
skip_check_patterns = [
    "27.148.240.185",
    "PLTV/88888888",
]

# 输出格式配置 - 重点优化
output_format = {
    "include_original": True,
    "url_suffix_enabled": False,
    "suffix_style": "simple",
    "max_urls_per_channel": 10,
    "preserve_source_order": True,
}

# 请求配置
request_timeout = 10
max_workers = 50
