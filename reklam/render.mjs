// Sahne videosu: node render.mjs <html> <süre sn> <çıktı.mp4> [fadein sn] [fadeout sn]
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
const [html, sureS, cikti, fi = '0', fo = '0'] = process.argv.slice(2);
const FPS = 30, N = Math.round(parseFloat(sureS) * FPS);
const gecici = cikti.replace(/\.mp4$/, '.gecici.mp4');
const vf = [];
if (parseFloat(fi) > 0) vf.push(`fade=t=in:st=0:d=${fi}`);
if (parseFloat(fo) > 0) vf.push(`fade=t=out:st=${(parseFloat(sureS) - parseFloat(fo)).toFixed(2)}:d=${fo}`);
vf.push('format=yuv420p');
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-vcodec', 'mjpeg', '-i', '-',
  '-vf', vf.join(','), '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-r', String(FPS), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', gecici], { stdio: ['pipe', 'inherit', 'inherit'] });
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.error('sayfa hatası:', e.message); process.exitCode = 1; });
await page.goto('file://' + path.resolve(html));
await page.waitForFunction('window.hazir === true', null, { timeout: 60000 });
await page.evaluate(async () => { await document.fonts.ready; });
const t0 = Date.now();
for (let i = 0; i < N; i++) {
  await page.evaluate(tt => window.kare(tt), i / FPS);
  const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 30 === 0) console.log(`${html}: kare ${i}/${N} (${((Date.now() - t0) / 1000).toFixed(0)} sn)`);
}
ff.stdin.end();
await new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
await browser.close();
fs.renameSync(gecici, cikti);
console.log('bitti →', cikti, ((Date.now() - t0) / 1000).toFixed(0) + ' sn');
