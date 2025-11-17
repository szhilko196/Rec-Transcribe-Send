"""
Test jvc.inspider.ru page - wait for dynamic content and take screenshot
"""
from playwright.sync_api import sync_playwright
import time

meeting_url = "https://jvc.inspider.ru/e611663b580bf20c2029c839ce3bf933"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print(f"Navigating to {meeting_url}...")
    page.goto(meeting_url, wait_until='networkidle', timeout=30000)

    print("\nWaiting 5 seconds for dynamic content...")
    time.sleep(5)

    print(f"\n=== Page Title ===")
    print(page.title())

    print(f"\n=== Page URL ===")
    print(page.url)

    # Take screenshot
    screenshot_path = "jvc_page_screenshot.png"
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"\nScreenshot saved to: {screenshot_path}")

    # Get page HTML
    html = page.content()
    with open("jvc_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML saved to: jvc_page.html")

    # Try to find any visible elements
    print("\n=== Looking for visible inputs ===")
    all_inputs = page.locator('input').all()
    print(f"Total input elements: {len(all_inputs)}")
    for i, inp in enumerate(all_inputs):
        if inp.is_visible():
            print(f"\nVisible input {i+1}:")
            print(f"  Type: {inp.get_attribute('type')}")
            print(f"  Name: {inp.get_attribute('name')}")
            print(f"  ID: {inp.get_attribute('id')}")
            print(f"  Placeholder: {inp.get_attribute('placeholder')}")

    print("\n=== Looking for visible buttons ===")
    all_buttons = page.locator('button').all()
    print(f"Total button elements: {len(all_buttons)}")
    for i, btn in enumerate(all_buttons):
        if btn.is_visible():
            print(f"\nVisible button {i+1}:")
            print(f"  Text: {btn.text_content()}")
            print(f"  Class: {btn.get_attribute('class')}")

    # Try to find text "Войти"
    print("\n=== Looking for 'Войти' text ===")
    guest_elements = page.get_by_text("Войти", exact=False).all()
    print(f"Found {len(guest_elements)} elements with 'Войти' text")

    print("\nKeeping browser open for 30 seconds so you can inspect...")
    time.sleep(30)

    browser.close()
