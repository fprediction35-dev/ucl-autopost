// Renders one simulated match to a 1080x1920 MP4 (H.264 + AAC), frame by frame, independent of machine speed.
// Usage: node render.js --home "Galatasaray" --away "Stuttgart" --out out/gs-vfb.mp4 [--dur 60] [--fps 30] [--music hype] [--handle @channel] [--meta setup.json with {meta, lang}]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? a.concat([[v.slice(2), arr[i + 1]]]) : a), []));
const fps = +(args.fps || 30), dur = +(args.dur || 60);
const out = args.out || 'out/match.mp4';
fs.mkdirSync(path.dirname(out), { recursive: true });

(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1300, height: 1000 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto('file://' + path.resolve(__dirname, 'sim/index.html'));
  await page.waitForFunction(() => window.AUTO, null, { timeout: 15000 });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  const info = await page.evaluate(o => window.AUTO.setup(o), { home: args.home, away: args.away, dur, music: args.music || 'hype', handle: args.handle || '', goals: +(args.goals || 2), ...(args.meta ? JSON.parse(fs.readFileSync(args.meta, 'utf8')) : {}) });

  const tmpVideo = out.replace(/\.mp4$/, '.video.mp4'), tmpWav = out.replace(/\.mp4$/, '.wav');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-profile:v', 'high', '-level', '4.0', '-g', '60', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-r', String(fps), tmpVideo], { stdio: ['pipe', 'inherit', 'inherit'] });
  let frames = 0, res;
  const maxFrames = Math.ceil((dur * 1.7 + 25) * fps);
  do {
    res = await page.evaluate(dt => { const r = window.AUTO.frame(dt); r.img = document.getElementById('cv').toDataURL('image/jpeg', 0.9); return r; }, 1 / fps);
    const buf = Buffer.from(res.img.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    frames++;
  } while (!res.done && frames < maxFrames);
  ff.stdin.end();
  await new Promise((ok, bad) => ff.on('close', c => (c === 0 ? ok() : bad(new Error('ffmpeg video failed ' + c)))));

  const wav = await page.evaluate(() => window.AUTO.audio());
  fs.writeFileSync(tmpWav, Buffer.from(wav, 'base64'));
  await browser.close();

  await new Promise((ok, bad) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-i', tmpVideo, '-i', tmpWav, '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', out], { stdio: 'inherit' })
    .on('close', c => (c === 0 ? ok() : bad(new Error('ffmpeg mux failed ' + c)))));
  fs.unlinkSync(tmpVideo); fs.unlinkSync(tmpWav);
  info.final = res.score; info.seconds = frames / fps; info.file = out;
  fs.writeFileSync(out.replace(/\.mp4$/, '.json'), JSON.stringify(info, null, 2));
  console.log(JSON.stringify(info));
})().catch(e => { console.error(e); process.exit(1); });
