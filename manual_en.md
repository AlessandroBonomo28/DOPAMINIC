# DOPAMINIC manual (EN)

Program knowledge used by the assistant. Each `##` section is a self-contained
answer; the "Keywords:" line helps the assistant find it.

## What the program does
Keywords: what does it do, purpose, program, intro, overview, how it works
I turn a long video into several vertical (9:16) shorts, fully locally on your PC.
I analyze the audio to find the loudest moments (the highlights), cut the clips,
make them vertical, and can add a watermark and subtitles. Finished shorts go to the
output folder. There's also a YouTube tab to schedule their publishing.

## How to generate shorts
Keywords: generate, create, how to, start, produce, make, steps, short, split, cut
1) Genera tab, press "Browse" and pick the long video.
2) Set the number of shorts and the duration.
3) (Optional) enable watermark, subtitles, face-tracking.
4) Press "GENERATE SHORTS" and wait: progress shows in the log at the bottom.
Finished shorts go to the output folder ("Open output folder" button).

## Number of shorts and duration
Keywords: number, how many, duration, seconds, length, clip
"Number of shorts" = how many clips to extract. "Duration" = length of each in seconds.
If the video is too short for your values, I adapt them automatically. If I find fewer
distinct moments than requested, I generate the available ones and tell you in the log.

## Face-tracking OpenCV
Keywords: face tracking, faces, opencv, face, framing, crop
If enabled, the vertical crop follows the most centered face instead of cropping center.
It's slower and needs the OpenCV library (I offer to download it on first use). If your
video has no faces (gameplay, screens), leave it OFF: much faster, nearly identical result.

## Watermark
Keywords: watermark, logo, signature, overlay text, brand
Adds a semi-transparent text at the bottom of the video. Enable the "Watermark" checkbox
and type your text (e.g. your @name). It can be turned off.

## Subtitles
Keywords: subtitles, subtitle, whisper, transcription, captions, language, text
Subtitles are generated locally with Whisper. Enable "Subtitles (local Whisper)". On first
use I offer to download the library. You can choose the LANGUAGE (use "it"/"en" so it
doesn't pick the wrong one) and the MODEL (bigger = more accurate but slower/heavier).
Subtitles are synced word by word.

## Whisper model and sizes
Keywords: model, whisper, tiny, base, small, medium, large, size, weight
Available models: tiny (~75 MB), base (~145 MB), small (~480 MB), medium (~1.5 GB),
large-v3 (~3 GB). Bigger = more accurate but slower and heavier. The model downloads on
first use.

## NVIDIA GPU for subtitles
Keywords: gpu, nvidia, cuda, graphics card, vram, acceleration, fast
If you have an NVIDIA GPU you can enable "Use GPU": transcription is much faster,
especially with big models. On first use I download the CUDA libraries (~1 GB). If you
have no NVIDIA or something is missing, I automatically use the CPU. The line under the
checkbox tells you how much VRAM you have and which model I recommend.

## Subtitle style (font, size, outline)
Keywords: font, style, color, size, outline, look, typeface, preview
The "Style..." button opens an editor with a live preview: pick the font (PT Sans, Anton,
Bebas Neue, Poppins, Bangers), size, black outline thickness and text color. You see how
it will look as you change the values.

## Output folder
Keywords: output, where do they go, files, folder, saved, result, find
Generated shorts go to the output folder. From the Genera tab press "Open output folder".
When installed, output and settings live in a writable folder in your home directory.

## YouTube tab: overview
Keywords: youtube, upload, publish, channel, schedule
In the YouTube tab you connect your channel, define weekly slots, auto-assign the videos
from the output folder to the slots, and upload them scheduled. It works like the
scheduling of Buffer/YouTube Studio.

## Connect the YouTube channel (OAuth)
Keywords: account, oauth, client secret, connect, access, authorization, google
Press "Set up access..." and pick your client_secret.json file (you create it in the
Google Cloud Console, enabling "YouTube Data API v3" and creating OAuth credentials of
type "Desktop app"). The browser opens, you sign in with the channel and grant access:
you do it once.

## Weekly slots and auto-assign
Keywords: slot, calendar, schedule, weekly, auto assign, planning
Define the slots (day + time) when you want to publish. Press "Auto-assign" and I assign
each video from the output folder to the next free slot, showing you the schedule. Then
"Upload and schedule" uploads them as private with an automatic publish time.

## Scheduled upload: how it works
Keywords: scheduled, private, public, publishat, publishing, when does it go live
Videos are uploaded right away but as PRIVATE, with a publish time: YouTube makes them
public by itself at the slot time. You don't lose the algorithm "boost", because it starts
when the video goes public. There's a limit of ~6 uploads per day (YouTube quota): the
rest you upload another day.

## The second video freezes / is very slow
Keywords: freeze, stuck, slow, loop, never finishes, frozen, error
If generation seems stuck: with subtitles on GPU the model is now loaded once (it used to
hang on the second short). With face-tracking ON on videos without faces it was very slow:
now fixed. If it's just slow, try a smaller Whisper model, turn off face-tracking, or use
the GPU.

## Errors and crashes at startup
Keywords: error, crash, won't start, doesn't open, problem, log
If the app won't start, check crash.log (in the program folder or in your home, under
DOPAMINIC). It has the error detail. Heavy features (OpenCV, Whisper, GPU, YouTube)
download on first use: you need internet that first time.
