# IPTV配置文件

# 源URL列表
source_urls = [
    #"https://gitee.com/xiaranxiaran/tv/raw/master/1.txt",
    "https://raw.githubusercontent.com/xmlim/ziyong/main/FJTELE.m3u",
    "https://raw.githubusercontent.com/xmlim/ziyong/main/FJCMCC.m3u",
    # 台湾频道源（示例，请测试可用性）
    #"https://raw.githubusercontent.com/iptv-org/iptv/master/countries/tw.m3u",
    #"https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/global.m3u",
    #"https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u",
]
    # 可以添加更多包含台湾频道的源
]

# URL黑名单
url_blacklist = [
    "epg.pw/stream/",
    "103.40.13.71:12390",
    # ... 其他黑名单项
]

# 公告频道配置
announcements = [
    {
        "channel": "LINTCL更新日期",
        "entries": [
            {"name": None, "url": "https://gitlab.com/lr77/IPTV/-/raw/main/%E8%B5%B7%E9%A3%8E%E4%BA%86.mp4", "logo": "http://175.178.251.183:6689/LR.jpg"}
        ]
    }
]

# EPG源URL列表
epg_urls = [
    "https://live.fanmingming.com/e.xml",
    "http://epg.51zmt.top:8000/e.xml",
    "http://epg.aptvapp.com/xml",
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
    "include_original": True,           # 包含原始格式（现在已默认）
    "url_suffix_enabled": False,        # 默认关闭URL后缀，确保电视APP兼容性
    "suffix_style": "simple",           # 后缀样式：simple/advanced
    "max_urls_per_channel": 10,         # 每个频道最大URL数量 - 已改为10
    "preserve_source_order": True,      # 保持源中的URL顺序，不进行质量排序
}

# 请求配置
request_timeout = 10
max_workers = 50