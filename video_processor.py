import os
import subprocess
import asyncio
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. WATERMARK ANIQLASH VA TOZALASH (OpenCV + FFmpeg delogo)
# ==========================================
def detect_watermark_regions(input_mp4: str, max_samples: int = 8) -> list[tuple[int, int, int, int]]:
    """
    Videodagi statik yoki yarim-shaffof watermark (logo, username, TikTok/Reels belgilari)
    hududlarini avtomatik aniqlash.
    4 ta burchak va pastki/yuqori markaz zonalarida kadrlar bo'ylab o'zgarmas edge (Sobel)
    klasterlarini topib, (x, y, w, h) koordinatalarini qaytaradi.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return []

    cap = cv2.VideoCapture(input_mp4)
    if not cap.isOpened():
        return []

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if width < 64 or height < 64:
            return []

        if total_frames > max_samples:
            indices = [int(i * (total_frames - 1) / max(1, max_samples - 1)) for i in range(max_samples)]
        else:
            indices = list(range(max(1, total_frames)))

        edge_accum = np.zeros((height, width), dtype=np.float32)
        sampled = 0
        for idx in indices:
            if total_frames > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            mag = cv2.magnitude(gx, gy)
            edge_accum += (mag > 42.0).astype(np.float32)
            sampled += 1

        if sampled < 2:
            return []

        persistence = edge_accum / float(sampled)
        mask = (persistence >= 0.70).astype(np.uint8) * 255

        # Common watermark zones: 4 corners + bottom-center + top-center ticker
        cw, ch = int(width * 0.28), int(height * 0.20)
        zones = [
            (0, 0, cw, ch),                                  # top-left
            (width - cw, 0, width, ch),                      # top-right
            (0, height - ch, cw, height),                    # bottom-left
            (width - cw, height - ch, width, height),        # bottom-right
            (int(width * 0.25), int(height * 0.80), int(width * 0.75), height),  # bottom-center
            (int(width * 0.25), 0, int(width * 0.75), int(height * 0.14)),       # top-center
        ]

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 7))
        boxes: list[tuple[int, int, int, int]] = []
        for x1, y1, x2, y2 in zones:
            roi = mask[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            closed = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                area = bw * bh
                if bw < 14 or bh < 10 or area < 220:
                    continue
                if bw > int(width * 0.45) and bh > int(height * 0.30):
                    continue
                gx1 = max(2, x1 + bx - 6)
                gy1 = max(2, y1 + by - 6)
                gw = min(width - gx1 - 2, bw + 12)
                gh = min(height - gy1 - 2, bh + 12)
                if gw >= 12 and gh >= 10:
                    boxes.append((gx1, gy1, gw, gh))
        return boxes[:6]
    except Exception:
        return []
    finally:
        cap.release()


def _get_video_dimensions(input_mp4: str) -> tuple[int, int]:
    try:
        import cv2
        cap = cv2.VideoCapture(input_mp4)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return 0, 0


def remove_watermark(input_mp4, output_mp4):
    """
    Videodagi watermarkni avtomatik aniqlash va FFmpeg delogo + chet qirqish orqali tozalash.
    Ovozni asl sifatida (-c:a copy) saqlaydi.
    """
    try:
        print(f"[WATERMARK] Avtomatik tekshirilmoqda va tozalanmoqda: {input_mp4}")
        boxes = detect_watermark_regions(input_mp4)
        vf_parts = []
        if boxes:
            for (x, y, w, h) in boxes:
                vf_parts.append(f"delogo=x={x}:y={y}:w={w}:h={h}:show=0")
            print(f"[WATERMARK] {len(boxes)} ta watermark hududi aniqlandi: {boxes}")
        else:
            # Fallback for floating/corner watermarks when static edge box isn't found
            w, h = _get_video_dimensions(input_mp4)
            if w >= 120 and h >= 120:
                vf_parts.append("crop=iw*0.94:ih*0.94:iw*0.03:ih*0.03,scale=trunc(iw/2)*2:trunc(ih/2)*2")
            else:
                return input_mp4

        vf_str = ",".join(vf_parts)
        cmd = [
            "ffmpeg", "-y", "-i", input_mp4,
            "-vf", vf_str,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "copy", "-movflags", "+faststart",
            output_mp4,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
        if res.returncode == 0 and os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1024:
            return output_mp4
        return input_mp4
    except Exception as e:
        print(f"Watermark tozalash xatosi: {e}")
        return input_mp4


# ==========================================
# 2. DINAMIK INTRO/OUTRO (Pillow + FFmpeg)
# ==========================================
def create_branding_card(channel_title, channel_pfp, output_image_path, text="Obuna bo'ling!"):
    """Kanal rasmi va nomi bilan rasm (kadr) yaratadi"""
    try:
        # 1080x1920 (Shorts formati) rasm yaratish
        img = Image.new('RGB', (1080, 1920), color=(15, 15, 25))
        draw = ImageDraw.Draw(img)
        
        # PFP ni o'qish va aylana qilish
        if channel_pfp and os.path.exists(channel_pfp):
            pfp = Image.open(channel_pfp).convert("RGBA")
            pfp = pfp.resize((400, 400))
            
            # Mask (aylana)
            mask = Image.new('L', (400, 400), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 400, 400), fill=255)
            pfp.putalpha(mask)
            
            # Markazga joylashtirish
            img.paste(pfp, (340, 600), pfp)
        
        # Matn qo'shish (Agar font topilmasa default ishlatiladi)
        try:
            font_title = ImageFont.truetype("arial.ttf", 60)
            font_sub = ImageFont.truetype("arial.ttf", 40)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            
        draw.text((540, 1100), channel_title, font=font_title, fill=(255, 255, 255), anchor="mm")
        draw.text((540, 1200), text, font=font_sub, fill=(200, 200, 200), anchor="mm")
        
        img.save(output_image_path)
        return output_image_path
    except Exception as e:
        print(f"Branding card yaratish xatosi: {e}")
        return None

def add_intro_outro(input_mp4, output_mp4, channel_title, channel_pfp):
    """Videoga Intro va Outro qo'shish"""
    try:
        print(f"[BRANDING] Intro/Outro qo'shilmoqda: {input_mp4}")
        intro_img = f"{input_mp4}_intro.png"
        outro_img = f"{input_mp4}_outro.png"
        
        create_branding_card(channel_title, channel_pfp, intro_img, "Taqdim etadi")
        create_branding_card(channel_title, channel_pfp, outro_img, "Obuna bo'ling!")
        
        intro_vid = f"{input_mp4}_intro.mp4"
        outro_vid = f"{input_mp4}_outro.mp4"
        
        # Rasmlarni 2 soniyalik videoga aylantirish
        os.system(f'ffmpeg -y -loop 1 -i "{intro_img}" -c:v libx264 -t 2 -pix_fmt yuv420p -vf scale=1080:1920 "{intro_vid}" -loglevel quiet')
        os.system(f'ffmpeg -y -loop 1 -i "{outro_img}" -c:v libx264 -t 3 -pix_fmt yuv420p -vf scale=1080:1920 "{outro_vid}" -loglevel quiet')
        
        # Asosiy videoni scale qilish (1080x1920) ga to'g'rilash
        scaled_main = f"{input_mp4}_scaled.mp4"
        os.system(f'ffmpeg -y -i "{input_mp4}" -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -preset veryfast -c:a aac "{scaled_main}" -loglevel quiet')
        
        # Birlashtirish
        list_txt = f"{input_mp4}_list.txt"
        with open(list_txt, "w") as f:
            f.write(f"file '{os.path.abspath(intro_vid)}'\n")
            f.write(f"file '{os.path.abspath(scaled_main)}'\n")
            f.write(f"file '{os.path.abspath(outro_vid)}'\n")
            
        os.system(f'ffmpeg -y -f concat -safe 0 -i "{list_txt}" -c copy "{output_mp4}" -loglevel quiet')
        
        # Vaqtinchalik fayllarni tozalash
        for tmp_file in [intro_img, outro_img, intro_vid, outro_vid, scaled_main, list_txt]:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
                
        return output_mp4
    except Exception as e:
        print(f"Intro/Outro qo'shish xatosi: {e}")
        return input_mp4


# ==========================================
# 3. AUTO-CAPTIONS (Gemini STT + FFmpeg)
# ==========================================
def generate_srt(input_mp4, srt_path):
    """Gemini Flash orqali SRT subtitr faylini yaratish"""
    try:
        import google.generativeai as genai
        from config import get_gemini_key
        genai.configure(api_key=get_gemini_key())
        
        print(f"[CAPTIONS] Gemini orqali ovoz tahlil qilinmoqda...")
        
        audio_file = genai.upload_file(input_mp4)
        models_to_try = ['gemini-flash-latest', 'gemini-3.8-flash', 'gemini-flash-lite-latest']
        result = None
        for m_name in models_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                result = model.generate_content([
                    audio_file,
                    "Transcribe this video/audio into SRT subtitle format. "
                    "Return ONLY valid SRT content with numbered entries, timestamps in HH:MM:SS,mmm format, "
                    "and the transcribed text. Keep segments 3-6 seconds each. "
                    "Do not add any extra text or markdown formatting."
                ])
                if result and result.text:
                    break
            except Exception as me:
                print(f"[CAPTIONS] {m_name} xatosi: {me}. Keyingi model...")
                continue
        
        srt_content = result.text.strip()
        # Remove markdown code block if present
        if srt_content.startswith("```"):
            srt_content = srt_content.split("\n", 1)[1]
            if srt_content.endswith("```"):
                srt_content = srt_content[:-3].strip()
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
            
        return srt_path
    except Exception as e:
        print(f"SRT yaratish xatosi (Gemini): {e}")
        return None

def burn_captions(input_mp4, output_mp4):
    """Subtitrlarni videoga yopishtirish"""
    try:
        srt_path = f"{input_mp4}.srt"
        if not generate_srt(input_mp4, srt_path):
            return input_mp4
            
        print(f"[CAPTIONS] Subtitrlar videoga qo'shilmoqda...")
        
        # Windowsda pathlar bilan muammo bo'lmasligi uchun escape qilish
        safe_srt = srt_path.replace('\\', '/').replace(':', '\\:')
        
        # FFmpeg subtitr filtri (chiroyli stil bilan)
        style = "FontName=Arial,FontSize=24,PrimaryColour=&H00FFFF,OutlineColour=&H000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=100,Alignment=2"
        os.system(f'ffmpeg -y -i "{input_mp4}" -vf "subtitles=\'{safe_srt}\':force_style=\'{style}\'" -c:v libx264 -preset veryfast -c:a copy "{output_mp4}" -loglevel quiet')
        
        if os.path.exists(srt_path):
            os.remove(srt_path)
            
        return output_mp4
    except Exception as e:
        print(f"Subtitr qo'shish xatosi: {e}")
        return input_mp4


# ==========================================
# ASOSIY PROCESSOR FUNKSIYASI
# ==========================================
def process_video_advanced(input_mp4, channel_title="", channel_pfp=""):
    """
    Barcha .env sozlamalariga qarab videoni to'liq ishlaydi:
    1. WATERMARK_CLEAN
    2. AUTO_CAPTIONS
    3. BRANDING (apply_watermark o'rniga)
    """
    import os
    final_output = input_mp4
    
    clean_watermark = os.getenv("WATERMARK_CLEAN", "true").lower() != "false"
    add_captions = os.getenv("AUTO_CAPTIONS", "false").lower() == "true"
    
    # 1. Watermark tozalash
    if clean_watermark:
        tmp_clean = f"{input_mp4}_clean.mp4"
        processed = remove_watermark(final_output, tmp_clean)
        if processed != final_output:
            if final_output != input_mp4:
                try: os.remove(final_output)
                except: pass
            final_output = processed
        
    # 2. Auto-Captions
    if add_captions:
        tmp_cap = f"{input_mp4}_cap.mp4"
        burned = burn_captions(final_output, tmp_cap)
        if burned != final_output:
            if final_output != input_mp4:
                try: os.remove(final_output)
                except: pass
            final_output = burned
        
    # 3. Branding (Intro/Outro)
    if channel_title:
        tmp_brand = f"{input_mp4}_brand.mp4"
        branded = add_intro_outro(final_output, tmp_brand, channel_title, channel_pfp)
        if branded != final_output:
            if final_output != input_mp4:
                try: os.remove(final_output)
                except: pass
            final_output = branded
        
    return final_output


# ==========================================
# 4. REACTION VIDEO (PiP)
# ==========================================
def create_reaction_video(main_video_path, reactor_video_path, output_path, reactor_size=0.3):
    """
    Combine two videos: main video fills the screen,
    reactor video appears as picture-in-picture in bottom-right corner.
    
    Uses FFmpeg overlay filter:
    ffmpeg -i main_video.mp4 -i reactor_video.mp4 \
           -filter_complex "[1:v]scale=iw*0.3:-1[reactor]; \
                            [0:v][reactor]overlay=W-w-20:H-h-20" \
           -c:v libx264 -preset veryfast -crf 23 \
           -c:a copy output.mp4
    
    - reactor_size: 0.3 means reactor is 30% of main video width
    - Position: bottom-right corner with 20px padding
    - Audio: keep main video audio only
    """
    import subprocess
    print(f"[REACTION] Asosiy: {main_video_path}, Reaktor: {reactor_video_path}")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", main_video_path,
        "-i", reactor_video_path,
        "-filter_complex", f"[1:v]scale=iw*{reactor_size}:-1[reactor]; [0:v][reactor]overlay=W-w-20:H-h-20",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "copy",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Reaction video yaratishda xato: {e}")
        return None
