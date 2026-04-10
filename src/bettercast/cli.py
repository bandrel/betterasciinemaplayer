from __future__ import annotations

from pathlib import Path

import click

from bettercast.engine import PlaybackEngine
from bettercast.formats.v2 import V2Parser
from bettercast.ui.app import BettercastApp


@click.command()
@click.argument("cast_file", type=click.Path(exists=True, path_type=Path))
@click.option("--speed", default=1.0, type=float, help="Initial playback speed (default: 1.0)")
def main(cast_file: Path, speed: float) -> None:
    """Play asciinema recordings in a terminal UI."""
    parser = V2Parser()
    try:
        recording = parser.parse(cast_file)
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    if not recording.events:
        raise click.ClickException("Recording has no events.")

    engine = PlaybackEngine(recording)
    engine.set_speed(speed)

    app = BettercastApp(engine)
    app.run()
