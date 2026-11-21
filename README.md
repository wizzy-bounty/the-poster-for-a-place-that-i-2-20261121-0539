# VELMARA — Isles of the Amber Tide

A travel poster for a place that isn't there. A lagoon archipelago where a
single colossal crystal spire — the Tideglass Spire — rises out of still
water and catches the last amber light of a dusk that never quite ends.

[![Competition](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![Rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wizzy-bounty/the-poster-for-a-place-that-i-2-20261121-0539/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![Reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wizzy-bounty/the-poster-for-a-place-that-i-2-20261121-0539/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)

## What the poster shows

- **One landmark:** the Tideglass Spire, a faceted crystal tower with a
  pale sunlit face, a deep shaded face, terrace lines, glowing window
  slits and an amber light streak running down its centre — reflected in
  the lagoon below.
- **The promise of a stay:** a low amber sun over a calm sea, its light
  shimmering back up the water in a long reflection column, a small
  lantern boat, a dark headland with lit windows, birds crossing a violet
  dusk sky.
- **The name, set with intent:** VELMARA in large bold geometric
  letterforms across the top, with the subtitle ISLES OF THE AMBER TIDE
  beneath it — the eye travels from the name to the spire to the horizon.

## How it works

`main.py` (Python 3.13, standard library only, no network) draws the whole
poster with its own rasteriser — gradients, scanline polygons, circles and
a hand-designed bold stroke font — and writes a deterministic 1024×1024
PNG to `/output/entry.png` (or `--output <dir>/entry.png`). Two runs are
byte-identical.
