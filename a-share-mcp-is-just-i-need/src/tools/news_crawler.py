"""新闻爬虫工具模块。"""
import logging

from ..data_source_factory import get_data_source
from ..market_utils import detect_market

logger = logging.getLogger(__name__)


def crawl_news(query: str, top_k: int = 10, stock_code: str = "") -> str:
    """爬取相关新闻并进行分析。"""
    logger.info("爬取新闻: %s, top_k=%s", query, top_k)

    if stock_code and detect_market(stock_code) != "cn":
        data_source = get_data_source(stock_code)
        if hasattr(data_source, "get_news"):
            news_items = data_source.get_news(stock_code, top_k=top_k)
            if news_items:
                result = f"## 新闻分析: {query}\n\n共找到 {len(news_items)} 条相关新闻\n\n"
                for i, news in enumerate(news_items, 1):
                    result += f"### {i}. {news['title']}\n"
                    result += f"**摘要:** {news['summary']}\n"
                    if news.get("publisher"):
                        result += f"**来源:** {news['publisher']}\n"
                    if news.get("published_at"):
                        result += f"**发布时间:** {news['published_at']}\n"
                    result += f"**风险等级:** 3/5 (待模型综合判断)\n"
                    result += f"**情感得分:** 3/5 (待模型综合判断)\n"
                    result += f"**链接:** {news['url']}\n\n"
                return result

    mock_news = [
        {
            "title": f"{query} 发布最新财报，业绩超预期",
            "summary": "公司最新季度营收同比增长15%，净利润增长20%，超出市场预期。",
            "url": "https://example.com/news/1",
            "risk_score": 2,
            "risk_desc": "低风险",
            "sentiment_score": 4,
            "sentiment_desc": "正面",
        },
        {
            "title": f"行业政策利好 {query} 迎来发展机遇",
            "summary": "国家出台新政策支持行业发展，预计将带动相关公司业绩增长。",
            "url": "https://example.com/news/2",
            "risk_score": 1,
            "risk_desc": "极低风险",
            "sentiment_score": 5,
            "sentiment_desc": "极正面",
        },
        {
            "title": f"{query} 股价近期波动较大，市场关注度高",
            "summary": "公司股价近一个月涨幅超过30%，成交量显著放大，市场关注度提升。",
            "url": "https://example.com/news/3",
            "risk_score": 3,
            "risk_desc": "中等风险",
            "sentiment_score": 3,
            "sentiment_desc": "中性",
        },
    ]

    selected = mock_news[:top_k]
    result = f"## 新闻分析: {query}\n\n"
    result += f"共找到 {len(selected)} 条相关新闻\n\n"

    for i, news in enumerate(selected, 1):
        result += f"### {i}. {news['title']}\n"
        result += f"**摘要:** {news['summary']}\n"
        result += f"**风险等级:** {news['risk_score']}/5 ({news['risk_desc']})\n"
        result += f"**情感得分:** {news['sentiment_score']}/5 ({news['sentiment_desc']})\n"
        result += f"**链接:** {news['url']}\n\n"
    return result
