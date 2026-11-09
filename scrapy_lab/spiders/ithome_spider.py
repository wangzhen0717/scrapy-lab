# IT 之家按日新闻爬虫
# 通过滚动新闻按日页面抓取指定日期的全部新闻，进入详情页抓取深度数据
# 通过 Scrapy Feeds 写入 data/ithome_日期.jsonl

import re
from datetime import datetime

import scrapy

from scrapy_lab.items import IthomeItem


def ithome_uri_params(params, spider):
    return {**params, "date": spider.target_date}


class IthomeSpider(scrapy.Spider):
    name = "ithome"
    allowed_domains = ["ithome.com"]

    custom_settings = {
        "FEED_URI": "data/ithome_%(date)s.jsonl",
        "FEED_FORMAT": "jsonlines",
        "FEED_EXPORT_ENCODING": "utf-8",
        "FEED_URI_PARAMS": "scrapy_lab.spiders.ithome_spider.ithome_uri_params",
    }

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(self, date=None, limit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("date 参数格式应为 YYYY-MM-DD") from exc
            self.target_date = date
        else:
            self.target_date = datetime.now().strftime("%Y-%m-%d")
        self.limit = int(limit) if limit else 0
        self.seen_urls: set[str] = set()
        self.list_count = 0
        self.detail_count = 0

    async def start(self):
        for request in self.start_requests():
            yield request

    def start_requests(self):
        url = f"https://www.ithome.com/list/{self.target_date}.html"
        yield scrapy.Request(
            url=url, callback=self.parse, headers=self.headers, dont_filter=True
        )

    def parse(self, response):
        # 按日页面使用滚动新闻列表，<i> 为发布时间，可用于过滤跨日推广条目
        items = response.xpath(
            '//div[@id="list"]//ul[contains(concat(" ", normalize-space(@class), " "), " datel ")]/li'
        )

        for li in items:
            link = li.xpath(
                './a[contains(concat(" ", normalize-space(@class), " "), " t ")]'
            )
            title = "".join(link.xpath(".//text()").getall()).strip()
            href = link.xpath("./@href").get()
            if not href or "lapin.ithome.com" in href:
                continue

            raw_time = li.xpath("./i/text()").get(default="").strip()
            if not raw_time.startswith(self.target_date):
                continue

            url = response.urljoin(href)
            if url in self.seen_urls:
                continue
            self.seen_urls.add(url)
            self.list_count += 1
            print(f"[列表页] {raw_time} | {title} | {url}")

            if not self.limit or self.detail_count < self.limit:
                self.detail_count += 1
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                    meta={"list_url": url},
                    headers=self.headers,
                )

        self._print_list_summary()

    def _print_list_summary(self):
        print(f"\n[列表页] 当天新闻总数：{self.list_count}，进入详情页：{self.detail_count}\n")

    def parse_detail(self, response):
        content_selector = response.xpath('//div[@id="paragraph"]')
        content_selector = content_selector[0] if content_selector else None

        title = response.xpath("normalize-space(//h1)").get(default="")
        publish_time = response.xpath(
            'normalize-space(//span[@id="pubtime_baidu"])'
        ).get(default="")

        source = response.xpath('//span[@id="source_baidu"]/a/text()').get()
        if source:
            source = source.strip()
        else:
            source = response.xpath(
                'normalize-space(//span[@id="source_baidu"])'
            ).get(default="")
            source = source.split("：", 1)[-1].strip() if source else ""
        if not source:
            source = "IT之家"

        author = response.xpath('//span[@id="author_baidu"]/strong/text()').get()
        if author:
            author = author.strip()
        else:
            author = response.xpath(
                'normalize-space(//span[@id="author_baidu"])'
            ).get(default="")
            author = author.split("：", 1)[-1].strip() if author else ""
        if not author:
            author = "未知"

        item = {
            "url": response.meta.get("list_url", response.url),
            "title": title,
            "publish_time": publish_time,
            "source": source,
            "author": author,
            "content": self._extract_content(content_selector),
            "images": [],
            "videos": [],
            "article_value": None,
            "rating_count": None,
        }
        item["images"], item["videos"] = self._extract_media(response, content_selector)

        newsid = response.xpath('//div[@id="post_comm"]/@data-nid').get()
        newsid = newsid.strip() if newsid else ""
        if not newsid:
            match = re.search(r"/grade/(\d+)", response.text)
            newsid = match.group(1) if match else ""

        if newsid:
            yield scrapy.Request(
                url=f"https://dyn.ithome.com/grade/{newsid}",
                callback=self.parse_grade,
                meta={"item": item},
                headers=self.headers,
                errback=self.parse_grade_error,
            )
        else:
            yield IthomeItem(**item)

    def parse_grade(self, response):
        item = response.meta["item"]
        article_value = None
        rating_count = 0

        match = re.search(r"var gradestr = '(.*?)';", response.text, re.S)
        if match:
            grade_selector = scrapy.Selector(text=match.group(1))

            raw_value = grade_selector.xpath('//span[@class="ss"]/text()').get()
            if raw_value:
                try:
                    article_value = float(raw_value.strip())
                except ValueError:
                    article_value = raw_value.strip()

            raw_count = grade_selector.xpath('//span[@class="m"]/text()').get()
            if raw_count:
                count_match = re.search(r"(\d+)", raw_count)
                if count_match:
                    rating_count = int(count_match.group(1))

        item["article_value"] = article_value
        item["rating_count"] = rating_count
        yield IthomeItem(**item)

    def parse_grade_error(self, failure):
        item = failure.request.meta.get("item", {})
        item["article_value"] = None
        item["rating_count"] = 0
        yield IthomeItem(**item)

    def _extract_content(self, content_selector):
        if content_selector is None:
            return ""

        paragraphs = []
        for paragraph in content_selector.xpath(".//p"):
            raw_text = "".join(paragraph.xpath(".//text()").getall())
            text = re.sub(r"\s+", " ", raw_text).strip()
            if text:
                paragraphs.append(text)

        if paragraphs:
            return "\n".join(paragraphs)

        text = content_selector.xpath("string(.)").get(default="")
        return re.sub(r"\s+", " ", text).strip()

    def _extract_media(self, response, content_selector):
        images = []
        videos = []
        seen = set()

        if content_selector is None:
            return images, videos

        for image in content_selector.xpath(".//img"):
            src = (
                image.xpath("./@data-original").get()
                or image.xpath("./@data-src").get()
                or image.xpath("./@src").get()
            )
            if not src:
                srcset = image.xpath("./@srcset").get()
                if srcset:
                    src = srcset.split(",")[0].strip().split(" ")[0]

            if src:
                src = src.strip()
                if "images/v2/t.png" not in src and not src.startswith("data:"):
                    absolute = response.urljoin(src)
                    if absolute not in seen:
                        seen.add(absolute)
                        images.append(absolute)

            live = image.xpath("./@data-live").get()
            if live:
                absolute = response.urljoin(live.strip())
                if absolute not in seen:
                    seen.add(absolute)
                    videos.append(absolute)

        for iframe in content_selector.xpath(".//iframe"):
            src = iframe.xpath("./@src").get()
            if not src:
                continue
            css_class = iframe.xpath("./@class").get() or ""
            if "video" not in css_class.lower() and not re.search(
                r"bilibili|youtube|youku|v\.qq\.com|ixigua|douyin|weibo|player",
                src,
                re.I,
            ):
                continue
            absolute = response.urljoin(src.strip())
            if absolute not in seen:
                seen.add(absolute)
                videos.append(absolute)

        for video in content_selector.xpath(".//video"):
            for src in video.xpath("./@src | ./source/@src").getall():
                if not src:
                    continue
                absolute = response.urljoin(src.strip())
                if absolute not in seen:
                    seen.add(absolute)
                    videos.append(absolute)

        return images, videos
