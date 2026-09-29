## 2026-09-29 — Fix GUI Preview/Generate Request Blocking

### What I did
- Changed the Studio HTTP server from single-threaded `HTTPServer` to `ThreadingHTTPServer`.
- This prevents a slow preview request from blocking the Generate button or `/api/status` polling.
- Configured SDL's dummy video driver before importing Pygame so the web renderer consistently uses headless surfaces.
- Added explicit `[GUI] POST ...` and render-job start/completion/failure logging so Generate activity is visible in the terminal.
- Kept the fighter skeleton, animation, physics, renderer, choreography, and MP4 pipeline unchanged.

### Diagnosis
- The GUI was using a single-threaded HTTP server while preview generation and rendering can take noticeable time. That can make the browser appear unresponsive without a Python exception.
- The `/api/preview` endpoint is responsible for the on-screen fighter snapshot, so it must not block the render/status path.

### Validation
- Repository source updated.
- A real local browser run has not yet been executed here; the next run should confirm both fighters appear in the snapshot and Generate immediately starts progress polling.

# AI Change Log

## 2026-09-29 — Optional Bold Seamless-Line Visual Style

### What I did
- Added a new fighter render style: `bold`, implemented in `stickfight/engine/bold_style.py`.
- `renderer.py` only gained an import and a small dispatch (`style == "bold"`), so all existing styles (`segmented`, `silhouette`, `classic`, `tech`, `ink_fight`) are untouched.
- The body is drawn as **one continuous silhouette**: every outline is drawn first, then every fill in a single colour, so overlapping limbs never draw borders across each other.
- Limbs, spine, neck and head are smooth curves through the joints (quadratic curves anchored at segment midpoints), so elbows, knees and shoulders bend without visible breaks.
- Added a soft glow (small silhouette smooth-scaled up), a top-edge highlight so lines read as rounded tubes, and motion smear (ghost frames plus speed lines) for punch/kick/uppercut/slash/sweep clips.
- Headbands and sword/staff weapons still attach to the existing skeleton joints.
- Added `tests/test_bold_style.py` (style is configurable, draws without error while animating, and body curve points are body-coloured rather than outline-coloured).

### Important architecture decision
`bold` is an **option**, not a replacement. Skeleton, animation, physics, collision/hitboxes, choreography, camera, effects and audio are unchanged. Motion-smear history is kept per fighter on the `Renderer` instance and only used by this style.

### Example
```python
A = scene.add_fighter("A", x=350, y=1500, color=(232, 68, 58), render_style="bold")
B = scene.add_fighter("B", x=730, y=1500, color=(61, 139, 255), render_style="bold")
```

### Validation
- The drawing module was exercised against a stand-in pygame to check its logic (curve sampling, missing joints, no active clip, ghost history filling over frames).
- **Real pygame tests and a render preview have NOT been run yet.** Line widths (`BASE_LINE_WIDTH = 16`), highlight strength and glow alpha are tuned from a browser mock-up, not from actual frames.

### Next plan
1. Run `pytest tests/test_bold_style.py tests/test_fighter.py`.
2. Render a short preview with `render_style="bold"` and check width, glow and smear against the real camera zoom.
3. Tune `BASE_LINE_WIDTH`, `OUTLINE_EXTRA`, `TRAIL_GHOSTS` in `bold_style.py` based on real frames.
4. Decide whether to document the style in `readme.md` and expose it in the GUI style picker.


## 2026-09-28 — Optional Black-Ink Fight Visual Style

### What I did
- Added a new fighter render style: `ink_fight`.
- Kept the existing `segmented`, `silhouette`, `classic`, and `tech` styles intact.
- Implemented the black-ink renderer as a presentation layer over the existing animation skeleton.
- Added heavy black comic-style strokes, clean negative-space torso shapes, minimal eye marks, red accent details, and animation-driven motion marks.
- Kept sword and staff rendering attached to the existing right-hand skeleton joints.
- Added `ink_fight` to the fighter render-style test coverage.
- Documented the option in `readme.md`.
- Updated the fighter render-style comment to include `ink_fight`.

### Important architecture decision
The black-ink direction is currently an **option**, not a forced replacement. The existing skeleton, animation, physics, collision/hitboxes, choreography, camera, effects, audio, and weapon logic remain underneath the visual layer.

### Example
```python
A = scene.add_fighter("A", x=350, y=1500, render_style="ink_fight")
B = scene.add_fighter("B", x=730, y=1500, render_style="ink_fight")
```

### Validation
- Added automated render-style configuration coverage for `ink_fight`.
- GitHub-side edits completed successfully.
- Full local pytest/render preview has **not yet been run in this change**.

### Next plan
1. Run the fighter/style tests locally.
2. Render a short preview using `render_style="ink_fight"`.
3. Inspect the generated frames for pose readability, limb overlap, weapon clarity, and motion-line quality.
4. Refine the ink renderer based on the actual preview rather than changing the physics/choreography layer.


## 2026-09-28 — Fix GUI Preview Generator Parameter Mismatch

### What I did
- Updated `generate_fight()` to accept the render parameters already supplied by `gui/app.py`: `width`, `height`, `fps`, `ground_y`, and `style`.
- Replaced the generator's hard-coded 1080×1920/30 FPS scene configuration with the supplied values.
- Preserved the existing procedural choreography, fighter builders, combat logic, physics, and collision behavior.
- This fixes the `TypeError: generate_fight() got an unexpected keyword argument 'width'` that caused `POST /api/preview` to return HTTP 500.
- Kept the style value optional and attached it to the scene without coupling the generator to a specific renderer.

### Validation
- Repository source updated successfully.
- The exact GUI-to-generator parameter mismatch is resolved at the function interface.
- A local preview render still needs to be run to validate the complete rendering path.


## 2026-09-28 — Fix Missing Fighter Design Presets

### What I did
- Defined the missing `DESIGN_PRESETS` registry used by `Fighter.__init__()`.
- Added presets for classic, ninja, samurai, brawler, monk, and cyborg designs.
- Reused the repository's existing archetype colors, render styles, scales, headband colors, and skeleton proportions.
- This fixes `NameError: name 'DESIGN_PRESETS' is not defined`.

### Validation
- The missing symbol is now defined before `Fighter` uses it.
- Changes committed to the repository.
- A full local preview run is still required to catch any subsequent integration errors.

## 2026-09-28 — Fix Missing Fighter Proportion Imports

### What I did
- Fixed the startup `NameError: name 'PROPORTIONS_NINJA' is not defined` in `stickfight/engine/fighter.py`.
- Imported all archetype proportion presets from `stickfight.engine.skeleton`: ninja, samurai, brawler, monk, and cyborg.
- Kept the existing design presets and renderer architecture unchanged.

### Validation
- Confirmed the referenced proportion constants are defined in `stickfight/engine/skeleton.py`.
- The next step is to run `python3 gui.py` locally and continue resolving any remaining runtime errors.

## 2026-09-28 — Fix Render Progress Callback API

### What I did
- Updated `FightScene.render()` to accept the GUI's `progress_callback` argument.
- The callback is invoked during rendering with `(frame, total_frames, progress)` so the GUI can update its render status.
- Preserved the existing rendering, simulation, FFmpeg export, audio, physics, and choreography flow.

### Validation
- Fixed the runtime mismatch causing `FightScene.render() got an unexpected keyword argument 'progress_callback'`.
- Next step: rerun `python3 gui.py` and start another render/preview.
