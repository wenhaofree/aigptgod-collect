"""
Main application module for AI Daily Report Generator.
"""
import asyncio
import logging
from typing import Dict, List
from datetime import datetime

from utils.config import Config
from crawlers.news_crawler import NewsCrawler
from processors.content_processor import ContentProcessor
from generators.report_generator import ReportGenerator
from notion.notion_client import NotionSync

logger = logging.getLogger(__name__)

class AIReportGenerator:
    """Main application class."""
    
    def __init__(self, config_path: str = None):
        """Initialize the application."""
        # Load configuration
        self.config = Config(config_path)
        self.config.setup_logging()
        
        # Initialize components
        self.crawler = NewsCrawler(self.config.get('crawler'))
        self.processor = ContentProcessor(self.config.get('processor'))
        self.generator = ReportGenerator(self.config.get('generator'))
        self.notion_sync = NotionSync(self.config.get('notion'))
        
        logger.info("AI Report Generator initialized")

    async def run(self) -> None:
        """Run the report generation process."""
        try:
            # Step 1: Fetch news articles
            logger.info("Fetching news articles...")
            articles = await self.crawler.fetch_news()
            logger.info(f"Fetched {len(articles)} articles")
            
            if not articles:
                logger.warning("No articles found, stopping process")
                return
            
            # Step 2: Process articles
            logger.info("Processing articles...")
            processed_articles = await self.processor.process_articles(articles)
            logger.info(f"Processed {len(processed_articles)} articles")
            
            # Step 3: Generate report
            logger.info("Generating report...")
            report = await self.generator.generate_report(processed_articles)
            logger.info("Report generated successfully")
            
            # report = self.generator.load_report('2024-12-12')

            # Step 4: Sync to Notion (now synchronous)
            logger.info("Syncing report to Notion...")
            notion_url = self.notion_sync.sync_report(report)
            logger.info(f"Report synced to Notion: {notion_url}")
            
        except Exception as e:
            logger.error(f"Error in report generation process: {str(e)}")
            raise

async def run_scheduled():
    """Run the report generator on a schedule."""
    try:
        generator = AIReportGenerator()
        
        while True:
            current_time = datetime.now()
            logger.info(f"Starting scheduled run at {current_time}")
            
            await generator.run()
            
            # Wait for next interval
            interval = generator.config.get('crawler.update_interval', 3600)
            logger.info(f"Waiting {interval} seconds until next run")
            await asyncio.sleep(interval)
            
    except Exception as e:
        logger.error(f"Error in scheduled run: {str(e)}")
        raise

def main():
    """Main entry point."""
    try:
        # Run the async event loop
        asyncio.run(run_scheduled())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 