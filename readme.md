# Stick Fight Video Engine

A code-driven 2D animation engine for creating **stick-figure fighting videos automatically**.

The purpose of this project is to allow a creator to design a complete fight using code, run the program, and automatically produce a finished **vertical short-form video**.

The creator controls the **actions, timing, characters, positions, camera, story, and effects** through code.

The animation engine handles the frame-by-frame movement, physics, rendering, and video generation.

---

# 1. Project Vision

The core idea is simple:

> **Write the fight. Run the program. Get the video.**

For example:

```python
scene = FightScene()

A = scene.add_fighter("A", x=350, y=1500)
B = scene.add_fighter("B", x=730, y=1500)

scene.at(0.0, A.walk_to(500))
scene.at(1.5, B.walk_to(600))

scene.at(2.5, A.punch(B))
scene.at(3.2, B.block())

scene.at(4.0, B.kick(A))
scene.at(4.8, A.dodge())

scene.at(5.5, A.punch(B))
scene.at(6.0, B.fall())

scene.render("output/fight001.mp4")
```

Running:

```bash
python fight001.py
```

should eventually produce:

```text
output/
└── fight001.mp4
```

The creator does **not** need to manually animate hundreds of frames.

---

# 2. How the Fight Is Controlled

The main control system is a **scripted choreography system**.

The creator controls the fight at the action level.

For example:

```python
A.punch(B)
B.block()
B.kick(A)
A.dodge()
A.counter(B)
B.fall()
```

The creator does not have to manually specify:

```text
Move arm to x=421
Rotate elbow
Move shoulder
Move hand
Move body
Move foot
...
```

Instead, the animation engine knows how a punch, kick, dodge, block, fall, etc. should be animated.

The system converts high-level actions into individual animation frames.

---

# 3. Fighter Visual Styles

The renderer supports multiple visual treatments without changing the fight simulation.

The optional **black-ink comic fight style** is selected per fighter:

```python
A = scene.add_fighter("A", x=350, y=1500, render_style="ink_fight")
B = scene.add_fighter("B", x=730, y=1500, render_style="ink_fight")
```

`ink_fight` changes only presentation: heavy black ink strokes, clean negative-space body shapes, minimal directional eye marks, red combat accents, and animation-driven motion marks. The existing skeleton, animation clips, physics, collision/hitboxes, choreography, and weapon attachment points remain the source of truth.

Existing styles remain available:

- `segmented`
- `silhouette`
- `classic`
- `tech`
- `ink_fight`

This makes the black-ink direction an **option**, rather than forcing a visual replacement across the whole engine.

---

# 4. One Fight on One Scene

The first version of the project is intentionally simple.

The initial goal is:

```text
ONE SCENE
   │
   ├── Fighter A
   │
   ├── Fighter B
   │
   ├── Background
   │
   ├── Camera
   │
   └── Fight Timeline
```

For example:

```text
┌─────────────────────────────┐
│                             │
│                             │
│       O             O       │
│      /|\           /|\      │
│      / \           / \      │
│                             │
│       A             B       │
│                             │
└─────────────────────────────┘
```

The entire fight happens inside this scene.

Later, the engine can support multiple scenes.

---

# 5. The Fight Timeline

The timeline controls **when things happen**.

Example:

```python
scene.at(0.0, A.walk_to(500))
scene.at(1.5, B.walk_to(600))

scene.at(2.5, A.punch(B))
scene.at(3.2, B.block())

scene.at(4.0, B.kick(A))
scene.at(4.8, A.dodge())

scene.at(5.5, A.counter(B))
scene.at(6.0, B.fall())
```

This creates:

```text
TIME

0s       A walks
│
1.5s     B walks
│
2.5s     A punches
│
3.2s     B blocks
│
4.0s     B kicks
│
4.8s     A dodges
│
5.5s     A counters
│
6.0s     B falls
│
END
```

The timeline becomes the choreography of the video.

---

# 5. Parallel Actions

Some actions need to happen simultaneously.

For example:

```python
scene.parallel(
    A.punch(B),
    B.dodge()
)
```

This means both actions occur at the same time.

Another example:

```python
scene.parallel(
    A.run_to(500),
    B.run_to(650)
)
```

The engine must therefore support both:

```text
SEQUENTIAL ACTIONS
```

and:

```text
PARALLEL ACTIONS
```

---

# 6. Preview Mode

The project should provide a preview mode for testing a fight before rendering the final video.

Run:

```bash
python fight001.py --preview
```

The program opens an animation window.

The creator should be able to:

```text
▶ Play
⏸ Pause
⏮ Restart
```

and inspect the choreography.

A timeline can eventually show:

```text
0s        2s        4s        6s        8s
│---------│---------│---------│---------│
 walk      punch     kick      dodge     fall
```

The preview does not need to produce the final-quality video.

Its purpose is to make development fast.

---

# 7. Render Mode

After the fight looks correct, the creator renders the final video.

Run:

```bash
python fight001.py --render
```

The renderer generates the required frames and creates the final MP4.

Example:

```text
output/
├── frames/
│   ├── 000001.png
│   ├── 000002.png
│   ├── 000003.png
│   └── ...
│
└── videos/
    └── fight001.mp4
```

---

# 8. Rendering Pipeline

The complete rendering process is:

```text
Fight Script
     │
     ▼
Scene
     │
     ▼
Timeline
     │
     ▼
Actions
     │
     ▼
Animation Engine
     │
     ▼
Physics
     │
     ▼
Collision
     │
     ▼
Camera
     │
     ▼
Visual Effects
     │
     ▼
Audio
     │
     ▼
Frame Renderer
     │
     ▼
FFmpeg
     │
     ▼
MP4
```

---

# 9. Technology Stack

## Python

Python is the primary programming language.

It will control:

* Scene logic
* Characters
* Actions
* Animation
* Physics
* Collision
* Camera
* Effects
* Audio
* Rendering
* Fight scripting

## Pygame

Pygame will initially provide:

* 2D rendering
* Animation preview
* Drawing primitives
* Timing
* Input for development tools

## FFmpeg

FFmpeg will handle final video encoding.

It can be used for:

* Frame-to-video conversion
* MP4 encoding
* Audio
* Video processing
* Final output formatting

---

# 10. Initial Project Architecture

The project should eventually look approximately like:

```text
stickfight/
│
├── README.md
├── requirements.txt
├── main.py
├── generate.py
│
├── engine/
│   ├── __init__.py
│   ├── fighter.py
│   ├── animation.py
│   ├── physics.py
│   ├── collision.py
│   ├── scene.py
│   ├── timeline.py
│   ├── camera.py
│   ├── renderer.py
│   ├── effects.py
│   └── audio.py
│
├── scripting/
│   ├── __init__.py
│   ├── actions.py
│   ├── parser.py
│   └── choreography.py
│
├── scenes/
│   ├── fight001.py
│   ├── fight002.py
│   └── fight003.py
│
├── assets/
│   ├── sounds/
│   ├── music/
│   ├── backgrounds/
│   └── effects/
│
├── output/
│   ├── frames/
│   └── videos/
│
└── tests/
    ├── test_fighter.py
    ├── test_animation.py
    ├── test_physics.py
    ├── test_collision.py
    └── test_renderer.py
```

The structure can change as the project evolves.

---

# 11. Core Engine Components

## Fighter

Responsible for:

* Position
* Rotation
* Scale
* Skeleton
* Health
* State
* Movement
* Current animation

Example:

```python
A = Fighter("A")
B = Fighter("B")
```

---

## Animation

Responsible for:

* Poses
* Keyframes
* Interpolation
* Animation speed
* Animation transitions

Example:

```text
Idle
 ↓
Punch preparation
 ↓
Punch
 ↓
Recovery
 ↓
Idle
```

---

## Physics

Responsible for:

* Gravity
* Velocity
* Acceleration
* Jumping
* Falling
* Knockback
* Ground detection

---

## Collision

Responsible for:

* Hitboxes
* Hurtboxes
* Attack range
* Collision detection
* Damage detection

---

## Timeline

Responsible for:

* Action timing
* Sequencing
* Parallel actions
* Delays
* Scene duration

---

## Camera

Responsible for:

* Position
* Following fighters
* Zoom
* Pan
* Shake
* Framing

---

## Effects

Responsible for:

* Impact flashes
* Particles
* Dust
* Motion lines
* Hit effects
* Screen shake

---

## Audio

Responsible for:

* Punch sounds
* Kick sounds
* Footsteps
* Jump sounds
* Impact sounds
* Background music
* Audio timing

---

## Renderer

Responsible for:

* Drawing frames
* Resolution
* FPS
* Frame output
* Video encoding

---

# 12. Fighter Actions

The first action library should contain:

```text
idle
walk
run
jump
punch
kick
block
dodge
crouch
hit
knockback
fall
```

Eventually:

```text
uppercut
sweep
throw
grab
counter
spin
air_attack
combo
```

---

# 13. Example Fight

A simple fight could be:

```python
from stickfight import FightScene

scene = FightScene(
    width=1080,
    height=1920,
    fps=30
)

A = scene.add_fighter(
    "A",
    x=350,
    y=1500
)

B = scene.add_fighter(
    "B",
    x=730,
    y=1500
)

scene.at(0.0, A.walk_to(500))
scene.at(1.0, B.walk_to(600))

scene.at(2.0, A.punch(B))
scene.at(2.7, B.block())

scene.at(3.5, B.kick(A))
scene.at(4.2, A.dodge())

scene.at(5.0, A.punch(B))
scene.at(5.5, B.knockback())

scene.at(6.2, B.fall())

scene.render("output/fight001.mp4")
```

The creator describes **what happens**.

The engine determines **how it is animated**.

---

# 14. Animation Generation

The engine should eventually use key poses rather than manually creating every frame.

For example:

```text
PUNCH

Pose 1
     O
    /|\
    / \

Pose 2
     O
    /|\
    / \

Pose 3
     O────>
    /|
    / \

Pose 4
     O
    /|\
    / \
```

The engine interpolates the movement.

At 30 FPS:

```text
Pose 1
 ↓
Frame 1
Frame 2
Frame 3
Frame 4
Frame 5
 ↓
Pose 2
...
```

This is what allows high-level commands such as:

```python
A.punch(B)
```

to generate smooth animation.

---

# 15. Physics and Combat

Combat should not be purely visual.

Each fighter should eventually have:

```text
Health
Strength
Speed
Defense
Position
Velocity
State
```

An attack can have:

```text
Damage
Range
Duration
Knockback
Hitbox
Recovery
```

For example:

```python
A.punch(B)
```

could perform:

```text
Prepare
   ↓
Extend arm
   ↓
Activate hitbox
   ↓
Check B
   ↓
Apply damage
   ↓
Apply knockback
   ↓
Play impact effect
   ↓
Play sound
   ↓
Recover
```

---

# 16. Camera System

The camera should make the animation look more cinematic.

Example:

```python
scene.camera.follow(A)
scene.camera.zoom(1.2)
```

During an impact:

```python
scene.camera.shake(
    intensity=8,
    duration=0.2
)
```

The camera system should eventually support:

* Follow
* Zoom
* Pan
* Shake
* Focus
* Transitions
* Automatic framing

---

# 17. TikTok Video Format

The final target is vertical short-form video.

Default target:

```text
Resolution: 1080 × 1920
Aspect Ratio: 9:16
Format: MP4
```

Default frame rate:

```text
30 FPS
```

The system should eventually allow other FPS values.

---

# 18. Backgrounds

The initial background can be simple:

```python
scene.background("plain")
```

Later:

```python
scene.background("dojo")
scene.background("street")
scene.background("arena")
scene.background("city")
```

The background system should support reusable environments.

---

# 19. Audio

Actions should be able to trigger sounds automatically.

Example:

```python
A.punch(B)
```

can automatically trigger:

```text
Punch animation
+
Impact sound
+
Impact effect
+
Camera shake
```

The creator should not have to manually synchronize every sound with every frame.

---

# 20. Captions and Text

The engine should eventually support:

```python
scene.caption(
    "YOU SHOULD HAVE RUN.",
    start=0,
    end=2
)
```

Possible text types:

* Intro
* Dialogue
* Captions
* Character names
* End screen
* Story text

---

# 21. Story System

Once the basic fighting engine works, scenes can include story events.

Example:

```python
scene.dialogue(
    A,
    "You should not have come here."
)

scene.wait(1)

scene.dialogue(
    B,
    "Too late."
)

scene.wait(0.5)

A.punch(B)
```

A video can therefore become:

```text
INTRO
  ↓
DIALOGUE
  ↓
CHARACTERS APPROACH
  ↓
FIGHT
  ↓
COMBO
  ↓
FINAL ATTACK
  ↓
ENDING
```

---

# 22. Multiple Characters

The initial MVP should use two fighters.

Later:

```python
A = scene.fighter("A")
B = scene.fighter("B")
C = scene.fighter("C")
```

This allows:

```text
1 vs 1
2 vs 1
2 vs 2
Tournament
Group fights
Boss fights
```

---

# 23. Character System

Characters should eventually be reusable templates.

Example:

```python
ninja = Character(
    name="Ninja",
    speed=8,
    strength=7
)

robot = Character(
    name="Robot",
    speed=4,
    strength=10
)
```

Different characters can have different:

* Size
* Speed
* Strength
* Jump height
* Attack styles
* Animations
* Effects
* Sounds

---

# 24. Combo System

The engine should support reusable combos.

Example:

```python
A.combo(
    A.punch(B),
    A.punch(B),
    A.kick(B),
    A.uppercut(B)
)
```

Eventually:

```python
A.combo("basic_combo", B)
```

The engine loads the predefined choreography.

---

# 25. Random Fight Generation

Once scripted fights work reliably, the engine can generate fights automatically.

Example:

```python
fight = generate_fight(
    fighters=2,
    duration=30
)
```

The generator can select from:

```text
Walk
Attack
Block
Dodge
Jump
Counter
Combo
Knockback
Fall
```

The generator must still follow combat rules so that actions remain logically possible.

---

# 26. Batch Video Generation

The long-term content workflow should support multiple videos.

Example:

```bash
python generate.py --count 10
```

Output:

```text
output/
├── fight001.mp4
├── fight002.mp4
├── fight003.mp4
├── fight004.mp4
├── fight005.mp4
├── fight006.mp4
├── fight007.mp4
├── fight008.mp4
├── fight009.mp4
└── fight010.mp4
```

This makes the engine suitable for repeatable content production.

---

# 27. Video Templates

Reusable video structures can eventually be created.

Examples:

```text
Quick Fight
Boss Fight
1v1
2v1
Tournament
Comedy Fight
Training Fight
Unexpected Ending
```

A template could define:

```python
template = TikTokTemplate(
    intro=2,
    fight=20,
    outro=3
)
```

---

# 28. Development Roadmap

## Phase 0 — Project Setup

* [ ] Create repository
* [ ] Create Python environment
* [ ] Install Pygame
* [ ] Verify FFmpeg
* [ ] Create project structure
* [ ] Create `main.py`
* [ ] Create initial README
* [ ] Create Git workflow

### Goal

A working Python/Pygame project.

---

# Phase 1 — One Stick Fighter

* [ ] Create head
* [ ] Create body
* [ ] Create arms
* [ ] Create legs
* [ ] Create joints
* [ ] Create position system
* [ ] Create rotation system

### Goal

One programmable stick fighter appears on screen.

---

# Phase 2 — Two Fighters in One Scene

* [ ] Add multiple fighters
* [ ] Position Fighter A
* [ ] Position Fighter B
* [ ] Create scene
* [ ] Create ground
* [ ] Create background

### Goal

A scene containing two fighters.

```text
A                         B
O                         O
|\                        /|
/ \                       / \
```

---

# Phase 3 — Skeleton System

* [ ] Create joints
* [ ] Create body segments
* [ ] Create poses
* [ ] Create joint movement
* [ ] Separate animation from rendering

### Goal

Body parts can move independently.

---

# Phase 4 — Animation System

* [ ] Idle
* [ ] Walk
* [ ] Punch
* [ ] Kick
* [ ] Block
* [ ] Dodge
* [ ] Jump
* [ ] Hit
* [ ] Fall
* [ ] Keyframes
* [ ] Interpolation

### Goal

A fighter can perform complete animations automatically.

---

# Phase 5 — Action System

Implement:

```python
A.walk_to()
A.punch(B)
A.kick(B)
A.block()
A.dodge()
A.jump()
A.fall()
```

### Goal

High-level actions control the animation.

---

# Phase 6 — Timeline System

Implement:

```python
scene.at(time, action)
```

and:

```python
scene.parallel(...)
```

### Goal

The entire fight can be choreographed through time.

---

# Phase 7 — Physics

Implement:

* [ ] Gravity
* [ ] Velocity
* [ ] Jumping
* [ ] Falling
* [ ] Knockback
* [ ] Ground detection

### Goal

Movement becomes physically consistent.

---

# Phase 8 — Combat and Collision

Implement:

* [ ] Hitboxes
* [ ] Hurtboxes
* [ ] Damage
* [ ] Health
* [ ] Blocking
* [ ] Knockback
* [ ] Hit reactions

### Goal

Attacks actually interact with fighters.

---

# Phase 9 — Fight Scripting

Create a clean API such as:

```python
A.punch(B)
B.block()

B.kick(A)
A.dodge()

A.counter(B)
B.fall()
```

### Goal

A complete fight can be written as readable code.

---

# Phase 10 — Preview System

Implement:

```bash
python fight001.py --preview
```

Add:

```text
Play
Pause
Restart
Timeline
```

### Goal

The creator can test choreography before rendering.

---

# Phase 11 — Camera

Implement:

* [ ] Follow
* [ ] Zoom
* [ ] Pan
* [ ] Shake
* [ ] Automatic framing

### Goal

The scene starts looking like a video rather than a technical preview.

---

# Phase 12 — Visual Effects

Implement:

* [ ] Impact flash
* [ ] Particles
* [ ] Dust
* [ ] Motion lines
* [ ] Screen shake
* [ ] Hit effects

### Goal

Make fights visually interesting.

---

# Phase 13 — Audio

Implement:

* [ ] Punch sounds
* [ ] Kick sounds
* [ ] Impact sounds
* [ ] Footsteps
* [ ] Jump sounds
* [ ] Fall sounds
* [ ] Music
* [ ] Automatic timing

### Goal

Audio follows the choreography automatically.

---

# Phase 14 — Video Renderer

Implement:

* [ ] Frame generation
* [ ] PNG output
* [ ] FFmpeg integration
* [ ] MP4 output
* [ ] FPS control

### Goal

Convert a scene into a video.

---

# Phase 15 — TikTok Format

Default:

```text
1080 × 1920
9:16
30 FPS
MP4
```

### Goal

Produce a vertical short-form video.

---

# Phase 16 — Captions and Story

Implement:

* [ ] Dialogue
* [ ] Captions
* [ ] Intro
* [ ] Outro
* [ ] Story events
* [ ] Text animation

### Goal

Produce complete short-form stories rather than only fights.

---

# Phase 17 — Reusable Characters

Implement character templates.

### Goal

Create different fighters without rewriting the engine.

---

# Phase 18 — Combos

Implement reusable attack combinations.

### Goal

Complex fight sequences can be represented by simple commands.

---

# Phase 19 — Random Fight Generator

Implement:

```bash
python generate.py
```

### Goal

Generate new fights automatically.

---

# Phase 20 — Batch Rendering

Implement:

```bash
python generate.py --count 10
```

### Goal

Generate multiple videos automatically.

---

# Phase 21 — Full Content Pipeline

The final workflow should become:

```text
CREATE IDEA
    ↓
CREATE STORY
    ↓
CREATE FIGHT SCRIPT
    ↓
RUN PREVIEW
    ↓
CHECK CHOREOGRAPHY
    ↓
RENDER
    ↓
ADD AUDIO
    ↓
ADD EFFECTS
    ↓
CREATE MP4
```

Eventually, the system can automate much more of this pipeline.

---

# 29. MVP Definition

The first version should **not** attempt to build the entire system.

The MVP is:

```text
ONE SCENE
     ↓
TWO FIGHTERS
     ↓
BASIC STICK FIGURES
     ↓
IDLE
     ↓
WALK
     ↓
PUNCH
     ↓
KICK
     ↓
BLOCK
     ↓
DODGE
     ↓
HIT
     ↓
FALL
     ↓
TIMELINE
     ↓
PREVIEW
     ↓
RENDER
     ↓
MP4
```

The first major success condition is:

```bash
python fight001.py --render
```

produces a short, playable stick-fighting MP4 automatically.

---

# 30. Example Final Workflow

Once the project is mature, creating a video should look something like this.

### Step 1 — Create a scene

```python
scene = FightScene(
    width=1080,
    height=1920,
    fps=30
)
```

### Step 2 — Add fighters

```python
A = scene.fighter("A", x=350)
B = scene.fighter("B", x=730)
```

### Step 3 — Write the choreography

```python
scene.at(0, A.walk_to(500))
scene.at(1, B.walk_to(600))

scene.at(2, A.punch(B))
scene.at(3, B.block())

scene.at(4, B.kick(A))
scene.at(5, A.dodge())

scene.at(6, A.counter(B))
scene.at(7, B.fall())
```

### Step 4 — Preview

```bash
python fight001.py --preview
```

### Step 5 — Render

```bash
python fight001.py --render
```

### Step 6 — Output

```text
output/videos/fight001.mp4
```

---

# 31. Design Principle

The project should always separate:

## WHAT HAPPENS

from:

## HOW IT IS ANIMATED

For example:

```python
A.punch(B)
```

is the **what**.

The engine handles:

```text
Arm movement
Body movement
Timing
Hit detection
Damage
Reaction
Particles
Camera shake
Sound
Frame generation
```

This separation is one of the most important architectural principles of the project.

---

# 32. Long-Term Vision

The final project is not intended to be only a stick-figure game.

It is intended to become a:

> **Programmatic 2D animation and short-form video generation engine.**

The creator writes:

```python
A.punch(B)
B.block()
B.kick(A)
A.dodge()
A.counter(B)
B.fall()
```

The computer handles:

```text
Animation
Physics
Collision
Camera
Effects
Audio
Rendering
Video Encoding
```

The final pipeline becomes:

```text
              CODE
                │
                ▼
          FIGHT SCRIPT
                │
                ▼
             SCENE
                │
                ▼
           TIMELINE
                │
                ▼
          ANIMATION ENGINE
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
    PHYSICS  COLLISION  CAMERA
       │        │        │
       └────────┼────────┘
                ▼
             EFFECTS
                │
                ▼
              AUDIO
                │
                ▼
            RENDERER
                │
                ▼
             FFmpeg
                │
                ▼
           TikTok MP4
```

---

# 33. Ultimate Objective

The completed system should make this possible:

```bash
python fight001.py
```

and automatically produce:

```text
fight001.mp4
```

with:

```text
✓ Stick-figure animation
✓ Fight choreography
✓ Physics
✓ Collision
✓ Camera movement
✓ Visual effects
✓ Sound effects
✓ Music
✓ Captions
✓ Vertical 9:16 format
✓ MP4 encoding
```

The creator's primary job becomes **writing and designing the fight**, rather than manually animating it.

---

# 34. Project Philosophy

Start simple.

Do not attempt to build the entire animation engine immediately.

Build in this order:

```text
ONE FIGHTER
    ↓
TWO FIGHTERS
    ↓
ONE ACTION
    ↓
MULTIPLE ACTIONS
    ↓
TIMELINE
    ↓
COMBAT
    ↓
PHYSICS
    ↓
CAMERA
    ↓
EFFECTS
    ↓
AUDIO
    ↓
VIDEO
    ↓
AUTOMATION
```

Every stage should produce something that can be tested before moving to the next stage.

---

# 35. First Target

The very first target is deliberately small:

```text
Two stick figures
      ↓
One scene
      ↓
A walks toward B
      ↓
A punches B
      ↓
B reacts
      ↓
B falls
      ↓
Animation finishes
```

Once that works reliably, the engine can grow into the full automated TikTok video-generation system.

---

**Core idea:**

> **You write the choreography. The engine creates the animation.**
