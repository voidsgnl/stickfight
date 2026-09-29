# GUI Redesign Change Log — 2026-09-29

## Completed
- Added Studio timeline combat timing visualization using the same normalized attack markers as the engine.
- Attack blocks now show anticipation, active/dangerous window, impact, active end, and follow-through markers.
- Impact marker tooltips show the calculated wall-clock impact time for the current action duration.
- Timing markers scale automatically when an action block duration changes or the block is moved.
- Specialized attack actions now enter the semantic attack state while selecting their authored clip.
- Added regression coverage for specialized attack clip selection.
- Wired `CombatImpactEvent` into `FightScene` as the single impact-response path.
- Centralized hit particles/shockwaves, camera shake, audio, and hit-reaction animation behind the impact event.
- Added scene-level integration coverage for resolved combat impacts.
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

## Completed
- Replaced tolerance-only impact detection with animation-time crossing detection, so larger frame steps cannot skip the authored impact marker.
- Routed action impact checks through the same one-shot Fighter impact-consumption path used by the combat event architecture.
- Added regression coverage for crossing the impact marker in a large frame step.

## Completed
- Added attack-specific impact profiles for punches, kicks, specialized strikes, takedowns, ground pounds, and blade slashes.
- Impact profiles now control sound selection, pitch/gain, camera shake, heavy-impact treatment, and knockback scaling while preserving the shared CombatImpactEvent pipeline.
- Added integration coverage proving different attack types produce different impact responses.

## Completed
- Integrated Fighter physics updates through a single physics-aware scene step and exposed airborne state from the physical body.
- Added deterministic physics velocity support for scripted motion.
- Converted KnockbackAction from direct position teleporting to physics-driven velocity, allowing animation, momentum, gravity, and collision to remain coupled.
- Added regression coverage for fighter physics synchronization and physics-driven knockback.

## Completed
- Added a reusable 2D two-bone IK solver that preserves authored limb lengths.
- Integrated world-space procedural arm targeting into Fighter animation evaluation.
- Punch, jab and hook attacks can aim the striking hand toward the opponent's head instead of relying only on fixed authored coordinates.
- Procedural IK targets are cleared when attacks finish so idle/recovery poses remain authored.
- Added IK regression tests for reach accuracy and attack targeting.

## Completed
- Restored the missing `WalkToAction` class declaration in the choreography action module so `RunToAction` has a valid base class.

## Next
- Add richer per-attack effect/audio profiles so each attack type can author its own impact presentation.
- Add resize handles to timeline blocks for duration editing.
- Add real camera/effects/audio event types and corresponding engine hooks.
- Replace CSS character thumbnails with actual renderer thumbnails.
- Add multi-scene project management.
