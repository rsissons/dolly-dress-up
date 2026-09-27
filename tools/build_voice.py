"""Record Dolly's spoken lines in a child voice and bake them into the page.

Usage:  python tools/build_voice.py      (needs: pip install edge-tts ; ffmpeg on PATH)
Every line the game says is in the LINES list in dolly-dress-up.html. Add a line there, run this,
and it records only the new clips (cached in voice/), then rewrites dolly-dress-up.html and index.html.
Voice: Microsoft's en-US-AnaNeural child voice, the same one Unicorn Stable uses.
"""
import base64, hashlib, json, os, re, shutil, subprocess, tempfile
import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'dolly-dress-up.html')
VDIR = os.path.join(ROOT, 'voice')
VOICE = 'en-US-AnaNeural'
AFILTER = ('silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
           'silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-16:TP=-1.5:LRA=11')


def clip(text):
    return os.path.join(VDIR, hashlib.sha1(f'{VOICE}|{text}'.encode()).hexdigest()[:12] + '.mp3')


def main():
    os.makedirs(VDIR, exist_ok=True)
    src = open(PAGE, encoding='utf-8').read()
    lines = json.loads(re.search(r'/\*LINES-START\*/(.*?)/\*LINES-END\*/', src, re.S).group(1))
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, 'raw.mp3')
        for t in lines:
            if not os.path.exists(clip(t)):
                edge_tts.Communicate(t, VOICE).save_sync(raw)
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', AFILTER,
                                '-ac', '1', '-ar', '24000', '-b:a', '48k', clip(t)], check=True)
                print('recorded:', t)
    keep = {os.path.basename(clip(t)) for t in lines}
    for f in os.listdir(VDIR):
        if f not in keep:
            os.remove(os.path.join(VDIR, f))
    vox = {t: base64.b64encode(open(clip(t), 'rb').read()).decode() for t in lines}
    src = re.sub(r'/\*VOX-START\*/.*?/\*VOX-END\*/',
                 lambda _: '/*VOX-START*/' + json.dumps(vox, separators=(',', ':')) + '/*VOX-END*/', src, flags=re.S)
    open(PAGE, 'w', encoding='utf-8', newline='').write(src)
    shutil.copyfile(PAGE, os.path.join(ROOT, 'index.html'))
    print(f'{len(lines)} clips, page {len(src) / 1e6:.2f} MB')


if __name__ == '__main__':
    main()
