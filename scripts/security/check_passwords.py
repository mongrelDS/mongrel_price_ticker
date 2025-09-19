#!/usr/bin/env python3
"""
Security Check Script - Check for hardcoded passwords and sensitive data
"""

import os
import re
import sys
from pathlib import Path

# Patterns to detect sensitive information
SENSITIVE_PATTERNS = [
    # Password patterns
    (r'password\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded password'),
    (r'pwd\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded password'),
    (r'passwd\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded password'),
    
    # API key patterns
    (r'api_key\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded API key'),
    (r'apikey\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded API key'),
    (r'access_token\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded access token'),
    
    # Email patterns (in code, not comments)
    (r'email\s*=\s*[\'"][^\'"]+@[^\'"]+[\'"]', 'Hardcoded email'),
    (r'username\s*=\s*[\'"][^\'"]+@[^\'"]+[\'"]', 'Hardcoded email'),
    
    # Database connection strings with hardcoded credentials (not variables)
    (r'mysql\+mysqlconnector://[^:]+:[^@]+@[^}]+', 'Hardcoded database connection'),
    (r'postgresql://[^:]+:[^@]+@[^}]+', 'Hardcoded database connection'),
    
    # Common sensitive patterns
    (r'secret\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded secret'),
    (r'token\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded token'),
]

# Files to exclude from scanning
EXCLUDE_PATTERNS = [
    '.env',
    '.env.example',
    '.git/',
    '__pycache__/',
    '.pytest_cache/',
    'venv/',
    'env/',
    'SECURITY_',
    'PASSWORD_',
    'NEXT_STEPS_',
]

def should_exclude_file(file_path):
    """Check if file should be excluded from scanning."""
    file_str = str(file_path)
    return any(pattern in file_str for pattern in EXCLUDE_PATTERNS)

def scan_file(file_path):
    """Scan a single file for sensitive patterns."""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped_line = line.strip()
                if stripped_line.startswith('#') or stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                    continue
                
                for pattern, description in SENSITIVE_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Skip if it's using variables (secure) or is in security check script
                        if ('{' in line and '}' in line and ('db_' in line or 'os.getenv' in line or 'self.' in line)) or 'check_passwords.py' in str(file_path):
                            continue
                        issues.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'issue': description,
                            'pattern': pattern
                        })
    
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
    
    return issues

def scan_directory(directory):
    """Scan all Python files in directory for sensitive patterns."""
    all_issues = []
    directory = Path(directory)
    
    for file_path in directory.rglob('*.py'):
        if should_exclude_file(file_path):
            continue
        
        issues = scan_file(file_path)
        all_issues.extend(issues)
    
    return all_issues

def main():
    """Main function to run security checks."""
    print("🔍 Running security checks for hardcoded passwords and sensitive data...")
    print("=" * 70)
    
    # Scan current directory
    issues = scan_directory('.')
    
    if not issues:
        print("✅ No hardcoded passwords or sensitive data found!")
        print("🎉 Your codebase looks secure!")
        return 0
    
    print(f"❌ Found {len(issues)} potential security issues:")
    print()
    
    for issue in issues:
        print(f"🚨 {issue['issue']}")
        print(f"   File: {issue['file']}:{issue['line']}")
        print(f"   Content: {issue['content']}")
        print()
    
    print("💡 Recommendations:")
    print("   - Move hardcoded credentials to environment variables")
    print("   - Use .env files for configuration")
    print("   - Never commit passwords or API keys to version control")
    print("   - Use os.getenv() to load environment variables")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
