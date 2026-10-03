"""Build gallery thumbnails from draft PDF exports; no fabricated paper data."""
import argparse
from pathlib import Path
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path)
parser.add_argument('target',type=Path)
args = parser.parse_args()
if args.target.exists():
    parser.error('Refusing to overwrite existing thumbnail')
args.target.parent.mkdir(parents=True,exist_ok=True)
with Image.open(args.source) as im:
    im.thumbnail((900,1400))
    im.save(args.target)
