# -*- coding: utf-8 -*-
"""
Created on Sat Nov  7 22:31:40 2026

@author: Morteza
"""


"""
CAMERA ISP SIMULATION
From a synthetic scene to a processed photograph

Requires:
    Pillow (PIL)
    Tkinter
    No NumPy required

Run in Anaconda Spyder with F5.

Controls:
    SPACE         Pause / Resume
    RIGHT ARROW   Next ISP stage
    LEFT ARROW    Previous ISP stage
    R             Restart
    ESC           Exit
"""

import math
import random
import time
import tkinter as tk

from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageTk
)


# ============================================
# SETTINGS
# ============================================

W = 400
H = 264

STEP_SECONDS = 5

BG = "#09111F"
WHITE = "#F4F8FF"
CYAN = "#6DE8FA"
MUTED = "#B8CAE5"


# ============================================
# STEP 1: GENERATE SYNTHETIC SCENE
# ============================================

def create_scene():

    image = Image.new(
        "RGB",
        (W, H)
    )

    pixels = image.load()

    # Sky and grass
    for y in range(H):

        for x in range(W):

            if y < 153:

                t = y / 153

                r = int(32 + 115 * t)
                g = int(109 + 98 * t)
                b = int(213 + 20 * t)

            else:

                t = (y - 153) / (H - 153)

                r = int(58 + 23 * t)
                g = int(130 - 34 * t)
                b = int(62 - 16 * t)

            pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(image)

    # Sun
    draw.ellipse(
        (291, 22, 351, 82),
        fill=(255, 241, 154)
    )

    # Mountains
    draw.polygon(
        [(0, 172), (90, 92), (195, 170)],
        fill=(90, 133, 146)
    )

    draw.polygon(
        [(112, 172), (246, 94), (399, 173)],
        fill=(74, 115, 133)
    )

    # Snowcaps
    draw.polygon(
        [(72, 113), (90, 92), (109, 114)],
        fill=(220, 226, 230)
    )

    draw.polygon(
        [(226, 117), (246, 94), (267, 117)],
        fill=(225, 228, 231)
    )

    # House body
    draw.rectangle(
        (130, 151, 255, 234),
        fill=(225, 168, 103)
    )

    # House roof
    draw.polygon(
        [(114, 151), (192, 104), (271, 151)],
        fill=(158, 65, 51)
    )

    # Door
    draw.rectangle(
        (178, 185, 207, 234),
        fill=(71, 51, 45)
    )

    # Windows
    draw.rectangle(
        (147, 171, 171, 196),
        fill=(93, 194, 230)
    )

    draw.rectangle(
        (218, 171, 242, 196),
        fill=(93, 194, 230)
    )

    # Colorful objects in foreground
    objects = [
        (47, 204, 14, (223, 56, 58)),
        (77, 224, 18, (243, 188, 46)),
        (307, 210, 18, (134, 67, 188)),
        (349, 228, 21, (239, 105, 55))
    ]

    for x, y, radius, color in objects:

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius
            ),
            fill=color
        )

    # Neutral reference patches
    for i, value in enumerate(
        (245, 190, 120, 60)
    ):

        draw.rectangle(
            (
                8 + i * 29,
                243,
                32 + i * 29,
                260
            ),
            fill=(value, value, value)
        )

    return image


# ============================================
# COLOR SPACE FUNCTIONS
# ============================================

def srgb_to_linear(value):

    value /= 255.0

    if value <= 0.04045:
        return value / 12.92

    return (
        (value + 0.055) / 1.055
    ) ** 2.4


def linear_to_srgb(value):

    value = max(
        0.0,
        min(1.0, value)
    )

    if value <= 0.0031308:

        encoded = 12.92 * value

    else:

        encoded = (
            1.055 * value ** (1 / 2.4)
            - 0.055
        )

    return int(
        round(255 * encoded)
    )


# ============================================
# BAYER COLOR FILTER ARRAY
# ============================================

def cfa_channel(y, x):

    # RGGB pattern:
    #
    # R G R G
    # G B G B
    # R G R G
    # G B G B

    if y % 2 == 0:

        if x % 2 == 0:
            return 0  # Red

        return 1      # Green

    if x % 2 == 0:
        return 1      # Green

    return 2          # Blue


# ============================================
# IMAGE CONVERSION HELPERS
# ============================================

def make_rgb_image(data, gamma=False):

    output = bytearray()

    for pixel in data:

        for value in pixel:

            if gamma:

                output.append(
                    linear_to_srgb(value)
                )

            else:

                output.append(
                    int(
                        max(
                            0,
                            min(
                                255,
                                round(255 * value)
                            )
                        )
                    )
                )

    return Image.frombytes(
        "RGB",
        (W, H),
        bytes(output)
    )


def make_gray_image(data, gain=1.0):

    output = bytes(
        max(
            0,
            min(
                255,
                round(255 * v * gain)
            )
        )
        for v in data
    )

    return Image.frombytes(
        "L",
        (W, H),
        output
    ).convert("RGB")


# ============================================
# STEP 2-8: SIMULATE THE ISP
# ============================================

def build_isp_pipeline():

    print("Generating synthetic scene...")

    scene = create_scene()

    source_pixels = list(
        scene.getdata()
    )

    # Convert sRGB scene into linear RGB
    linear_scene = [
        tuple(
            srgb_to_linear(v)
            for v in pixel
        )
        for pixel in source_pixels
    ]

    # Camera simulation parameters
    random_generator = random.Random(19)

    black_level = 0.035
    exposure = 0.72

    # Simulated channel sensitivities
    sensor_gains = (
        0.68,
        1.00,
        0.53
    )

    # ----------------------------------------
    # SENSOR ACQUISITION
    # ----------------------------------------

    raw = []

    for i, pixel in enumerate(linear_scene):

        x = i % W
        y = i // W

        channel = cfa_channel(y, x)

        response = (
            exposure
            * sensor_gains[channel]
            * pixel[channel]
        )

        noise = random_generator.gauss(
            0,
            0.002
        )

        value = (
            response
            + black_level
            + noise
        )

        raw.append(
            max(0, min(1, value))
        )

    # Stage collection
    stages = []

    stages.append(
        (
            "01  ORIGINAL SCENE",
            "The scene before sensor acquisition",
            scene
        )
    )

    stages.append(
        (
            "02  BAYER RAW",
            "One intensity measurement per RGGB pixel",
            make_gray_image(raw, 2.2)
        )
    )

    # ----------------------------------------
    # BLACK LEVEL CORRECTION
    # ----------------------------------------

    corrected = [
        max(0, v - black_level)
        for v in raw
    ]

    stages.append(
        (
            "03  BLACK LEVEL CORRECTION",
            "Remove the sensor black offset",
            make_gray_image(
                corrected, 2.2
            )
        )
    )

    # ----------------------------------------
    # DEMOSAICING
    # ----------------------------------------

    print("Demosaicing Bayer RAW...")

    rgb = []

    for y in range(H):

        for x in range(W):

            values = [0.0, 0.0, 0.0]

            measured_channel = (
                cfa_channel(y, x)
            )

            values[measured_channel] = (
                corrected[y * W + x]
            )

            # Interpolate missing channels
            for channel in range(3):

                if channel == measured_channel:
                    continue

                total = 0.0
                weight_sum = 0.0

                for dy in (-1, 0, 1):

                    yy = y + dy

                    if not (0 <= yy < H):
                        continue

                    for dx in (-1, 0, 1):

                        xx = x + dx

                        if not (0 <= xx < W):
                            continue

                        if cfa_channel(yy, xx) != channel:
                            continue

                        weight = (
                            1.0
                            if dx == 0 or dy == 0
                            else 0.7071
                        )

                        sample = corrected[
                            yy * W + xx
                        ]

                        total += sample * weight

                        weight_sum += weight

                if weight_sum > 0:

                    values[channel] = (
                        total / weight_sum
                    )

            rgb.append(tuple(values))

    stages.append(
        (
            "04  DEMOSAICING",
            "Reconstruct the missing RGB channels",
            make_rgb_image(rgb)
        )
    )

    # ----------------------------------------
    # WHITE BALANCE
    # ----------------------------------------

    wb = []

    for pixel in rgb:

        new_pixel = tuple(
            min(1, value / gain)
            for value, gain in zip(
                pixel, sensor_gains
            )
        )

        wb.append(new_pixel)

    stages.append(
        (
            "05  WHITE BALANCE",
            "Compensate for the simulated channel response",
            make_rgb_image(wb)
        )
    )

    # ----------------------------------------
    # COLOR CORRECTION MATRIX
    # ----------------------------------------

    ccm = []

    for r, g, b in wb:

        new_r = (
            1.12 * r
            - 0.08 * g
            - 0.04 * b
        )

        new_g = (
            -0.04 * r
            + 1.09 * g
            - 0.05 * b
        )

        new_b = (
            -0.04 * r
            - 0.08 * g
            + 1.12 * b
        )

        ccm.append(
            (
                max(0, min(1, new_r)),
                max(0, min(1, new_g)),
                max(0, min(1, new_b))
            )
        )

    stages.append(
        (
            "06  COLOR CORRECTION",
            "Apply an illustrative 3x3 color matrix",
            make_rgb_image(ccm)
        )
    )

    # ----------------------------------------
    # DISPLAY RENDERING
    # ----------------------------------------

    # Restore exposure and encode sRGB
    tone_mapped = []

    for pixel in ccm:

        new_pixel = tuple(
            max(
                0,
                min(1, value / exposure)
            )
            for value in pixel
        )

        tone_mapped.append(new_pixel)

    rendered = make_rgb_image(
        tone_mapped,
        gamma=True
    )

    stages.append(
        (
            "07  DISPLAY RENDERING",
            "Exposure compensation and sRGB encoding",
            rendered
        )
    )

    # ----------------------------------------
    # SHARPENING
    # ----------------------------------------

    sharpened = rendered.filter(
        ImageFilter.UnsharpMask(
            radius=1.2,
            percent=115,
            threshold=3
        )
    )

    stages.append(
        (
            "08  SHARPENING",
            "Enhance local edge contrast",
            sharpened
        )
    )

    print("ISP pipeline ready!")

    return stages


# ============================================
# ANIMATED PRESENTATION
# ============================================

class ISPVisualization:

    def __init__(self):

        # Generate all stages
        self.stages = build_isp_pipeline()

        self.root = tk.Tk()

        self.root.title(
            "How a Camera Reconstructs a Photo"
        )

        self.root.configure(bg=BG)

        try:

            self.root.state("zoomed")

        except tk.TclError:

            self.root.attributes(
                "-fullscreen", True
            )

        self.canvas = tk.Canvas(
            self.root,
            bg=BG,
            highlightthickness=0
        )

        self.canvas.pack(
            fill="both",
            expand=True
        )

        self.index = 0
        self.paused = False

        self.elapsed = 0.0
        self.previous = time.monotonic()

        # Precompute display images
        self.images = []

        for i, (_, _, image) in enumerate(
            self.stages
        ):

            interpolation = (
                Image.Resampling.NEAREST
                if i in (1, 2)
                else Image.Resampling.LANCZOS
            )

            large = image.resize(
                (800, 528),
                interpolation
            )

            self.images.append(
                ImageTk.PhotoImage(large)
            )

        # Small preview images
        self.thumbnails = []

        for _, _, image in self.stages:

            small = image.resize(
                (105, 70),
                Image.Resampling.LANCZOS
            )

            self.thumbnails.append(
                ImageTk.PhotoImage(small)
            )

        # Keyboard controls
        self.root.bind(
            "<Escape>",
            lambda e: self.root.destroy()
        )

        self.root.bind(
            "<space>",
            self.toggle_pause
        )

        self.root.bind(
            "<Right>",
            lambda e: self.step(1)
        )

        self.root.bind(
            "<Left>",
            lambda e: self.step(-1)
        )

        self.root.bind(
            "<r>",
            self.restart
        )

        self.root.bind(
            "<R>",
            self.restart
        )

        self.root.after(
            200,
            self.animate
        )

        self.root.mainloop()

    # ----------------------------------------
    # TEXT HELPER
    # ----------------------------------------

    def draw_text(
        self,
        x,
        y,
        message,
        size=17,
        color=WHITE,
        bold=False
    ):

        self.canvas.create_text(
            x,
            y,
            text=message,
            fill=color,
            font=(
                "Arial",
                size,
                "bold" if bold else "normal"
            )
        )

    # ----------------------------------------
    # DRAW FRAME
    # ----------------------------------------

    def draw(self):

        c = self.canvas

        c.delete("all")

        w = max(
            980,
            c.winfo_width()
        )

        h = max(
            760,
            c.winfo_height()
        )

        name, description, _ = (
            self.stages[self.index]
        )

        # Main title
        self.draw_text(
            w / 2,
            40,
            "HOW A CAMERA RECONSTRUCTS A PHOTO",
            27,
            WHITE,
            True
        )

        # Current ISP stage
        self.draw_text(
            w / 2,
            83,
            name,
            24,
            CYAN,
            True
        )

        self.draw_text(
            w / 2,
            119,
            description,
            16,
            MUTED
        )

        center_y = h * 0.46

        # Main image
        c.create_image(
            w / 2,
            center_y,
            image=self.images[self.index]
        )

        # Bayer RGGB inset
        if self.index in (1, 2):

            inset_x = w / 2 + 260
            inset_y = center_y - 248

            for yy in range(8):

                for xx in range(8):

                    channel = cfa_channel(
                        yy, xx
                    )

                    color = [
                        "#ED5C65",
                        "#5ED78B",
                        "#6B9AF0"
                    ][channel]

                    x = inset_x + xx * 16
                    y = inset_y + yy * 16

                    c.create_rectangle(
                        x, y,
                        x + 15,
                        y + 15,
                        fill=color,
                        outline="#202B38"
                    )

            self.draw_text(
                inset_x + 64,
                inset_y + 146,
                "RGGB layout",
                12,
                WHITE
            )

        # ------------------------------------
        # Timeline thumbnails
        # ------------------------------------

        thumb_width = 105
        gap = 12

        total = (
            8 * thumb_width
            + 7 * gap
        )

        start_x = (w - total) / 2

        thumb_y = h - 155

        for i, image in enumerate(
            self.thumbnails
        ):

            x = start_x + i * (
                thumb_width + gap
            )

            c.create_image(
                x,
                thumb_y,
                image=image,
                anchor="nw"
            )

            border = (
                CYAN
                if i == self.index
                else "#34465F"
            )

            c.create_rectangle(
                x - 2,
                thumb_y - 2,
                x + thumb_width + 2,
                thumb_y + 72,
                outline=border,
                width=(
                    3 if i == self.index else 1
                )
            )

            self.draw_text(
                x + thumb_width / 2,
                thumb_y + 91,
                str(i + 1),
                13,
                border,
                i == self.index
            )

        # Controls
        self.draw_text(
            w / 2,
            h - 25,
            "SPACE: Pause | LEFT/RIGHT: Stages | "
            "R: Restart | ESC: Exit",
            12,
            "#8FA6C6"
        )

    # ----------------------------------------
    # CONTROLS
    # ----------------------------------------

    def toggle_pause(self, event=None):

        self.paused = not self.paused
        self.previous = time.monotonic()

    def restart(self, event=None):

        self.index = 0
        self.elapsed = 0

        self.paused = False

        self.previous = time.monotonic()

        self.draw()

    def step(self, direction):

        self.index = (
            self.index + direction
        ) % len(self.stages)

        self.elapsed = 0
        self.paused = True

        self.draw()

    # ----------------------------------------
    # ANIMATION
    # ----------------------------------------

    def animate(self):

        now = time.monotonic()

        dt = min(
            0.15,
            now - self.previous
        )

        self.previous = now

        if not self.paused:

            self.elapsed += dt

            if self.elapsed >= STEP_SECONDS:

                self.elapsed = 0

                self.index = (
                    self.index + 1
                ) % len(self.stages)

        self.draw()

        self.root.after(
            70,
            self.animate
        )


# ============================================
# START SIMULATION
# ============================================

if __name__ == "__main__":

    ISPVisualization()
