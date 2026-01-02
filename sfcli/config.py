"""
Configuration Module

Handles configuration and credential management.
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration manager for Salesforce CLI."""
    
    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            env_path: Optional path to .env file
        """
        if env_path:
            self.env_path = Path(env_path)
        else:
            # Look for .env in current directory or parent
            current = Path.cwd()
            if (current / '.env').exists():
                self.env_path = current / '.env'
            else:
                # Look in script directory
                script_dir = Path(__file__).parent.parent
                self.env_path = script_dir / '.env'
    
    @property
    def exists(self) -> bool:
        """Check if .env file exists."""
        return self.env_path.exists()
    
    def get_credential(self, key: str) -> Optional[str]:
        """
        Get a credential from environment.
        
        Args:
            key: Credential key (e.g., 'SF_USERNAME')
            
        Returns:
            Credential value or None
        """
        return os.getenv(key)
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration.
        
        Returns:
            Tuple of (is_valid, missing_keys)
        """
        required_keys = [
            'SF_USERNAME',
            'SF_PASSWORD',
            'SF_SECURITY_TOKEN',
            'SF_DOMAIN'
        ]
        
        missing = []
        for key in required_keys:
            if not os.getenv(key):
                missing.append(key)
        
        return len(missing) == 0, missing
    
    def create_template(self):
        """Create a template .env file."""
        template = """# Salesforce Credentials
SF_USERNAME=your.email@company.com
SF_PASSWORD=your_password
SF_SECURITY_TOKEN=your_security_token
SF_DOMAIN=login  # Use 'test' for sandbox, 'login' for production

# Optional Settings
# SF_API_VERSION=58.0
"""
        with open(self.env_path, 'w') as f:
            f.write(template)
        
        return self.env_path
