"""
Report generator module for AI Daily Report Generator.
"""
import logging
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate daily AI news reports."""
    
    def __init__(self, config: Dict):
        """Initialize the report generator with configuration."""
        self.config = config
        self.output_dir = Path(config.get('output_dir', 'data/reports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_report(self, articles: List[Dict]) -> Dict:
        """
        Generate a daily report from processed articles.
        
        Args:
            articles: List of processed article dictionaries
            
        Returns:
            Dict: Generated report with all sections
        """
        try:
            # Generate report with all articles
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'articles': [self._format_article(article) for article in articles],
                'metadata': self._generate_metadata(articles)
            }
            
            # Save report
            self._save_report(report)
            
            return report
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    def _format_article(self, article: Dict) -> Dict:
        """Format an article for the report."""
        formatted = {
            'id': article['id'],
            'title': article['title'],
            'summary': article['summary'],
            'url': article['url'],
            'published_date': article['published_date']
        }
        
        # Add optional image URL if available
        if article.get('image_url'):
            formatted['image_url'] = article['image_url']
            
        return formatted

    def _generate_metadata(self, articles: List[Dict]) -> Dict:
        """Generate report metadata."""
        return {
            'total_articles': len(articles),
            'generation_time': datetime.now().isoformat(),
            'version': '1.0'
        }

    def _save_report(self, report: Dict) -> None:
        """Save the report to a file."""
        try:
            date_str = report['date']
            file_path = self.output_dir / f"report_{date_str}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Report saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")
            raise

    def load_report(self, date_str: str) -> Dict:
        """
        Load a report from a JSON file.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Dict: The loaded report dictionary
            
        Raises:
            FileNotFoundError: If the report file doesn't exist
            JSONDecodeError: If the file content is not valid JSON
        """
        try:
            file_path = self.output_dir / f"report_{date_str}.json"
            
            if not file_path.exists():
                raise FileNotFoundError(f"Report file not found: {file_path}")
                
            with open(file_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
                
            logger.info(f"Report loaded from {file_path}")
            return report
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading report: {str(e)}")
            raise