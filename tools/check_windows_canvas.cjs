// Run after registering the fixed family on a disposable Windows runner.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert');
(async () => {
  const root = process.argv[2] || 'dist/windows-check';
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const results = [];
    for (const style of JSON.parse(fs.readFileSync(path.join(root, 'styles.json')))) {
      const bytes = fs.readFileSync(path.join(root, 'fixed', style.file)).toString('base64');
      const result = await page.evaluate(async ({bytes, style}) => {
        const face = new FontFace('CompactReference', Uint8Array.from(atob(bytes), c => c.charCodeAt(0)),
          {weight: String(style.weight), style: style.style});
        document.fonts.add(await face.load());
        const render = family => {
          const canvas = document.createElement('canvas');
          canvas.width = 1100; canvas.height = 100;
          const ctx = canvas.getContext('2d');
          ctx.font = `${style.style} ${style.weight} 28px ${family}`;
          ctx.fillText('Maple 012345 != -> {Bold/Italic} 中文测试', 20, 55);
          return canvas.toDataURL();
        };
        const ref = render('CompactReference');
        return {file: style.file, weight: style.weight, style: style.style,
          matchesReference: render('"Maple Compact Mono NF CN", monospace') === ref,
          differsFromFallback: render('monospace') !== ref};
      }, {bytes, style});
      console.log(JSON.stringify(result));
      results.push(result);
    }
    fs.writeFileSync(path.join(root, 'chromium-results.json'), JSON.stringify({browser: browser.version(), results}, null, 2));
    assert(results.length === 16 && results.every(r => r.matchesReference && r.differsFromFallback),
      'Chromium did not select each installed Compact weight/style by the requested family name');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
