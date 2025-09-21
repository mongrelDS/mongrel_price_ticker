#!/usr/bin/env python3
"""
Enhanced Proxy Configuration Module
Provides proxy configuration for web scraping with multiple proxy credentials and automatic switching
"""

import os
import time
import random
from typing import Dict, Optional, Union, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ProxyCredentials:
    """Individual proxy credential set"""
    
    def __init__(self, username: str, password: str, city: str = ""):
        self.username = username
        self.password = password
        self.city = city
        self.usage_count = 0
        self.last_used = None
        self.is_blocked = False
    
    def __str__(self):
        return f"ProxyCredentials(username={self.username}, city={self.city}, usage_count={self.usage_count})"

class ProxyConfig:
    """
    Enhanced proxy configuration class with multiple credentials and automatic switching
    """
    
    def __init__(self):
        """Initialize proxy configuration with multiple credentials"""
        self.host = "residential.ipb.cloud"
        self.port = 7777
        
        # Define multiple proxy credentials
        self.credentials = [
            ProxyCredentials(
                username="customer-oxyl29185902-city-boston-sessid-aigR-sesstime-30",
                password="ykdszwucoa_O5o",
                city="Boston"
            ),
            ProxyCredentials(
                username="customer-mnft29185901-city-toronto-sessid-oUcO-sesstime-30",
                password="xyspgptxmm_J9v",
                city="Toronto"
            )
        ]
        
        self.current_credential_index = 0
        self.switch_threshold = 5  # Switch after 5 uses
        self.switch_on_error = True  # Switch immediately on error
        
        # Override with environment variables if available
        self.host = os.getenv('PROXY_HOST', self.host)
        self.port = int(os.getenv('PROXY_PORT', self.port))
    
    def get_current_credential(self) -> ProxyCredentials:
        """Get the current active credential"""
        return self.credentials[self.current_credential_index]
    
    def switch_to_next_credential(self) -> ProxyCredentials:
        """Switch to the next available credential"""
        # Find next available credential
        for i in range(len(self.credentials)):
            next_index = (self.current_credential_index + 1 + i) % len(self.credentials)
            if not self.credentials[next_index].is_blocked:
                self.current_credential_index = next_index
                return self.credentials[next_index]
        
        # If all are blocked, reset all and use first one
        print("⚠️ All credentials blocked, resetting...")
        for cred in self.credentials:
            cred.is_blocked = False
        self.current_credential_index = 0
        return self.credentials[0]
    
    def mark_credential_blocked(self, credential: ProxyCredentials):
        """Mark a credential as blocked"""
        credential.is_blocked = True
        print(f"🚫 Marked credential {credential.city} as blocked")
    
    def should_switch_credential(self) -> bool:
        """Check if we should switch credentials"""
        current = self.get_current_credential()
        return (current.usage_count >= self.switch_threshold or 
                current.is_blocked)
    
    def record_usage(self, success: bool = True):
        """Record usage of current credential"""
        current = self.get_current_credential()
        current.usage_count += 1
        current.last_used = time.time()
        
        if not success and self.switch_on_error:
            self.mark_credential_blocked(current)
            return self.switch_to_next_credential()
        elif self.should_switch_credential():
            return self.switch_to_next_credential()
        
        return current
    
    def get_proxy_dict(self) -> Dict[str, str]:
        """
        Get proxy configuration as dictionary for requests library
        
        Returns:
            Dict[str, str]: Proxy configuration dictionary
        """
        current = self.get_current_credential()
        proxy_url = f'http://{current.username}:{current.password}@{self.host}:{self.port}'
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def get_proxy_url(self) -> str:
        """
        Get proxy URL for Playwright and other libraries
        
        Returns:
            str: Proxy URL in format http://username:password@host:port
        """
        current = self.get_current_credential()
        return f'http://{current.username}:{current.password}@{self.host}:{self.port}'
    
    def get_playwright_proxy_config(self) -> Dict[str, Union[str, int]]:
        """
        Get proxy configuration for Playwright browser context
        
        Returns:
            Dict[str, Union[str, int]]: Playwright proxy configuration
        """
        current = self.get_current_credential()
        return {
            "server": f"http://{self.host}:{self.port}",
            "username": current.username,
            "password": current.password
        }
    
    def get_selenium_proxy_config(self) -> Dict[str, str]:
        """
        Get proxy configuration for Selenium WebDriver
        
        Returns:
            Dict[str, str]: Selenium proxy configuration
        """
        return {
            'http': f'{self.host}:{self.port}',
            'https': f'{self.host}:{self.port}',
            'ftp': f'{self.host}:{self.port}'
        }
    
    def validate_proxy_config(self) -> bool:
        """
        Validate proxy configuration
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        return (self.host and self.port and 
                len(self.credentials) > 0 and
                all(cred.username and cred.password for cred in self.credentials))
    
    def get_credential_stats(self) -> Dict[str, any]:
        """Get statistics about credential usage"""
        return {
            'total_credentials': len(self.credentials),
            'active_credential': self.current_credential_index,
            'blocked_credentials': sum(1 for cred in self.credentials if cred.is_blocked),
            'credentials': [
                {
                    'city': cred.city,
                    'usage_count': cred.usage_count,
                    'is_blocked': cred.is_blocked,
                    'last_used': cred.last_used
                }
                for cred in self.credentials
            ]
        }
    
    def reset_all_credentials(self):
        """Reset all credentials (unblock and reset usage counts)"""
        for cred in self.credentials:
            cred.usage_count = 0
            cred.is_blocked = False
            cred.last_used = None
        self.current_credential_index = 0
        print("🔄 All credentials reset")
    
    def __str__(self) -> str:
        """
        String representation of proxy configuration (without password)
        
        Returns:
            str: Proxy configuration string
        """
        current = self.get_current_credential()
        return f"ProxyConfig(host={self.host}, port={self.port}, current={current.city}, usage={current.usage_count})"
    
    def __repr__(self) -> str:
        """
        Detailed string representation of proxy configuration
        
        Returns:
            str: Detailed proxy configuration string
        """
        stats = self.get_credential_stats()
        return f"ProxyConfig(host='{self.host}', port={self.port}, credentials={stats['total_credentials']}, active={stats['active_credential']})"


# Global proxy configuration instance
_proxy_config_instance = None

def get_proxy_config() -> ProxyConfig:
    """
    Get proxy configuration instance (singleton pattern)
    
    Returns:
        ProxyConfig: Configured proxy instance
    """
    global _proxy_config_instance
    if _proxy_config_instance is None:
        _proxy_config_instance = ProxyConfig()
    return _proxy_config_instance


def get_proxy_for_playwright() -> Dict[str, Union[str, int]]:
    """
    Get proxy configuration specifically for Playwright
    
    Returns:
        Dict[str, Union[str, int]]: Playwright proxy configuration
    """
    config = get_proxy_config()
    return config.get_playwright_proxy_config()


def get_proxy_for_requests() -> Dict[str, str]:
    """
    Get proxy configuration specifically for requests library
    
    Returns:
        Dict[str, str]: Requests proxy configuration
    """
    config = get_proxy_config()
    return config.get_proxy_dict()


def get_proxy_for_selenium() -> Dict[str, str]:
    """
    Get proxy configuration specifically for Selenium
    
    Returns:
        Dict[str, str]: Selenium proxy configuration
    """
    config = get_proxy_config()
    return config.get_selenium_proxy_config()


def record_proxy_usage(success: bool = True):
    """
    Record proxy usage and handle automatic switching
    
    Args:
        success (bool): Whether the request was successful
    """
    config = get_proxy_config()
    return config.record_usage(success)


def switch_proxy_credential():
    """
    Manually switch to the next proxy credential
    
    Returns:
        ProxyCredentials: The new active credential
    """
    config = get_proxy_config()
    return config.switch_to_next_credential()


def get_proxy_stats() -> Dict[str, any]:
    """
    Get proxy usage statistics
    
    Returns:
        Dict[str, any]: Statistics about proxy usage
    """
    config = get_proxy_config()
    return config.get_credential_stats()


def reset_proxy_credentials():
    """Reset all proxy credentials"""
    config = get_proxy_config()
    config.reset_all_credentials()


def test_proxy_connection() -> bool:
    """
    Test proxy connection (basic validation)
    
    Returns:
        bool: True if proxy configuration is valid, False otherwise
    """
    config = get_proxy_config()
    return config.validate_proxy_config()


# Example usage and testing
if __name__ == "__main__":
    print("🔧 Enhanced Proxy Configuration Module")
    print("=" * 50)
    
    # Test proxy configuration
    config = get_proxy_config()
    
    print(f"Proxy Host: {config.host}")
    print(f"Proxy Port: {config.port}")
    print(f"Total Credentials: {len(config.credentials)}")
    print(f"Configuration Valid: {config.validate_proxy_config()}")
    
    print("\n📋 Credential Details:")
    print("-" * 30)
    for i, cred in enumerate(config.credentials):
        print(f"  {i+1}. {cred.city}: {cred.username[:20]}... (usage: {cred.usage_count})")
    
    print("\n📊 Current Active Credential:")
    current = config.get_current_credential()
    print(f"  City: {current.city}")
    print(f"  Username: {current.username}")
    print(f"  Usage Count: {current.usage_count}")
    print(f"  Is Blocked: {current.is_blocked}")
    
    print("\n📋 Configuration Examples:")
    print("-" * 30)
    
    print("\n1. For Playwright:")
    playwright_config = get_proxy_for_playwright()
    for key, value in playwright_config.items():
        if key == 'password':
            print(f"   {key}: {'*' * len(str(value))}")
        else:
            print(f"   {key}: {value}")
    
    print("\n2. For Requests:")
    requests_config = get_proxy_for_requests()
    for key, value in requests_config.items():
        print(f"   {key}: {value[:50]}...")
    
    print("\n3. For Selenium:")
    selenium_config = get_proxy_for_selenium()
    for key, value in selenium_config.items():
        print(f"   {key}: {value}")
    
    print("\n🔄 Testing Credential Switching:")
    print("-" * 30)
    
    # Test switching
    print("Current credential:", config.get_current_credential().city)
    new_cred = switch_proxy_credential()
    print("After switch:", new_cred.city)
    
    # Test usage recording
    print("\n📈 Testing Usage Recording:")
    record_proxy_usage(success=True)
    record_proxy_usage(success=True)
    record_proxy_usage(success=False)  # This should trigger a switch
    
    print("\n📊 Final Stats:")
    stats = get_proxy_stats()
    for cred_info in stats['credentials']:
        print(f"  {cred_info['city']}: usage={cred_info['usage_count']}, blocked={cred_info['is_blocked']}")
    
    print(f"\n✅ Enhanced proxy configuration ready for use!")
