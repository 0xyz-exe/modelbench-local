import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def capture():
    print("Launching Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Overview
        print("Capturing 1. Overview...")
        page.goto("http://127.0.0.1:8000/", timeout=20000)
        page.wait_for_selector("text=Registered Models", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(OUT_DIR / "overview.png"))
        print("Saved docs/screenshots/overview.png")

        # 2. Models Page
        print("Capturing 2. Models...")
        page.locator("nav button:has-text('Models')").first.click()
        page.wait_for_selector("text=Discovered Local Models", timeout=10000)
        time.sleep(1.0)
        page.screenshot(path=str(OUT_DIR / "models.png"))
        print("Saved docs/screenshots/models.png")

        # 3. Benchmark Lab
        print("Capturing 3. Benchmark Lab...")
        page.locator("nav button:has-text('Benchmark Lab')").click()
        page.wait_for_selector("text=Benchmark Execution Lab", timeout=10000)
        time.sleep(1.0)
        page.screenshot(path=str(OUT_DIR / "benchmark_lab.png"))
        print("Saved docs/screenshots/benchmark_lab.png")

        # 4. Compare Models
        print("Capturing 4. Compare Models...")
        page.locator("nav button:has-text('Compare Models')").click()
        page.wait_for_selector("text=Model Comparison Matrix", timeout=10000)
        time.sleep(1.0)
        page.screenshot(path=str(OUT_DIR / "model_comparison.png"))
        print("Saved docs/screenshots/model_comparison.png")

        # 5. Datasets
        print("Capturing 5. Datasets...")
        page.locator("nav button:has-text('Datasets')").click()
        page.wait_for_selector("text=Benchmark Datasets", timeout=10000)
        time.sleep(1.0)
        page.screenshot(path=str(OUT_DIR / "datasets.png"))
        print("Saved docs/screenshots/datasets.png")

        # 6. Results History
        print("Capturing 6. Results History...")
        page.locator("nav button:has-text('Results History')").click()
        page.wait_for_selector("text=Results History & Reports", timeout=10000)
        time.sleep(1.0)
        page.screenshot(path=str(OUT_DIR / "results_history.png"))
        print("Saved docs/screenshots/results_history.png")

        # 7. System Monitor
        print("Capturing 7. System Monitor...")
        page.locator("nav button:has-text('System Monitor')").click()
        page.wait_for_selector("text=Hardware & System Telemetry", timeout=10000)
        time.sleep(1.0)
        page.screenshot(path=str(OUT_DIR / "system_monitor.png"))
        print("Saved docs/screenshots/system_monitor.png")

        browser.close()
        print("All screenshots successfully captured!")

if __name__ == "__main__":
    capture()
