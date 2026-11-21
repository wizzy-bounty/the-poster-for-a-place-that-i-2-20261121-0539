#!/usr/bin/env python3
"""VELMARA — Isles of the Amber Tide.

A travel poster for a place that does not exist. Pure-stdlib Python 3.13:
draws a 1024x1024 PNG (dusk lagoon, one crystal spire, big invented
place-name) and writes it to /output/entry.png. No network, deterministic.
"""
import math
import os
import random
import struct
import sys
import zlib

W = 1024
H = 1024
HORIZON = 620
SEED = 20261121

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def px(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.buf[o:o + 3] = bytes(rgb)

    def hspan(self, y, x0, x1, rgb):
        """Fill one horizontal run (clipped). rgb is a 3-tuple of ints."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(math.ceil(x0)))
        x1 = min(self.w - 1, int(math.floor(x1)))
        if x1 < x0:
            return
        o = self._off(x0, y)
        n = x1 - x0 + 1
        self.buf[o:o + n * 3] = bytes(rgb) * n

    def vgrad(self, y0, y1, stops):
        """Vertical gradient between (pos 0..1, rgb) stops, full width."""
        for y in range(max(0, y0), min(self.h, y1)):
            t = (y - y0) / max(1, (y1 - y0))
            rgb = grad_at(stops, t)
            self.hspan(y, 0, self.w - 1, rgb)

    def poly(self, pts, rgb):
        """Scanline-filled polygon. pts = list of (x, y) floats."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.ceil(min(ys))))
        y1 = min(self.h - 1, int(math.floor(max(ys))))
        n = len(pts)
        for y in range(y0, y1 + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                x1, yy1 = pts[i]
                x2, yy2 = pts[(i + 1) % n]
                if (yy1 <= yc < yy2) or (yy2 <= yc < yy1):
                    t = (yc - yy1) / (yy2 - yy1)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hspan(y, xs[k], xs[k + 1], rgb)

    def circle(self, cx, cy, r, rgb):
        r = int(r)
        for y in range(max(0, cy - r), min(self.h - 1, cy + r) + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hspan(y, cx - dx, cx + dx, rgb)

    def ellipse(self, cx, cy, rx, ry, rgb):
        for y in range(max(0, cy - ry), min(self.h - 1, cy + ry) + 1):
            dy = (y - cy) / float(ry)
            dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
            self.hspan(y, cx - dx, cx + dx, rgb)

    def thick_line(self, x0, y0, x1, y1, w, rgb):
        """Thick segment with round caps (quad + end circles)."""
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L == 0:
            self.circle(int(round(x0)), int(round(y0)), int(round(w / 2)), rgb)
            return
        nx, ny = -dy / L * w / 2.0, dx / L * w / 2.0
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                   (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], rgb)
        r = int(math.ceil(w / 2.0))
        self.circle(int(round(x0)), int(round(y0)), r, rgb)
        self.circle(int(round(x1)), int(round(y1)), r, rgb)

    def polyline(self, pts, w, rgb):
        for i in range(len(pts) - 1):
            self.thick_line(pts[i][0], pts[i][1], pts[i + 1][0],
                            pts[i + 1][1], w, rgb)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(round(lerp(c1[0], c2[0], t))),
            int(round(lerp(c1[1], c2[1], t))),
            int(round(lerp(c1[2], c2[2], t))))


def grad_at(stops, t):
    """stops: list of (pos, rgb), sorted by pos."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            p0, c0 = stops[i - 1]
            p1, c1 = stops[i]
            return mix(c0, c1, (t - p0) / max(1e-9, (p1 - p0)))
    return stops[-1][1]


# ------------------------------------------------------------------ font
# Bold geometric stroke font on a 6x8 grid (x 0..6, y 0..8, y down).
# Each glyph is a list of polylines.
GLYPHS = {
    'A': [[(0.7, 8), (3, 0), (5.3, 8)], [(1.8, 5.2), (4.2, 5.2)]],
    'B': [[(0.7, 8), (0.7, 0), (4.2, 0), (5.1, 1.0), (5.1, 2.8),
           (4.2, 3.8), (0.7, 3.8)],
          [(4.2, 3.8), (5.2, 4.6), (5.2, 6.8), (4.2, 7.8), (0.7, 7.8)]],
    'D': [[(0.7, 8), (0.7, 0), (3.8, 0), (5.1, 1.6), (5.1, 6.4),
           (3.8, 8), (0.7, 8)]],
    'E': [[(5.0, 0), (0.7, 0), (0.7, 8), (5.0, 8)], [(0.7, 4), (4.0, 4)]],
    'F': [[(0.7, 8), (0.7, 0), (5.0, 0)], [(0.7, 4), (4.0, 4)]],
    'H': [[(0.7, 0), (0.7, 8)], [(5.3, 0), (5.3, 8)], [(0.7, 4), (5.3, 4)]],
    'I': [[(3, 0), (3, 8)], [(1.8, 0), (4.2, 0)], [(1.8, 8), (4.2, 8)]],
    'L': [[(0.7, 0), (0.7, 8), (5.0, 8)]],
    'M': [[(0.7, 8), (0.7, 0), (3, 5.0), (5.3, 0), (5.3, 8)]],
    'O': [[(2.0, 0.4), (4.0, 0.4), (5.3, 1.8), (5.3, 6.2), (4.0, 7.6),
           (2.0, 7.6), (0.7, 6.2), (0.7, 1.8), (2.0, 0.4)]],
    'R': [[(0.7, 8), (0.7, 0), (4.2, 0), (5.1, 1.0), (5.1, 3.0),
           (4.2, 4.0), (0.7, 4.0)], [(3.8, 4.0), (5.4, 8)]],
    'S': [[(4.9, 1.4), (4.1, 0.3), (2.1, 0.3), (0.9, 1.3), (0.9, 2.9),
           (2.0, 3.7), (4.2, 4.3), (5.1, 5.3), (5.1, 6.7), (4.1, 7.7),
           (2.1, 7.7), (0.9, 6.7)]],
    'T': [[(0.7, 0), (5.3, 0)], [(3, 0), (3, 8)]],
    'V': [[(0.7, 0), (3, 8), (5.3, 0)]],
}


def text_width(text, cap_h, advance_units=6.8):
    s = cap_h / 8.0
    return len(text) * advance_units * s - (advance_units - 6.0) * s


def draw_text(cv, text, x, y_top, cap_h, stroke_w, rgb, advance_units=6.8):
    """Draw caps text; (x, y_top) is the top-left of the first cell."""
    s = cap_h / 8.0
    cx = x
    for ch in text:
        if ch == ' ':
            cx += advance_units * s
            continue
        for pl in GLYPHS.get(ch, []):
            pts = [(cx + gx * s, y_top + gy * s) for gx, gy in pl]
            cv.polyline(pts, stroke_w, rgb)
        cx += advance_units * s
    return cx


# ------------------------------------------------------------------- png
def write_png(cv, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += cv.buf[y * stride:(y + 1) * stride]
    data = zlib.compress(bytes(raw), 9)

    def chunk(typ, payload):
        c = struct.pack('>I', len(payload)) + typ + payload
        c += struct.pack('>I', zlib.crc32(typ + payload) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
           + chunk(b'IDAT', data) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)
    return len(png)


# ------------------------------------------------------------------ scene
SKY = [(0.00, (25, 20, 55)), (0.30, (61, 42, 99)), (0.52, (138, 74, 107)),
       (0.68, (224, 120, 64)), (0.80, (246, 169, 75))]
SEA = [(0.00, (42, 31, 78)), (0.45, (30, 24, 62)), (1.00, (19, 15, 44))]
CREAM = (255, 242, 206)
SHADOW = (20, 16, 46)


def sky_at(y):
    return grad_at(SKY, y / float(HORIZON))


def sea_at(y):
    return grad_at(SEA, (y - HORIZON) / float(H - HORIZON))


def draw_scene(cv, rng):
    # --- sky
    cv.vgrad(0, HORIZON, SKY)

    # --- stars, upper sky only
    for _ in range(70):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, 300)
        a = rng.random()
        base = sky_at(y)
        star = mix(base, (255, 244, 214), 0.55 + 0.4 * a)
        cv.px(x, y, star)
        if a > 0.75:
            cv.px(x + 1, y, star)

    # --- soft high cloud bands
    for (cx, cy, rx, ry, tint) in [
            (300, 268, 260, 16, (107, 74, 138)),
            (760, 300, 300, 14, (122, 82, 128)),
            (520, 210, 200, 10, (90, 62, 128))]:
        base = sky_at(cy)
        cv.ellipse(cx, cy, rx, ry, mix(base, tint, 0.35))

    # --- sun glow + disc (low, right of centre)
    sun_cx, sun_cy, sun_r = 665, 462, 80
    for rr, mix_t in [(250, 0.16), (215, 0.24), (182, 0.33), (152, 0.44),
                      (126, 0.56), (104, 0.70), (88, 0.85)]:
        cv.circle(sun_cx, sun_cy, rr,
                  mix(sky_at(sun_cy), (255, 196, 107), mix_t))
    cv.circle(sun_cx, sun_cy, sun_r, (255, 233, 168))

    # --- sea
    cv.vgrad(HORIZON, H, SEA)

    # --- sun reflection column (shimmering dashes under the sun)
    for k in range(46):
        y = HORIZON + 8 + k * 8
        depth = (y - HORIZON) / float(H - HORIZON)
        half = int(lerp(70, 14, depth) * (0.55 + 0.9 * rng.random()))
        cx = sun_cx + int(rng.randint(-26, 26) * (0.4 + depth))
        col = mix(sea_at(y), (255, 196, 107), lerp(0.75, 0.25, depth))
        cv.hspan(y, cx - half, cx + half, col)
        cv.hspan(y + 3, cx - half // 2, cx + half // 2, col)

    # --- the Tideglass Spire (one landmark, centre; apex kept below the
    # type so the name and subtitle stay clean)
    apex = (415, 272)
    base_l, base_r = (345, HORIZON), (520, HORIZON)
    mid_l = (398, 300)
    mid_r = (440, 300)
    # left facet (cool teal, in shade)
    cv.poly([base_l, mid_l, apex, (430, HORIZON)], (94, 157, 180))
    # centre facet (pale aqua, catches the sun)
    cv.poly([apex, mid_r, (472, HORIZON), (430, HORIZON)], (191, 232, 224))
    # right facet (deep blue, away from the sun)
    cv.poly([mid_r, base_r, (472, HORIZON)], (46, 110, 140))
    # bright left edge + apex glint
    cv.thick_line(base_l[0], base_l[1], apex[0], apex[1], 5, (255, 246, 216))
    cv.thick_line(apex[0], apex[1], mid_r[0], mid_r[1], 4, (255, 246, 216))
    # inner amber light streak down the centre facet
    cv.thick_line(417, 310, 424, 560, 7, (255, 196, 107))
    cv.thick_line(431, 330, 437, 540, 4, (255, 214, 140))
    # terrace lines across the facets
    for ty, wfrac in [(380, 0.62), (460, 0.74), (540, 0.86)]:
        t = (ty - apex[1]) / float(HORIZON - apex[1])
        lx = int(lerp(apex[0], base_l[0], t))
        rx = int(lerp(apex[0], base_r[0], t))
        cv.hspan(ty, lx + 4, rx - 4, mix((120, 180, 200), (255, 246, 216), 0.25))
    # glowing window slits near the top
    for wy in (332, 364, 398):
        t = (wy - apex[1]) / float(HORIZON - apex[1])
        lx = int(lerp(apex[0], base_l[0], t))
        rx = int(lerp(apex[0], base_r[0], t))
        wxx = (lx + rx) // 2
        cv.hspan(wy, wxx - 7, wxx + 7, (255, 220, 130))
        cv.hspan(wy + 1, wxx - 7, wxx + 7, (255, 220, 130))

    # --- spire reflection (squashed, wavy slices)
    for k in range(30):
        y = HORIZON + 6 + k * 5
        depth = k / 30.0
        spread = int(lerp(46, 88, depth))
        cx = 415 + int(rng.randint(-8, 8))
        col = mix(sea_at(y), (120, 180, 200), lerp(0.5, 0.12, depth))
        cv.hspan(y, cx - spread, cx + spread, col)

    # --- gentle swell lines across the sea
    for _ in range(26):
        y = rng.randint(HORIZON + 30, H - 20)
        x = rng.randint(0, W - 260)
        ln = rng.randint(60, 220)
        col = mix(sea_at(y), (150, 170, 210), 0.22)
        cv.hspan(y, x, x + ln, col)

    # --- dark headland, bottom-left, with lit windows
    cv.poly([(0, H), (0, 872), (110, 812), (250, 848), (330, 905),
             (305, H)], (20, 16, 46))
    for (wx, wy) in [(96, 862), (132, 856), (168, 866), (205, 880)]:
        cv.hspan(wy, wx, wx + 7, (255, 196, 107))
        cv.hspan(wy + 1, wx, wx + 7, (255, 196, 107))

    # --- small lantern boat, right side
    bx, by = 770, 742
    cv.poly([(bx - 34, by), (bx + 34, by), (bx + 22, by + 16),
             (bx - 22, by + 16)], (20, 16, 46))
    cv.thick_line(bx, by, bx, by - 52, 4, (20, 16, 46))
    cv.poly([(bx, by - 50), (bx + 26, by - 8), (bx, by - 8)],
            (255, 242, 206))
    cv.circle(bx, by - 58, 12, mix(sea_at(by), (255, 196, 107), 0.55))
    cv.circle(bx, by - 58, 6, (255, 214, 140))

    # --- birds (mid-sky band, clear of the type and the spire)
    for (bx0, by0, s) in [(250, 300, 16), (322, 345, 12), (700, 330, 14),
                          (800, 290, 11), (585, 360, 10)]:
        cv.polyline([(bx0 - s, by0), (bx0, by0 + s // 2),
                     (bx0 + s, by0)], 3, (20, 16, 46))

    # --- typography: name + subtitle (on top, legible)
    name = "VELMARA"
    cap_h = 112
    nw = text_width(name, cap_h)
    nx = (W - nw) / 2.0
    ny = 66
    draw_text(cv, name, nx + 3, ny + 4, cap_h, 24, SHADOW)
    draw_text(cv, name, nx, ny, cap_h, 24, CREAM)
    sub = "ISLES OF THE AMBER TIDE"
    sub_h = 30
    sw = text_width(sub, sub_h, advance_units=7.4)
    sx = (W - sw) / 2.0
    draw_text(cv, sub, sx + 1, 208 + 2, sub_h, 6, SHADOW, advance_units=7.4)
    draw_text(cv, sub, sx, 208, sub_h, 6, CREAM, advance_units=7.4)


def main(argv):
    out_dir = "/output"
    for i, a in enumerate(argv):
        if a == "--output" and i + 1 < len(argv):
            out_dir = argv[i + 1]
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(SEED)
    cv = Canvas(W, H)
    draw_scene(cv, rng)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(cv, path)
    print("wrote %s (%d bytes)" % (path, size))
    if size > 1048576:
        print("ERROR: over the 1 MiB cap", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
