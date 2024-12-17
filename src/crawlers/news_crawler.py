"""
News crawler module for fetching AI-related articles from various sources.
"""
import logging
import asyncio
import aiohttp
from typing import List, Dict
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import pytz
import re
import yaml
import os
import feedparser
from dateutil import parser as date_parser
import hashlib
from aiohttp_socks import ProxyConnector

logger = logging.getLogger(__name__)

class NewsCrawler:
    """Crawler for fetching AI-related news articles from configured sources."""
    
    def __init__(self, config: Dict = None):
        """Initialize the news crawler with configuration."""
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
        self.base_config = self._load_config()
        
        # Merge provided config with base config
        if config:
            self.base_config.update(config)
        
        self.config = self.base_config
        self.sources = self.config.get('news_sources', {})
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, application/atom+xml, application/json',
        }

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {}

    def _get_proxy_settings(self) -> Dict:
        """Get proxy settings from config."""
        proxy_settings = self.config.get('proxy_settings', {})
        if not proxy_settings.get('enabled', False):
            return None
        
        return {
            'http': proxy_settings.get('http'),
            'https': proxy_settings.get('https')
        }

    async def fetch_news(self) -> List[Dict]:
        """
        Fetch news from all configured sources.
        
        Returns:
            List[Dict]: List of articles from all sources
        """
        all_articles = []
        
        # Create connector with proxy if enabled
        proxy_settings = self._get_proxy_settings()
        if proxy_settings:
            connector = ProxyConnector.from_url(proxy_settings['http'])
        else:
            connector = None

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for source_name, source_config in self.sources.items():
                tasks.append(self._fetch_from_source(session, source_name, source_config))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error fetching news: {str(result)}")
                else:
                    all_articles.extend(result)
        
        return self._deduplicate_articles(all_articles)

    async def _fetch_from_source(self, session: aiohttp.ClientSession, source_name: str, source_config: Dict) -> List[Dict]:
        """Fetch articles from a single source."""
        articles = []
        try:
            logger.info(f"Fetching from {source_name}...")
            
            # Enhanced headers for RSSHub
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }

            async with session.get(source_config['feed_url'], 
                                 headers=headers, 
                                 ssl=False,  # Disable SSL verification if needed
                                 allow_redirects=True) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error fetching from {source_name}: Status {response.status}, Response: {error_text[:200]}")
                    return []
                
                feed_content = await response.text()
                logger.debug(f"Received response from {source_name}, content length: {len(feed_content)}")
                
                if not feed_content:
                    logger.error(f"Empty response from {source_name}")
                    return []
                
                try:
                    feed = feedparser.parse(feed_content)
                    if feed.bozo:  # feedparser encountered an error
                        logger.error(f"Feed parsing error for {source_name}: {feed.bozo_exception}")
                        return []
                except Exception as e:
                    logger.error(f"Error parsing feed content from {source_name}: {str(e)}")
                    return []
                
                logger.info(f"Found {len(feed.entries)} entries in {source_name} feed")
                
                for entry in feed.entries:
                    try:
                        # Check if article is AI-related
                        if not self._is_ai_related(entry, source_config['keywords']):
                            continue
                        
                        article = await self._parse_feed_entry(entry, source_name, source_config)
                        if article:
                            articles.append(article)
                        
                        if len(articles) >= 50:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error processing entry from {source_name}: {str(e)}")
                        continue
                
                logger.info(f"Successfully processed {len(articles)} AI-related articles from {source_name}")
                return articles
                
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {str(e)}")
            return []

    async def _parse_feed_entry(self, entry: Dict, source_name: str, source_config: Dict) -> Dict:
        """Parse a feed entry into a standardized article format."""
        try:
            # Get parser type and config
            parser_type = source_config.get('type', 'rss')
            parser_config = source_config.get('parser_config', {})

            if parser_type == 'rsshub':
                # RSSHub specific parsing
                title = entry.get(parser_config.get('title_selector', 'title'), '')
                content = entry.get(parser_config.get('content_selector', 'description'), '')
                link = entry.get(parser_config.get('link_selector', 'link'), '')
                published = entry.get(parser_config.get('date_selector', 'pubDate'), '')
                if source_config.get('name')=='aibase':
                    image_urls = re.findall(r'src="([^"]+)"', entry.get('summary', ''))
                    image_url = image_urls[0] if image_urls else ''
                elif source_config.get('name')=='techcrunch':
                    image_url = re.search(r'<img src="([^"]+)"', entry.get('summary', '')).group(1) if entry.get('summary') else ''
            else:
                # Traditional RSS parsing
                title = entry.get('title', '')
                content = entry.get('description', '') or entry.get('summary', '')
                link = entry.get('link', '')
                published = entry.get('published', '') or entry.get('pubDate', '')

            # Clean the content (remove HTML tags)
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text(separator=' ', strip=True)

            # Parse and standardize the date
            try:
                if published:
                    dt = date_parser.parse(published)
                    published_date = dt.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
                else:
                    published_date = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
            except Exception as e:
                logger.error(f"Error parsing date: {str(e)}")
                published_date = datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')

            return {
                'id': hashlib.md5(link.encode()).hexdigest(),
                'title': title,
                'content': content,
                'summary': '',  # Will be filled by the content processor
                'link': link,
                'source': source_name,
                'image_url': image_url,
                'published_date': published_date
            }
        except Exception as e:
            logger.error(f"Error parsing feed entry: {str(e)}")
            return None

    def _is_ai_related(self, entry: Dict, keywords: List[str]) -> bool:
        """
        Check if an article is AI-related based on keywords, focusing on:
        1. Large AI models (GPT, LLM, etc.)
        2. Major tech companies (Google, Microsoft, etc.)
        3. AI technology and developments
        """
        # Convert all text to lowercase for case-insensitive matching
        title = entry.get('title', '').lower()
        summary = entry.get('summary', '').lower()
        tags = [tag.get('term', '').lower() for tag in entry.get('tags', [])]
        
        # Define specific keywords for different categories
        ai_model_keywords = {'gpt', 'llm', 'large language model', 'chatgpt', 'claude', 'gemini', 
                           'anthropic', 'mistral', 'llama', 'palm', 'bert', 'transformer'}
        tech_company_keywords = {'openai', 'google', 'microsoft', 'meta', 'apple', 'amazon', 
                               'anthropic', 'tesla', 'nvidia', 'baidu', 'alibaba', 'tencent'}
        ai_tech_keywords = {'artificial intelligence', 'machine learning', 'deep learning', 
                          'neural network', 'ai model', 'foundation model', 'generative ai'}
        
        # Combine all keywords
        all_keywords = ai_model_keywords | tech_company_keywords | ai_tech_keywords | set(k.lower() for k in keywords)
        
        # Check title, summary, and tags
        text_to_check = f"{title} {summary} {' '.join(tags)}"
        
        # Title has higher priority - if any keyword is in title, return True
        if any(keyword in title for keyword in all_keywords):
            return True
            
        # For summary and tags, require stronger relevance
        return any(keyword in text_to_check for keyword in all_keywords)

    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on URL and sort by publication date."""
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            if article['link'] and article['link'] not in seen_urls:
                seen_urls.add(article['link'])
                unique_articles.append(article)
        
        return sorted(unique_articles, key=lambda x: x['published_date'], reverse=True)