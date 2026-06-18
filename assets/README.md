# Discord Rich Presence art assets

Ready-to-upload icons (512x512 PNG) for the Discord application. In the developer portal
go to your app > **Rich Presence > Art Assets > Add Image(s)**, upload each file, and set
its **key to the filename without `.png`**. The keys must match exactly.

| File | Asset key | Used for |
|------|-----------|----------|
| `claude.png` | `claude` | large image (the big logo) |
| `thinking.png` | `thinking` | small icon while the model is thinking |
| `tool.png` | `tool` | small icon while a tool is running |
| `idle.png` | `idle` | small icon when a session is idle |
| `waiting.png` | `waiting` | small icon when waiting for input |
| `starting.png` | `starting` | small icon right after a session starts |

The large key is `claude` by default; override it with `DISCORD_LARGE_IMAGE` if you upload
it under a different name. The small status keys are referenced by the client in
`SMALL_IMAGE` in `local/client.py`. Discord asset uploads can take a few minutes to
propagate before they render.

## Sources

All icons sit on terracotta (`#da7756`) tiles with cream (`#f5efe6`) glyphs:
- `claude.png` - the Claude logo from [Simple Icons](https://simpleicons.org) (CC0). The Claude
  mark is a trademark of Anthropic; swap it for your own art if you prefer.
- `thinking.png` - our own recreation of the claude.ai working indicator (a dotted ring with a
  trailing fade), **not** the original asset. Built from scratch in `thinking.html` with CSS and
  screenshotted via headless Chromium. Edit the `N`/`R`/`TRAIL` constants and re-render to tweak it.
- `tool.png`, `idle.png`, `waiting.png`, `starting.png` - generated icons in the same style.

Note: Discord Rich Presence art assets are static; animated GIFs are not supported, so
`thinking.png` is a static representation of the animation.
