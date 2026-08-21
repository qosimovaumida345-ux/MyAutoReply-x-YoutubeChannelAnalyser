import os
import subprocess
import asyncio
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. WATERMARK TOZALASH (OpenCV)
# ==========================================
def remove_watermark(input_mp4, output_mp4):
    """
    TikTok/Instagram watermarkini olib tashlash (OpenCV yordamida blur qilish).
    Asosan pastki markaz va ba'zi burchaklardagi logolarni xiralashtiradi.
    """
    try:
        import cv2
        import numpy as np
        print(f"[WATERMARK] Tozalanmoqda: {input_mp4}")
        
        cap = cv2.VideoCapture(input_mp4)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_no_audio = output_mp4 + "_temp.mp4"
        out = cv2.VideoWriter(temp_no_audio, fourcc, fps, (width, height))
        
        # TikTok logosi odatda pastki o'ng va yuqori chapda bo'ladi (yoki aksincha)
        # Biz umumiy pastki qism va burchaklarni blur qilamiz
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Pastki o'ng burchak (TikTok/Reels logolari)
            h_start, h_end = int(height * 0.85), height
            w_start, w_end = int(width * 0.70), width
            
            roi = frame[h_start:h_end, w_start:w_end]
            blurred = cv2.GaussianBlur(roi, (51, 51), 0)
            frame[h_start:h_end, w_start:w_end] = blurred
            
            # Yuqori chap burchak
            h2_start, h2_end = 0, int(height * 0.15)
            w2_start, w2_end = 0, int(width * 0.35)
            
            roi2 = frame[h2_start:h2_end, w2_start:w2_end]
            blurred2 = cv2.GaussianBlur(roi2, (51, 51), 0)
            frame[h2_start:h2_end, w2_start:w2_end] = blurred2
            
            out.write(frame)
            
        cap.release()
        out.release()
        
        # Ovozni qaytarib qo'shish
        os.system(f'ffmpeg -y -i "{temp_no_audio}" -i "{input_mp4}" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 "{output_mp4}" -loglevel quiet')
        
        if os.path.exists(temp_no_audio):
            os.remove(temp_no_audio)
            
        return output_mp4
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
# 3. AUTO-CAPTIONS (Whisper + FFmpeg)
# ==========================================
def generate_srt(input_mp4, srt_path):
    """Whisper orqali SRT subtitr faylini yaratish"""
    try:
        from faster_whisper import WhisperModel
        import os
        model_size = os.getenv("WHISPER_MODEL", "base")
        print(f"[CAPTIONS] Ovoz tahlil qilinmoqda ({model_size})...")
        
        # For auto captions, we can also use the global cache from userbot if we want, but doing it fresh here is fine
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(input_mp4, beam_size=5, word_timestamps=True)
        
        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds - int(seconds)) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
            
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, start=1):
                f.write(f"{i}\n")
                f.write(f"{format_time(segment.start)} --> {format_time(segment.end)}\n")
                f.write(f"{segment.text.strip()}\n\n")
                
        return srt_path
    except Exception as e:
        print(f"SRT yaratish xatosi: {e}")
        return None

def burn_captions(input_mp4, output_mp4):
    """Subtitrlarni videoga yopishtirish"""
    try:
        srt_path = f"{input_mp4}.srt"
        if not generate_srt(input_mp4, srt_path):
            return input_mp4
            
        print(f"[CAPTIONS] Subtitrlar videoga qo'shilmoqda...")
        
        # Windowsda pathlar bilan muammo bo'lmasligi uchun escape qilish
        safe_srt = srt_path.replace('\\', '/')
        
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
    
    clean_watermark = os.getenv("WATERMARK_CLEAN", "false").lower() == "true"
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
