"""Create, preview, export and package academic posters."""
from __future__ import annotations

import argparse
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import mimetypes
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ('band-story', 'two-column', 'figure-first')


def require_new(path: Path) -> None:
    if path.exists():
        raise ValueError(f'Refusing to overwrite: {path}')


def local_asset(value: str, parent: Path) -> Path:
    if Path(value).is_absolute():
        raise ValueError('Use project-relative asset paths')
    raw = parent / value
    for candidate in [raw, *raw.parents]:
        if candidate == parent:
            break
        if candidate.is_symlink():
            raise ValueError('Symlink assets are not deliverable: ' + value)
    path = (parent / value).resolve()
    if not path.is_relative_to(parent.resolve()) or not path.is_file():
        raise ValueError(f'Asset must exist inside the project: {value}')
    return path


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def dependencies(source: Path) -> list[Path]:
    text = source.read_text(encoding='utf-8')
    values = re.findall(r'\bsrc=[\"\']([^\"\']+)',text)
    return sorted({local_asset(v,source.parent) for v in values if not v.startswith('data:')})


def fingerprint(source: Path) -> dict[str,str]:
    source = source.resolve()
    return {p.relative_to(source.parent).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [source,*dependencies(source)]}


def bundle_text(source: Path) -> str:
    """Inline local CSS and images; reject unresolved or remote resources."""
    text = source.read_text(encoding='utf-8')

    def css_link(match):
        tag = match.group(0)
        href = re.search(r'href=[\"\']([^\"\']+)', tag).group(1)
        css_path = local_asset(href, source.parent)
        css = css_path.read_text(encoding='utf-8')
        if re.search(r'@import|url\(', css):
            raise ValueError('Inline CSS assets first; @import/url() are not supported by this lean bundler')
        return '<style>\n' + css + '\n</style>'

    text = re.sub(r'<link\b(?=[^>]*rel=[\"\']stylesheet[\"\'])[^>]*>', css_link, text, flags=re.I)

    def inline_src(match):
        quote, value = match.groups()
        if value.startswith('data:'):
            return match.group(0)
        return f'src={quote}{data_uri(local_asset(value, source.parent))}{quote}'

    text = re.sub(r'\bsrc=([\"\'])(.*?)\1', inline_src, text)
    if re.search(r'@import|url\(|<script\b|<iframe\b', text, re.I):
        raise ValueError('Poster handoff must have no script/iframe or unresolved CSS resource')
    return text


def canvas(source: Path) -> tuple[float, float]:
    text = source.read_text(encoding='utf-8')
    for href in re.findall(r'<link[^>]*href=[\"\']([^\"\']+)', text):
        # Templates may reference ../styles; projects are flattened at init.
        candidate = (source.parent / href).resolve()
        text += '\n' + candidate.read_text(encoding='utf-8')
    match = re.search(r'@page\s*\{[^}]*size:\s*([\d.]+)mm\s+([\d.]+)mm', text)
    if not match:
        raise ValueError('Expected @page { size: WIDTHmm HEIGHTmm; ... }')
    width, height = map(float, match.groups())
    if not 100 <= width <= 2000 or not 100 <= height <= 2000:
        raise ValueError('Canvas must be between 100 and 2000 mm on each side')
    return width, height


def init(args):
    dest = args.dest.resolve()
    require_new(dest)
    dest.mkdir(parents=True)
    html = (ROOT / 'templates' / f'{args.template}.html').read_text(encoding='utf-8')
    css = (ROOT / 'styles/poster.css').read_text(encoding='utf-8')
    html = html.replace('<link rel="stylesheet" href="../styles/poster.css">', '<style>\n' + css + '\n</style>')
    html = html.replace('../assets/', 'assets/')
    (dest / 'poster.html').write_text(html, encoding='utf-8')
    shutil.copytree(ROOT / 'assets', dest / 'assets')
    shutil.copytree(ROOT / 'project', dest / 'notes')
    (dest / 'design_tokens.json').write_text(json.dumps({
        'template':args.template, 'canvas_mm':[841,1189], 'status':'unfilled scaffold',
        'accent':'#633a91', 'decision':'Choose content and venue before locking this direction',
        'hue_centers':{'accent':268,'emph':268}}, indent=2) + '\n')
    print(dest / 'poster.html')


def inspect(source, draft=False):
    from playwright.sync_api import sync_playwright
    width, height = canvas(source)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width':round(width / 25.4 * 96), 'height':round(height / 25.4 * 96)})
        page.emulate_media(media='print')
        # Rendering must never silently depend on internet resources.
        page.route(re.compile(r'^https?://'), lambda route: route.abort())
        page.goto(source.as_uri(), wait_until='networkidle')
        page.evaluate('async () => {await document.fonts.ready; await Promise.all([...document.images].map(i => i.decode().catch(() => null)));}')
        report = page.evaluate((ROOT / 'tools/qa.js').read_text())
        report['canvas_mm'] = [width, height]
        visible = page.locator('.poster').inner_text()
        if not draft and re.search(r'\bTODO\b|\bDEMO\b|example\.org', visible + source.read_text()):
            report['errors'].append('Unfilled TODO/DEMO/example.org placeholders; use --draft only for scaffolds')
        browser.close()
    return report


def render(args):
    import pymupdf
    from playwright.sync_api import sync_playwright
    source, out = args.source.resolve(), args.out.resolve()
    report = inspect(source, draft=args.draft)
    if report['errors']:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise ValueError('Fix layout/resource/placeholder errors before export')
    require_new(out)
    out.mkdir(parents=True)
    width, height = canvas(source)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width':round(width / 25.4 * 96), 'height':round(height / 25.4 * 96)})
        page.emulate_media(media='print')
        page.route(re.compile(r'^https?://'), lambda route: route.abort())
        page.goto(source.as_uri(), wait_until='networkidle')
        page.evaluate('async () => {await document.fonts.ready; await Promise.all([...document.images].map(i => i.decode()));}')
        page.pdf(path=str(out / 'poster.pdf'), width=f'{width / 25.4}in', height=f'{height / 25.4}in',
                 print_background=True, margin={k:'0' for k in ('top','right','bottom','left')})
        browser.close()
    with pymupdf.open(out / 'poster.pdf') as doc:
        if len(doc) != 1:
            raise ValueError(f'Expected one page, got {len(doc)}')
        rect = doc[0].rect
        if abs(rect.width * 25.4 / 72 - width) > 1 or abs(rect.height * 25.4 / 72 - height) > 1:
            raise ValueError('PDF dimensions differ from the canvas by more than 1 mm')
        pixels = round(width / 25.4 * args.dpi) * round(height / 25.4 * args.dpi)
        if pixels > 160_000_000:
            raise ValueError('PNG exceeds 160 MP; reduce --dpi')
        doc[0].get_pixmap(dpi=args.dpi, alpha=False).save(out / f'poster_{args.dpi}dpi.png')
        # Decode QR crops from the actual PDF, not just the source image.
        import zxingcpp
        from PIL import Image
        decoded = []
        for image in report['images']:
            if not image['qr']:
                continue
            r = pymupdf.Rect(image['x']*.75, image['y']*.75,
                            (image['x']+image['width'])*.75, (image['y']+image['height'])*.75)
            pix = doc[0].get_pixmap(clip=r, dpi=300, alpha=False)
            codes = zxingcpp.read_barcodes(Image.frombytes('RGB', (pix.width,pix.height), pix.samples))
            values = [code.text for code in codes]
            expected = image['expected']
            # WeChat QR is not a public URL; set its anchor href to the decoded target
            # or omit href and manually verify by phone. Never claim an untested QR passed.
            matched = bool(values) and (not expected or expected in values)
            decoded.append({'asset':image['src'], 'decoded':bool(values), 'target_matches':matched})
            if not matched:
                report['errors'].append('QR decode/target mismatch: ' + image['src'])
        report['qr_checks'] = decoded
        report['pdf_pages'] = 1
    report['status'] = 'DRAFT_LAYOUT_CHECKED' if args.draft else 'LAYOUT_CHECKED_MANUAL_REVIEW_REQUIRED'
    report['source_hashes'] = fingerprint(source)
    (out / 'check_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    if report['errors']:
        raise ValueError('PDF was rendered, but QR checks failed. See check_report.json; not final.')
    if not args.draft:
        (out / 'poster_standalone.html').write_text(bundle_text(source), encoding='utf-8')
    print(out)


def qr(args):
    import qrcode
    from qrcode.image.svg import SvgPathImage
    require_new(args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4, box_size=24)
    code.add_data(args.url)
    code.make(fit=True)
    code.make_image(image_factory=SvgPathImage).save(str(args.out))
    print(args.out)


def package(args):
    """Explicit allowlist, never include notes, evidence, drafts, envs, or history."""
    from PIL import Image
    project, final = args.project.resolve(), args.final.resolve()
    report = json.loads((final / 'check_report.json').read_text())
    if report.get('errors') or report.get('status') != 'LAYOUT_CHECKED_MANUAL_REVIEW_REQUIRED':
        raise ValueError('Package requires a non-draft export with no errors')
    require_new(args.out)
    names = ['poster.pdf', 'poster_300dpi.png', 'poster_standalone.html']
    for name in names:
        if not (final / name).is_file():
            raise ValueError('Final export must include ' + name)
    source = project / 'poster.html'
    if report.get('source_hashes') != fingerprint(source):
        raise ValueError('Source/assets changed after export; export again before packaging')
    files = [(source,'source/poster.html')]
    for path in dependencies(source):
        if path.is_symlink() or path.suffix.lower() not in {'.svg','.png','.jpg','.jpeg','.webp'} or any(p.startswith('.') for p in path.relative_to(project).parts):
            raise ValueError('Unexpected delivery asset: ' + path.name)
        if path.suffix.lower() != '.svg':
            with Image.open(path) as image:
                if image.getexif() or any(k in image.info for k in ('exif','xmp','XML:com.adobe.xmp','comment','Description')):
                    raise ValueError('Remove metadata from a separate delivery copy: ' + path.name)
        files.append((path,'source/' + path.relative_to(project).as_posix()))
    files += [(final / name,name) for name in names]
    files += [(ROOT / 'tools' / name,'tools/' + name) for name in ('poster.py','qa.js')]
    files += [(ROOT / 'requirements.txt','requirements.txt'),(ROOT / 'DELIVERY_README.md','README.md')]
    for path, name in files:
        if path.suffix in {'.html','.svg','.md'}:
            text = path.read_text()
            if re.search(r'/Users/|/home/|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}', text):
                raise ValueError('Possible private local path or secret in ' + path.name)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path,name in files:
            archive.write(path,name)
    print(args.out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command',required=True)
    p = subs.add_parser('init'); p.add_argument('template',choices=TEMPLATES); p.add_argument('dest',type=Path); p.set_defaults(func=init)
    p = subs.add_parser('preview'); p.add_argument('--root',type=Path,default=ROOT); p.add_argument('--port',type=int,default=8790)
    p = subs.add_parser('check'); p.add_argument('source',type=Path); p.add_argument('--draft',action='store_true')
    p = subs.add_parser('export'); p.add_argument('source',type=Path); p.add_argument('--out',type=Path,required=True); p.add_argument('--dpi',type=int,choices=(72,150,300),default=300); p.add_argument('--draft',action='store_true'); p.set_defaults(func=render)
    p = subs.add_parser('qr'); p.add_argument('url'); p.add_argument('out',type=Path); p.set_defaults(func=qr)
    p = subs.add_parser('package'); p.add_argument('project',type=Path); p.add_argument('--final',type=Path,required=True); p.add_argument('--out',type=Path,required=True); p.add_argument('--privacy-reviewed',action='store_true'); p.set_defaults(func=package)
    args = parser.parse_args()
    try:
        if args.command == 'preview':
            handler = partial(SimpleHTTPRequestHandler,directory=str(args.root.resolve()))
            print(f'Local only: http://127.0.0.1:{args.port}/',flush=True)
            ThreadingHTTPServer(('127.0.0.1',args.port),handler).serve_forever()
        elif args.command == 'check':
            report = inspect(args.source.resolve(),args.draft)
            print(json.dumps(report,ensure_ascii=False,indent=2))
            if report['errors']: raise SystemExit(1)
        elif args.command == 'package' and not args.privacy_reviewed:
            parser.error('Review exact public files and permitted contact details first, then add --privacy-reviewed')
        else:
            args.func(args)
    except (ValueError,FileNotFoundError) as error:
        parser.exit(1,str(error) + '\n')


if __name__ == '__main__':
    main()
