from __future__ import annotations

import json
from pathlib import Path

import click

from bettercast.engine import PlaybackEngine
from bettercast.formats.v2 import V2Parser
from bettercast.formats.v3 import V3Parser
from bettercast.ui.app import BettercastApp


def _detect_version(cast_file: Path) -> int:
    with open(cast_file) as f:
        first_line = f.readline().strip()
    if not first_line:
        raise ValueError("Empty cast file")
    header = json.loads(first_line)
    return header.get("version", 2)


@click.command()
@click.argument("cast_file", type=click.Path(exists=True, path_type=Path))
@click.option("--speed", default=1.0, type=float, help="Initial playback speed (default: 1.0)")
@click.option("--idle-threshold", default=2.0, type=float, help="Skip idle gaps longer than this (seconds, default: 2.0)")
@click.option("--no-idle-compress", is_flag=True, default=False, help="Disable idle time compression")
def main(cast_file: Path, speed: float, idle_threshold: float, no_idle_compress: bool) -> None:
    """Play asciinema recordings in a terminal UI."""
    try:
        version = _detect_version(cast_file)
        if version == 3:
            parser = V3Parser()
        else:
            parser = V2Parser()
        recording = parser.parse(cast_file)
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    if not recording.events:
        raise click.ClickException("Recording has no events.")

    engine = PlaybackEngine(recording)
    engine.set_speed(speed)
    engine.idle_threshold = float("inf") if no_idle_compress else idle_threshold

    app = BettercastApp(engine)
    app.run()
