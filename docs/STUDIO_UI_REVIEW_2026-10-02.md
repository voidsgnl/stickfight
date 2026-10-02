# Studio UI Review — 2026-10-02

## Review findings
- The merged `main` copy of `stickfight/gui/static/index.html` still contained unresolved Git merge markers inside `bindCoreStudioControls()`.
- Those markers made the browser JavaScript invalid, preventing the Studio initialization/binding code after that point from executing. This explains why multiple UI controls appeared missing or non-functional.
- The Studio Properties panel contains the intended Play/Pause and Export MP4 controls.
- The Studio timeline transport should not introduce a second Play/Export control. Its transport is limited to previous-frame, next-frame, stop, and scrubbing.
- The playback state must update the Properties-panel Play button consistently.

## Changes made
- Removed the leftover `<<<<<<< HEAD`, `=======`, and `>>>>>>> origin/main` conflict block.
- Kept the functional `bindClickOnce` approach for Studio transport controls.
- Bound the actual Properties-panel `studioHeaderPlay` and `studioHeaderExport` controls.
- Updated playback state synchronization so the Properties-panel Play button changes between PLAY and PAUSE.
- Kept the Studio scrub track and frame navigation behavior.

## Next verification
1. Pull the new `main` commit locally.
2. Restart `python3 gui.py`.
3. Hard-refresh the browser page.
4. Verify the Studio initializes without JavaScript console errors.
5. Verify the Properties-panel Play/Export controls are the only Play/Export controls in the Studio UI.
6. Verify fighters, timeline tracks, keyframes, workspace tabs, pose controls, combat controls, and playback render correctly.
