# Scrapy 项目配置文件
SPIDER_MODULES = ['scrapy_lab.spiders']
# 这里配置项目级别的设置
# 部分设置会被 scrapy.cfg 覆盖

# 设置日志级别
# DEBUG: 详细日志，适合调试
# INFO: 正常日志，默认级别
# WARNING: 警告日志
# ERROR: 错误日志
# CRITICAL: 严重错误日志
LOG_LEVEL = "INFO"

# 日志输出到控制台
LOG_STDOUT = True

# 反爬配置
# 每个请求之间延迟 1 秒
DOWNLOAD_DELAY = 1
# 在 DOWNLOAD_DELAY 基础上增加随机抖动
RANDOMIZE_DOWNLOAD_DELAY = True

# 启用随机 User-Agent 下载中间件
DOWNLOADER_MIDDLEWARES = {
    "scrapy_lab.middlewares.RandomUserAgentMiddleware": 400,
}
