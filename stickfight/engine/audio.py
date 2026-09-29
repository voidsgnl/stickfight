"""
Audio synthesizer and timeline sound mixer.
Synthesizes procedural combat sound effects (punch, kick, block, whoosh, fall)
and mixes them for live playback in Pygame and audio muxing via FFmpeg.
"""

from __future__ import annotations
import os
import math
import struct
import wave
from typing import Callable, List, Tuple, Dict, Optional
import numpy as np


class SoundSynthesizer:
    SAMPLE_RATE = 44100
    NOISE_SEED = 1337  # fixed so generated sounds are identical on every machine

    @classmethod
    def _noise(cls, n: int) -> np.ndarray:
        return np.random.default_rng(cls.NOISE_SEED).uniform(-1, 1, n)

    @classmethod
    def generate_whoosh(cls) -> np.ndarray:
        """Fast pitch drop white noise + tone for swinging limbs."""
        dur = 0.22
        t = np.linspace(0, dur, int(cls.SAMPLE_RATE * dur), endpoint=False)
        noise = cls._noise(len(t))
        envelope = np.sin(np.pi * (t / dur)) ** 2
        # Pitch glide tone
        freq = 300 - 180 * (t / dur)
        tone = np.sin(2 * np.pi * freq * t)
        signal = (0.6 * noise + 0.4 * tone) * envelope * 0.7
        return signal

    @classmethod
    def generate_punch(cls) -> np.ndarray:
        """Meaty impact: swift transient, punchy mid-low thud, decay."""
        dur = 0.28
        t = np.linspace(0, dur, int(cls.SAMPLE_RATE * dur), endpoint=False)
        # Low frequency punch thump (160 Hz -> 50 Hz)
        f_start, f_end = 180.0, 45.0
        inst_phase = 2 * np.pi * (f_start * t + 0.5 * (f_end - f_start) * (t**2) / dur)
        sub = np.sin(inst_phase)
        # Snap transient
        noise = cls._noise(len(t)) * np.exp(-35.0 * t)
        env = np.exp(-12.0 * t)
        signal = (sub * 0.7 + noise * 0.8) * env
        return np.clip(signal, -1.0, 1.0) * 0.9

    @classmethod
    def generate_kick(cls) -> np.ndarray:
        """Heavy bass impact: deep thud with higher energy."""
        dur = 0.35
        t = np.linspace(0, dur, int(cls.SAMPLE_RATE * dur), endpoint=False)
        f_start, f_end = 140.0, 35.0
        inst_phase = 2 * np.pi * (f_start * t + 0.5 * (f_end - f_start) * (t**2) / dur)
        sub = np.sin(inst_phase)
        noise = cls._noise(len(t)) * np.exp(-25.0 * t)
        env = np.exp(-9.0 * t)
        signal = (sub * 0.85 + noise * 0.6) * env
        return np.clip(signal, -1.0, 1.0) * 0.95

    @classmethod
    def generate_block(cls) -> np.ndarray:
        """High-pitched sharp metallic/wooden clack."""
        dur = 0.20
        t = np.linspace(0, dur, int(cls.SAMPLE_RATE * dur), endpoint=False)
        tone1 = np.sin(2 * np.pi * 880 * t)
        tone2 = np.sin(2 * np.pi * 1240 * t)
        tone3 = np.sin(2 * np.pi * 1760 * t)
        noise = cls._noise(len(t)) * 0.4
        env = np.exp(-28.0 * t)
        signal = (tone1 * 0.4 + tone2 * 0.3 + tone3 * 0.2 + noise) * env
        return np.clip(signal, -1.0, 1.0) * 0.85

    @classmethod
    def generate_fall(cls) -> np.ndarray:
        """Low body slam against floor."""
        dur = 0.40
        t = np.linspace(0, dur, int(cls.SAMPLE_RATE * dur), endpoint=False)
        sub = np.sin(2 * np.pi * 65 * t) * np.exp(-8.0 * t)
        noise = cls._noise(len(t)) * np.exp(-20.0 * t) * 0.5
        signal = (sub + noise)
        return np.clip(signal, -1.0, 1.0) * 0.9

    @classmethod
    def generate_clang(cls) -> np.ndarray:
        """Metallic sword blade clash with resonant harmonic ringing."""
        dur = 0.55
        t = np.linspace(0, dur, int(cls.SAMPLE_RATE * dur), endpoint=False)
        harmonics = [
            (1180.0, 0.5, 18.0),
            (1740.0, 0.4, 22.0),
            (2620.0, 0.35, 26.0),
            (3880.0, 0.25, 32.0),
            (5200.0, 0.15, 38.0),
        ]
        signal = np.zeros_like(t)
        for freq, amp, decay in harmonics:
            signal += amp * np.sin(2 * np.pi * freq * t) * np.exp(-decay * t)
        # Sharp impact transient
        transient = cls._noise(len(t)) * np.exp(-80.0 * t) * 0.6
        signal += transient
        return np.clip(signal, -1.0, 1.0) * 0.9

    @classmethod
    def generate_blade_slice(cls) -> np.ndarray:
        """High frequency razor-sharp air slicing whoosh."""
        dur = 0.26
        t = np.linspace(0, dur, int(cls.SAMPLE_RATE * dur), endpoint=False)
        noise = cls._noise(len(t))
        envelope = np.sin(np.pi * (t / dur)) ** 3
        freq = 900 - 550 * (t / dur)
        whistle = np.sin(2 * np.pi * freq * t)
        signal = (0.7 * noise + 0.3 * whistle) * envelope
        return np.clip(signal, -1.0, 1.0) * 0.85


class AudioManager:
    # Sounds that get a small random pitch/gain change so repeated hits
    # don't sound like the same sample played ten times.
    VARIED = {"punch", "kick", "block", "whoosh", "clang", "blade_slice", "fall"}

    def __init__(self, asset_dir: str = "assets/sounds", seed: int = 0):
        self.asset_dir = asset_dir
        self.sample_rate = 44100
        self.sounds: Dict[str, np.ndarray] = {}
        # (scene_timestamp, sound_name, pitch_rate, gain)
        self.scheduled_events: List[Tuple[float, str, float, float]] = []
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.variation = True
        self.pygame_sounds: Dict[str, any] = {}
        self._initialized_pygame = False

        self._load_or_generate_sounds()

    def _load_or_generate_sounds(self):
        os.makedirs(self.asset_dir, exist_ok=True)
        generators = {
            "whoosh": SoundSynthesizer.generate_whoosh,
            "punch": SoundSynthesizer.generate_punch,
            "kick": SoundSynthesizer.generate_kick,
            "block": SoundSynthesizer.generate_block,
            "fall": SoundSynthesizer.generate_fall,
            "clang": SoundSynthesizer.generate_clang,
            "blade_slice": SoundSynthesizer.generate_blade_slice,
        }

        for name, gen_fn in generators.items():
            path = os.path.join(self.asset_dir, f"{name}.wav")
            if os.path.exists(path):
                # Read WAV
                try:
                    with wave.open(path, 'rb') as wf:
                        n_frames = wf.getnframes()
                        frames = wf.readframes(n_frames)
                        data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
                        self.sounds[name] = data
                        continue
                except Exception:
                    pass

            # Generate and write WAV
            raw = gen_fn()
            self.sounds[name] = raw
            int_data = (np.clip(raw, -1.0, 1.0) * 32767.0).astype(np.int16)
            # Write atomically so parallel renderers never read a half-written file.
            tmp_path = f"{path}.{os.getpid()}.tmp"
            try:
                with wave.open(tmp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(int_data.tobytes())
                os.replace(tmp_path, path)
            except Exception:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def reset(self):
        """Clears scheduled sounds and restarts the variation RNG."""
        self.scheduled_events.clear()
        self.rng = np.random.default_rng(self.seed)

    def schedule_sound(self, timestamp: float, sound_name: str,
                       pitch: Optional[float] = None, gain: Optional[float] = None):
        """Schedules a sound effect at a scene timestamp.

        pitch is a playback-rate multiplier (1.0 = original). When left as
        None, varied sounds get a small seeded random pitch/gain change.
        """
        if sound_name not in self.sounds:
            return
        if pitch is None and gain is None and self.variation and sound_name in self.VARIED:
            pitch = float(self.rng.uniform(0.93, 1.07))
            gain = float(self.rng.uniform(0.88, 1.0))
        self.scheduled_events.append((timestamp, sound_name, pitch or 1.0, 1.0 if gain is None else gain))

    def play_sound_immediate(self, sound_name: str):
        """Attempts to play sound immediately via Pygame mixer (preview mode)."""
        import pygame
        if not self._initialized_pygame:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1)
                self._initialized_pygame = True
            except Exception:
                return

        if sound_name not in self.pygame_sounds and sound_name in self.sounds:
            try:
                raw_bytes = (self.sounds[sound_name] * 32767.0).astype(np.int16).tobytes()
                self.pygame_sounds[sound_name] = pygame.mixer.Sound(buffer=raw_bytes)
            except Exception:
                pass

        snd = self.pygame_sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    @staticmethod
    def _resample(data: np.ndarray, rate: float) -> np.ndarray:
        """Tape-style pitch shift: rate > 1 is higher and shorter."""
        if abs(rate - 1.0) < 1e-3 or len(data) < 2:
            return data
        idx = np.arange(0.0, len(data) - 1, rate)
        return np.interp(idx, np.arange(len(data)), data).astype(np.float32)

    def export_mix_wav(self, total_duration: float, output_path: str,
                       time_map: Optional[Callable[[float], float]] = None):
        """Mixes all scheduled sound events into a single master WAV file.

        time_map converts scene time to video time (slow motion and hit-stop
        make them differ); by default they are the same.
        """
        total_samples = int(total_duration * self.sample_rate) + self.sample_rate
        master = np.zeros(total_samples, dtype=np.float32)

        for ts, name, pitch, gain in self.scheduled_events:
            if name not in self.sounds:
                continue
            video_ts = time_map(ts) if time_map else ts
            start_idx = int(video_ts * self.sample_rate)
            if start_idx < 0:
                continue
            snd_data = self._resample(self.sounds[name], pitch) * gain
            end_idx = min(len(master), start_idx + len(snd_data))
            length = end_idx - start_idx
            if length > 0:
                master[start_idx:end_idx] += snd_data[:length]

        master = np.clip(master, -1.0, 1.0)
        int_data = (master * 32767.0).astype(np.int16)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(int_data.tobytes())
