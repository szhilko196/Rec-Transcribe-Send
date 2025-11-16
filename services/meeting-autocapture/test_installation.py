"""
Installation Verification Test Script
Tests all components of Meeting Auto Capture
"""
import os
import sys
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_success(text):
    """Print success message"""
    print(f"[PASS]  {text}")


def print_error(text):
    """Print error message"""
    print(f"[FAIL]  {text}")


def print_warning(text):
    """Print warning message"""
    print(f"[WARN]  {text}")


def test_python_version():
    """Test Python version"""
    print_header("Testing Python Version")
    version = sys.version_info

    if version.major == 3 and version.minor >= 10:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} (Need 3.10+)")
        return False


def test_dependencies():
    """Test required Python packages"""
    print_header("Testing Python Dependencies")

    required_packages = {
        'pydantic': 'pydantic',
        'dotenv': 'python-dotenv',
        'imapclient': 'imapclient',
        'icalendar': 'icalendar',
        'dateutil': 'python-dateutil',
        'playwright': 'playwright',
        'apscheduler': 'APScheduler'
    }

    missing = []

    for module, package in required_packages.items():
        try:
            __import__(module)
            print_success(f"{package}")
        except ImportError:
            print_error(f"{package} - NOT INSTALLED")
            missing.append(package)

    if missing:
        print_error(f"\nMissing packages: {', '.join(missing)}")
        print("\nInstall missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True


def test_playwright_browsers():
    """Test Playwright browser installation"""
    print_header("Testing Playwright Browsers")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Check if chromium is installed
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print_success("Chromium browser installed")
                return True
            except Exception as e:
                print_error(f"Chromium not installed: {e}")
                print("\nInstall Playwright browsers:")
                print("  playwright install chromium")
                return False

    except ImportError:
        print_error("Playwright not installed")
        return False


def test_directory_structure():
    """Test required directories"""
    print_header("Testing Directory Structure")

    required_dirs = [
        'src',
        'src/platform_handlers',
        'config',
        'data',
        'data/meetings',
        'data/meetings/pending',
        'data/meetings/in_progress',
        'data/meetings/completed',
        'data/browser_profiles',
        'logs'
    ]

    all_exist = True

    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print_success(f"{dir_path}/")
        else:
            print_warning(f"{dir_path}/ - MISSING (will be created)")
            os.makedirs(dir_path, exist_ok=True)

    return all_exist


def test_required_files():
    """Test required files exist"""
    print_header("Testing Required Files")

    required_files = [
        'requirements.txt',
        'README.md',
        'config/meeting_patterns.json',
        'config/.env.example',
        'src/main.py',
        'src/models.py',
        'src/email_monitor.py',
        'src/meeting_parser.py',
        'src/scheduler.py',
        'src/browser_joiner.py',
        'src/video_manager.py',
        'src/platform_handlers/__init__.py',
        'src/platform_handlers/base_handler.py',
        'src/platform_handlers/gpb_video.py',
        'src/platform_handlers/psbank_meeting.py'
    ]

    all_exist = True

    for file_path in required_files:
        if os.path.exists(file_path):
            print_success(file_path)
        else:
            print_error(f"{file_path} - MISSING")
            all_exist = False

    return all_exist


def test_imports():
    """Test module imports"""
    print_header("Testing Module Imports")

    # Add src to path
    sys.path.insert(0, 'src')

    modules = [
        'models',
        'email_monitor',
        'meeting_parser',
        'scheduler',
        'browser_joiner',
        'video_manager',
        'platform_handlers'
    ]

    all_imported = True

    for module in modules:
        try:
            __import__(module)
            print_success(f"{module}")
        except Exception as e:
            print_error(f"{module} - ERROR: {e}")
            all_imported = False

    return all_imported


def test_configuration():
    """Test configuration files"""
    print_header("Testing Configuration")

    # Check .env file
    if os.path.exists('config/.env'):
        print_success("config/.env exists")

        # Try to load it
        from dotenv import load_dotenv
        load_dotenv('config/.env')

        # Check required variables
        required_vars = [
            'MAC_IMAP_HOST',
            'MAC_IMAP_USER',
            'MAC_IMAP_PASSWORD'
        ]

        missing_vars = []
        for var in required_vars:
            if os.getenv(var):
                print_success(f"  {var} is set")
            else:
                print_warning(f"  {var} is NOT set")
                missing_vars.append(var)

        if missing_vars:
            print_warning(f"\nMissing environment variables: {', '.join(missing_vars)}")
            print("Please edit config/.env and set these variables")
            return False

        return True
    else:
        print_warning("config/.env does NOT exist")
        print("\nCreate config file:")
        print("  cp config/.env.example config/.env")
        print("  # Then edit config/.env with your credentials")
        return False


def test_ffmpeg():
    """Test ffmpeg installation"""
    print_header("Testing ffmpeg Installation")

    ffmpeg_path = "../../tools/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe"

    if os.path.exists(ffmpeg_path):
        print_success(f"ffmpeg found: {ffmpeg_path}")

        # Verify it works
        try:
            import subprocess
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version info
                version_line = result.stdout.split('\n')[0]
                print_success(f"  {version_line}")
                return True
            else:
                print_error("  ffmpeg found but not working")
                return False
        except Exception as e:
            print_error(f"  ffmpeg verification failed: {e}")
            return False
    else:
        print_error(f"ffmpeg NOT found at: {ffmpeg_path}")
        print("\nInstall ffmpeg:")
        print("  Run setup.bat and select 'Y' for automatic installation")
        print("  Or download from: https://www.gyan.dev/ffmpeg/builds/")
        return False


def main():
    """Main test runner"""
    print("\n" + "="*60)
    print("  MEETING AUTO CAPTURE - Installation Verification")
    print("="*60)

    tests = [
        ("Python Version", test_python_version),
        ("Python Dependencies", test_dependencies),
        ("Playwright Browsers", test_playwright_browsers),
        ("ffmpeg Installation", test_ffmpeg),
        ("Directory Structure", test_directory_structure),
        ("Required Files", test_required_files),
        ("Module Imports", test_imports),
        ("Configuration", test_configuration)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print_header("Test Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status:10} {test_name}")

    print("\n" + "-"*60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("-"*60)

    if passed == total:
        print_success("\nAll tests passed! Installation is complete.")
        print("\nYou can now run the service:")
        print("  python src/main.py")
        print("\nOr use the launch script:")
        print("  start.bat (Windows)")
        return 0
    else:
        print_error(f"\n{total - passed} test(s) failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
