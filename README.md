# Scrapy Lab

基于 [Scrapy](https://scrapy.org/) 的按日新闻数据采集项目。当前实现了 IT之家（ITHome）指定日期新闻的列表解析、详情页正文抓取、媒体资源提取与文章评分采集，并按日期以 JSON Lines 格式持久化。

## 功能特性

- **按日采集**：以 IT之家滚动新闻按日页面为数据源，抓取指定日期的全部新闻。
- **详情页深度抓取**：采集标题、发布时间、来源、作者、正文、图片、视频与文章评分。
- **跨日过滤**：按发布时间过滤页面中混入的跨日推广条目。
- **排除购物内容**：跳过 `lapin.ithome.com` 的优惠/带货条目，只保留新闻正文。
- **URL 去重**：同一次采集内按链接去重。
- **随机 User-Agent**：内置下载中间件为每个请求随机设置 UA，降低反爬识别概率。
- **幂等输出**：按日期命名输出文件，同一天重跑会覆盖为最新完整快照。

## 项目结构

```text
scrapy-lab/
├── scrapy.cfg                  # Scrapy 项目配置
├── requirements.txt            # Python 依赖
├── .gitignore                  # Git 忽略规则
├── scrapy_lab/
│   ├── settings.py             # 项目全局配置（日志、延迟、中间件等）
│   ├── items.py                # Item 数据模型（IthomeItem）
│   ├── pipelines.py            # 数据处理管道（默认模板，未启用）
│   ├── middlewares.py          # 随机 User-Agent 下载中间件
│   ├── utils/                  # 工具模块（预留）
│   └── spiders/
│       └── ithome_spider.py    # IT之家按日新闻爬虫
├── data/                       # 采集结果输出目录（不纳入版本控制）
└── README.md
```

## 环境要求

- Python 3.10+
- Scrapy 2.x

## 安装

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 使用

```bash
# 采集指定日期的新闻
scrapy crawl ithome -a date=2026-11-09

# 不传 date 时默认采集当天
scrapy crawl ithome

# 限制进入详情页的条数（便于调试）
scrapy crawl ithome -a date=2026-11-08 -a limit=10
```

运行结束后，数据会写入 `data/ithome_<YYYY-MM-DD>.jsonl`。同一天重复运行会覆盖该文件，便于定时任务重复执行。

## 数据字段

每条记录包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `url` | string | 新闻链接 |
| `title` | string | 标题 |
| `publish_time` | string | 发布时间 |
| `source` | string | 来源媒体 |
| `author` | string | 作者 |
| `content` | string | 正文纯文本 |
| `images` | array | 正文图片 URL 列表 |
| `videos` | array | 正文视频 URL 列表 |
| `article_value` | number \| null | 文章评分 |
| `rating_count` | number \| null | 评分人数 |

## 配置说明

主要配置位于 `scrapy_lab/settings.py`：

- `DOWNLOAD_DELAY`：请求间隔，默认 1 秒
- `RANDOMIZE_DOWNLOAD_DELAY`：请求延迟随机抖动
- `LOG_LEVEL`：日志级别
- `DOWNLOADER_MIDDLEWARES`：启用随机 User-Agent 中间件

输出路径、格式与编码在 `ithome_spider.py` 的 `custom_settings` 中定义。

## 数据完整性说明

IT之家在凌晨 01:00–05:59 基本没有新闻发布，按日页面的内容即该日期从当天首条到末条的完整列表。对于已结束的日期，页面数据完整；对于当天，页面会实时更新为“截至目前”的完整快照。

## 合规与免责声明

本项目仅用于学习与研究。请遵守目标网站的 `robots.txt`、服务条款及相关法律法规，合理控制抓取频率，不得将采集数据用于商业用途或侵犯他人权益。

## 后续计划

- 容器化部署（Docker）
- 定时任务调度
