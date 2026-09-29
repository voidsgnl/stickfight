# GUI Redesign Change Log — 2026-09-29

## Completed
- Started the animation-engine upgrade: added a dedicated AnimationPlayer runtime for clip playback, completion tracking, and cross-fade transitions.
- Routed Fighter animation playback through AnimationPlayer while preserving the existing Fighter/choreography API.
- Added animation-player tests for playback, completion, and cross-fade behavior.
- Added ANIMATION_ENGINE_ROADMAP.md documenting the architecture, phases, and definition of done.
- Reworked the Stick Fight Studio interface into a professional three-pane animation workspace.
- Added character inspector panels for Fighter A and Fighter B.
- Added Visual Style selection: ink_fight, bold, classic, silhouette, segmented, tech.
- Made ink_fight the default GUI art direction.
- Added central viewport toolbar, transport controls, viewport metadata, and production render controls.
- Upgraded the choreography timeline from a plain event list into a visual multi-track sequencer with Fighter A, Fighter B, Camera, Effects, and Audio lanes.
- Timeline actions now render as duration blocks positioned on a time ruler.
- Timeline blocks can be dragged horizontally to change their start time.
- Preserved the existing procedural generation, choreography, preview, render progress, and MP4 export flow.
- Wired visual_style through stickfight/gui/app.py for preview, timeline rendering, and procedural rendering.
- Fixed the choreography duration-control hook.
- Added this changelog so the design work is recorded as requested.

## Next
- Build the animation state machine on top of AnimationPlayer.
- Add attack timing markers for anticipation, active/contact, follow-through, and recovery.
- Add resize handles to timeline blocks for duration editing.
- Add real camera/effects/audio event types and corresponding engine hooks.
- Replace CSS character thumbnails with actual renderer thumbnails.
- Add multi-scene project management.
