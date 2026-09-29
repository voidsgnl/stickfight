# Animation Engine Roadmap

## Objective

Turn the existing Stick Fight engine into a proper 2D character-animation runtime while preserving the current skeleton, physics, collision, choreography, renderer, visual styles, GUI timeline, and FFmpeg pipeline.

The target architecture is:

```
Fight Script
    ↓
Choreography / Timeline
    ↓
Animation Runtime
    ↓
Skeleton + IK
    ↙       ↘
Physics   Hitboxes / Hurtboxes
    ↓       ↓
Combat Resolution
    ↓
Camera / Effects / Audio
    ↓
Renderer
    ↓
FFmpeg
    ↓
MP4
```

## Current baseline

The repository already has substantial animation infrastructure:

- `Pose` and skeleton joint representation.
- Keyframe-based `AnimationClip`.
- Pose interpolation and easing functions.
- A broad procedural combat clip library.
- Fighter-level animation selection and playback.
- Physics and collision systems.
- A code-driven choreography/timeline system.
- A visual multi-track GUI timeline.
- Multiple renderer styles, including `ink_fight`.
- Preview and MP4 rendering.

The missing architectural step was separating **animation clip definitions** from the **runtime that plays and blends those clips**.

## Completed in this milestone

### AnimationPlayer

Added:

`stickfight/engine/animation_player.py`

The new `AnimationPlayer` owns:

- active clip
- local playback time
- looping
- completion state
- clip switching
- transition state
- cross-fade blending

This keeps animation runtime state out of the clip definitions.

### Fighter integration

`Fighter.set_animation()` now supports:

```python
fighter.set_animation("punch", blend=0.08)
```

The optional `blend` value cross-fades from the current pose into the new clip.

The existing public Fighter API remains compatible.

### Tests

Added:

`tests/test_animation_player.py`

Coverage includes:

- initial idle state
- advancing a non-looping clip
- completion detection
- cross-fade lifecycle

## Phase 1 — Animation Runtime

- [x] Separate playback state from clip definitions.
- [x] Add clip switching.
- [x] Add local animation time.
- [x] Add loop handling.
- [x] Add completion detection.
- [x] Add cross-fade transitions.
- [x] Add runtime tests.

## Phase 2 — Animation State Machine

Next, build a state machine above `AnimationPlayer`.

Target states:

```
IDLE
  ├── WALK
  ├── RUN
  ├── ATTACK
  │    └── RECOVERY
  ├── BLOCK
  ├── DODGE
  ├── HIT
  ├── KNOCKBACK
  ├── AIRBORNE
  └── FALLEN
```

Each state will define:

- allowed transitions
- default clip
- entry behavior
- exit behavior
- transition blend
- optional conditions

The state machine must not replace the choreography system. Choreography requests state/action changes; the state machine resolves the animation transition.

## Phase 3 — Better Combat Animation

Expand clips into structured combat phases:

```
ANTICIPATION
    ↓
ACTION
    ↓
CONTACT
    ↓
FOLLOW-THROUGH
    ↓
RECOVERY
```

Every attack should eventually expose meaningful timing markers such as:

- startup
- active
- impact
- recovery

Those markers will later drive hitboxes, effects, camera shake, and audio.

## Phase 4 — Animation / Physics Integration

The animation system must cooperate with physics instead of fighting it.

Target flow:

```
Animation pose
    ↓
root motion
    ↓
physics constraints
    ↓
world position
    ↓
final skeleton pose
```

Combat impulses remain physics-driven.

Animation should provide intended motion and pose; physics remains authoritative for collisions, gravity, knockback, and grounded state.

## Phase 5 — IK and Procedural Motion

Add procedural solving for:

- hand-to-target reach
- foot placement
- weapon alignment
- target facing
- balance
- grounded stance
- contact correction

The goal is to avoid manually authoring every possible variation of an action.

## Phase 6 — Animation Authoring

Upgrade the Studio timeline from an event sequencer into an animation authoring surface.

Target capabilities:

- resize animation blocks
- scrub animation time
- edit duration
- preview transitions
- show action markers
- show impact/contact markers
- eventually expose keyframes

## Phase 7 — Camera, Effects and Audio Hooks

Add real event types for:

- camera moves
- camera shake
- zoom
- impact effects
- particles
- motion lines
- sound effects
- music cues

These should consume the same timing markers used by animation/combat.

## Phase 8 — Render Quality

Improve:

- frame interpolation
- motion readability
- animation consistency
- renderer performance
- vertical 9:16 composition
- final FFmpeg output

## Design rule

Do **not** replace the existing skeleton, physics, collision, weapons, choreography, or renderer.

The animation system sits between choreography and those existing systems and becomes the authoritative source for character pose over time.

## Definition of done

A fight should eventually be expressible as:

```python
scene.at(0.0, A.walk_to(500))
scene.at(1.0, B.walk_to(600))
scene.at(2.0, A.punch(B))
scene.at(2.7, B.block())
scene.at(3.5, B.kick(A))
scene.at(4.2, A.dodge())
scene.at(5.0, A.counter(B))
scene.at(6.0, B.fall())
```

while the engine automatically handles:

- animation
- transitions
- pose interpolation
- root motion
- physics
- collision
- reactions
- camera
- effects
- audio
- rendering
- MP4 encoding

The creator controls the fight; the engine controls the frame-by-frame execution.
