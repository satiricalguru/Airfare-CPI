import time
import os
import subprocess
from playwright.sync_api import sync_playwright

def smooth_mouse_move(page, start_x, start_y, end_x, end_y, steps=25, delay=0.02):
    for i in range(1, steps + 1):
        x = start_x + (end_x - start_x) * (i / steps)
        y = start_y + (end_y - start_y) * (i / steps)
        page.mouse.move(x, y)
        time.sleep(delay)

def record():
    output_dir = "/Users/jatinpandey/Antigravity/Airfare CPI/recordings"
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=output_dir,
            record_video_size={"width": 1280, "height": 800},
            device_scale_factor=1.5
        )
        page = context.new_page()

        print("1. Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(3.5) # Wait for 3D A320 model to fully load

        print("2. Interacting with 3D Airbus A320 (demonstrating localized color change)...")
        # Start outside plane
        page.mouse.move(100, 100)
        time.sleep(0.5)

        # Move mouse smoothly over Nose & Cockpit
        smooth_mouse_move(page, 100, 100, 760, 380, steps=30, delay=0.02)
        time.sleep(1.0) # Hover over cockpit / nose

        # Glide across fuselage
        smooth_mouse_move(page, 760, 380, 580, 370, steps=25, delay=0.025)
        time.sleep(0.8)

        # Glide down to CFM LEAP Engine nacelle
        smooth_mouse_move(page, 580, 370, 490, 440, steps=25, delay=0.025)
        time.sleep(0.8)

        # Glide out along Supercritical Swept Wing
        smooth_mouse_move(page, 490, 440, 340, 480, steps=25, delay=0.025)
        time.sleep(0.8)

        # Glide up to Empennage / Tail Stabilizer (Vstab)
        smooth_mouse_move(page, 340, 480, 200, 300, steps=30, delay=0.025)
        time.sleep(1.0)

        # Move away to show color fading smoothly back to original white
        smooth_mouse_move(page, 200, 300, 100, 100, steps=25, delay=0.02)
        time.sleep(1.0)

        # Move back over fuselage to show re-activation
        smooth_mouse_move(page, 100, 100, 550, 370, steps=25, delay=0.02)
        time.sleep(0.8)

        print("3. Scrolling to Booking Horizon Dynamics...")
        page.evaluate("window.scrollTo({ top: 750, behavior: 'smooth' })")
        time.sleep(1.5)

        # Click different horizon buttons
        horizon_buttons = page.query_selector_all("#volatility button")
        if len(horizon_buttons) >= 5:
            for btn in horizon_buttons:
                btn.click()
                time.sleep(0.7)

        print("4. Scrolling to Headline All-India CPI Area Chart...")
        page.evaluate("window.scrollTo({ top: 1400, behavior: 'smooth' })")
        time.sleep(1.5)

        # Switch chart time range tabs
        range_buttons = page.query_selector_all("#index button")
        for btn in range_buttons[:4]:
            btn.click()
            time.sleep(0.6)

        print("5. Scrolling to India Domestic Aviation Corridor Grid...")
        page.evaluate("window.scrollTo({ top: 2100, behavior: 'smooth' })")
        time.sleep(1.5)

        # Hover over city hubs
        hubs = page.query_selector_all("#network svg g")
        for hub in hubs[:5]:
            hub.hover()
            time.sleep(0.5)

        print("6. Scrolling to Heatmap & Econometric Formulation...")
        page.evaluate("window.scrollTo({ top: 2800, behavior: 'smooth' })")
        time.sleep(1.2)
        page.evaluate("window.scrollTo({ top: 3500, behavior: 'smooth' })")
        time.sleep(1.2)

        print("7. Scrolling to Scraper Fleet Diagnostics & Triggering Cycle...")
        page.evaluate("window.scrollTo({ top: 4150, behavior: 'smooth' })")
        time.sleep(1.2)

        # Click Trigger Scrape Cycle
        scrape_btn = page.query_selector("button:has-text('Trigger Scrape Cycle')")
        if scrape_btn:
            scrape_btn.click()
            time.sleep(3.6) # Wait for 4-stage ingestion cycle animation

        print("8. Scrolling to Developer API Playground...")
        page.evaluate("window.scrollTo({ top: 4800, behavior: 'smooth' })")
        time.sleep(1.5)

        # Click different endpoints on the left
        endpoints = page.query_selector_all("#api > div > div > div > div")
        for ep in endpoints[1:3]:
            ep.click()
            time.sleep(0.6)

        # Switch tabs in terminal
        for tab_name in ["cURL", "JavaScript", "Python", "Response (JSON)"]:
            tab = page.query_selector(f"#api button:has-text('{tab_name}')")
            if tab:
                tab.click()
                time.sleep(0.6)

        # Click Send Request
        send_btn = page.query_selector("#api button:has-text('Send Request')")
        if send_btn:
            send_btn.click()
            time.sleep(0.8)

        # Click Copy
        copy_btn = page.query_selector("#api button:has-text('Copy')")
        if copy_btn:
            copy_btn.click()
            time.sleep(0.8)

        print("9. Scrolling back to top & Opening MoSPI Bulletin...")
        page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
        time.sleep(1.5)

        bulletin_btn = page.query_selector("button:has-text('MoSPI Bulletin')")
        if bulletin_btn:
            bulletin_btn.click()
            time.sleep(2.0)
            close_btn = page.query_selector("button:has-text('Close Bulletin')")
            if close_btn:
                close_btn.click()
                time.sleep(1.0)

        # Final showcase view of the 3D plane
        smooth_mouse_move(page, 600, 200, 680, 420, steps=20, delay=0.02)
        time.sleep(1.5)

        # Close page to flush video recording
        video_path = page.video.path()
        page.close()
        context.close()
        browser.close()

        print(f"Video recorded to: {video_path}")

        # Convert to high-quality MP4 using ffmpeg
        mp4_path = "/Users/jatinpandey/Antigravity/Airfare CPI/airfare_cpi_demo.mp4"
        webm_path = "/Users/jatinpandey/Antigravity/Airfare CPI/airfare_cpi_demo.webm"

        # Copy original webm
        subprocess.run(["cp", video_path, webm_path], check=True)

        # Transcode to universal MP4 (H.264 + AAC)
        ffmpeg_cmd = [
            "/opt/homebrew/bin/ffmpeg",
            "-y",
            "-i", video_path,
            "-c:v", "libx264",
            "-preset", "slow",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            mp4_path
        ]
        print("Transcoding to MP4...")
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Final MP4 ready at: {mp4_path}")

if __name__ == "__main__":
    record()
