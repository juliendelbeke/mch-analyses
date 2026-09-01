#!/usr/bin/env python3
"""Step through a folder of frames with the arrow keys.

Writes a viewer page into the folder and serves that folder, so the frames can be stepped one
by one, scrubbed with a slider, or played. The page only links the PNGs, so it stays a few kB
however many frames there are, and it needs no VSCode extension.

    python3 scripts/frame_viewer.py figures/lff_state_frames
    python3 scripts/frame_viewer.py figures/clc_section_frames --port 8010
    python3 scripts/frame_viewer.py figures/lff_state_frames --keep all
    python3 scripts/frame_viewer.py "$SCRATCH/figures" --name a_viewer.html
    python3 scripts/frame_viewer.py figures/lff_state_frames --write-only

The page is named so that it sorts to the top of the folder listing, above the frames, since
that is where it has to be found among a few hundred PNGs.

Over a remote connection the page is opened for you, through VSCode's browser helper, which
forwards the port and maps it to a free one on the laptop. Do not click the printed URL: it
names the port on the node, and the laptop's port of that number is something else, so it
loads only by coincidence. If the tab does not appear, forward the port by hand from the Ports
panel ("Forward a Port"), or paste the URL into "Simple Browser: Show". Ctrl-C stops the server.

Stdlib only, so the plain login-node python3 runs it - no uenv or notebook kernel needed.
"""

import argparse
import http.server
import json
import webbrowser
from pathlib import Path

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; font: 13px/1.4 system-ui, sans-serif;
          display: flex; flex-direction: column; height: 100vh; }}
  #bar {{ display: flex; gap: .6rem; align-items: center; padding: .5rem .8rem;
          border-bottom: 1px solid #8886; flex: none; flex-wrap: wrap; }}
  #bar button {{ font: inherit; padding: .25rem .6rem; cursor: pointer; }}
  #slider {{ flex: 1 1 240px; min-width: 160px; }}
  #label, #cache {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  #cache {{ opacity: .7; }}
  #stage {{ flex: 1; overflow: auto; display: grid; place-items: center; }}
  /* fit to the window by default; the zoom button switches to pixel-for-pixel and back */
  #stage img {{ max-width: 100%; max-height: 100%; }}
  #stage.zoom img {{ max-width: none; max-height: none; }}
  kbd {{ border: 1px solid #8886; border-radius: 3px; padding: 0 .25rem; }}
</style>
</head>
<body>
<div id="bar">
  <button id="prev" title="previous frame">&#9664;</button>
  <button id="next" title="next frame">&#9654;</button>
  <button id="play">play</button>
  <input id="slider" type="range" min="0" max="{last}" value="0" step="1">
  <span id="label"></span>
  <label>fps <input id="fps" type="number" value="4" min="1" max="30" style="width:3.5em"></label>
  <button id="zoom">actual size</button>
  <span id="cache"></span>
  <span style="opacity:.7"><kbd>&larr;</kbd><kbd>&rarr;</kbd> step &middot;
    <kbd>space</kbd> play &middot; <kbd>home</kbd>/<kbd>end</kbd> ends</span>
</div>
<div id="stage"></div>
<script>
const FRAMES = {frames};
const KEEP = {keep};        // frames held decoded either side of the current one; 0 = all
const stage = document.getElementById('stage'), slider = document.getElementById('slider');
const label = document.getElementById('label'), play = document.getElementById('play');
const cache = document.getElementById('cache');
let i = 0, timer = null;

// Swapping one <img>'s src re-decodes the PNG on every step: the bytes are cached but the
// bitmap is not, and decoding a large frame is the slow part. So every frame gets its own
// <img>, kept in the DOM and already decoded, and stepping only flips which one is visible -
// a composite, no decode, no flash. A decoded frame costs width*height*4 bytes, so KEEP
// bounds how many are held at once; raise it as far as memory allows, or set 0 to hold the
// whole series.
const slots = new Map();                        // index -> <img>, in the DOM and decoding

function slot(n) {{
  let im = slots.get(n);
  if (!im) {{
    im = new Image();
    im.alt = FRAMES[n];
    im.style.display = 'none';
    im.src = FRAMES[n];
    stage.appendChild(im);
    slots.set(n, im);
    // decode() resolves once the bitmap is ready, so a frame is never shown half-drawn
    if (im.decode) im.decode().catch(() => {{}});
  }}
  return im;
}}

function prune() {{
  if (!KEEP) return;                            // holding everything: nothing to drop
  for (const [n, im] of slots) {{
    let d = Math.abs(n - i);
    d = Math.min(d, FRAMES.length - d);         // the series wraps, so the ends are adjacent
    if (d > KEEP) {{ im.remove(); slots.delete(n); }}
  }}
}}

function show(n) {{
  const prev = slots.get(i);
  i = (n + FRAMES.length) % FRAMES.length;
  const im = slot(i);
  if (prev && prev !== im) prev.style.display = 'none';
  im.style.display = 'block';
  slider.value = i;
  label.textContent = `${{i + 1}} / ${{FRAMES.length}}  ${{FRAMES[i]}}`;
  const reach = KEEP || FRAMES.length;
  for (let d = 1; d <= reach; d++) {{           // outwards, so the neighbours are ready first
    slot((i + d) % FRAMES.length);
    slot((i - d + FRAMES.length) % FRAMES.length);
  }}
  prune();
  cache.textContent = `${{slots.size}} cached`;
}}

function stop() {{ clearInterval(timer); timer = null; play.textContent = 'play'; }}
function toggle() {{
  if (timer) return stop();
  const fps = Math.max(1, +document.getElementById('fps').value || 4);
  timer = setInterval(() => show(i + 1), 1000 / fps);
  play.textContent = 'pause';
}}

document.getElementById('prev').onclick = () => {{ stop(); show(i - 1); }};
document.getElementById('next').onclick = () => {{ stop(); show(i + 1); }};
play.onclick = toggle;
slider.oninput = () => {{ stop(); show(+slider.value); }};
document.getElementById('zoom').onclick = e => {{
  // the class lives on the container, so it applies to every cached frame at once
  stage.classList.toggle('zoom');
  e.target.textContent = stage.classList.contains('zoom') ? 'fit to window' : 'actual size';
}};
addEventListener('keydown', e => {{
  const k = e.key;
  if (k === 'ArrowRight' || k === 'ArrowDown' || k === 'j') {{ stop(); show(i + 1); }}
  else if (k === 'ArrowLeft' || k === 'ArrowUp' || k === 'k') {{ stop(); show(i - 1); }}
  else if (k === ' ') toggle();
  else if (k === 'Home') {{ stop(); show(0); }}
  else if (k === 'End') {{ stop(); show(FRAMES.length - 1); }}
  else return;
  e.preventDefault();                           // so the page does not scroll under the image
}});
show(0);
</script>
</body>
</html>
"""


def write_viewer(folder: Path, pattern: str, keep: int, name: str) -> Path:
    """Write the viewer page, listing every matching frame in filename order.

    The frame names are zero-padded timestamps, so sorting them is chronological. Paths go in
    relative to `folder`, which keeps a nested pattern such as "**/*.png" working: the server
    roots itself at `folder`, so a relative path is also the URL.
    """
    frames = sorted(p.relative_to(folder).as_posix()
                    for p in folder.glob(pattern) if p.is_file())
    if not frames:
        raise SystemExit(f"no files matching {pattern!r} in {folder}")
    out = folder / name
    out.write_text(PAGE.format(title=folder.name, frames=json.dumps(frames),
                               last=len(frames) - 1, keep=keep))
    held = len(frames) if keep == 0 else min(len(frames), 2 * keep + 1)
    print(f"{len(frames)} frames: {frames[0]} .. {frames[-1]}")
    print(f"holding {held} decoded at a time"
          + (" (the whole series)" if keep == 0 else f" (--keep {keep})"))
    print(f"wrote {out}")
    return out


def serve(folder: Path, port: int, open_browser: bool, name: str) -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
        # HTTP/1.1 keeps the connection open between frames, so prefetching the decode window
        # does not pay for a handshake per PNG. Safe here because every response this handler
        # sends carries a Content-Length.
        protocol_version = "HTTP/1.1"
        timeout = 30            # so an abandoned keep-alive connection releases its thread

        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(folder), **kw)

        def send_head(self):
            # Serve the viewer at the root as well as under its own name. VSCode's "your
            # application is running on port N" notification opens the root, so without this
            # that button lands on a directory listing (or a 404) rather than the viewer,
            # while the page itself keeps a name that sorts to the top of the folder.
            if self.path in ("/", "/index.html"):
                self.path = "/" + name
            return super().send_head()

        def end_headers(self):
            # Cache the frames, so one dropped from the decoded window comes back without a
            # round trip. Only the frames: caching anything else means a stale page, or - as
            # happened - a 404 cached for a day, which no amount of restarting the server can
            # clear because the browser stops asking.
            frame = Path(self.path).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            cacheable = frame and 200 <= getattr(self, "_status", 200) < 300
            self.send_header("Cache-Control",
                             "public, max-age=86400" if cacheable else "no-store")
            super().end_headers()

        def send_response(self, code, *a):
            self._status = code             # so end_headers never caches an error response
            super().send_response(code, *a)

        def log_message(self, *a):      # a line per frame step is just noise
            pass

    # Threaded, not the plain single-connection server: a browser opens speculative sockets
    # before it sends anything on them, and VSCode's port forwarder probes the port the same
    # way. A one-connection-at-a-time server blocks in the read for a request line that never
    # comes, and the page load that follows waits behind it forever - the tab just spins.
    class Server(http.server.ThreadingHTTPServer):
        daemon_threads = True           # a stray connection never holds up Ctrl-C
        allow_reuse_address = True      # no TIME_WAIT wait on restart

    # Bound to localhost only: reached through VSCode's port forwarding or an ssh tunnel,
    # never exposed on the node's network interface.
    with Server(("127.0.0.1", port), Handler) as httpd:
        url = f"http://localhost:{port}/{name}"
        print(f"\nserving {folder}\n  {url}")
        if open_browser:
            # $BROWSER, under VSCode remote, is the server's browser.sh helper, and
            # webbrowser honours it. That routes through VSCode's asExternalUri, which opens
            # the tunnel and picks a free *local* port - so it lands on the viewer even when
            # the laptop's own port 8000 is taken. Clicking the URL above does not: it aims
            # the laptop's browser at the laptop's port 8000, which is a different machine's
            # port than the one printed, and fails whenever the numbers do not line up.
            print("  opening it through VSCode (check the Ports panel for the local port)")
            webbrowser.open(url)
        else:
            print("  if that URL does not load, the port is not forwarded: rerun with --open,"
                  "\n  or forward it by hand from the Ports panel (Forward a Port -> "
                  f"{port})")
        print("Ctrl-C to stop.", flush=True)     # flush: visible even when redirected to a log
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path, help="folder holding the frames")
    ap.add_argument("--pattern", default="*.png",
                    help="glob for the frames (default *.png)")
    ap.add_argument("--keep", default="24",
                    help="frames held decoded either side of the current one, or 'all' to "
                         "hold the whole series (default 24). A decoded frame costs about "
                         "width*height*4 bytes, so 'all' on a long series of large frames "
                         "can run to gigabytes")
    ap.add_argument("--name", default="00_viewer.html",
                    help="filename for the page (default 00_viewer.html, which sorts above "
                         "the frames in a file listing)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--write-only", action="store_true",
                    help="write viewer.html and exit, without serving")
    ap.add_argument("--open", action=argparse.BooleanOptionalAction, default=True,
                    help="open the page in a browser through VSCode's helper, which forwards "
                         "the port on the way (default; --no-open to just serve)")
    args = ap.parse_args()

    keep = 0 if str(args.keep).lower() == "all" else int(args.keep)
    if keep < 0:
        raise SystemExit("--keep must be 'all' or a non-negative number")

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        raise SystemExit(f"not a directory: {folder}")
    name = args.name if args.name.endswith(".html") else args.name + ".html"
    write_viewer(folder, args.pattern, keep, name)
    if not args.write_only:
        serve(folder, args.port, args.open, name)


if __name__ == "__main__":
    main()
