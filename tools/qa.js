() => {
  const poster = document.querySelector('.poster');
  if (!poster) throw new Error('Missing .poster');
  const box = poster.getBoundingClientRect();
  const errors = [], warnings = [];
  const describe = e => e.id || e.className || e.tagName;
  for (const e of poster.querySelectorAll('*')) {
    const r = e.getBoundingClientRect(), c = getComputedStyle(e);
    if (!r.width || !r.height || c.display === 'none') continue;
    if (r.left < box.left - 2 || r.top < box.top - 2 || r.right > box.right + 2 || r.bottom > box.bottom + 2)
      errors.push('Outside canvas: ' + describe(e));
    if (e.matches('.card,header,footer,.metric,.track,.byline,.presenter') &&
        (e.scrollWidth > e.clientWidth + 2 || e.scrollHeight > e.clientHeight + 2))
      errors.push('Content overflows its region: ' + describe(e));
    if (e.matches('p,li,.caption') && parseFloat(c.fontSize) < 18)
      warnings.push('Small print text (< approximately 13.5 pt): ' + describe(e));
  }
  const images = [...poster.querySelectorAll('img')].map(e => {
    const r = e.getBoundingClientRect();
    if (!e.complete || !e.naturalWidth) errors.push('Broken image: ' + e.getAttribute('src'));
    const vector = e.src.startsWith('data:image/svg') || /\.svg(?:$|[?#])/.test(e.src);
    const dpi = vector ? null : Math.round(e.naturalWidth / (r.width / 96));
    if (dpi && dpi < 150) warnings.push('Raster source <150 effective DPI: ' + e.getAttribute('src'));
    return {src: e.getAttribute('src'), dpi, x:r.x, y:r.y, width:r.width, height:r.height,
      qr: !!e.closest('.qr-block'), expected:e.closest('a')?.getAttribute('href') || null};
  });
  return {errors:[...new Set(errors)], warnings:[...new Set(warnings)], images,
    canvas_px:{width:box.width,height:box.height},
    content_audit:'NOT_RUN: verify claims and author metadata against the paper manually'};
}
