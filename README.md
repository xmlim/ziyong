# IPTV Sources Collector

自动收集和更新IPTV直播源的工具。

## 功能特点

- 自动获取地理位置信息
- 搜索并验证IPTV直播源
- 每12小时自动更新
- 保存有效的直播源列表

## 文件说明

- `moyun.txt`: 包含直播源列表和详细信息
- `iptv_stream.m3u`: 最新的直播源文件
- `get_iptv.py`: 主程序脚本
- `requirements.txt`: 依赖包列表

## 自动更新

本项目使用GitHub Actions进行自动更新，每12小时运行一次。你也可以在Actions页面手动触发更新。

## 使用方法

1. Fork 本仓库
2. 启用 GitHub Actions
3. 直接从 `moyun.txt` 或 `iptv_stream.m3u` 获取直播源

## 注意事项

- 部分直播源可能不稳定
- 建议定期检查更新
- 仅供学习研究使用

## 订阅地址

直接复制以下地址到播放器中：