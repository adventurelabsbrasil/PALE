#!/usr/bin/env python3
"""Serve the isolated Music Sculpture and its local piano library."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import mimetypes
import shutil
import urllib.parse

ROOT = Path(__file__).resolve().parents[1] / "src" / "acoustic_lab" / "web"
DOWNLOADS = Path.home() / "Downloads"
TRACKS = {
    "chopin": DOWNLOADS / "Classicals.de - Chopin - Nocturne Op. 9, No. 2 in E-flat major.mp3",
    "beethoven": DOWNLOADS / "Classicals.de - Beethoven - Für Elise - Bagatelle No. 25 in A Minor, WoO 59.mp3",
    "bach": DOWNLOADS / "Classicals.de - Bach - The Well-Tempered Clavier, Book 1 - 03 - Prelude No. 2 in C minor, BWV 847 (Kimiko Ishizaka).mp3",
    "moonlight": Path(__file__).resolve().parents[1] / "artifacts" / "musics" / "Classicals.de-Beethoven-Moonlight-Sonata-1.-Movement-Sonata-Nr.-14,-Op.-27,-Nr.-2.mp3",
    "tetris": Path(__file__).resolve().parents[1] / "artifacts" / "musics" / "Classicals.de+-+Tetris+Theme+-+Korobeiniki+-+Rearranged+-+Arranged+for+Piano.mp3",
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/music/"):
            key = path.removeprefix("/music/").removesuffix(".mp3")
            source = TRACKS.get(key)
            if source is None or not source.is_file():
                self.send_error(404, "Track unavailable")
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(source.stat().st_size))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with source.open("rb") as stream:
                shutil.copyfileobj(stream, self.wfile)
            return
        super().do_GET()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", type=int, default=8007)
    args = parser.parse_args()
    missing = [str(path) for path in TRACKS.values() if not path.is_file()]
    if missing:
        print("Aviso: faixas ausentes:")
        for path in missing:
            print(f"  - {path}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Music Sculpture em http://127.0.0.1:{args.port}/music_painting.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
