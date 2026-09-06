# YouTube Bot Marketplace & Xavfsizlik Arxitekturasi (Spetsifikatsiya)

Ushbu hujjat foydalanuvchi tomonidan tasdiqlangan barcha Marketplace mahsulotlari, narxlari va xavfsizlik (KYC) qoidalarini o'z ichiga oladi.

---

## 1. 🔒 Qat'iy 3D Biometrik & Telegram Raqam Gate (/start xavfsizligi)
* **Qoida:** Agar foydalanuvchi bazada `is_user_kyc_verified` bo'lmasa, unga **ASOSIY MENYU VA BOSHQA TUGMALAR KO'RSATILMAYDI**.
* **Telefon raqamni ulashish:**
  * Telefon raqamni qo'lda yozish taqiqlanadi (aldov va soxta ma'lumotlarning oldini olish uchun).
  * Faqat Telegram `request_contact=True` orqali o'z akkauntiga ulangan real raqamni yuborishi shart (`contact.user_id == message.from_user.id`).
* **3D Yuz Skaneri (MediaPipe 468 mesh):**
  * Raqam yuborilgach, WebApp ochiladi.
  * WebApp ichida telefon raqam qulflanadi (o'zgartirib bo'lmaydi).
  * Foydalanuvchi kameraga qarab, boshini to'g'riga (1/3), chapga (2/3) va o'ngga (3/3) burib liveness testdan o'tadi.
* **Muvaffaqiyat:**
  * Bazada `status = 'verified'` saqlanadi va bot avtomatik ravishda Asosiy menyu tugmalarini to'liq ochadi.

---

## 2. 🛒 Marketplace Mahsulotlari va Aniq Qoidalari

### 1) 🌐 Private Proxy (Dedicated IP) — $3 (38,000 so'm)
* **Miqdori:** 1 ta xarid = 1 dona toza proxy.
* **Qoidasi:** Proxy **FAQAT va FAQAT video yuklab olish (download) jarayonida** ishlatiladi. Download tugagach, oddiy bot va API so'rovlarida proxy ishlatilmaydi.
* **Bog'lanish:** Sotib olingan proxy faqat o'sha xaridorga biriktiriladi (`set_user_proxy`).

### 2) ⚡ 24/7 Autostream Cloud Slot (Soatbay to'lov) — $0.5 / soat (6,000 so'm / soat)
* **To'lov modeli:** Doimiy obuna emas, soatiga $0.5.
* **Avto-o'chish:** Foydalanuvchi qancha soat uchun to'lasa (masalan 2 soat, 10 soat), to'langan vaqt tugashi bilan jonli efir **avtomatik to'xtaydi (auto o'chadi)**.

### 3) 🎨 500+ Virusli Prompt & SEO Taglar To'plami — $3 (38,000 so'm)
* Clickbait sarlavhalar, viral Shorts tavsiflari va eng yuqori reytingli SEO teglari to'plami.
* Xariddan so'ng darhol ochiladi va foydalanuvchi profilida saqlanadi.

### 4) 👑 VIP Cheksiz Pro Obuna — $15 / oy (192,000 so'm)
* Kunlik cheklovlar to'liq bekor qilinadi (cheksiz avtopost, cheksiz tahlillar).
* Prioritetli navbat va eng yuqori server tezligi.

### 5) 🤖 OpenRouter API Kalit — $3 (38,000 so'm)
* Rasmiy hisobda $3 balans bilan. 100+ AI modellarini ishlatish uchun.
* Nusxalanuvchi kod bloki va profilida saqlanadi.

### 6) ✨ Google Gemini API Kalit — $5 (64,000 so'm)
* Rasmiy Google AI kaliti ($5 balans).
* Nusxalanuvchi kod bloki va profilida saqlanadi.

### 7) 💎 Referal & Keshbek Tizimi
* Har bir foydalanuvchining shaxsiy taklif havolasi bo'ladi.
* Taklif qilingan do'stining har bir to'lovidan 10% taklif qiluvchining balansiga tushadi.

### 8) ⚡ Video Unikalizatsiya & Content ID Tozalash — 1,500 so'm / video
* Metadata tozalash, 1% tezlik o'zgartirish, ovoz pitchini siljitish va rang filtri (LUT).
* **OGOHLANTIRISH (Warning):**
  * `⚠️ DIQQAT: YouTube Content ID va mualliflik huquqi algoritmlari doimiy yangilanib turadi. Ushbu xizmat videoni unikalizatsiya qilish ehtimolini oshiradi, biroq 100% kafolat bermaydi. Qaytarib berilmaydi (NO REFUNDS)!`

### 9) ✂️ Uzun Videodan Avtomatik 3 ta Shorts Kesish — $1 (12,800 so'm) / video
* Uzun YouTube videodan (podkast, darslik, intervyu) eng qiziqarli 3 ta 9:16 vertikal Shorts kesib berish.
* **OGOHLANTIRISH (Warning):**
  * `⚠️ DIQQAT: AI algoritmlari videoning eng faol joylarini avtomatik tahlil qilib kesadi. Kadrlash, markazlashtirish yoki video sifati ba'zi videolarda kutilgandek chiqmasligi mumkin. Qaytarib berilmaydi (NO REFUNDS)!`

### 10) 🎨 Flux.1 AI Rasm Generatsiya Obunasi — $2 / hafta (25,000 so'm / hafta)
* **Limit:** Haftasiga 25 marta fotorealistik rasm va YouTube muqova (thumbnail) generatsiya qilish imkoniyati.
* **Xususiyati:** 7 kunlik faol obuna. Botda `/flux <tavsif>` yoki menyu orqali eng yuqori sifatli (Flux.1 / Midjourney darajasida) rasm yasash.

### 11) 🔗 YouTube Deep Link & Smart QR Kod — 3,000 so'm
* Instagram bio, TikTok yoki reklama uchun maxsus aqlli havola.
* Foydalanuvchi bosganda brauzerda emas, to'g'ridan-to'g'ri YouTube mobil ilovasida ochiladi va obunachi bo'lish konversiyasini keskin oshiradi. Stilistik QR kod birga beriladi.

### 12) ⚡ Groq Cloud API Kalit (LPU — 500 token/s, gptoss 120b / Llama 3.3) — 10,000 so'm ($0.8)
* Dunyodagi eng tezkor AI xizmati. Dasturchilar va AI ishqibozlari uchun tayyor kalit.
* Biz uchun $0 xarajat, 100% sof foyda.

### 13) 🚀 Orqa Fondagi Bepul Dvigatellar (Bizga $0 xarajat):
* **Cobalt API (api.cobalt.tools):** Hech qanday API kalit talab qilmaydi, videolarni 4K/1080p sifatda tekinga tortadi.
* **Jina AI Reader (r.jina.ai):** Hech qanday API kalit talab qilmaydi, veb sahifalarni LLM uchun tozalaydi.
* **Cloudflare Workers AI:** Kuniga 10,000 ta bepul so'rov imkoniyati.

---

## 3. ❌ Bekor qilingan / Qo'shilmaydigan Bo'limlar
* Raqobatchi josuslik tahlili (kerak emas).
* NoCopyright musiqa to'plami (mualliflik huquqi xavfi va scam bo'lib qolmasligi uchun bekor qilindi).
* YouTube eski akkauntlar sotuvi (100+ obunachili toza akkauntlar yo'qligi sababli qo'shilmaydi).
