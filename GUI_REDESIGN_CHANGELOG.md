# GUI Redesign Change Log — 2026-09-29

## Completed
- Added a one-shot `CombatEventBus` and `CombatImpactEvent` so the authored animation impact can drive downstream combat/effects/audio/camera systems.
- Routed core strike actions through the animation impact marker instead of relying solely on hard-coded strike timestamps.
- Added impact-event tests and documented the new event-driven combat path.
- Added Phase 3 combat timing metadata with normalized anticipation, action, contact, follow-through, recovery, and impact markers.
- Connected Fighter hitbox availability to the active/contact timing window and exposed attack phase/impact queries.
- Added timing-window tests and extended hitbox coverage for jab, cross, hook, low kick, and clinch knee.
- Added the Phase 2 combat animation state machine with validated transitions and state-to-clip mapping.
- Integrated the state machine into Fighter while retaining AnimationPlayer for playback/blending.
- Added state-machine tests for valid/invalid transitions, timing, and recovery.
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
- Subscribe effects, camera shake, audio, and hit reactions to the combat impact event bus.
- Route specialized action clips through the animation state machine instead of direct clip selection.
- Add timing-marker visualization to the Studio timeline.
- Connect the timing layer to explicit one-shot impact events so effects, camera shake, and audio consume the same authored impact marker.
- Route specialized action clips through the animation state machine instead of direct clip selection.
- Add timing-marker visualization to the Studio timeline.
- Add resize handles to timeline blocks for duration editing.
- Add real camera/effects/audio event types and corresponding engine hooks.
- Replace CSS character thumbnails with actual renderer thumbnails.
- Add multi-scene project management.
