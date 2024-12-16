"""
Configuration utility module for AI Daily Report Generator.
"""
import os
import logging
import yaml
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        # Load environment variables from .env file
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
        else:
            logger.warning(".env file not found")
            
        self.config_path = config_path or os.getenv('CONFIG_PATH', 'config/config.yaml')
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                logger.warning(f"Config file not found at {self.config_path}, using default configuration")
                return self._get_default_config()
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Merge with defaults and environment variables
            merged_config = self._get_default_config()
            if config:
                self._merge_configs(merged_config, config)
            
            # Override with environment variables
            self._override_from_env(merged_config)
            
            return merged_config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            # News sources configuration
            'news_sources': {
                'techcrunch': {
                    'type': 'rsshub',
                    'feed_url': 'https://rsshub.app/techcrunch/news',
                    'keywords': ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'gpt', 'llm'],
                    'parser_config': {
                        'title_selector': 'title',
                        'content_selector': 'description',
                        'link_selector': 'link',
                        'date_selector': 'pubDate'
                    }
                }
            },
            
            # Proxy settings
            'proxy_settings': {
                'enabled': True,
                'http': 'http://127.0.0.1:7890',
                'https': 'http://127.0.0.1:7890'
            },
            
            # Crawler configuration
            'crawler': {
                'update_interval': 3600,  # 1 hour
                'max_articles_per_source': 50
            },
            
            # Content processor configuration
            'processor': {
                'groq_api_key': os.getenv('GROQ_API_KEY', ''),
                'summary_max_length': 200,
                'min_relevance_score': 0.5
            },
            
            # Report generator configuration
            'generator': {
                'output_dir': 'data/reports',
                'max_articles_per_section': 5,
                'report_format': 'json'
            },
            
            # Notion configuration
            'notion': {
                'api_key': os.getenv('NOTION_API_KEY', ''),
                'database_id': os.getenv('NOTION_DATABASE_ID', ''),
                'auto_cleanup': True,
                'retention_days': 30
            },
            
            # Logging configuration
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/ai_report_generator.log'
            }
        }

    def _merge_configs(self, base: Dict, override: Dict) -> None:
        """Recursively merge override config into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def _override_from_env(self, config: Dict) -> None:
        """Override configuration with environment variables."""
        # Map of config keys to environment variables
        env_mapping = {
            'processor.groq_api_key': 'GROQ_API_KEY',
            'notion.api_key': 'NOTION_API_KEY',
            'notion.database_id': 'NOTION_DATABASE_ID'
        }
        
        for config_path, env_var in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value:
                # Split the config path and set the value
                parts = config_path.split('.')
                current = config
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = env_value

    def _validate_config(self) -> None:
        """Validate configuration values."""
        required_env_vars = {
            'GROQ_API_KEY': 'processor.groq_api_key',
            'NOTION_API_KEY': 'notion.api_key',
            'NOTION_DATABASE_ID': 'notion.database_id'
        }
        
        missing_vars = []
        for env_var, config_path in required_env_vars.items():
            if not self._get_nested_value(config_path):
                missing_vars.append(env_var)
        
        if missing_vars:
            logger.warning(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def _get_nested_value(self, path: str) -> any:
        """Get nested configuration value using dot notation."""
        current = self.config
        for key in path.split('.'):
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def get(self, key: str, default: any = None) -> any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key in dot notation
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        value = self._get_nested_value(key)
        return value if value is not None else default

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        log_config = self.config['logging']
        
        # Create logs directory if it doesn't exist
        log_file = Path(log_config['file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        ) 