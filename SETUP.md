# Profile README

Your GitHub profile page, drawn from scratch once a day.

Every graphic is generated in this repo and committed as an SVG: the portrait is
your photo pushed through a character ramp, and the stat block, language bars and
year grid come straight from the GitHub GraphQL API. Nothing loads from a
third-party badge service, so nothing here can rate-limit, go stale, or disappear
when someone else's free tier runs out.

## Setup

**1. Make the repo.** Create a *public* repo named exactly your GitHub username —
`yourname/yourname`. That's the magic name that makes a README show on your
profile. Drop these files in it.

**2. Add your photo.** Replace `assets/me.jpg`. A head-and-shoulders shot with a
plain, contrasty background works best — the ramp has about twenty tones to play
with, so busy backgrounds turn to mush. Square-ish crops sit best on the page.

**3. Fill in `profile.toml`.** Username, links, about, stack, projects. It's the
only file you edit; `README.md` is generated and will be overwritten.

**4. Try it locally.**

```bash
pip install -r requirements.txt
python generate.py --demo    # sample data, no token needed
python preview.py            # opens both themes side by side
```

When it looks right, run it against your real numbers:

```bash
GITHUB_TOKEN=ghp_yourtoken python generate.py
```

**5. Push.** The workflow in `.github/workflows/profile.yml` runs at 06:17 UTC
daily, regenerates everything, and commits only the files that actually changed.
You can also trigger it by hand from the Actions tab.

### Private contributions (optional)

The workflow's built-in token sees public activity only. For the full number:
create a classic PAT with the `read:user` scope, add it to this repo as a secret
named `PROFILE_TOKEN`, and switch on *Settings → Profile → Include private
contributions on my profile*.

## Tuning the portrait

The defaults in `profile.toml` are already tuned for your avatar. If you swap
the photo, these are the knobs, in the order worth trying:

| Knob | What it does |
| --- | --- |
| `portrait_polarity` | `ink` puts the dense glyphs where the *picture* is dark, in both themes — right for artwork, line work, or anything shot on a light background. `light` puts them where the picture is bright — right for a lit subject on a dark background. `theme` follows the page instead of the picture. |
| `portrait_weight` | Above 1 pulls the mid-tones down. Raise it when a big black mass — a suit, a jacket, hair — floods the frame. Yours is at 1.6. |
| `portrait_local` | Local contrast. A ramp has about twenty tones, and in most portraits the face and the background sit within a few of each other, so global levels flatten one into the other. This re-separates them the way CLAHE would. 0 turns it off; above ~1.2 it starts eating the tonal structure. |
| `portrait_cols` | Grid width. 140 is where your avatar starts reading as a face; below about 110 it turns to mush, and past 160 the file grows for detail nobody sees. |
| `portrait_vignette` | Fades the edges toward the background tone. Useful for a busy backdrop, pointless when the background is part of the artwork — yours is at 0. |
| `portrait_scatter` | How the picture arrives. The reveal thresholds every character cell against a vertical ramp plus noise, and `scatter` is how much of that threshold is noise: `0` is a soft top-down fade with no grain, `1` is every cell appearing in pure random order with no sense of direction. The default `0.35` keeps about 38% of the height mid-dissolve at any moment — a solid top, a speckled middle, an empty bottom, and no edge anywhere. Past ~0.5 the downward lean washes out. |
| `portrait_grain` | Size of one noise feature, in character cells. `1.0` means cells appear individually; `2` clumps them into pairs; below ~0.5 the noise starts breaking up glyphs rather than revealing them. |
| `portrait_duration` | Seconds from first cell to last. The threshold sweeps linearly, because the noise is bell-shaped and so eases the reveal by itself — half the picture is up at the halfway mark and 99% of it by about 84%, with a thin tail after. |
| `portrait_ramp` | `even` is the default and was measured, not guessed: every printable ASCII glyph was rasterised, its ink coverage recorded, and the ramp picked so the steps land evenly. `fine` and `classic` are the hand-written ramps. `blocks` and `dots` need Unicode block glyphs, so avoid them if you care about odd machines. |

Change one at a time and run `python generate.py --demo && python preview.py`.
For a much cleaner cutout than the vignette can manage, run the photo through
`rembg` once and save the result as your `assets/me.jpg`.

Other knobs: `DARK` / `LIGHT` in `build/svgkit.py` are the two palettes, and the
`cron` in the workflow sets when it redraws — odd minutes get scheduled more
reliably than `:00`.

## Why it's built this way

GitHub renders README images in a locked-down mode: no scripts, no external
references, and the surrounding CSS never reaches inside. So:

- **Animation is SMIL**, declared inside each SVG (`<animate>`, `<mask>`).
  It survives sanitising; JavaScript would not. Every animated element carries
  its *finished* value as its plain attribute and is reset to the start by a
  `<set>` at t=0, so a viewer that never runs the clock shows the completed
  drawing instead of an empty frame.
- **The portrait dissolves rather than wipes.** A `<feTurbulence>` noise field
  plus a vertical gradient make a per-cell threshold, and one `<animate>`
  sweeps a steep cutoff across it. A growing clip rect always has an edge; this
  has none.
- **Headings are images.** GitHub strips CSS from READMEs, so an SVG is the only
  way to set a heading in a typeface that isn't GitHub's.
- **Heading text is converted to outlines** with fontTools, because an SVG
  rendered as an image can't fetch a font file. The bulk character grids use a
  generic monospace stack instead, with each row pinned by `textLength` so the
  grid holds its shape whatever face the viewer has.
- **The year grid is rects, not block characters.** U+2588 and friends aren't on
  every system, and a missing glyph is a row of tofu.
- **Dark and light are two files**, paired with `<picture>` and a
  `prefers-color-scheme` media query — supported in GitHub Markdown since 2022.

One note: the daily commit is made by `github-actions[bot]`, so it won't inflate
your own contribution graph. That felt like the right call.

Fonts are JetBrains Mono, subset to the characters this page uses. OFL, licence
in `assets/fonts/`.
