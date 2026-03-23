# RenderIQ Launch Content

## Reddit Posts

### r/VideoEditing (~500K members)

**Title:** I built a free tool that applies cinematic color grading to any video in 30 seconds

**Body:**

Hey r/VideoEditing,

I've been working on a side project called RenderIQ — it's a free web tool that automatically color grades your video footage.

**How it works:**
1. Upload your raw footage (MP4, MOV, etc.)
2. Pick from 10 built-in cinematic presets (or upload a reference video to match its style)
3. Download your graded video or export a .cube LUT file

The LUT export is the part I'm most proud of — you can download the .cube file and drop it straight into DaVinci Resolve, Premiere, or Final Cut. So even if you don't like the web app, you get a professional LUT you can tweak further.

**What's under the hood:** It analyzes color distributions in LAB color space, matches histograms, and generates a 3D LUT. The strength is adjustable from 0-100% so you can dial in exactly how much grade you want.

Try it free at renderiq.in — no signup, no credit card.

I'd love feedback from actual editors. What presets should I add? What's missing?

[Attach: best before/after comparison image]

---

### r/SmallYTChannel (~300K members)

**Title:** Free AI color grading tool for YouTube creators — makes your footage look cinematic

**Body:**

I know color grading is one of those things that can make a huge difference in production quality but takes forever to learn. So I built a tool that does it automatically.

RenderIQ takes your raw footage and applies professional color grading in about 30 seconds. You just pick a style from 10 presets (cinematic warm, teal & orange, vintage film, etc.) and it handles the rest.

No software to install — it runs in your browser at renderiq.in. Free, no signup needed.

It also exports .cube LUT files if you want to use the grade in your existing editing workflow.

Would love to hear if this is useful for your channels. What kind of look are you going for in your videos?

---

### r/Filmmakers (~1M members)

**Title:** Side project: AI-powered LUT generator that extracts color style from any reference video

**Body:**

Built this over the past few weeks — RenderIQ is a tool that analyzes the color grading of a reference video and generates a 3D LUT you can apply to your own footage.

**Technical details for the curious:**
- Extracts keyframes using scene detection
- Analyzes color distributions in CIELAB color space
- Generates a 17x17x17 3D lookup table via histogram matching
- Supports strength control, multi-scene mode, and auto white balance
- Exports standard .cube files compatible with DaVinci Resolve, Premiere, Final Cut

There are also 10 built-in presets if you just want a quick grade without a reference.

The web app is at renderiq.in (free, no signup). Source code is on GitHub if you want to look under the hood.

Interested in feedback from people who actually do color work professionally. How does the output compare to your manual grades?

---

### r/SideProject (~100K members)

**Title:** I built RenderIQ — AI color grading tool in 4 weeks as a solo developer

**Body:**

**What:** RenderIQ is a free web tool that applies cinematic color grading to any video. Upload footage, pick a style, download.

**Why:** 90% of YouTube creators and indie filmmakers shoot great content but their footage looks amateur because they don't know color grading. Professional colorists charge $50-200+ per video.

**How (tech stack):**
- Backend: Python, FastAPI, OpenCV, FFmpeg
- Frontend: React, Vite, Tailwind CSS
- Color science: LAB color space histogram matching, 3D LUT generation
- Deployment: Docker, Nginx

**Timeline:**
- Week 1: Core engine — keyframe extraction, color analysis, LUT generation
- Week 2: Edge cases, 10 presets, performance optimization (76 tests)
- Week 3: Web app — FastAPI backend + React frontend
- Week 4: Deployment, landing page, launch

**Results:** 90+ passing tests, processes a 1-minute video in under 60 seconds, exports industry-standard .cube LUT files.

Try it: renderiq.in
GitHub: [link]

---

### r/webdev or r/reactjs

**Title:** Built a video processing web app with FastAPI + React — architecture breakdown

**Body:**

Sharing the architecture of RenderIQ, a video color grading tool I built:

**Backend (FastAPI/Python):**
- Multipart file upload with streaming (handles up to 500MB)
- Background job processing with ThreadPoolExecutor (max 3 concurrent)
- In-memory job queue with status polling
- Auto-cleanup of expired jobs after 1 hour
- Rate limiting with slowapi
- Video processing: OpenCV + FFmpeg + NumPy

**Frontend (React + Vite + Tailwind CSS 4):**
- XHR uploads for real-time progress (can't do this with fetch)
- 2-second polling interval for job status
- Before/after comparison slider (CSS clip-path, mouse + touch events)
- Dark theme with CSS custom properties

**Deployment:**
- Multi-stage Docker build (frontend: Node build → Nginx, backend: Python + FFmpeg)
- Docker Compose for local dev
- Nginx reverse proxy for API routing

The interesting challenge was the before/after slider component — needed to be 60fps smooth, work with both mouse and touch, and handle the image comparison purely in CSS.

Try the app: renderiq.in

Happy to answer questions about the architecture or any specific decisions.

---

## Twitter/X Launch Thread

**Tweet 1 (hook):**
I built a free tool that makes any video look cinematic in 30 seconds.

No editing skills needed.

Here's how it works:

[Attach: best before/after comparison GIF or image]

**Tweet 2:**
The problem: 90% of YouTube creators shoot great content but their footage looks amateur.

Professional color grading costs $50-200 per video. And learning DaVinci Resolve takes months.

**Tweet 3:**
RenderIQ fixes this.

Upload your video → pick a style → download.

That's it. The AI handles the color science.

[Attach: screenshot of the 3-step UI]

**Tweet 4:**
10 built-in presets:

- Cinematic Warm
- Teal & Orange
- Vintage Film
- Moody Dark
- Golden Hour
- Anime Vibrant
- and 4 more

Or upload any reference video to match its look.

[Attach: preset grid screenshot]

**Tweet 5:**
For the pros: it exports .cube LUT files you can drop into DaVinci Resolve, Premiere, or Final Cut.

So you get a starting point you can refine further.

**Tweet 6:**
Built in 4 weeks as a solo dev.

Stack: Python + FastAPI + React + OpenCV + FFmpeg

The color science uses LAB color space histogram matching to generate 3D LUTs. 90+ automated tests.

**Tweet 7:**
Try it free: renderiq.in

No signup. No credit card.

Star it on GitHub: [link]

Built by @kanishka

---

## YouTube Shorts / Instagram Reels Concepts

### Video 1 — "Raw vs Graded" (15s)
- Split screen: raw footage left, graded right
- Quick cuts between 5 different scene types
- Text overlay: "All graded by AI in seconds"
- End card: "renderiq.in — free"

### Video 2 — "Speed Run" (20s)
- Screen recording of the full flow at 2x speed
- Upload → select preset → processing → done
- Dramatic before/after slider reveal at the end
- Text: "30 seconds. No editing skills."

### Video 3 — "10 Presets" (30s)
- Same raw footage with all 10 presets applied
- 2-second cut for each with preset name overlay
- End: "Which one's your favorite? Try them all free"
- Link: renderiq.in
