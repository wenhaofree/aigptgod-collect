"""
Notion integration module for AI Daily Report Generator.
"""
import logging
from typing import Dict, List
from datetime import datetime
from notion_client import Client

logger = logging.getLogger(__name__)

class NotionSync:
    """Sync reports to Notion workspace."""
    
    def __init__(self, config: Dict):
        """Initialize the Notion client with configuration."""
        self.config = config
        
        # Get API key from config
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("Notion API key not found in configuration")
            
        self.client = Client(auth=api_key)
        self.database_id = config.get('database_id')
        
        if not self.database_id:
            raise ValueError("Notion database ID not found in configuration")

    def sync_report(self, report: Dict) -> str:
        """
        Sync a report to Notion database.
        
        Args:
            report: Report dictionary to sync
            
        Returns:
            str: URL of the created Notion page
        """
        try:
            # Try to find today's page
            existing_page = self._find_today_page()
            
            if existing_page:
                # If page exists, add articles to it
                logger.info("Found existing page for today, adding articles...")
                self._add_articles(existing_page['id'], report['articles'])
                return existing_page['url']
            else:
                # If no page exists, create new one
                logger.info("Creating new page for today...")
                page = self._create_report_page(report)
                self._add_articles(page['id'], report['articles'])
                return page['url']
                
        except Exception as e:
            logger.error(f"Error syncing report to Notion: {str(e)}")
            raise

    def _find_today_page(self) -> Dict:
        """
        Find today's report page if it exists.
        
        Returns:
            Dict: Page object if found, None otherwise
        """
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "and": [
                        {
                            "property": "date",
                            "date": {
                                "equals": today
                            }
                        },
                        {
                            "property": "category",
                            "select": {
                                "equals": "AI Daily Report"
                            }
                        }
                    ]
                }
            )
            
            if response['results']:
                return response['results'][0]
            return None
            
        except Exception as e:
            logger.error(f"Error finding today's page: {str(e)}")
            return None

    def _create_report_page(self, report: Dict) -> Dict:
        """Create the main report page in Notion."""
        try:
            # Create the page first
            page = self.client.pages.create(
                parent={'database_id': self.database_id},
                properties=self._get_page_properties(report)
            )
            
            # Update the page to add cover image
            self.client.pages.update(
                page_id=page['id'],
                cover={
                    "type": "external",
                    "external": {
                        "url": "https://img.wenhaofree.com/AIDaily-01.png"
                    }
                }
            )
            
            return page
            
        except Exception as e:
            logger.error(f"Error creating report page: {str(e)}")
            raise
            
    def _get_page_properties(self, report: Dict) -> Dict:
        """Get page properties for Notion page creation."""
        # Get all article IDs for this report
        article_ids = [article['id'] for article in report.get('articles', [])]
        
        return {
            'title': {  # This is the title property
                'title': [
                    {
                        'text': {
                            'content': f"【AI Daily Report】{report['date']}"
                        }
                    }
                ]
            },
            'type': {
                'select': {
                    'name': 'Post'  # Based on screenshot
                }
            },
            'status': {
                'select': {
                    'name': 'Published'  # Based on screenshot
                }
            },
            'date': {
                'date': {
                    'start': datetime.strptime(report['date'], '%Y-%m-%d').date().isoformat()
                }
            },
            'category': {
                'select': {
                    'name': 'AI Daily Report'  # Based on screenshot
                }
            },
            'tags': {
                'multi_select': [
                    {'name': 'AI'},
                ]
            },
            'article_ids': {  # Store all article IDs in a multi-select property
                'multi_select': [{'name': article_id} for article_id in article_ids]
            }
        }

    def _add_articles(self, parent_id: str, articles: List[Dict]) -> None:
        """Add articles as blocks in the page."""
        try:
            blocks = []
            added_articles = []
            
            for article in articles:
                # Check if article already exists in any Notion page
                if article.get('id') and self._article_exists(article['id']):
                    logger.info(f"Article {article['title']} already exists in Notion, skipping...")
                    continue

                # Add article title with link
                blocks.append({
                    'type': 'heading_2',
                    'heading_2': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {
                                    'content': article['title'],
                                    'link': {'url': article['url']}
                                }
                            }
                        ]
                    }
                })
                
                # Add summary
                if article.get('summary'):
                    blocks.append({
                        'type': 'paragraph',
                        'paragraph': {
                            'rich_text': [
                                {
                                    'type': 'text',
                                    'text': {'content': article['summary']}
                                }
                            ]
                        }
                    })
                
                # Add image if available
                if article.get('image_url'):
                    blocks.append({
                        'type': 'image',
                        'image': {
                            'type': 'external',
                            'external': {
                                'url': article['image_url']
                            }
                        }
                    })
                
                # Add metadata (published date)
                blocks.append({
                    'type': 'bulleted_list_item',
                    'bulleted_list_item': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {
                                    'content': f"Published: {article['published_date']}"
                                }
                            }
                        ]
                    }
                })
                
                # Add divider between articles
                blocks.append({
                    'type': 'divider',
                    'divider': {}
                })
                
                added_articles.append(article['id'])
            
            if blocks:  # Only append if there are new articles
                # Add the blocks
                self.client.blocks.children.append(
                    block_id=parent_id,
                    children=blocks
                )
                
                # Update the page's article_ids property to include newly added articles
                if added_articles:
                    self.client.pages.update(
                        page_id=parent_id,
                        properties={
                            'article_ids': {
                                'multi_select': [{'name': article_id} for article_id in added_articles]
                            }
                        }
                    )
            
        except Exception as e:
            logger.error(f"Error adding articles: {str(e)}")
            raise

    def _article_exists(self, article_id: str) -> bool:
        """Check if an article already exists in any Notion page by its content ID."""
        try:
            # Query all pages in the database
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "article_ids",  # This is a multi-select property in Notion
                    "multi_select": {
                        "contains": article_id
                    }
                }
            )
            return len(response['results']) > 0
        except Exception as e:
            logger.error(f"Error checking article existence: {str(e)}")
            return False

    def _cleanup_old_reports(self) -> None:
        """Clean up old reports based on retention policy."""
        try:
            retention_days = self.config.get('retention_days', 30)
            cutoff_date = (
                datetime.now()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .isoformat()
            )
            
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    'property': 'date',  # Using the date property from your database
                    'date': {
                        'before': cutoff_date
                    }
                }
            )
            
            # Archive old pages
            for page in response['results']:
                self.client.pages.update(
                    page_id=page['id'],
                    archived=True
                )
            
            logger.info(f"Cleaned up {len(response['results'])} old reports")
        except Exception as e:
            logger.error(f"Error cleaning up old reports: {str(e)}")
            raise 