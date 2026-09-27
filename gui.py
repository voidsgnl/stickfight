#!/usr/bin/env python3
"""
Stick Fight Video Engine — Interactive Studio GUI
Launch with: python gui.py
"""

from __future__ import annotations
import sys
import os
import argparse
import webbrowser

# Ensure stickfight package is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from stickfight.gui.app import run_server


def main():
    parser = argparse.ArgumentParser(description="Stick Fight Video Engine — Interactive Studio GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind server (default: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print("=" * 60)
    print("⚔️  STICK FIGHT VIDEO ENGINE — STUDIO GUI")
    print(f"📍 Web Interface: {url}")
    print("💡 Configure fighters, test live previews, and render MP4s easily!")
    print("=" * 60)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
