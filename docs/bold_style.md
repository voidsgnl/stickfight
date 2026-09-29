# `bold` render style

A bold, seamless-line look for fighters. Presentation-only: it uses the same
skeleton joints, animation clips, physics, hitboxes and weapon attachment
points as every other style.

```python
A = scene.add_fighter("A", x=350, y=1500, color=(232, 68, 58), render_style="bold")
B = scene.add_fighter("B", x=730, y=1500, color=(61, 139, 255), render_style="bold")
```

## What it looks like

- **One continuous body.** All outlines are drawn first, then all fills in a
  single colour, so overlapping limbs never draw a border across each other and
  the figure never looks segmented.
- **Smooth joints.** Spine, neck, head, arms and legs are drawn as smooth
  curves through the joints, so elbows, knees and shoulders bend without breaks.
- **Polish.** A soft glow in the fighter's colour, a highlight line so strokes
  read as rounded tubes, and a darker outline that keeps colours crisp on any
  background.
- **Motion smear.** Punch, uppercut, slash, jab, cross and hook clips leave
  ghost frames of the striking arm; kick, sweep and low_kick clips do the same
  for the leg. Speed lines trail behind the hand or foot.
- **Headbands and weapons** (sword, staff) still attach to the existing
  skeleton joints.

## Tuning

Constants at the top of `stickfight/engine/bold_style.py`:

| Constant | Default | Effect |
|---|---|---|
| `BASE_LINE_WIDTH` | `16.0` | Body line thickness (rig units, scaled by fighter scale and zoom) |
| `OUTLINE_EXTRA` | `6.0` | Extra thickness of the dark outline |
| `TRAIL_GHOSTS` | `((6, 30), (4, 55), (2, 80))` | Smear ghosts as (frames ago, opacity) |
| `ATTACK_ARM_CLIPS` / `ATTACK_LEG_CLIPS` | see file | Which clips trigger smear |

The glow strength is the alpha value (`95`) in `_draw_glow`.

## Notes

- Motion-smear history is stored per fighter on the `Renderer` instance
  (`_bold_trails`) and is only used by this style.
- Values were tuned from a browser mock-up. Check them against real rendered
  frames and adjust the constants above if needed.
