## 2026-09-29 — Initial Story Animation Timeline Workspace

### What I implemented
- Added a dedicated Story Animation Studio workspace below the existing editor instead of replacing the legacy fight controls.
- Added a reusable character/asset panel with support for adding additional character instances and selecting visual families including anime and cartoon.
- Added a frame-based timeline ruler with playhead, character tracks, camera/events tracks, event blocks, FPS and duration controls.
- Added timeline scrubbing, basic playback, reset, and keyframe insertion.
- The workspace mirrors the existing legacy timeline state for compatibility, so current fight presets and rendering continue to work while the new editor is developed.
- Kept the Studio state isolated in `window.__storyStudio`; it does not rewrite the existing Fighter, physics, collision, or combat code.

### Stability rule
The new timeline is an additive migration layer. Future editor features should move functionality from the legacy controls into the Studio model incrementally, with the old path retained until the replacement has equivalent behavior and validation.

### Status
- Implemented on `story-animation-studio-foundation`.
- Browser interaction/render verification has not yet been executed here.
- Next step: connect timeline selection/keyframes to actual character transforms and scene playback, then add asset editing and multi-character preview.

## 2026-09-29 — Modular Story Animation Studio Foundation

### What I implemented
- Added a new `stickfight.studio` authoring layer separate from the existing combat/physics engine.
- Added reusable `CharacterAsset` definitions and lightweight `CharacterInstance` placements, so a project can contain many characters and multiple copies of the same character.
- Added independent `VisualStyle` identities. Built-in registrations include classic, ink_fight, bold, silhouette, anime, cartoon, and custom.
- Added scene-level timeline tracks, keyframes, and events as data structures for the future visual editor.
- Added project validation that detects missing assets, duplicate IDs, and invalid track targets before runtime.
- Added tests covering multiple characters with different styles and structural validation.

### Architecture rule
Large changes must be added behind stable boundaries rather than mixed into the existing fighter implementation.

```
Studio Project / Scenes / Timeline
          ↓
Character Assets + Instances
          ↓
Animation / Story Orchestration
          ↓
Existing Fighter / Skeleton / IK / Physics / Combat
          ↓
Renderer / Effects / Audio / Export
```

The Studio layer must not require a specific drawing style, and visual style must not determine physics or combat behavior.

### Character/style direction
- A scene is not limited to two fighters.
- A scene can contain many character instances.
- Different instances may reference different character assets.
- Character assets can use different visual families such as anime, cartoon, ink, silhouette, or custom while sharing the same animation/physics foundations where compatible.
- Future custom renderers should plug into the style registry rather than modify combat logic.

### Stability strategy
This is intentionally additive. Existing fight scenes, skeletons, physics, collision, choreography, and render styles remain the runtime foundation. Future editor work should consume this model instead of embedding new state directly into the existing HTML/GUI handlers.

### Status
- Foundation implemented on branch `story-animation-studio-foundation`.
- Tests added but not executed in this environment.
- Next step: connect the Studio model to the GUI timeline and create a real multi-character scene authoring workflow.

## 2026-09-29 — Story-Mode Animation Direction Documented

### Product direction
- Expanded the project's target from standalone fight clips to **story-mode animation** inspired by the reference style shared by the user.
- The long-term goal is to support narrative episodes made from multiple cinematic scenes, while retaining the existing fight engine as the combat subsystem.

### Planned story capabilities
- Episode/chapter structure containing multiple scenes.
- Character continuity across scenes: identity, visual design, weapons, clothing, state, and damage/progression.
- Dialogue, narration, subtitles, and timed pauses.
- Cinematic actions such as entrances, exits, reactions, conversations, establishing shots, close-ups, and camera transitions.
- Combat sequences that invoke the existing animation, physics, collision, timing, grappling, weapons, and choreography systems.
- Environment/world context for locations such as rooms, streets, rooftops, and other story settings.
- Audio layers including dialogue, footsteps, impacts, ambience, and music.
- Scene transitions such as cuts and fades.
- Script-driven story authoring so a creator can describe a scene using high-level commands instead of manually animating every frame.

### Proposed architecture
```
Story Project
    ↓
Story / Episode Manager
    ↓
Scene System
    ├── Dialogue / Narrative
    ├── Cinematic Actions
    ├── Camera Direction
    └── Combat Sequence
            ↓
        Existing Animation / Physics / Combat Engine
            ↓
        Renderer + Effects + Audio
            ↓
        FFmpeg Video Export
```

### First story-mode milestone
Build one complete **30–60 second vertical story scene** containing:
1. Establishing camera shot.
2. Character entrance/movement.
3. Dialogue exchange.
4. Camera close-up/reaction.
5. Fight transition.
6. Existing combat choreography and physics.
7. Fight aftermath.
8. Final dialogue or story beat.
9. Scene transition.
10. MP4 export.

### Architecture constraint
This is an expansion, not a rewrite. The existing skeleton, animation, physics, collision, combat timing, grappling, weapons, camera, effects, renderer, timeline, GUI, and FFmpeg pipeline remain the foundation. The story layer should orchestrate those systems rather than replace them.

### Authoring direction
A future story script should be able to express intent at a high level, for example:
```python
scene = StoryScene("warehouse")

kai.enter(from_side="left")
rex.enter(from_side="right")

kai.say("You came back.")
rex.say("I came to finish this.")

scene.camera.closeup(kai)

fight = scene.start_fight(kai, rex)
fight.sequence([
    "standoff",
    "jab",
    "block",
    "cross",
    "dodge",
    "low_kick",
    "counter",
    "takedown",
])

rex.say("This isn't over.")
scene.end()
```

The implementation should translate these high-level story actions into the existing timeline, animation, physics, camera, audio, effects, and rendering systems.

### Status
- This is the documented long-term product direction.
- No story-engine implementation was claimed in this change.
- The first implementation milestone is the single 30–60 second end-to-end story scene described above.

## 2026-09-29 — Restore Non-Responsive Studio Controls and Fighter Preview

### What I did
- Added a separate Studio UI recovery script after the main editor script.
- The recovery layer restores the critical inline button handlers if the large editor script fails to parse or initialize.
- Added an immediate browser-side two-fighter SVG preview so the viewport cannot remain as only the `Fight Preview` alt text.
- The recovery layer then attempts the real `/api/preview` renderer and replaces the fallback with the actual Pygame-rendered snapshot when successful.
- Restored Generate/Render status polling and visible error reporting in the Studio.
- Kept the existing engine, skeleton, animation, physics, collision, and renderer untouched.

### Diagnosis
- Seeing only `Fight Preview` means the `<img>` element has no usable image source.
- Multiple unrelated buttons failing at the same time strongly indicates the large inline JavaScript is not successfully initializing in the browser, rather than a Pygame drawing-only problem.
- The recovery layer is isolated in its own script block so a JavaScript parse/runtime failure in the main editor script cannot leave the entire Studio inert.

### Validation
- Source updated on `main`.
- Browser-side execution still needs to be verified from the user's local GUI session.

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


## 2026-09-29 — Studio control binding repair
- Corrected the HTML script order so the main Studio code runs before the recovery layer and both scripts remain inside the document body.
- Added a final DOMContentLoaded rebinding pass that restores the recovery handlers after the main script has loaded, preventing inline controls from becoming inert when the large editor script overrides globals.
- Exposed the recovery handlers through an internal binding registry and retained the working fighter-preview fallback.
- Validation: source structure was inspected; live browser clicking was not available in this session.

- Added recovery-safe implementations for OPEN PRESET and LOAD PRESET, so those controls also work if the editor script fails before defining its original versions.


## 2026-09-29 — Render crash fix: grapple cleanup
- Fixed `Fighter.clear_grapple_reaction()` where an accidentally duplicated fragment referenced undefined `attacker` and `mode` variables.
- The cleanup method now only clears the active grapple reaction state, matching its purpose and preventing render-time `NameError` failures when an IK/timeline action finishes.
- Validation: source-level fix applied from the traceback; full render/test execution has not yet been run in this session.
