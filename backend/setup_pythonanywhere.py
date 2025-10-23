#!/usr/bin/env python
"""
Setup script for PythonAnywhere deployment
This script helps configure the Django project for PythonAnywhere hosting
"""

import os
import subprocess
import sys

def run_command(command, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd,
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        return None

def setup_pythonanywhere():
    """Main setup function for PythonAnywhere"""

    print("🚀 Setting up Django project for PythonAnywhere...")

    # Check if we're on PythonAnywhere
    if 'PYTHONANYWHERE_DOMAIN' not in os.environ:
        print("⚠️  Warning: This doesn't appear to be running on PythonAnywhere")
        print("   Continuing anyway for testing purposes...")

    # Create virtual environment if it doesn't exist
    if not os.path.exists('venv'):
        print("📦 Creating virtual environment...")
        run_command('python -m venv venv')
    else:
        print("✅ Virtual environment already exists")

    # Activate virtual environment and install requirements
    print("📥 Installing requirements...")
    pip_install = 'source venv/bin/activate && pip install -r requirements.txt'
    result = run_command(pip_install)

    if result is None:
        print("❌ Failed to install requirements")
        return False

    # Run Django migrations
    print("🗄️  Running Django migrations...")
    migrate_cmd = 'source venv/bin/activate && python manage.py migrate'
    result = run_command(migrate_cmd)

    if result is None:
        print("❌ Failed to run migrations")
        return False

    # Collect static files
    print("📄 Collecting static files...")
    static_cmd = 'source venv/bin/activate && python manage.py collectstatic --noinput'
    result = run_command(static_cmd)

    if result is None:
        print("❌ Failed to collect static files")
        return False

    print("✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Set up your environment variables in PythonAnywhere dashboard")
    print("2. Configure scheduled tasks:")
    print("   - News scraping: python manage.py scrape_news (every 30 minutes)")
    print("   - Stock prices: python manage.py scrape_stock_prices (every 5 minutes)")
    print("3. Update ALLOWED_HOSTS in settings.py with your PythonAnywhere domain")

    return True

if __name__ == '__main__':
    success = setup_pythonanywhere()
    sys.exit(0 if success else 1)
