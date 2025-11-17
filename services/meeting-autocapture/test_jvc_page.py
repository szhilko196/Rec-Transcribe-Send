"""
Quick test to inspect jvc.inspider.ru page and find correct selectors
"""
from playwright.sync_api import sync_playwright
import time

meeting_url = "https://jvc.inspider.ru/e611663b580bf20c2029c839ce3bf933"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print(f"Navigating to {meeting_url}...")
    page.goto(meeting_url, wait_until='networkidle', timeout=30000)

    print("\nWaiting 3 seconds for page to load...")
    time.sleep(3)

    print("\n=== Page Title ===")
    print(page.title())

    print("\n=== All input fields ===")
    inputs = page.query_selector_all('input')
    for i, inp in enumerate(inputs):
        print(f"{i+1}. Tag: input")
        print(f"   Type: {inp.get_attribute('type')}")
        print(f"   Name: {inp.get_attribute('name')}")
        print(f"   ID: {inp.get_attribute('id')}")
        print(f"   Class: {inp.get_attribute('class')}")
        print(f"   Placeholder: {inp.get_attribute('placeholder')}")
        print(f"   Visible: {inp.is_visible()}")
        print()

    print("\n=== All buttons ===")
    buttons = page.query_selector_all('button')
    for i, btn in enumerate(buttons):
        print(f"{i+1}. Tag: button")
        print(f"   Type: {btn.get_attribute('type')}")
        print(f"   Class: {btn.get_attribute('class')}")
        print(f"   ID: {btn.get_attribute('id')}")
        print(f"   Text content: {btn.text_content()}")
        print(f"   Visible: {btn.is_visible()}")
        print()

    print("\nPress Ctrl+C when done inspecting...")
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print("\nClosing browser...")

    browser.close()
