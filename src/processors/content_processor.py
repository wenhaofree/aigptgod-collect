"""
Content processor module for AI Daily Report Generator.
"""
import logging
from typing import List, Dict
from groq import Groq  # This is based on README requirements
import hashlib
import asyncio
import time
import re

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Process and analyze news content."""
    
    def __init__(self, config: Dict):
        """Initialize the content processor with configuration."""
        self.config = config
        self.groq_client = Groq(api_key=config['groq_api_key'])
        self.max_retries = 3
        self.base_delay = 5  # Base delay in seconds

    async def _make_groq_request(self, messages: List[Dict], max_tokens: int = 150, temperature: float = 0.5) -> str:
        """Make a request to Groq API with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = self.groq_client.chat.completions.create(
                    messages=messages,
                    model="llama-3.3-70b-specdec",
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if response and hasattr(response, 'choices') and response.choices:
                    message = response.choices[0].message.content
                    return message if message is not None else ""
                return ""
                
            except Exception as e:
                error_msg = str(e)
                if "rate_limit_exceeded" in error_msg:
                    # Extract wait time from error message
                    wait_time = 0
                    match = re.search(r'try again in (\d+)m(\d+.\d+)s', error_msg)
                    if match:
                        minutes, seconds = match.groups()
                        wait_time = int(minutes) * 60 + float(seconds)
                    else:
                        wait_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                    
                    logger.warning(f"Rate limit reached, waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error in Groq API request: {error_msg}")
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(self.base_delay * (2 ** attempt))
        
        return ""

    async def process_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Process a list of articles with summarization, classification, and analysis.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            List[Dict]: Processed articles with additional metadata
        """
        processed_articles = []
        
        for article in articles:
            try:
                processed = await self._process_single_article(article)
                processed_articles.append(processed)
            except Exception as e:
                logger.error(f"Error processing article {article.get('url')}: {str(e)}")
                continue
        
        return processed_articles

    async def _process_single_article(self, article: Dict) -> Dict:
        """Process a single article with all analysis steps."""
        try:
            # Generate unique ID from URL and title
            id_string = f"{article['url']}-{article['title']}"
            
            # Create processed article with only required fields
            processed = {
                'id': hashlib.md5(id_string.encode()).hexdigest(),
                'title': article['title'],
                'url': article['url'],
                'published_date': article.get('published_date', ''),
                'summary': await self._generate_summary(article['content'])
            }
            
            # Add image URL if available
            if article.get('image_url'):
                processed['image_url'] = article['image_url']
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing article {article.get('url')}: {str(e)}")
            raise

    async def _generate_summary(self, content: str) -> str:
        """Generate a concise summary of the article content."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert AI content summarizer specializing in creating concise, informative summaries. Follow these guidelines:

                    1. Focus on the most important and impactful information
                    2. Highlight key insights, findings, and conclusions
                    3. Maintain the original meaning while being concise
                    4. Use clear, professional language
                    5. Include relevant technical details when appropriate
                    6. IMPORTANT: Keep the summary under 2000 characters

                    Format your summary with:
                    - Main points first
                    - Supporting details if space allows
                    - Technical specifics if relevant"""
                },
                {
                    "role": "user",
                    "content": f"Please summarize the following content following the above guidelines. Remember to keep it under 2000 characters:\n\n{content}"
                }
            ]
            return await self._make_groq_request(messages, max_tokens=150, temperature=0.5)
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return ""