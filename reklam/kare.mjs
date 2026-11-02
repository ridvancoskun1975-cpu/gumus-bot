// Tek kare: node kare.mjs <html> <t> <çıktı.png|jpg>  (deneme ve önizleme için)
import { chromium } from 'playwright';
import path from 'node:path';
const [html, t, cikti] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('sayfa hatası:', e.message));
page.on('console', m => { if (m.type() === 'error') console.error('konsol:', m.text()); });
await page.goto('file://' + path.resolve(html));
await page.waitForFunction('window.hazir === true', null, { timeout: 60000 });
await page.evaluate(async () => { await document.fonts.ready; });
const t0 = Date.now();
await page.evaluate(tt => window.kare(tt), parseFloat(t));
await page.screenshot({ path: cikti, type: cikti.endsWith('.jpg') ? 'jpeg' : 'png', quality: cikti.endsWith('.jpg') ? 92 : undefined });
console.log('kare', t, 'sn →', cikti, (Date.now() - t0) + ' ms');
await browser.close();
