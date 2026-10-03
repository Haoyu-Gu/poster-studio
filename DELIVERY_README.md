# HTML poster delivery

- `poster.pdf`: one-page print canvas. Print at 100% / actual size; verify physical dimensions.
- `poster_300dpi.png`: high-resolution raster export. Prefer PDF for printing.
- `poster_standalone.html`: one self-contained editable preview; local images inlined.
- `source/poster.html` + referenced `source/assets/`: editable source.
- `tools/` + `requirements.txt`: local check, QR and export code.

To reproduce, create a dedicated virtual environment, install requirements and Playwright Chromium, then run:

```bash
.venv/bin/python tools/poster.py export source/poster.html --out reproduced --dpi 300
```

No process notes or private evidence are included. Printed QR codes need adequate contrast and a clear quiet zone. Fonts depend on the local machine unless licensed static font files have been embedded manually; cross-platform pixel equality is not guaranteed.
