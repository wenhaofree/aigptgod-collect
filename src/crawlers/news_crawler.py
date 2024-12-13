"""
News crawler module for AI Daily Report Generator.
"""
import logging
import asyncio
from typing import List, Dict
from datetime import datetime, timezone
import aiohttp
import feedparser
from bs4 import BeautifulSoup
import pytz
import json
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

class NewsCrawler:
    """News crawler class to fetch AI-related news from various sources."""
    
    def __init__(self, config: Dict):
        """Initialize the news crawler with configuration."""
        self.config = config
        self.sources = {
            'techcrunch': {
                'feed_url': 'https://techcrunch.com/feed/',
                'keywords': ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'gpt', 'llm'],
            },
            'mit_tech_review': {
                'feed_url': 'https://www.technologyreview.com/feed/',
                'keywords': ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'gpt', 'llm'],
            }
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, application/atom+xml, application/json',
        }

    async def fetch_news(self) -> List[Dict]:
        """
        Fetch news from all configured sources.
        
        Returns:
            List[Dict]: List of news articles with metadata
        """
        try:
            articles = []
            timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds timeout
            async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
                # Create tasks for each source
                tasks = []
                for source_name, source_config in self.sources.items():
                    task = self._fetch_from_source(session, source_name, source_config)
                    tasks.append(task)
                
                # Gather results from all sources
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error fetching news: {str(result)}")
                    elif isinstance(result, list):
                        articles.extend(result)
                        logger.info(f"Found {len(result)} articles")
            
            # Deduplicate and sort articles
            unique_articles = self._deduplicate_articles(articles)
            logger.info(f"After deduplication: {len(unique_articles)} unique articles")
            
            return unique_articles
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            raise

    async def _fetch_from_source(self, session: aiohttp.ClientSession, source_name: str, source_config: Dict) -> List[Dict]:
        """
        Fetch articles from a specific source's RSS feed.
        
        Args:
            session: aiohttp client session
            source_name: Name of the source
            source_config: Configuration for the source
            
        Returns:
            List[Dict]: List of articles from the source
        """
        try:
            logger.info(f"Fetching from {source_name} at {source_config['feed_url']}")
            
            async with session.get(source_config['feed_url']) as response:
                if response.status != 200:
                    logger.error(f"Error fetching from {source_name}: Status {response.status}")
                    return []
                
                feed_content = await response.text()
                feed = feedparser.parse(feed_content)
                
                if feed.bozo:  # Check if there were any parsing errors
                    logger.error(f"Error parsing feed from {source_name}: {feed.bozo_exception}")
                    return []
                
                logger.info(f"Found {len(feed.entries)} entries in {source_name} feed")
                
                articles = []
                for entry in feed.entries:
                    try:
                        # Check if article is AI-related
                        if not self._is_ai_related(entry, source_config['keywords']):
                            continue
                        
                        # Parse publication date
                        try:
                            published_date = date_parser.parse(entry.published)
                            if not published_date.tzinfo:
                                published_date = published_date.replace(tzinfo=timezone.utc)
                        except (AttributeError, ValueError):
                            published_date = datetime.now(timezone.utc)
                        
                        # Extract content
                        content = ''
                        if hasattr(entry, 'content'):
                            content = entry.content[0].value
                        elif hasattr(entry, 'summary'):
                            content = entry.summary
                        elif hasattr(entry, 'description'):
                            content = entry.description
                        
                        # Clean content HTML
                        if content:
                            soup = BeautifulSoup(content, 'lxml')
                            content = soup.get_text(separator=' ', strip=True)
                        
                        article = {
                            'title': entry.title,
                            'url': entry.link,
                            'content': content,
                            'published_date': published_date.isoformat(),
                            'source': source_name,
                            'author': entry.get('author', ''),
                            'categories': entry.get('tags', []),
                        }
                        
                        logger.debug(f"Found article: {json.dumps({'title': article['title'], 'url': article['url']}, indent=2)}")
                        articles.append(article)
                        
                        if len(articles) >= self.config.get('max_articles_per_source', 50):
                            break
                            
                    except Exception as e:
                        logger.error(f"Error processing entry from {source_name}: {str(e)}")
                        continue
                
                logger.info(f"Successfully processed {len(articles)} AI-related articles from {source_name}")
                return articles
                
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {str(e)}")
            return []

    def _is_ai_related(self, entry: Dict, keywords: List[str]) -> bool:
        """Check if an article is AI-related based on keywords."""
        # Convert all text to lowercase for case-insensitive matching
        title = entry.title.lower()
        summary = entry.get('summary', '').lower()
        tags = [tag.get('term', '').lower() for tag in entry.get('tags', [])]
        
        # Check title, summary, and tags for keywords
        text_to_check = f"{title} {summary} {' '.join(tags)}"
        return any(keyword.lower() in text_to_check for keyword in keywords)

    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on URL and sort by publication date."""
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            if article['url'] and article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        return sorted(unique_articles, key=lambda x: x['published_date'], reverse=True)