
import asyncio
import argparse
import random
from playwright.async_api import async_playwright

VIDEO_URL = "https://www.youtube.com/watch?v=cdKop6aixVE"  # up to 4k, no ads
EXPERIMENT_DURATION = 10 # how long the video should play in the experiment (in seconds) # TODO - set a real duration
QUALITIES = [480, 2160]


"""
Under target/release add the energibridge executable (cargo build -- release) so we can call the command
example run:
python run_experiment.py --qualities 480 2160
"""


async def run_all_iterations():
    # represent each iteration with a list entry
    quality_list = []
    for q in QUALITIES:
        quality_list.extend([q] * 2) # this is only 2 for testing, should be 30
    print("qualities are" + str(quality_list))

    # randomly choose between the two cases
    random.shuffle(quality_list)

    for i, quality in enumerate(quality_list, start=1):
        output_file = f"./results/q{quality}/run_{i:02d}.csv"
        print(f"\n=== Run {i} | Quality {quality}p ===")
        await run_experiment(quality, output_file)
        print(f"\n=== Finished, sleeping in between")
        await asyncio.sleep(10000)


async def run_experiment(quality, output_file):
    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            "--autoplay-policy=no-user-gesture-required",
            "--incognito",
        ],
    )

    # incognito context with cache disabled
    context = await browser.new_context(
        viewport={"width": 1512, "height": 982},  # macbook 14 size
    )
    await context.set_extra_http_headers({"Cache-Control": "no-cache"})

    page = await context.new_page()
    print("Browser ready")

    await page.goto(VIDEO_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # accept cookies
    try:
        await page.click('button:has-text("Accept all")', timeout=5000)
        await page.wait_for_timeout(1000)
    except Exception:
        pass

    # pause the video
    try:
        await page.click('button.ytp-play-button', timeout=5000)
    except Exception:
        pass

    await page.wait_for_timeout(3000)
    print("Video loaded")

    # set quality
    await page.mouse.move(960, 540)
    await page.wait_for_timeout(1000)
    await page.locator('button.ytp-settings-button').hover()
    await page.wait_for_timeout(500)
    await page.locator('button.ytp-settings-button').click()
    await page.wait_for_timeout(1000)
    await page.click('div.ytp-menuitem-label:has-text("Quality")')
    await page.wait_for_timeout(1000)

    await page.click(f'div.ytp-menuitem-label:has-text("{quality}")')
    await page.wait_for_timeout(1000)

    print(f"Quality set to {quality}p")

    # enter fullscreen
    await page.keyboard.press('f')
    await page.wait_for_timeout(1000)

    # click play
    await page.locator('button.ytp-play-button').click()
    await page.wait_for_timeout(3000)

    print("Playing... -> Ready to start measuring!!")

    # measurement
    print(f"Measuring {EXPERIMENT_DURATION}s at {quality}p...")

    # start measurement with release
    await start_energibridge(output_file)

    await page.wait_for_timeout(EXPERIMENT_DURATION * 1000)

    print("Measurement done.")

    # close the browser
    await browser.close()
    await playwright.stop()

    print("Browser closed")


async def start_energibridge(output):
    print("Starting energibridge.")
    process = await asyncio.create_subprocess_exec(
        "target/release/energibridge",
        "-o", output,
        "--summary",
        "sleep", str(EXPERIMENT_DURATION)
    )
    await process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualities", nargs="+", type=int, required=True) # f.e. 480 2160

    # old output file argument, currently not used
    parser.add_argument("--output", required=False) # f.e. ./results/q480/run_01.csv

    args = parser.parse_args()
    QUALITIES = args.qualities
    asyncio.run(run_all_iterations())