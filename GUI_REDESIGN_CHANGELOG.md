# GUI Redesign Change Log — 2026-09-29

## Completed
- Reworked the Stick Fight Studio interface into a professional three-pane animation workspace.
- Added character inspector panels for Fighter A and Fighter B.
- Added a dedicated Visual Style selector: ink_fight, bold, classic, silhouette, segmented, tech.
- Made ink_fight the default GUI art direction.
- Added a central viewport toolbar, transport controls, viewport metadata, and timeline workspace.
- Kept the existing procedural generation, choreography timeline, presets, preview, render progress, and MP4 download flow.
- Wired visual_style through stickfight/gui/app.py for preview, timeline rendering, and procedural rendering.
- Fixed the choreography duration-control hook.
- Updated the GUI document title.

## Next
- Turn the event list into draggable visual timeline blocks/keyframes.
- Add camera, effects, and audio tracks.
- Replace CSS character thumbnails with actual renderer thumbnails.
- Add multi-scene project management.
