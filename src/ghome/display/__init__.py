import asyncio
import os
from ssl import CHANNEL_BINDING_TYPES
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING or sys.platform == "darwin":
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
else:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

from ghome.data.train_time import Departure, get_departure_times_for_stop, get_feeds

STOP_ID = "R32N"
DISPLAY_WIDTH = 64
CHAR_WIDTH = 6  # 5x7 font: 5px glyph + ~1px spacing
CHAR_HEIGHT = 8  # 5x7 font: 7px glyph + ~1px spacing
FONT = "5x7.bdf"

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

font_dir = os.path.abspath(os.path.dirname(__file__) + "/../../../fonts")
font = graphics.Font()
font.LoadFont(os.path.join(font_dir, FONT))

WHITE = graphics.Color(255, 255, 255)

LINE_COLORS: dict[str, graphics.Color] = {
    line: color
    for lines, color in [
        (("1", "2", "3"), graphics.Color(238, 53, 46)),
        (("4", "5", "6"), graphics.Color(0, 147, 60)),
        (("7",), graphics.Color(185, 51, 173)),
        (("A", "C", "E"), graphics.Color(0, 57, 166)),
        (("B", "D", "F", "M"), graphics.Color(255, 99, 25)),
        (("G",), graphics.Color(108, 190, 69)),
        (("J", "Z"), graphics.Color(153, 102, 51)),
        (("L",), graphics.Color(167, 169, 172)),
        (("N", "Q", "R", "W"), graphics.Color(252, 204, 10)),
        (("S",), graphics.Color(128, 129, 131)),
    ]
    for line in lines
}


@dataclass(frozen=True)
class TickerSegment:
    text: str
    color: graphics.Color
    x_offset: int


def build_ticker_segments(
    direction: str,
    departures: list[Departure],
) -> tuple[list[TickerSegment], int]:
    segments: list[TickerSegment] = []
    x = 1
    if not departures:
        message = "Error"
        return [
            TickerSegment(message, WHITE, x),
        ], len(message) * CHAR_WIDTH

    # up arrow or down arrow depending on direction
    dir = "\u2191" if direction == "N" else "\u2193"
    segments.append(TickerSegment(dir, WHITE, x))
    x += CHAR_WIDTH
    last_line: str | None = None
    for i, dep in enumerate(departures):
        if dep.line != last_line:
            last_line = dep.line
            line_color = LINE_COLORS.get(dep.line, WHITE)
            if i > 0:
                x += CHAR_WIDTH
            segments.append(TickerSegment(dep.line, line_color, x))
        x += CHAR_WIDTH
        minutes_str = str(dep.minutes)
        segments.append(TickerSegment(minutes_str, WHITE, x))
        x += len(minutes_str) * CHAR_WIDTH - 1
    return segments, x


def draw_ticker(
    canvas,
    segments: list[TickerSegment],
    scroll_pos: int,
    y: int,
) -> None:
    for seg in segments:
        x = seg.x_offset + scroll_pos
        if -len(seg.text) * CHAR_WIDTH < x < DISPLAY_WIDTH:
            graphics.DrawText(canvas, font, x, y, seg.color, seg.text)


# --- Background data fetch ---

_departures: list[Departure] = []
_lock = threading.Lock()


def _fetch_worker() -> None:
    async def _loop() -> None:
        while True:
            try:
                feeds = await get_feeds()
                deps = get_departure_times_for_stop(feeds, STOP_ID)
                with _lock:
                    _departures[:] = deps
            except Exception:
                pass  # keep displaying last good data on error
            await asyncio.sleep(15)

    asyncio.run(_loop())


threading.Thread(target=_fetch_worker, daemon=True).start()

# --- Main display loop ---

PIXELS_PER_SEC = 20

scroll_pos = DISPLAY_WIDTH
last_advance = time.monotonic()

try:
    while True:
        with _lock:
            deps = list(_departures)

        # deps = [Departure("R", 3), Departure("R", 8), Departure("D", 12)]

        segments, ticker_width = build_ticker_segments("N", deps[:3])

        now = time.monotonic()
        if now - last_advance >= 1 / PIXELS_PER_SEC:
            scroll_pos -= 1
            last_advance = now
        if scroll_pos < -ticker_width:
            scroll_pos = DISPLAY_WIDTH

        canvas.Clear()

        dt = datetime.now().strftime("%H:%M")
        graphics.DrawText(canvas, font, 0, CHAR_HEIGHT, WHITE, dt)

        weather = "72\xb0"
        graphics.DrawText(
            canvas,
            font,
            DISPLAY_WIDTH - len(weather) * CHAR_WIDTH,
            CHAR_HEIGHT,
            WHITE,
            weather,
        )
        if segments:
            draw_ticker(canvas, segments, 0, CHAR_HEIGHT * 2)
        else:
            graphics.DrawText(canvas, font, 0, CHAR_HEIGHT * 2, WHITE, "Loading...")

        graphics.DrawText(canvas, font, 0, CHAR_HEIGHT * 3, WHITE, "72\xb0 CLOUDY")

        canvas = matrix.SwapOnVSync(canvas)

except KeyboardInterrupt:
    canvas.Clear()
    print("\nExiting and clearing matrix.")
