"""Adapt this two-step browser test to the engineer's English scenario.

Run with the Playwright interpreter, from the exported kit's parent directory:
python -m presentation_tools.example --url http://127.0.0.1:8000 \
    --expected-text 'Welcome' --evidence /project/evidence/welcome/run-001 \
    --ffmpeg /opt/playwright/browsers/ffmpeg-1011/ffmpeg-linux

The ffmpeg revision above is illustrative; locate the installed encoder.
Public operation: ``main``. All host discovery stays at this entry point.
"""
import argparse
import importlib
from pathlib import Path

from .producer import Script, ScriptStep
from .recording import Recording

__all__ = ["main"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--ffmpeg", required=True)
    args = parser.parse_args()
    playwright = importlib.import_module("playwright.sync_api")
    script = Script(
        goal="Verify the application's welcome page survives a reload.",
        stack=(("Browser", "Chromium driven by Playwright"),), illustrates=(),
        steps=(
            ScriptStep("Open the application", "Navigate to the application.", args.expected_text),
            ScriptStep("Reload", "Reload the page.", args.expected_text),
        ),
    )
    recording = Recording(args.evidence, script=script, scenario_id="welcome",
                          title="Welcome page", summary=script.goal, ffmpeg=(args.ffmpeg,))
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800},
                                      record_video_dir=str(args.evidence / "raw"))
        page = context.new_page()

        def open_application() -> None:
            page.goto(args.url)
            playwright.expect(page.get_by_text(args.expected_text, exact=True)).to_be_visible()

        def reload_application() -> None:
            page.reload()
            playwright.expect(page.get_by_text(args.expected_text, exact=True)).to_be_visible()

        try:
            recording.action(page, 1, "Open the application and check its welcome message", open_application)
            recording.action(page, 2, "Reload and check the message remains visible", reload_application)
        finally:
            try:
                recording.finish()
            finally:
                context.close()
                browser.close()


if __name__ == "__main__":
    main()
