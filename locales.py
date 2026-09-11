"""
Multi-Language (i18n) Engine for YouTube Analytics & Monetization Bot
Qo'llab-quvvatlanadigan tillar:
- uz: O'zbekcha 🇺🇿
- ru: Русский 🇷🇺
- en: English 🇬🇧
- es: Español 🇪🇸
- tr: Türkçe 🇹🇷
"""

SUPPORTED_LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "tr": "🇹🇷 Türkçe"
}

TRANSLATIONS = {
    "select_lang": {
        "uz": "🌍 <b>Iltimos, tilni tanlang:</b>\n\nQuyidagi tugmalardan birini bosing:",
        "ru": "🌍 <b>Пожалуйста, выберите язык:</b>\n\nНажмите одну из кнопок ниже:",
        "en": "🌍 <b>Please select your language:</b>\n\nTap one of the buttons below:",
        "es": "🌍 <b>Por favor, selecciona tu idioma:</b>\n\nToca uno de los botones abajo:",
        "tr": "🌍 <b>Lütfen bir dil seçin:</b>\n\nAşağıdaki butonlardan birine dokunun:"
    },
    "lang_changed": {
        "uz": "✅ <b>Til muvaffaqiyatli o'zgartirildi:</b> O'zbekcha 🇺🇿",
        "ru": "✅ <b>Язык успешно изменён:</b> Русский 🇷🇺",
        "en": "✅ <b>Language successfully updated:</b> English 🇬🇧",
        "es": "✅ <b>Idioma actualizado con éxito:</b> Español 🇪🇸",
        "tr": "✅ <b>Dil başarıyla güncellendi:</b> Türkçe 🇹🇷"
    },
    "main_menu": {
        "uz": (
            "✨ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Foydalanuvchi:</b> <b>{name}</b>\n"
            "⚡ <b>Tizim holati:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Asosiy Imkoniyatlar & Xizmatlar:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Izohlarga avtomatik aqlli javoblar\n"
            "• 📊 <b>Analitika:</b> Kanal tahlili, trendlar va o'sish\n"
            "• 🌐 <b>Web Dashboard:</b> Boshqaruv paneli (Telegram WebApp)\n"
            "• 🎁 <b>Creator Perks:</b> Mini-o'yinlar, bonuslar va sovg'alar\n"
            "• 📥 <b>Yuklovchi:</b> Shorts & Reels yuklab olish\n"
            "• 🔑 <b>API & Studio:</b> Developer integratsiya\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Kerakli bo'limni tanlang:</i>"
        ),
        "ru": (
            "✨ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Пользователь:</b> <b>{name}</b>\n"
            "⚡ <b>Статус системы:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Основные возможности и услуги:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Умные авто-ответы на комментарии\n"
            "• 📊 <b>Аналитика:</b> Анализ каналов, тренды и рост\n"
            "• 🌐 <b>Web Dashboard:</b> Панель управления (Telegram WebApp)\n"
            "• 🎁 <b>Creator Perks:</b> Мини-игры, бонусы и призы\n"
            "• 📥 <b>Загрузчик:</b> Скачивание Shorts и Reels\n"
            "• 🔑 <b>API & Studio:</b> Интеграция для разработчиков\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Выберите нужный раздел:</i>"
        ),
        "en": (
            "✨ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>User:</b> <b>{name}</b>\n"
            "⚡ <b>System Status:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Core Features & Services:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Smart contextual comment replies\n"
            "• 📊 <b>Analytics:</b> Channel insights, trends & growth\n"
            "• 🌐 <b>Web Dashboard:</b> Telegram WebApp control panel\n"
            "• 🎁 <b>Creator Perks:</b> Daily perks, spins & rewards\n"
            "• 📥 <b>Downloader:</b> High-speed Shorts & Reels\n"
            "• 🔑 <b>API & Studio:</b> Developer integrations\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Select an option below:</i>"
        ),
        "es": (
            "✨ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Usuario:</b> <b>{name}</b>\n"
            "⚡ <b>Estado del sistema:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Funciones principales y servicios:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Respuestas inteligentes a comentarios\n"
            "• 📊 <b>Analítica:</b> Estadísticas de canal y crecimiento\n"
            "• 🌐 <b>Web Dashboard:</b> Panel de control en Telegram WebApp\n"
            "• 🎁 <b>Creator Perks:</b> Premios diarios y recompensas\n"
            "• 📥 <b>Descargador:</b> Descarga rápida de Shorts y Reels\n"
            "• 🔑 <b>API & Studio:</b> Integración para desarrolladores\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Selecciona una opción abajo:</i>"
        ),
        "tr": (
            "✨ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Kullanıcı:</b> <b>{name}</b>\n"
            "⚡ <b>Sistem Durumu:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Temel Özellikler ve Hizmetler:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Yorumlara yapay zeka ile akıllı yanıtlar\n"
            "• 📊 <b>Analitik:</b> Kanal analizi, büyüme ve viral trendler\n"
            "• 🌐 <b>Web Dashboard:</b> Telegram WebApp kontrol paneli\n"
            "• 🎁 <b>Creator Perks:</b> Günlük ödüller ve hediyeler\n"
            "• 📥 <b>İndirici:</b> Hızlı Shorts ve Reels indirme\n"
            "• 🔑 <b>API & Studio:</b> Geliştirici entegrasyonu\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Aşağıdan bir seçenek belirleyin:</i>"
        )
    },
    "btn_marketplace": {
        "uz": "💸 Xizmatlar / Marketplace",
        "ru": "💸 Услуги / Маркетплейс",
        "en": "💸 Services / Marketplace",
        "es": "💸 Servicios / Mercado",
        "tr": "💸 Hizmetler / Pazar"
    },
    "btn_balance": {
        "uz": "💰 Balans & To'lovlar",
        "ru": "💰 Баланс и Оплата",
        "en": "💰 Balance & Deposit",
        "es": "💰 Saldo y Recarga",
        "tr": "💰 Bakiye & Ödeme"
    },
    "btn_games": {
        "uz": "🎮 Mini O'yinlar & Sovg'alar",
        "ru": "🎮 Мини-Игры и Призы",
        "en": "🎮 Games & Prizes",
        "es": "🎮 Juegos y Premios",
        "tr": "🎮 Oyunlar & Ödüller"
    },
    "btn_api": {
        "uz": "🔑 Developer & Reseller API",
        "ru": "🔑 Разработчикам / Reseller API",
        "en": "🔑 Developer & Reseller API",
        "es": "🔑 API de Desarrollador",
        "tr": "🔑 Geliştirici / Reseller API"
    },
    "btn_referral": {
        "uz": "🎁 Do'stlarni chaqirish (Referal)",
        "ru": "🎁 Пригласить друзей (Реферал)",
        "en": "🎁 Invite Friends (Referral)",
        "es": "🎁 Invitar Amigos (Referidos)",
        "tr": "🎁 Arkadaşlarını Davet Et (Referans)"
    },
    "btn_leaderboard": {
        "uz": "🏆 Liderlar Jadvali",
        "ru": "🏆 Таблица Лидеров",
        "en": "🏆 Leaderboard",
        "es": "🏆 Tabla de Líderes",
        "tr": "🏆 Liderlik Tablosu"
    },
    "btn_help": {
        "uz": "📖 Yordam & Buyruqlar",
        "ru": "📖 Помощь и Команды",
        "en": "📖 Help & Commands",
        "es": "📖 Ayuda y Comandos",
        "tr": "📖 Yardım & Komutlar"
    },
    "btn_lang": {
        "uz": "🌍 Til / Language",
        "ru": "🌍 Язык / Language",
        "en": "🌍 Language / Til",
        "es": "🌍 Idioma / Language",
        "tr": "🌍 Dil / Language"
    },
    "btn_back": {
        "uz": "⬅️ Orqaga",
        "ru": "⬅️ Назад",
        "en": "⬅️ Back",
        "es": "⬅️ Volver",
        "tr": "⬅️ Geri"
    },
    "btn_home": {
        "uz": "🏠 Bosh Menyu",
        "ru": "🏠 Главное меню",
        "en": "🏠 Main Menu",
        "es": "🏠 Menú Principal",
        "tr": "🏠 Ana Menü"
    },
    "btn_support": {
        "uz": "💬 Yordam & Live Admin",
        "ru": "💬 Поддержка и Админ",
        "en": "💬 Support & Live Admin",
        "es": "💬 Soporte y Administrador",
        "tr": "💬 Destek ve Canlı Yönetici"
    },
    "btn_vouchers": {
        "uz": "💸 P2P Shartli Cheklar",
        "ru": "💸 P2P Условные Чеки",
        "en": "💸 P2P Conditional Vouchers",
        "es": "💸 Vales Condicionales P2P",
        "tr": "💸 P2P Koşullu Çekler"
    },
    "btn_ig_cloner": {
        "uz": "📸 Instagram Auto-Kloner",
        "ru": "📸 Instagram Авто-Клонер",
        "en": "📸 Instagram Auto-Cloner",
        "es": "📸 Auto-Clonador Instagram",
        "tr": "📸 Instagram Otomatik Klonlayıcı"
    },
    "btn_capcut": {
        "uz": "🎬 CapCut Pro (Pullik)",
        "ru": "🎬 CapCut Pro (Платный)",
        "en": "🎬 CapCut Pro (Paid)",
        "es": "🎬 CapCut Pro (De Pago)",
        "tr": "🎬 CapCut Pro (Ücretli)"
    },
    "btn_ai_video": {
        "uz": "🎬 AI Video Studio ($20/oy)",
        "ru": "🎬 AI Видео Студия ($20/мес)",
        "en": "🎬 AI Video Studio ($20/mo)",
        "es": "🎬 AI Video Studio ($20/mes)",
        "tr": "🎬 AI Video Studio ($20/ay)"
    },
    "btn_spy": {
        "uz": "🔍 Raqobatchi Tahlili (Spy & SEO)",
        "ru": "🔍 Шпион Конкурентов (SEO)",
        "en": "🔍 Competitor Spy & SEO Stealer",
        "es": "🔍 Espía de Competidores y SEO",
        "tr": "🔍 Rakip Casusu ve SEO Analizi"
    },
    "btn_cashout": {
        "uz": "💸 Pul Yechish (Stars & TON)",
        "ru": "💸 Вывод средств (Stars и TON)",
        "en": "💸 Cashout (Stars & TON)",
        "es": "💸 Retiro de Fondos (Stars y TON)",
        "tr": "💸 Para Çekme (Stars ve TON)"
    },
    "btn_deeplink": {
        "uz": "📲 DeepLink & QR Generator",
        "ru": "📲 DeepLink и QR Генератор",
        "en": "📲 DeepLink & QR Generator",
        "es": "📲 Generador DeepLink y QR",
        "tr": "📲 DeepLink ve QR Oluşturucu"
    },
    "btn_nft": {
        "uz": "🖼️ 3D NFT Studio",
        "ru": "🖼️ 3D NFT Студия",
        "en": "🖼️ 3D NFT Studio",
        "es": "🖼️ Estudio 3D NFT",
        "tr": "🖼️ 3D NFT Stüdyosu"
    },
    "nft_menu_title": {
        "uz": "🖼️ <b>Web3 3D NFT Studio (Polygon & TON)</b>\n━━━━━━━━━━━━━━━━━━━━\n💎 <b>0 Gas Fee:</b> EIP-712 Lazy Minting orqali bepul 3D NFT yarating!\n📦 <b>Format:</b> Haqiqiy 3D <code>.glb</code> model + HD Render + IPFS Metadata\n🏪 <b>Bozor:</b> O'zingiz yaratgan NFT larni boshqalarga soting yoki kolleksiya qiling!",
        "ru": "🖼️ <b>Web3 3D NFT Студия (Polygon и TON)</b>\n━━━━━━━━━━━━━━━━━━━━\n💎 <b>0 Комиссий:</b> Создавайте 3D NFT бесплатно через EIP-712 Lazy Minting!\n📦 <b>Формат:</b> Настоящая 3D <code>.glb</code> модель + HD Рендер + IPFS Метаданные\n🏪 <b>Рынок:</b> Продавайте свои NFT или коллекционируйте!",
        "en": "🖼️ <b>Web3 3D NFT Studio (Polygon & TON)</b>\n━━━━━━━━━━━━━━━━━━━━\n💎 <b>0 Gas Fee:</b> Create 3D NFTs for free via EIP-712 Lazy Minting!\n📦 <b>Format:</b> Genuine 3D <code>.glb</code> model + HD Render + IPFS Metadata\n🏪 <b>Market:</b> Sell your minted NFTs to others or build your collection!",
        "es": "🖼️ <b>Estudio 3D NFT Web3 (Polygon y TON)</b>\n━━━━━━━━━━━━━━━━━━━━\n💎 <b>Sin Gas:</b> ¡Crea NFTs 3D gratis con EIP-712 Lazy Minting!\n📦 <b>Formato:</b> Modelo 3D <code>.glb</code> real + Render HD + Metadatos IPFS\n🏪 <b>Mercado:</b> ¡Vende tus NFTs o crea tu colección!",
        "tr": "🖼️ <b>Web3 3D NFT Stüdyosu (Polygon ve TON)</b>\n━━━━━━━━━━━━━━━━━━━━\n💎 <b>0 Gas Ücreti:</b> EIP-712 Lazy Minting ile ücretsiz 3D NFT oluşturun!\n📦 <b>Format:</b> Gerçek 3D <code>.glb</code> model + HD Render + IPFS Metaverisi\n🏪 <b>Pazar:</b> NFT'lerinizi satın veya koleksiyon yapın!"
    },

    # ==================== REFERRAL ====================
    "referral_title": {
        "uz": (
            "🎁 <b>Do'stlarni chaqiring va Pul / Bepul Qutilar yuting!</b>\n\n"
            "Har bir taklif qilingan do'stingiz uchun:\n"
            "• 🎁 <b>1 ta Bepul Omadli Quti (Mystery Box)</b> — AI kalitlar yoki naqd pul yutish imkoni!\n"
            "• 💸 <b>10% Keshbek</b> — Do'stingiz hisobini to'ldirganda uning 10%i balansingizga tushadi!\n\n"
            "👥 <b>Taklif qilingan do'stlar:</b> <code>{invited_count} ta</code>\n"
            "💰 <b>Ishlangan jami keshbek:</b> <code>{total_earned:,} so'm</code>\n\n"
            "🔗 <b>Sizning shaxsiy referal havolangiz:</b>\n"
            "<code>{ref_link}</code> <i>(Nusxalash uchun ustiga bosing)</i>"
        ),
        "ru": (
            "🎁 <b>Приглашайте друзей и получайте Призы и Деньги!</b>\n\n"
            "За каждого приглашённого друга вы получаете:\n"
            "• 🎁 <b>1 Бесплатный Mystery Box</b> — шанс выиграть API ключи или деньги!\n"
            "• 💸 <b>10% Кэшбэк</b> — 10% от всех пополнений баланса вашего друга!\n\n"
            "👥 <b>Приглашено друзей:</b> <code>{invited_count} чел.</code>\n"
            "💰 <b>Заработано кэшбэка:</b> <code>{total_earned:,} сум</code>\n\n"
            "🔗 <b>Ваша персональная реферальная ссылка:</b>\n"
            "<code>{ref_link}</code> <i>(Нажмите, чтобы скопировать)</i>"
        ),
        "en": (
            "🎁 <b>Invite Friends & Win Mystery Boxes & Cash!</b>\n\n"
            "For every friend you invite, you get:\n"
            "• 🎁 <b>1 Free Mystery Box</b> — Chance to win top AI keys or instant cash!\n"
            "• 💸 <b>10% Lifetime Cashback</b> — On every deposit your friend makes!\n\n"
            "👥 <b>Friends invited:</b> <code>{invited_count}</code>\n"
            "💰 <b>Total cashback earned:</b> <code>{total_earned:,} UZS</code>\n\n"
            "🔗 <b>Your personal referral link:</b>\n"
            "<code>{ref_link}</code> <i>(Tap to copy)</i>"
        ),
        "es": (
            "🎁 <b>¡Invita Amigos y Gana Cajas Misteriosas y Dinero!</b>\n\n"
            "Por cada amigo que invites recibes:\n"
            "• 🎁 <b>1 Caja Misteriosa Gratis</b> — ¡Gana claves de IA o dinero real!\n"
            "• 💸 <b>10% de Reembolso de por vida</b> — ¡En cada recarga de tus amigos!\n\n"
            "👥 <b>Amigos invitados:</b> <code>{invited_count}</code>\n"
            "💰 <b>Total ganado:</b> <code>{total_earned:,} UZS</code>\n\n"
            "🔗 <b>Tu enlace de referido personal:</b>\n"
            "<code>{ref_link}</code> <i>(Toca para copiar)</i>"
        ),
        "tr": (
            "🎁 <b>Arkadaşlarını Davet Et, Mystery Box & Para Kazan!</b>\n\n"
            "Davet ettiğin her arkadaşın için:\n"
            "• 🎁 <b>1 Ücretsiz Gizemli Kutu (Mystery Box)</b> — Yapay zeka API anahtarları veya nakit para kazanma şansı!\n"
            "• 💸 <b>%10 Ömür Boyu Nakit İade (Cashback)</b> — Arkadaşının yaptığı her bakiye yüklemesinden!\n\n"
            "👥 <b>Davet Edilenler:</b> <code>{invited_count} kişi</code>\n"
            "💰 <b>Kazanılan Toplam İade:</b> <code>{total_earned:,} UZS</code>\n\n"
            "🔗 <b>Kişisel referans bağlantınız:</b>\n"
            "<code>{ref_link}</code> <i>(Kopyalamak için dokunun)</i>"
        )
    },
    "btn_share_ref": {
        "uz": "🚀 Do'stlarga yuborish (Share)",
        "ru": "🚀 Поделиться с друзьями",
        "en": "🚀 Share with Friends",
        "es": "🚀 Compartir con Amigos",
        "tr": "🚀 Arkadaşlarla Paylaş"
    },
    "ref_share_message": {
        "uz": "🔥 YouTube kanalingizni rivojlantiring va Mystery Box qutilarini ochib pul yuting! Botga kiring:",
        "ru": "🔥 Развивайте свой YouTube канал и открывайте Mystery Box с призами! Заходите в бота:",
        "en": "🔥 Boost your YouTube channel and open Mystery Boxes to win rewards! Join the bot:",
        "es": "🔥 ¡Impulsa tu canal de YouTube y abre Cajas Misteriosas con premios! Entra al bot:",
        "tr": "🔥 YouTube kanalını büyüt ve Gizemli Kutuları açarak ödüller kazan! Bota katıl:"
    },
    "ref_joined_notify": {
        "uz": "🎉 <b>Yangi do'stingiz botga qo'shildi!</b>\n\nSizga referal tizimi orqali <b>1 ta Bepul Omadli Quti (Mystery Box)</b> taqdim etildi! 🎁\nOchish uchun: /box",
        "ru": "🎉 <b>Новый друг присоединился по вашей ссылке!</b>\n\nВам начислен <b>1 Бесплатный Mystery Box</b>! 🎁\nЧтобы открыть: /box",
        "en": "🎉 <b>A new friend joined using your link!</b>\n\nYou received <b>1 Free Mystery Box</b>! 🎁\nTo open it: /box",
        "es": "🎉 <b>¡Un nuevo amigo se unió con tu enlace!</b>\n\n¡Has recibido <b>1 Caja Misteriosa Gratis</b>! 🎁\nPara abrirla: /box",
        "tr": "🎉 <b>Yeni bir arkadaşın bota katıldı!</b>\n\nSana <b>1 Ücretsiz Gizemli Kutu (Mystery Box)</b> tanımlandı! 🎁\nAçmak için: /box"
    },

    # ==================== FORCE CHANNEL SUBSCRIPTION ====================
    "force_sub_title": {
        "uz": (
            "📢 <b>Kanalga a'zo bo'ling!</b>\n\n"
            "Botning barcha bepul va pullik imkoniyatlaridan to'liq foydalanish uchun rasmiy kanalimizga a'zo bo'ling.\n\n"
            "<i>A'zo bo'lgach, «✅ Tekshirish» tugmasini bosing:</i>"
        ),
        "ru": (
            "📢 <b>Подпишитесь на наш канал!</b>\n\n"
            "Для использования всех функций бота необходимо подписаться на наш официальный канал.\n\n"
            "<i>После подписки нажмите кнопку «✅ Проверить»:</i>"
        ),
        "en": (
            "📢 <b>Join our Official Channel!</b>\n\n"
            "To access all features of this bot, please subscribe to our official channel first.\n\n"
            "<i>After subscribing, tap «✅ Verify»:</i>"
        ),
        "es": (
            "📢 <b>¡Únete a nuestro canal oficial!</b>\n\n"
            "Para utilizar todas las funciones del bot, por favor suscríbete a nuestro canal oficial.\n\n"
            "<i>Después de unirte, toca «✅ Verificar»:</i>"
        ),
        "tr": (
            "📢 <b>Resmi Kanalımıza Katılın!</b>\n\n"
            "Botun tüm özelliklerinden yararlanmak için lütfen resmi kanalımıza abone olun.\n\n"
            "<i>Abone olduktan sonra «✅ Doğrula» butonuna tıklayın:</i>"
        )
    },
    "btn_join_channel": {
        "uz": "📢 Kanalga a'zo bo'lish",
        "ru": "📢 Подписаться на канал",
        "en": "📢 Join Channel",
        "es": "📢 Unirse al Canal",
        "tr": "📢 Kanala Katıl"
    },
    "btn_verify_sub": {
        "uz": "✅ Tekshirish",
        "ru": "✅ Проверить",
        "en": "✅ Verify",
        "es": "✅ Verificar",
        "tr": "✅ Doğrula"
    },
    "sub_success": {
        "uz": "🎉 <b>Rahmat! A'zoligingiz tasdiqlandi.</b> Endi botdan to'liq foydalanishingiz mumkin!",
        "ru": "🎉 <b>Спасибо! Подписка подтверждена.</b> Теперь вы можете пользоваться ботом!",
        "en": "🎉 <b>Thank you! Subscription verified.</b> You can now use the bot freely!",
        "es": "🎉 <b>¡Gracias! Suscripción confirmada.</b> ¡Ahora puedes usar el bot sin límites!",
        "tr": "🎉 <b>Teşekkürler! Aboneliğiniz doğrulandı.</b> Artık botu sınırsızca kullanabilirsiniz!"
    },
    "sub_not_found": {
        "uz": "❌ Siz hali kanalga a'zo bo'lmadingiz! Iltimos, a'zo bo'lib qayta tekshiring.",
        "ru": "❌ Вы ещё не подписались на канал! Пожалуйста, подпишитесь и проверьте снова.",
        "en": "❌ You haven't joined the channel yet! Please subscribe and verify again.",
        "es": "❌ ¡Aún no te has suscrito al canal! Por favor únete e inténtalo de nuevo.",
        "tr": "❌ Henüz kanala katılmadınız! Lütfen abone olup tekrar deneyin."
    },

    # ==================== LEADERBOARD ====================
    "leaderboard_title": {
        "uz": (
            "🏆 <b>Haftalik Liderlar Jadvali (Top Reyting)</b>\n\n"
            "🔥 <b>Eng faol referal taklif qiluvchilar:</b>\n{top_referrers}\n\n"
            "⚔️ <b>PvP Duel chempionlari:</b>\n{top_duels}\n\n"
            "<i>Hafta oxirida Top-3 o'rin egalariga maxsus bonuslar beriladi!</i>"
        ),
        "ru": (
            "🏆 <b>Таблица Лидеров (Топ Рейтинг)</b>\n\n"
            "🔥 <b>Топ рефералов (по приглашениям):</b>\n{top_referrers}\n\n"
            "⚔️ <b>Чемпионы PvP Дуэлей:</b>\n{top_duels}\n\n"
            "<i>В конце недели Топ-3 получают денежные бонусы!</i>"
        ),
        "en": (
            "🏆 <b>Weekly Leaderboard (Top Ranking)</b>\n\n"
            "🔥 <b>Top Referrers (Most Invites):</b>\n{top_referrers}\n\n"
            "⚔️ <b>PvP Duel Champions:</b>\n{top_duels}\n\n"
            "<i>Top 3 leaders receive cash bonuses every week!</i>"
        ),
        "es": (
            "🏆 <b>Tabla de Líderes Semanal (Top Ranking)</b>\n\n"
            "🔥 <b>Mayores Invitadores (Referidos):</b>\n{top_referrers}\n\n"
            "⚔️ <b>Campeones de Duelos PvP:</b>\n{top_duels}\n\n"
            "<i>¡Los 3 mejores clasificados reciben premios en efectivo cada semana!</i>"
        ),
        "tr": (
            "🏆 <b>Haftalık Liderlik Tablosu (Top Sıralama)</b>\n\n"
            "🔥 <b>En Çok Davet Edenler (Referans):</b>\n{top_referrers}\n\n"
            "⚔️ <b>PvP Düello Şampiyonları:</b>\n{top_duels}\n\n"
            "<i>İlk 3 sıradaki liderler her hafta nakit ödüller kazanır!</i>"
        )
    },

    # ==================== VIDEO DOWNLOAD PROMO FOOTER ====================
    "dl_promo_caption": {
        "uz": "\n\n📥 <b>Yuklab olindi:</b> @{bot_user}\n🎁 <i>Bepul Mystery Box ochish: /box</i>",
        "ru": "\n\n📥 <b>Скачано через:</b> @{bot_user}\n🎁 <i>Бесплатный Mystery Box: /box</i>",
        "en": "\n\n📥 <b>Downloaded via:</b> @{bot_user}\n🎁 <i>Open a Free Mystery Box: /box</i>",
        "es": "\n\n📥 <b>Descargado con:</b> @{bot_user}\n🎁 <i>Abre tu Caja Misteriosa Gratis: /box</i>",
        "tr": "\n\n📥 <b>İndiren:</b> @{bot_user}\n🎁 <i>Ücretsiz Mystery Box aç: /box</i>"
    },

    # ==================== BALANCE ====================
    "balance_text": {
        "uz": (
            '<emoji id="5343777479091831702">💰</emoji> <b>Sizning Balansingiz:</b> <code>{balance:,} so\'m</code>\n\n'
            "To'lov turlari:\n"
            '• <emoji id="5463424023734014980">💎</emoji> <b>TON (The Open Network)</b>\n'
            '• <emoji id="6215463953925934839">⭐</emoji> <b>Telegram Stars</b>\n'
            '• <emoji id="6319002678990998592">🎁</emoji> <b>Sovg\'a Vaucherlari (/redeem)</b>\n\n'
            "<i>Balansni to'ldirish uchun kerakli to'lov usulini tanlang:</i>"
        ),
        "ru": (
            '<emoji id="5343777479091831702">💰</emoji> <b>Ваш Баланс:</b> <code>{balance:,} сум</code>\n\n'
            "Способы пополнения:\n"
            '• <emoji id="5463424023734014980">💎</emoji> <b>TON (The Open Network)</b>\n'
            '• <emoji id="6215463953925934839">⭐</emoji> <b>Telegram Stars</b>\n'
            '• <emoji id="6319002678990998592">🎁</emoji> <b>Подарочные Ваучеры (/redeem)</b>\n\n'
            "<i>Выберите удобный способ оплаты для пополнения:</i>"
        ),
        "en": (
            '<emoji id="5343777479091831702">💰</emoji> <b>Your Balance:</b> <code>{balance:,} UZS</code>\n\n'
            "Payment methods:\n"
            '• <emoji id="5463424023734014980">💎</emoji> <b>TON (The Open Network)</b>\n'
            '• <emoji id="6215463953925934839">⭐</emoji> <b>Telegram Stars</b>\n'
            '• <emoji id="6319002678990998592">🎁</emoji> <b>Gift Vouchers (/redeem)</b>\n\n'
            "<i>Choose your preferred payment method below:</i>"
        ),
        "es": (
            '<emoji id="5343777479091831702">💰</emoji> <b>Tu Saldo:</b> <code>{balance:,} UZS</code>\n\n'
            "Métodos de pago:\n"
            '• <emoji id="5463424023734014980">💎</emoji> <b>TON (The Open Network)</b>\n'
            '• <emoji id="6215463953925934839">⭐</emoji> <b>Telegram Stars</b>\n'
            '• <emoji id="6319002678990998592">🎁</emoji> <b>Vales de Regalo (/redeem)</b>\n\n'
            "<i>Elige tu método de pago preferido a continuación:</i>"
        ),
        "tr": (
            '<emoji id="5343777479091831702">💰</emoji> <b>Bakiyeniz:</b> <code>{balance:,} UZS</code>\n\n'
            "Ödeme Yöntemleri:\n"
            '• <emoji id="5463424023734014980">💎</emoji> <b>TON (The Open Network)</b>\n'
            '• <emoji id="6215463953925934839">⭐</emoji> <b>Telegram Stars</b>\n'
            '• <emoji id="6319002678990998592">🎁</emoji> <b>Hediye Kuponları (/redeem)</b>\n\n'
            "<i>Bakiyenizi yüklemek için aşağıdaki yöntemlerden birini seçin:</i>"
        )
    },

    # ==================== GAMES HUB ====================
    "games_title": {
        "uz": (
            "🎮 <b>Mini O'yinlar & Sovg'alar Markazi</b>\n\n"
            "💰 <b>Balansingiz:</b> <code>{balance:,} so'm</code>\n\n"
            "Quyidagi o'yinlardan birini tanlang va omadingizni sinab ko'ring:\n"
            "• 🎁 <b>Mystery Box</b> — Quti ochib katta keshbek va API yuting\n"
            "• 🎰 <b>Wheel of Fortune</b> — Kunlik bepul aylantirish\n"
            "• ⚔️ <b>PvP Duel</b> — Boshqa o'yinchilar bilan tanga tashlash\n"
            "• 🎟️ <b>Mega Lotereya</b> — Tirajli jekpot o'yini"
        ),
        "ru": (
            "🎮 <b>Центр Мини-Игр и Призов</b>\n\n"
            "💰 <b>Ваш баланс:</b> <code>{balance:,} сум</code>\n\n"
            "Выберите игру и испытайте удачу:\n"
            "• 🎁 <b>Mystery Box</b> — Откройте коробку и выиграйте API или деньги\n"
            "• 🎰 <b>Колесо Фортуны</b> — Ежедневное бесплатное вращение\n"
            "• ⚔️ <b>PvP Дуэль</b> — Бросьте монетку против других игроков\n"
            "• 🎟️ <b>Мега Лотерея</b> — Тиражный джекпот"
        ),
        "en": (
            "🎮 <b>Games & Prizes Center</b>\n\n"
            "💰 <b>Your Balance:</b> <code>{balance:,} UZS</code>\n\n"
            "Pick a game and test your luck:\n"
            "• 🎁 <b>Mystery Box</b> — Open boxes for top API keys & cash\n"
            "• 🎰 <b>Wheel of Fortune</b> — Daily free spin\n"
            "• ⚔️ <b>PvP Duel</b> — Coin flip challenge against real players\n"
            "• 🎟️ <b>Mega Lottery</b> — Jackpot raffle"
        ),
        "es": (
            "🎮 <b>Centro de Juegos y Premios</b>\n\n"
            "💰 <b>Tu Saldo:</b> <code>{balance:,} UZS</code>\n\n"
            "Elige un juego y prueba tu suerte:\n"
            "• 🎁 <b>Caja Misteriosa</b> — Gana claves de IA y efectivo\n"
            "• 🎰 <b>Rueda de la Fortuna</b> — Giro gratis diario\n"
            "• ⚔️ <b>Duelo PvP</b> — Lanza la moneda contra jugadores reales\n"
            "• 🎟️ <b>Mega Lotería</b> — Gran bote acumulado"
        ),
        "tr": (
            "🎮 <b>Oyunlar ve Ödüller Merkezi</b>\n\n"
            "💰 <b>Bakiyeniz:</b> <code>{balance:,} UZS</code>\n\n"
            "Bir oyun seçin ve şansınızı deneyin:\n"
            "• 🎁 <b>Gizemli Kutu</b> — API anahtarları ve nakit para kazanın\n"
            "• 🎰 <b>Çarkıfelek</b> — Günlük ücretsiz çevirme\n"
            "• ⚔️ <b>PvP Düello</b> — Gerçek oyunculara karşı yazı-tura\n"
            "• 🎟️ <b>Mega Piyango</b> — Büyük ikramiye çekilişi"
        )
    }
}


def t(key: str, lang: str = "uz", **kwargs) -> str:
    """Xabarni tanlangan tilda formatlab qaytarish"""
    safe_lang = lang if lang in SUPPORTED_LANGUAGES else "uz"
    item = TRANSLATIONS.get(key, {})
    text = item.get(safe_lang) or item.get("uz") or key
    if "{name}" in text and "name" not in kwargs:
        kwargs["name"] = "Foydalanuvchi"
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
