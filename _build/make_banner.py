"""Draw the README banner: a black hard case with gold lettering, the left half rendered, the right half written in code.

Same recipe as the condom banner so the two read as a set: night background, a premium black product with gold type,
a green seam down the middle. The seam falls between LOAD and OUT. The wordmark and every line on the case are ours;
no brand's name, logo or artwork is copied. Output: ../assets/banner.png (1600 x 800).

Run: python3 _build/make_banner.py   (needs numpy and Pillow; fonts: Inter and JetBrains Mono, or the fallbacks below)
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WORD, SPLIT = "LOADOUT", 4           # the seam falls after the fourth letter
LINE = "SAME MODEL. BETTER LOADOUT."
FOOT = "8 PIECES  ·  3 JOBS  ·  NOTHING EXTRA"
CODE = "loadout(task);check();if(!pass)fix();deny(secrets);hook(stop);prune(stale);verdict(piece);"

W, H, S = 1600, 800, 2
NIGHT, LIT, PAPER = (9, 20, 15), (93, 184, 136), (245, 242, 234)
CX, CY, SIDE = 800, 400, 500  # the case sits in a 500 px square
N = SIDE * S
TALL = 1.50                   # the wordmark is stretched taller: open counters survive being redrawn in code characters

# the case, in units of N
X0, X1, Y0, Y1, RAD = 0.020, 0.980, 0.250, 0.930, 0.045
SEAM = 0.435                  # where the lid meets the body
LATCH = [(0.215, 0.295), (0.705, 0.785)]   # two latches, left and right edges of each
HANDLE = (0.385, 0.615, 0.135, 0.275, 0.040)  # x0, x1, y0, y1, corner radius


def font(names, size):
    roots = ["/usr/share/fonts/opentype/inter/", "/usr/share/fonts/truetype/jetbrains-mono/",
             "/usr/share/fonts/truetype/dejavu/", "C:\\Windows\\Fonts\\"]
    for n in names:
        for r in roots:
            try:
                return ImageFont.truetype(r + n, size)
            except OSError:
                continue
    raise SystemExit(f"none of these fonts found: {names}")


HEAVY = ["InterDisplay-Black.otf", "Inter-Black.otf", "InterDisplay-ExtraBold.otf", "DejaVuSans-Bold.ttf", "arialbd.ttf"]
CAPS = ["Inter-Bold.otf", "DejaVuSans-Bold.ttf", "arialbd.ttf"]
MONO_B = ["JetBrainsMono-Bold.ttf", "DejaVuSansMono-Bold.ttf", "consolab.ttf"]
MONO = ["JetBrainsMono-Regular.ttf", "DejaVuSansMono.ttf", "consola.ttf"]


def rounded(u, v, x0, x1, y0, y1, r):
    """Signed distance to a rounded rectangle: negative inside."""
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = np.abs(u - cx) - hx, np.abs(v - cy) - hy
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def gold_layer():
    """Everything printed in gold, as a mask 0..1 on the N x N grid. Returns the mask and where LOAD ends (in N px)."""
    m = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(m)
    gap = N * 0.012
    size = int(N * 0.30)
    while True:
        word = font(HEAVY, size)
        widths = [d.textlength(c, font=word) + gap for c in WORD]
        if sum(widths) - gap <= N * 0.860:
            break
        size -= 4
    box = d.textbbox((0, 0), WORD, font=word)
    h0 = box[3] - box[1]
    wm = Image.new("L", (N, h0 + 8), 0)
    d2 = ImageDraw.Draw(wm)
    x = (N - (sum(widths) - gap)) / 2
    split = None
    for i, (c, wd) in enumerate(zip(WORD, widths)):
        d2.text((x, 4 - box[1]), c, font=word, fill=255)
        x += wd
        if i == SPLIT - 1:
            split = x - gap / 2
    wm = wm.resize((N, int((h0 + 8) * TALL)), Image.LANCZOS)
    top = int(N * 0.528)
    m.paste(wm, (0, top), wm)
    wb = top + wm.size[1]

    def centred(text, f, y, spacing=0.0):
        ws = [d.textlength(c, font=f) + spacing for c in text]
        xx = (N - sum(ws) + spacing) / 2
        for c, wd in zip(text, ws):
            d.text((xx, y), c, font=f, fill=255)
            xx += wd

    caps = font(CAPS, int(N * 0.026))
    for y in (top - N * 0.022, wb + N * 0.016):  # thin rules above and below the wordmark
        d.rectangle([N * 0.07, y, N * 0.93, y + S * 2], fill=255)
    centred(LINE, caps, N * 0.328, spacing=N * 0.0065)
    centred(FOOT, caps, wb + N * 0.045, spacing=N * 0.0050)
    return np.asarray(m).astype(float) / 255, split


def case():
    """Return the case as an RGBA image (SIDE px) and the x where LOAD ends (in SIDE px)."""
    rng = np.random.default_rng(11)
    v, u = np.mgrid[0:N, 0:N].astype(float) / N
    sd = rounded(u, v, X0, X1, Y0, Y1, RAD)
    inside = sd < 0

    # moulded black polymer: a low sheen from the upper left, a slow ripple, fine grain
    lum = np.full((N, N), 0.068)
    lum += 0.085 * np.exp(-((u + 0.9 * v - 0.80) ** 2) / 0.020)
    lum += 0.035 * np.exp(-((u + 0.9 * v - 1.45) ** 2) / 0.050)
    lum += 0.006 * np.sin(u * 19 + np.sin(v * 7) * 1.7)
    lum += rng.normal(0, 0.0065, (N, N))
    lum = np.where(v < SEAM, lum * 1.12 + 0.006, lum)             # the lid sits a little prouder and catches more light

    # the bevel round the edge: lit from the upper left, in shadow at the lower right
    gy, gx = np.gradient(sd)
    nrm = np.hypot(gx, gy) + 1e-9
    facing = (gx / nrm) * -0.55 + (gy / nrm) * -0.83              # how much the edge faces the light
    rim = np.clip(1 + sd / 0.022, 0, 1) ** 1.5                    # 1 at the edge, 0 a bevel's width in
    lum += rim * (0.150 * np.clip(facing, 0, 1) - 0.050 * np.clip(-facing, 0, 1))

    # the seam between lid and body: a dark groove with a lit lip under it
    lum = np.where(np.abs(v - SEAM) < 0.0045, lum * 0.28, lum)
    lum = np.where((v > SEAM + 0.0045) & (v < SEAM + 0.0085), lum + 0.060, lum)
    lum = np.where((v > SEAM - 0.0100) & (v < SEAM - 0.0045), lum * 0.80, lum)

    # three moulded ribs along the foot of the case
    for y in (0.872, 0.890, 0.908):
        k = (v - y) / 0.0055
        on = np.abs(k) < 1
        lum = np.where(on, lum + 0.050 * np.clip(-k, 0, 1) - 0.030 * np.clip(k, 0, 1), lum)

    rgb = np.stack([lum * 0.98, lum, lum * 1.05], -1)

    # gold: the printing, then the latches
    gm, split = gold_layer()
    shine = 0.52 + 0.48 * np.exp(-((u + 0.9 * v - 0.80) ** 2) / 0.030) + 0.05 * np.sin(v * 170)
    gold = np.stack([np.clip(0.92 * shine, 0, 1), np.clip(0.72 * shine, 0, 0.98), np.clip(0.33 * shine, 0, 0.8)], -1)
    edge = np.asarray(Image.fromarray((gm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S * 1.6))).astype(float) / 255
    rgb = rgb * (1 - 0.55 * np.clip(edge - gm, 0, 1)[..., None])
    rgb = rgb * (1 - gm[..., None]) + gold * gm[..., None]

    for lx0, lx1 in LATCH:
        ly0, ly1 = SEAM - 0.056, SEAM + 0.044
        ls = rounded(u, v, lx0, lx1, ly0, ly1, 0.010)
        on = ls < 0
        t = (v - ly0) / (ly1 - ly0)
        g = 0.50 + 0.38 * np.exp(-((t - 0.20) ** 2) / 0.010) + 0.16 * np.exp(-((t - 0.78) ** 2) / 0.006)   # brushed brass
        g += 0.030 * np.sin(u * 900)
        g = np.where(np.abs(t - 0.56) < 0.030, g * 0.40, g)        # the hinge line
        g *= 1 - 0.5 * np.clip(1 + ls / 0.006, 0, 1) ** 2          # a darker edge
        lat = np.stack([np.clip(0.93 * g, 0, 1), np.clip(0.73 * g, 0, 1), np.clip(0.34 * g, 0, 1)], -1)
        shadow = (rounded(u - 0.006, v - 0.008, lx0, lx1, ly0, ly1, 0.010) < 0) & ~on
        rgb = np.where(shadow[..., None], rgb * 0.45, rgb)
        rgb = np.where(on[..., None], lat, rgb)

    alpha = inside.astype(float)

    # the handle: a rubber bar standing above the lid
    hx0, hx1, hy0, hy1, hr = HANDLE
    hs = np.abs(rounded(u, v, hx0, hx1, hy0, hy1, hr)) - 0.021   # a tube along the rounded rectangle
    on = (hs < 0) & (v < Y0 + 0.012)
    k = np.clip(hs / 0.021, -1, 0) + 1                            # 0 on the centre line, 1 at the tube's edge
    hl = 0.060 + 0.150 * (1 - k ** 2) * np.exp(-((u - 0.44) ** 2) / 0.012) + 0.050 * (1 - k ** 2)
    hgy, hgx = np.gradient(rounded(u, v, hx0, hx1, hy0, hy1, hr))
    hl += 0.060 * np.clip(-(hgy * 600), -1, 1) * k               # lighter above the centre line, darker below
    hl += rng.normal(0, 0.005, (N, N))
    hcol = np.stack([hl * 0.98, hl, hl * 1.05], -1)
    behind = on & ~inside
    rgb = np.where(behind[..., None], hcol, rgb)
    alpha = np.where(behind, 1.0, alpha)

    a = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S * 0.5))
    im = Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8)).convert("RGBA")
    im.putalpha(a)
    return im.resize((SIDE, SIDE), Image.LANCZOS), int(round(split * SIDE / N))


def main():
    art, split = case()
    x0, y0 = CX - split, CY - SIDE // 2 - 26    # the seam falls between LOAD and OUT
    out = Image.new("RGB", (W, H), NIGHT)

    # a soft shadow under the left half
    sh = Image.new("L", (W, H), 0)
    sh.paste(art.getchannel("A").point(lambda a: int(a * 0.75)), (x0 + 10, y0 + 18))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    sh.paste(0, (CX, 0, W, H))
    out.paste((0, 0, 0), (0, 0), sh)

    left = art.crop((0, 0, split, SIDE))
    out.paste(left, (x0, y0), left)
    d = ImageDraw.Draw(out)

    rgb = np.asarray(art.convert("RGB")).astype(float)
    alpha = np.asarray(art.getchannel("A")).astype(float) / 255
    mono = font(MONO_B, 10)
    cw, ch = 6, 12
    chars = ".:-=+*x#%@"
    k = 0
    for gy in range(0, SIDE, ch):
        for gx in range(split, SIDE, cw):
            a = alpha[gy:gy + ch, gx:gx + cw]
            if a.size == 0 or a.mean() < 0.45:
                continue
            px = rgb[gy:gy + ch, gx:gx + cw].reshape(-1, 3)
            col = px.mean(0)
            v = (0.299 * col[0] + 0.587 * col[1] + 0.114 * col[2]) / 255
            warm = ((px[:, 0] - px[:, 2]) > 38).mean() > 0.34  # enough of the cell is gold
            if warm:
                # gold: a lit cell with a code character on it, so the letters read as letters
                c = CODE[k % len(CODE)]
                k += 1
                d.rectangle([x0 + gx, y0 + gy, x0 + gx + cw - 1, y0 + gy + ch - 1], fill=(122, 90, 30))
                fill = (255, 226, 150)
            else:
                c = chars[min(len(chars) - 1, int(min(v, 0.30) / 0.30 * len(chars)))]
                g = int(min(205, 46 + v * 540))
                fill = (g, g, int(min(245, g * 1.05)))
            d.text((x0 + gx, y0 + gy), c, font=mono, fill=fill)

    d.rectangle([CX - 1, CY - SIDE // 2 - 44, CX, CY + SIDE // 2 + 44], fill=LIT)  # the seam

    big = font(MONO_B, 80)
    small = font(MONO, 26)
    name = WORD.lower()
    d.text((86, 304), name, font=big, fill=PAPER)
    d.text((90, 418), "same model.", font=small, fill=LIT)
    d.text((90, 452), "better loadout.", font=small, fill=LIT)
    d.text((1212, 372), f"$ /{name}", font=small, fill=LIT)
    d.text((1212, 412), "8 pieces checked", font=small, fill=PAPER)
    d.text((1212, 448), "tested, not guessed", font=small, fill=PAPER)

    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "banner.png")
    out.save(dst, optimize=True)
    print(os.path.abspath(dst), os.path.getsize(dst) // 1024, "KB", "| split at", split, "px; case spans", x0, "to", x0 + SIDE)


if __name__ == "__main__":
    main()
