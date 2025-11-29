# %%
import random
import numpy as np
import scipy
import matplotlib.pyplot as plt
%config InlineBackend.figure_format = 'retina'
from IPython.display import Audio

def approx(ratio, edo):
    # approximate a freq ratio to 12 edo
    if edo is None:
        return ratio
    semitone = np.log2(ratio) * edo
    semitone = round(semitone)
    return 2 ** (semitone / edo)

print(approx(3/2, None))
print(approx(3/2, 12))
print(approx(3/2, 31))

# %%

base_freq = 261.63 / 4
beat_duration = 0.25
sample_rate = 44100

piano = {}
N = 5
# N = 2
for i in range(1, N):
    piano[i] = 0
for i in range(1, N):
    piano[i] += 0.4 ** i
for i in range(1, N, 2):
    piano[i] += 0.5 ** i
# piano[N - 3] *= 0.3
# piano[N - 2] *= 0.1
# piano[N - 1] *= 2
print(piano)

def render(song, edo=None):
    audio = np.zeros(int(sample_rate * beat_duration * (len(song) + 9)))

    for i, ratio in enumerate(song):
        note_duration = 6 * beat_duration
        t = np.linspace(0, note_duration, int(sample_rate * note_duration), endpoint=False)
        waves = 0 * t

        if ratio == 0:
            continue
        
        ratio = approx(ratio, edo)

        freq = base_freq * ratio
        # freq = base_freq * (1 / ratio)
        # amp0 = 1 / ratio
        amp0 = 1

        for harmonic, amp in piano.items():
            # phase = np.random.uniform(0, 0.25 * np.pi)
            phase = 0
            f = freq * harmonic
            if f > 261 * 80:
                raise ValueError(f"Frequency too high.")
            
            wave = amp0 * amp * np.sin(2 * np.pi * f * t + phase)

            # attack = int(sample_rate / freq * 0.5)
            attack = 500
            decay = int(4 * beat_duration * sample_rate)
            wave[:attack] *= np.linspace(0, 1, attack)
            wave[-decay:] *= np.linspace(1, 0, decay)
            waves += wave
        waves *= 0.16 ** t

        dist = (len(song) - i) / 16
        if dist <= 1:
            waves *= (dist + 0.7) / 2

        start = int(i * sample_rate * beat_duration)
        end = start + len(waves)
        audio[start:end] += waves

    # some reverb
    random.seed(42)
    for i in range(1, len(song)):
        delay = int(i * beat_duration * sample_rate * random.uniform(0.9, 1.1))
        audio[delay:] += 0.025 * audio[:-delay]
    audio[-80000:] *= np.linspace(1, 0, 80000)
    
    return audio


# %%
from fractions import Fraction as F

base_freq = 261.63 / 4
beat_duration = 0.25

song = []

for i in range(1, 16 + 1):
    for j in range(-3, 1):
        if i + j <= 0:
            x = 0
        else:
            x = i + j
        song.append(x)
song = song + song[::-1] + [0] * 16

song_str = []
for i in range(0, len(song) - 16, 4):
    song_str.extend(', '.join(str(song[i + j]) for j in range(4)))
    song_str.append(',\n')
    if (i + 4) % 16 == 0:
        song_str.append('\n')
song_str = ''.join(song_str).strip()
print(song_str)

audio = render(song, edo=None)
Audio(audio, rate=sample_rate)

# %%

titles = '''
Just Intonation
Approximate with 12edo
Left: JI, Right: 12edo
Left: 12edo, Right: JI
Approximate with 41edo
Approximate with 31edo
Approximate with 22edo
Approximate with 19edo
Approximate with 7edo
[]
'''.strip().split('\n')


duration = len(audio) / sample_rate
for i in range(len(titles)):
    d = int(i * duration)
    seconds = d % 60
    minutes = d // 60
    print(f"{minutes:02}:{seconds:02} {titles[i]}")




# %%
import os
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

def find_font():
    search_paths = [
        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'),
        '/Library/Fonts', '/System/Library/Fonts', os.path.expanduser('~/Library/Fonts'),
        '/usr/share/fonts/truetype', '/usr/local/share/fonts/truetype',
        '/usr/share/fonts/opentype', '/usr/local/share/fonts/opentype',
    ]
    target_fonts = [
        'FiraCode', 'Fira Mono', 'SourceCodePro',
        'Menlo', 'Consolas', 'UbuntuMono', 'NotoMono',
        'JetBrainsMono', 'Hack', 'Cascadia', 'DejaVuSansMono', 'RobotoMono',
        'monofur', 'LiberationMono', 'PT Mono', 'Inconsolata'
    ]
    font_files = []
    for path in search_paths:
        if not os.path.isdir(path):
            continue
        for root, _, files in os.walk(path):
            for file in files:
                if not file.lower().endswith(('.ttf', '.otf', '.ttc')):
                    continue
                font_files.append(os.path.join(root, file))
    fontsize = 100
    for font in target_fonts:
        for font_path in font_files:
            if font.lower() in font_path.lower():
                print(f"Using font: {font} at {font_path}")
                return ImageFont.truetype(font_path, fontsize)
    print("No suitable font found, using default font.")
    return ImageFont.load_default(size=fontsize)

font = find_font()

def get_clip(name, audio, song_str):
    print(f"Generating video for {name}...")
    audio = audio / np.max(np.abs(audio)) * 0.5
    sf.write('audio.wav', audio, sample_rate)

    video_width = 1920
    video_height = 1080
    image_size = (video_width, video_height)
    global beat_duration
    print(beat_duration)

    import os
    if not os.path.exists("frames"):
        os.makedirs("frames")

    paragraphs = song_str.strip().split('\n\n')
    durations = []
    image_files = []

    for i, paragraph in enumerate(paragraphs):
        num_notes = paragraph.count(',')
        print(num_notes, paragraph)
        duration = num_notes * beat_duration
        durations.append(duration)

        background_color, text_color = 'black', 'white'

        lines = [line.strip() for line in paragraph.strip().split('\n')]
        text = "\n".join(lines)
        
        img = Image.new('RGB', image_size, color=background_color)
        d = ImageDraw.Draw(img)
        bbox = d.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (video_width - text_width) / 2
        y = (video_height - text_height) / 2
        
        d.text((x, y), text, fill=text_color, font=font, spacing=10)

        # also draw the name at top-left corner
        # tailwind text-gray-500
        gray = (107, 114, 128)
        d.text((20, 0), name, fill=gray, font=font)
        
        image_file = f"frames/{name}_frame_{i:04d}.png"
        img.save(image_file)
        image_files.append(image_file)
        print(f"Generated frame {image_file} for paragraph {i}, duration: {duration:.2f}s")

    durations[0] -= 0.4
    # durations[-1] += 2
    clips = []
    for i, image_file in enumerate(image_files):
        clip = mp.ImageClip(image_file).set_duration(durations[i])
        clips.append(clip)

    clip = mp.concatenate_videoclips(clips, method="compose")
    clip = clip.set_audio(mp.AudioFileClip("audio.wav"))
    return clip

def get_video(name, audio, song_str):
    clip = get_clip(name, audio, song_str)
    clip.write_videofile(
        f"{name}.mp4", fps=60, 
        codec="h264_videotoolbox"  # apple hardware acceleration on macOS
    )
    print(f"Video saved as {name}.mp4")

get_clip("pure", render(song, edo=None), song_str)


# %%
get_video("pure", render(song, edo=None), song_str)
get_video("12edo", render(song, edo=12), song_str)

get_video("L_pure_R_12edo", np.stack([
    render(song, edo=None), render(song, edo=12)
], axis=1), song_str)
get_video("L_12edo_R_pure", np.stack([
    render(song, edo=12), render(song, edo=None)
], axis=1), song_str)

get_video("41edo", render(song, edo=41), song_str)
get_video("31edo", render(song, edo=31), song_str)
get_video("22edo", render(song, edo=22), song_str)
get_video("19edo", render(song, edo=19), song_str)
get_video("7edo", render(song, edo=7), song_str)

# %%
# make a all-in-one version

clip = mp.concatenate_videoclips([
    get_clip("pure", render(song, edo=None), song_str),
    get_clip("12edo", render(song, edo=12), song_str),
    get_clip("L_pure_R_12edo", np.stack([
        render(song, edo=None), render(song, edo=12)
    ], axis=1), song_str),
    get_clip("L_12edo_R_pure", np.stack([
        render(song, edo=12), render(song, edo=None)
    ], axis=1), song_str),
    get_clip("41edo", render(song, edo=41), song_str),
    get_clip("31edo", render(song, edo=31), song_str),
    get_clip("22edo", render(song, edo=22), song_str),
    get_clip("19edo", render(song, edo=19), song_str),
    get_clip("7edo", render(song, edo=7), song_str),
], method="compose")
# save
clip.write_videofile("all_in_one.mp4", fps=60, codec="h264_videotoolbox")


