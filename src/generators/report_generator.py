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
        self.sections = [
            'headlines',
            'technical_updates',
            'industry_news',
            'policy_updates'
        ]
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
            # Organize articles by section
            categorized = self._categorize_articles(articles)
            
            # Generate report sections
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'sections': {}
            }
            
            # Generate each section
            for section in self.sections:
                report['sections'][section] = self._generate_section(
                    section,
                    categorized.get(section, [])
                )
            
            # Add metadata
            report['metadata'] = self._generate_metadata(articles)
            
            # Save report
            self._save_report(report)
            
            return report
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    def _categorize_articles(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize articles into different sections."""
        categorized = {section: [] for section in self.sections}
        
        # Mapping from article categories to report sections
        category_mapping = {
            'technical_innovation': 'technical_updates',
            'business_application': 'industry_news',
            'policy_regulation': 'policy_updates',
            'research_progress': 'technical_updates'
        }
        
        for article in articles:
            # Top articles go to headlines
            if article['relevance_score'] > 0.8:
                categorized['headlines'].append(article)
            
            # Add to appropriate section based on category
            section = category_mapping.get(article['category'])
            if section:
                categorized[section].append(article)
        
        return categorized

    def _generate_section(self, section: str, articles: List[Dict]) -> Dict:
        """Generate content for a specific section."""
        return {
            'title': self._get_section_title(section),
            'articles': [
                self._format_article(article)
                for article in articles[:5]  # Limit to top 5 articles per section
            ]
        }

    def _format_article(self, article: Dict) -> Dict:
        """Format an article for the report."""
        return {
            'title': article['title'],
            'summary': article['summary'],
            'key_points': article['key_points'],
            'url': article['url'],
            'sentiment': article['sentiment']['label'],
            'source': article['source'],
            'published_date': article['published_date']
        }

    def _get_section_title(self, section: str) -> str:
        """Get the display title for a section."""
        titles = {
            'headlines': 'Today\'s Headlines',
            'technical_updates': 'Technical Developments',
            'industry_news': 'Industry Insights',
            'policy_updates': 'Policy and Regulation Updates'
        }
        return titles.get(section, section.title())

    def _generate_metadata(self, articles: List[Dict]) -> Dict:
        """Generate report metadata."""
        return {
            'total_articles': len(articles),
            'sources': list(set(a['source'] for a in articles)),
            'categories': list(set(a['category'] for a in articles)),
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