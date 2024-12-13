"""
Content processor module for AI Daily Report Generator.
"""
import logging
from typing import List, Dict
from groq import Groq  # This is based on README requirements

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Process and analyze news content."""
    
    def __init__(self, config: Dict):
        """Initialize the content processor with configuration."""
        self.config = config
        self.groq_client = Groq(api_key=config['groq_api_key'])
        self.categories = [
            'technical_innovation',
            'business_application',
            'policy_regulation',
            'research_progress'
        ]

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
        
        return self._sort_by_relevance(processed_articles)

    async def _process_single_article(self, article: Dict) -> Dict:
        """Process a single article with all analysis steps."""
        processed = article.copy()
        
        # Generate summary
        processed['summary'] = await self._generate_summary(article['content'])
        
        # # Classify content
        # processed['category'] = await self._classify_content(article['content'])
        
        # # Extract key information
        # processed['key_points'] = await self._extract_key_info(article['content'])
        
        # # Perform sentiment analysis
        # processed['sentiment'] = await self._analyze_sentiment(article['content'])
        
        # # Calculate relevance score
        processed['relevance_score'] = self._calculate_relevance(processed)
        
        return processed

    async def _generate_summary(self, content: str) -> str:
        """Generate a concise summary of the article content."""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes articles concisely."
                    },
                    {
                        "role": "user",
                        "content": f"Please summarize the following content:\n\n{content}"
                    }
                ],
                model="llama-3.3-70b-specdec",
                temperature=0.5,
                max_tokens=150
            )
            
            if response and hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message.content
                return message if message is not None else ""
            return ""
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return ""

    async def _classify_content(self, content: str) -> str:
        """Classify the article into predefined categories."""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a classifier that categorizes content into one of these categories: {', '.join(self.categories)}. Only respond with the category name, nothing else."
                    },
                    {
                        "role": "user",
                        "content": f"Classify this content into one of the specified categories:\n\n{content}"
                    }
                ],
                model="llama-3.3-70b-specdec",
                temperature=0.3,
                max_tokens=50
            )
            
            if response and hasattr(response, 'choices') and response.choices:
                category = response.choices[0].message.content
                return category.strip() if category is not None else "uncategorized"
            return "uncategorized"
            
        except Exception as e:
            logger.error(f"Error classifying content: {str(e)}")
            return "uncategorized"

    async def _extract_key_info(self, content: str) -> List[str]:
        """Extract key information points from the article."""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "Extract 3-5 key points from the content. Format each point as a separate line starting with '- '. Be concise and factual."
                    },
                    {
                        "role": "user",
                        "content": f"Extract key points from this content:\n\n{content}"
                    }
                ],
                model="llama-3.3-70b-specdec",
                temperature=0.3,
                max_tokens=200
            )
            
            if response and hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                if content:
                    # Split by newlines and filter out empty lines
                    points = [point.lstrip('- ').strip() for point in content.split('\n') if point.strip()]
                    return points
            return []
            
        except Exception as e:
            logger.error(f"Error extracting key info: {str(e)}")
            return []

    async def _analyze_sentiment(self, content: str) -> Dict:
        """Analyze the sentiment of the article."""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of the content. Respond in JSON format with exactly this structure: {\"score\": <float between -1 and 1>, \"label\": <\"positive\", \"negative\", or \"neutral\">}"
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the sentiment of this content:\n\n{content}"
                    }
                ],
                model="llama-3.3-70b-specdec",
                temperature=0.3,
                max_tokens=100
            )
            
            if response and hasattr(response, 'choices') and response.choices:
                import json
                try:
                    content = response.choices[0].message.content
                    if content:
                        result = json.loads(content)
                        return {
                            'score': float(result.get('score', 0.0)),
                            'label': result.get('label', 'neutral')
                        }
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error parsing sentiment response: {str(e)}")
            
            return {'score': 0.0, 'label': 'neutral'}
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {'score': 0.0, 'label': 'neutral'}

    def _calculate_relevance(self, article: Dict) -> float:
        """Calculate relevance score based on various factors."""
        score = 0.0
        
        # Factor 1: Sentiment strength
        sentiment_score = abs(article['sentiment']['score'])
        score += sentiment_score * 0.3
        
        # Factor 2: Key points count
        key_points_score = min(len(article['key_points']) / 5, 1.0)
        score += key_points_score * 0.3
        
        # Factor 3: Category relevance
        category_weights = {
            'technical_innovation': 1.0,
            'business_application': 0.8,
            'policy_regulation': 0.7,
            'research_progress': 0.9,
            'uncategorized': 0.5
        }
        score += category_weights.get(article['category'], 0.5) * 0.4
        
        return min(score, 1.0)

    def _sort_by_relevance(self, articles: List[Dict]) -> List[Dict]:
        """Sort articles by relevance score in descending order."""
        return sorted(
            articles,
            key=lambda x: x['relevance_score'],
            reverse=True
        ) 