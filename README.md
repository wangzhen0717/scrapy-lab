# Scrapy Lab

基于 [Scrapy](https://scrapy.org/) 的按日新闻数据采集项目。当前实现了 IT之家（ITHome）指定日期新闻的列表解析、详情页正文抓取、媒体资源提取与文章评分采集，并按日期以 JSON Lines 格式持久化。项目已支持 Docker 部署，定时调度由宿主机负责触发。

## 功能特性

- **按日采集**：以 IT之家滚动新闻按日页面为数据源，抓取指定日期的全部新闻。
- **详情页深度抓取**：采集标题、发布时间、来源、作者、正文、图片、视频与文章评分。
- **跨日过滤**：按发布时间过滤页面中混入的跨日推广条目。
- **排除购物内容**：跳过 `lapin.ithome.com` 的优惠/带货条目，只保留新闻正文。
- **URL 去重**：同一次采集内按链接去重。
- **随机 User-Agent**：内置下载中间件为每个请求随机设置 UA，降低反爬识别概率。
- **幂等输出**：按日期命名输出文件，同一天重跑会覆盖为最新完整快照。
- **Docker 化部署**：镜像内固定时区与依赖，数据通过卷持久化，宿主用户身份运行。
- **构建优化**：国内 apt / PyPI 镜像、仅安装 wheel、精简编译依赖、分层缓存。

## 技术栈

| 组件 | 说明 |
| --- | --- |
| Python | 容器内 `python:3.12-slim`；本地开发 3.10+ |
| Scrapy | `scrapy==2.19.0` |
| 数据格式 | JSON Lines，按日期分文件 |
| 部署 | Docker |
| 调度 | 宿主机 cron / systemd timer（容器内不安装 cron） |

## 项目结构

```text
scrapy-lab/
├── Dockerfile                  # 容器镜像构建文件
├── .dockerignore               # Docker 构建上下文忽略规则
├── .gitignore                  # Git 忽略规则
├── requirements.txt            # Python 依赖
├── scrapy.cfg                  # Scrapy 项目配置
├── README.md
├── TODO.md                     # 后续演进路线
├── data/                       # 采集结果输出目录（挂载卷，不纳入版本控制）
└── scrapy_lab/
    ├── __init__.py
    ├── settings.py             # 项目全局配置（日志、延迟、中间件等）
    ├── items.py                # Item 数据模型（IthomeItem）
    ├── pipelines.py            # 数据处理管道（默认模板，未启用）
    ├── middlewares.py          # 随机 User-Agent 下载中间件
    ├── utils/                  # 工具模块（预留）
    └── spiders/
        ├── __init__.py
        └── ithome_spider.py    # IT之家按日新闻爬虫
```

## 快速开始

> 以下命令以 **Linux / WSL** 环境为准。Windows PowerShell 中 `$(pwd)` 需替换为当前目录绝对路径，`$(id -u)` / `$(id -g)` 建议在 WSL 中执行或替换为实际 UID/GID。

### 方式一：Docker（推荐）

#### 1. 构建镜像

```bash
docker build --progress=plain -t scrapy-lab:latest .
```

#### 2. 准备数据目录

```bash
mkdir -p data
```

#### 3. 运行采集

```bash
# 采集指定日期
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  --user "$(id -u):$(id -g)" \
  scrapy-lab:latest -a date=2026-11-10

# 不传 date 时，默认采集容器内 Asia/Shanghai 的当天
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  --user "$(id -u):$(id -g)" \
  scrapy-lab:latest

# 限制进入详情页的条数（便于调试）
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  --user "$(id -u):$(id -g)" \
  scrapy-lab:latest -a date=2026-11-10 -a limit=10
```

运行结束后，数据会写入宿主机 `data/ithome_<YYYY-MM-DD>.jsonl`。同一天重复运行会覆盖该文件。

#### 4. 验证时区

```bash
docker run --rm --entrypoint python scrapy-lab:latest \
  -c "from datetime import datetime; print(datetime.now())"
```

输出应为北京时间。

### 方式二：本地虚拟环境

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 采集指定日期
scrapy crawl ithome -a date=2026-11-10

# 默认采集当天
scrapy crawl ithome

# 限制详情页条数
scrapy crawl ithome -a date=2026-11-10 -a limit=10
```

## Docker 部署与优化

### 持久化与权限

- 使用 `-v "$(pwd)/data:/app/data"` 将采集结果挂载到宿主机，容器删除后数据仍然保留。
- 使用 `--user "$(id -u):$(id -g)"` 以宿主机当前用户身份运行，避免生成的 JSONL 文件被 root 锁定。
- 镜像内不包含历史数据，`data/` 目录通过挂载提供；运行前请先执行 `mkdir -p data`。
- 容器内工作目录固定为 `/app`，数据输出路径为 `/app/data/ithome_<日期>.jsonl`。
- 镜像入口为 `ENTRYPOINT ["scrapy", "crawl", "ithome"]`，因此镜像后可直接追加 `-a date=...`、`-a limit=...` 等参数。

### 依赖与构建优化

- **基础镜像**：使用 `python:3.12-slim`，体积较小且与项目依赖兼容。
- **时区固定**：通过 `TZ=Asia/Shanghai`、`/etc/localtime`、`/etc/timezone` 保证容器内时间为北京时间。
- **apt 国内镜像**：构建时自动识别 Debian 源格式，将 `deb.debian.org` 替换为清华镜像，兼容 `debian.sources` 与 `sources.list`。
- **apt 稳定性**：配置重试、超时与强制 IPv4，降低网络抖动导致的构建失败。
- **pip 国内镜像**：通过 `PIP_INDEX_URL` 使用清华 PyPI 源。
- **仅使用 wheel**：`pip install --only-binary=:all:` 强制使用预编译 wheel，避免容器内编译。
- **精简系统依赖**：只安装 `tzdata` 和 `ca-certificates`，移除 `build-essential` 及 `-dev` 编译包。
- **分层缓存**：先复制 `requirements.txt` 并安装依赖，再复制项目代码；代码变更不会触发依赖重装。
- **构建上下文精简**：`.dockerignore` 排除 `.venv/`、`.git/`、`data/`、`__pycache__/` 等无关内容。
- **依赖可复现**：`requirements.txt` 固定为 `scrapy==2.19.0`。

## 宿主机定时触发

定时任务由宿主机负责，容器内不安装 cron。以下为 crontab 配置示例（以 Linux/WSL 为例）：

```cron
# 每天 00:10 采集前一天数据（宿主机需能访问 docker 命令）
10 0 * * * cd /path/to/scrapy-lab && flock -n /tmp/scrapy-lab.lock docker run --rm -v "$PWD/data:/app/data" --user "$(id -u):$(id -g)" scrapy-lab:latest -a date="$(TZ=Asia/Shanghai date -d 'yesterday' +\%F)" >> /var/log/scrapy-lab.log 2>&1
```

注意事项：

- crontab 中的 `%` 需要转义为 `\%`。
- 如果宿主机时区不是 Asia/Shanghai，务必在 `date` 命令前加 `TZ=Asia/Shanghai`。
- `flock -n` 用于防止上一次任务未结束时重复启动。
- cron 的 `PATH` 通常很精简，必要时使用 `docker` 的绝对路径。
- 如果希望采集“当天”，可改为 `date +\%F`，并把执行时间安排在当天较晚时段（例如 23:50）。
- 更完整的脚本化、systemd timer、失败告警等方案见 [TODO.md](TODO.md)。

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

## 常见问题（FAQ）

### 1. 使用 `--user` 后出现权限报错

**现象**：容器无法写入 `/app/data`，报 `Permission denied`。

**原因**：宿主机 `data/` 目录对当前 UID/GID 不可写，或之前以 root 身份运行留下了 root 属主文件。

**处理**：

```bash
mkdir -p data
ls -ld data
id -u
id -g
sudo chown -R "$(id -u):$(id -g)" data
```

在 Fedora / RHEL 等启用 SELinux 的系统上，可尝试挂载时加 `:Z`：

```bash
-v "$(pwd)/data:/app/data:Z"
```

### 2. Docker Desktop 未启动

**现象**：

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**处理**：

1. 启动 Docker Desktop。
2. 等待引擎状态变为 Running。
3. 确认使用 Linux containers 模式。
4. 执行 `docker info` 或 `docker version` 验证。

### 3. 时区不正确

**现象**：容器内时间不是北京时间，或定时任务采集了错误日期。

**处理**：

```bash
# 检查容器时区
docker run --rm --entrypoint date scrapy-lab:latest
docker run --rm --entrypoint cat scrapy-lab:latest /etc/timezone

# 检查 Python 时间
docker run --rm --entrypoint python scrapy-lab:latest \
  -c "from datetime import datetime; print(datetime.now())"
```

预期时区为 `Asia/Shanghai`。如果宿主机 cron 使用 UTC，请在命令中显式设置 `TZ=Asia/Shanghai`。

### 4. 构建时报 `--only-binary=:all:` 找不到 wheel

**现象**：`No matching distribution found` 或提示只能从源码构建。

**处理**：

- 优先检查依赖是否有对应 Python 3.12 的 wheel。
- 临时移除 `--only-binary=:all:` 再构建。
- 如果确实需要编译，可恢复 `build-essential` 及对应 `-dev` 包，或改回多阶段构建。

### 5. 容器运行成功但 `data/` 没有文件

**原因**：未挂载数据卷，或挂载路径不一致。

**处理**：

```bash
mkdir -p data
ls -ld data

# 检查容器内目录
docker run --rm --entrypoint sh scrapy-lab:latest -c "ls -la /app/data"
```

确认运行命令包含：

```bash
-v "$(pwd)/data:/app/data"
```

### 6. 之前运行留下的文件属主是 root

```bash
sudo chown -R "$(id -u):$(id -g)" data
```

后续运行始终带上 `--user "$(id -u):$(id -g)"` 即可避免。

### 7. cron 到点执行但没有生成文件

排查顺序：

1. crontab 中的 `%` 是否已转义为 `\%`。
2. `date` 命令是否使用了正确的时区。
3. cron 是否能找到 `docker` 命令（必要时使用绝对路径）。
4. 查看日志：`tail -f /var/log/scrapy-lab.log`。
5. 手动执行 crontab 中的完整命令验证。
6. 确认 `flock` 锁文件没有残留（正常情况下会自动释放）。

### 8. 想覆盖镜像默认启动命令

镜像默认入口是 `scrapy crawl ithome`。如需执行其他命令：

```bash
docker run --rm --entrypoint scrapy scrapy-lab:latest version
docker run --rm -it --entrypoint sh scrapy-lab:latest
```

### 9. 构建速度慢或 apt 下载超时

- 确认 Dockerfile 中的清华镜像已生效。
- 检查宿主机/Docker Desktop 是否配置了冲突的 HTTP 代理。
- 检查 Docker DNS 配置。
- 重新执行构建；apt 与 pip 已配置重试和超时。
- 如果基础镜像 `python:3.12-slim` 本地不存在，拉取镜像本身也可能较慢，可先单独 `docker pull`。

## 合规与免责声明

本项目仅用于学习与研究。请遵守目标网站的 `robots.txt`、服务条款及相关法律法规，合理控制抓取频率，不得将采集数据用于商业用途或侵犯他人权益。

## 后续规划

多爬虫改造、消息队列评估、云服务器部署、CI/CD、测试、监控等演进方向见 [TODO.md](TODO.md)。
