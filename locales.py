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
        "uz": "🌐 <b>Iltimos, tilni tanlang:</b>\n\nQuyidagi tugmalardan birini bosing:",
        "ru": "🌐 <b>Пожалуйста, выберите язык:</b>\n\nНажмите одну из кнопок ниже:",
        "en": "🌐 <b>Please select your language:</b>\n\nTap one of the buttons below:",
        "es": "🌐 <b>Por favor, selecciona tu idioma:</b>\n\nToca uno de los botones abajo:",
        "tr": "🌐 <b>Lütfen bir dil seçin:</b>\n\nAşağıdaki butonlardan birine dokunun:"
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
            "⚡ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Foydalanuvchi:</b> <b>{name}</b>\n"
            "⚡ <b>Tizim holati:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Asosiy Imkoniyatlar & Xizmatlar:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Izohlarga avtomatik aqlli javoblar\n"
            "• 📊 <b>Analitika:</b> Kanal tahlili, trendlar va o'sish\n"
            "• 🌐 <b>Web Dashboard:</b> Boshqaruv paneli (Telegram WebApp)\n"
            "• 🎁 <b>Creator Perks:</b> Mini-o'yinlar, bonuslar va sovg'alar\n"
            "• 🎬 <b>Yuklovchi:</b> Shorts & Reels yuklab olish\n"
            "• 🔑 <b>API & Studio:</b> Developer integratsiya\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Kerakli bo'limni tanlang:</i>"
        ),
        "ru": (
            "⚡ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Пользователь:</b> <b>{name}</b>\n"
            "⚡ <b>Статус системы:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Основные возможности и услуги:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Умные авто-ответы на комментарии\n"
            "• 📊 <b>Аналитика:</b> Анализ каналов, тренды и рост\n"
            "• 🌐 <b>Web Dashboard:</b> Панель управления (Telegram WebApp)\n"
            "• 🎁 <b>Creator Perks:</b> Мини-игры, бонусы и призы\n"
            "• 🎬 <b>Загрузчик:</b> Скачивание Shorts и Reels\n"
            "• 🔑 <b>API & Studio:</b> Интеграция для разработчиков\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Выберите нужный раздел:</i>"
        ),
        "en": (
            "⚡ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>User:</b> <b>{name}</b>\n"
            "⚡ <b>System Status:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Core Features & Services:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Smart contextual comment replies\n"
            "• 📊 <b>Analytics:</b> Channel insights, trends & growth\n"
            "• 🌐 <b>Web Dashboard:</b> Telegram WebApp control panel\n"
            "• 🎁 <b>Creator Perks:</b> Daily perks, spins & rewards\n"
            "• 🎬 <b>Downloader:</b> High-speed Shorts & Reels\n"
            "• 🔑 <b>API & Studio:</b> Developer integrations\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Select an option below:</i>"
        ),
        "es": (
            "⚡ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Usuario:</b> <b>{name}</b>\n"
            "⚡ <b>Estado del sistema:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Funciones principales y servicios:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Respuestas inteligentes a comentarios\n"
            "• 📊 <b>Analítica:</b> Estadísticas de canal y crecimiento\n"
            "• 🌐 <b>Web Dashboard:</b> Panel de control en Telegram WebApp\n"
            "• 🎁 <b>Creator Perks:</b> Premios diarios y recompensas\n"
            "• 🎬 <b>Descargador:</b> Descarga rápida de Shorts y Reels\n"
            "• 🔑 <b>API & Studio:</b> Integración para desarrolladores\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <i>Selecciona una opción abajo:</i>"
        ),
        "tr": (
            "⚡ <b>CreatorFlow Studio | YouTube AI Suite</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Kullanıcı:</b> <b>{name}</b>\n"
            "⚡ <b>Sistem Durumu:</b> <code>Online 🟢</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 <b>Temel Özellikler ve Hizmetler:</b>\n"
            "• 💬 <b>AI AutoReply:</b> Yorumlara yapay zeka ile akıllı yanıtlar\n"
            "• 📊 <b>Analitik:</b> Kanal analizi, büyüme ve viral trendler\n"
            "• 🌐 <b>Web Dashboard:</b> Telegram WebApp kontrol paneli\n"
            "• 🎁 <b>Creator Perks:</b> Günlük ödüller ve hediyeler\n"
            "• 🎬 <b>İndirici:</b> Hızlı Shorts ve Reels indirme\n"
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
        "uz": "\n\n🎬 <b>Yuklab olindi:</b> @{bot_user}\n🎁 <i>Bepul Mystery Box ochish: /box</i>",
        "ru": "\n\n🎬 <b>Скачано через:</b> @{bot_user}\n🎁 <i>Бесплатный Mystery Box: /box</i>",
        "en": "\n\n🎬 <b>Downloaded via:</b> @{bot_user}\n🎁 <i>Open a Free Mystery Box: /box</i>",
        "es": "\n\n🎬 <b>Descargado con:</b> @{bot_user}\n🎁 <i>Abre tu Caja Misteriosa Gratis: /box</i>",
        "tr": "\n\n🎬 <b>İndiren:</b> @{bot_user}\n🎁 <i>Ücretsiz Mystery Box aç: /box</i>"
    },

    # ==================== BALANCE ====================
    "balance_text": {
        "uz": (
            '💰 <b>Sizning Balansingiz:</b> <code>{balance:,} so\'m</code>\n\n'
            "To'lov turlari:\n"
            '• 💎 <b>TON (The Open Network)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Sovg\'a Vaucherlari (/redeem)</b>\n\n'
            "<i>Balansni to'ldirish uchun kerakli to'lov usulini tanlang:</i>"
        ),
        "ru": (
            '💰 <b>Ваш Баланс:</b> <code>{balance:,} сум</code>\n\n'
            "Способы пополнения:\n"
            '• 💎 <b>TON (The Open Network)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Подарочные Ваучеры (/redeem)</b>\n\n'
            "<i>Выберите удобный способ оплаты для пополнения:</i>"
        ),
        "en": (
            '💰 <b>Your Balance:</b> <code>{balance:,} UZS</code>\n\n'
            "Payment methods:\n"
            '• 💎 <b>TON (The Open Network)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Gift Vouchers (/redeem)</b>\n\n'
            "<i>Choose your preferred payment method below:</i>"
        ),
        "es": (
            '💰 <b>Tu Saldo:</b> <code>{balance:,} UZS</code>\n\n'
            "Métodos de pago:\n"
            '• 💎 <b>TON (The Open Network)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Vales de Regalo (/redeem)</b>\n\n'
            "<i>Elige tu método de pago preferido a continuación:</i>"
        ),
        "tr": (
            '💰 <b>Bakiyeniz:</b> <code>{balance:,} UZS</code>\n\n'
            "Ödeme Yöntemleri:\n"
            '• 💎 <b>TON (The Open Network)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Hediye Kuponları (/redeem)</b>\n\n'
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
,
    # ==================== MAIN MENU EXTENSIONS ====================
    "btn_tariffs_vip": {
        "uz": "Tariflar & VIP (69,000 UZS)",
        "ru": "Тарифы и VIP (69,000 UZS)",
        "en": "Plans & VIP (69,000 UZS)",
        "es": "Planes y VIP (69,000 UZS)",
        "tr": "Planlar ve VIP (69,000 UZS)"
    },
    "btn_channel_video": {
        "uz": "Kanal & Video",
        "ru": "Канал и Видео",
        "en": "Channel & Video",
        "es": "Canal y Video",
        "tr": "Kanal ve Video"
    },
    "btn_analytics": {
        "uz": "Analitika",
        "ru": "Аналитика",
        "en": "Analytics",
        "es": "Analítica",
        "tr": "Analitik"
    },
    "btn_bundles": {
        "uz": "Super To'plamlar (Bundles)",
        "ru": "Супер Наборы (Bundles)",
        "en": "Super Bundles",
        "es": "Súper Paquetes",
        "tr": "Süper Paketler"
    },
    "kyc_vip_status": {
        "uz": "VIP Foydalanuvchi",
        "ru": "VIP Пользователь",
        "en": "VIP User",
        "es": "Usuario VIP",
        "tr": "VIP Kullanıcı"
    },
    "kyc_3d_status": {
        "uz": "3D KYC Verified",
        "ru": "3D KYC Проверен",
        "en": "3D KYC Verified",
        "es": "3D KYC Verificado",
        "tr": "3D KYC Doğrulandı"
    },
    "kyc_half_status": {
        "uz": "Yarim Verified",
        "ru": "Частично Проверен",
        "en": "Half Verified",
        "es": "Semi Verificado",
        "tr": "Yarı Doğrulanmış"
    },

    # ==================== WALLET & PAYMENTS ====================
    "btn_pay_humo": {
        "uz": "HUMO / Uzcard orqali to'ldirish (UZS)",
        "ru": "Пополнить через HUMO / Uzcard (UZS)",
        "en": "Deposit via HUMO / Uzcard (UZS)",
        "es": "Depositar con HUMO / Uzcard (UZS)",
        "tr": "HUMO / Uzcard ile Yükle (UZS)"
    },
    "btn_pay_stars": {
        "uz": "Telegram Stars orqali to'ldirish",
        "ru": "Пополнить через Telegram Stars",
        "en": "Deposit via Telegram Stars",
        "es": "Depositar con Telegram Stars",
        "tr": "Telegram Stars ile Yükle"
    },
    "btn_pay_ton": {
        "uz": "TON (The Open Network) orqali",
        "ru": "Через TON (The Open Network)",
        "en": "Via TON (The Open Network)",
        "es": "Vía TON (The Open Network)",
        "tr": "TON (The Open Network) ile"
    },
    "btn_ton_wallet_connect": {
        "uz": "TON Hamyonni Ulash",
        "ru": "Подключить TON Кошелек",
        "en": "Connect TON Wallet",
        "es": "Conectar Billetera TON",
        "tr": "TON Cüzdanı Bağla"
    },
    "btn_ton_wallet_connected": {
        "uz": "TON Hamyon ({masked})",
        "ru": "TON Кошелек ({masked})",
        "en": "TON Wallet ({masked})",
        "es": "Billetera TON ({masked})",
        "tr": "TON Cüzdan ({masked})"
    },
    "btn_redeem_promo": {
        "uz": "Promokod kiritish (/redeem)",
        "ru": "Ввести промокод (/redeem)",
        "en": "Enter Promo Code (/redeem)",
        "es": "Ingresar código promo (/redeem)",
        "tr": "Promosyon Kodu Gir (/redeem)"
    },
    "btn_pay_history": {
        "uz": "To'lovlar tarixi",
        "ru": "История платежей",
        "en": "Payment History",
        "es": "Historial de pagos",
        "tr": "Ödeme Geçmişi"
    },

    # ==================== GAMES MENU ====================
    "btn_spin_wheel": {
        "uz": "Omad G'ildiragi (Daily Spin)",
        "ru": "Колесо Фортуны (Daily Spin)",
        "en": "Lucky Wheel (Daily Spin)",
        "es": "Rueda de la Suerte (Daily Spin)",
        "tr": "Çarkıfelek (Daily Spin)"
    },
    "btn_mystery_box": {
        "uz": "Omadli Quti (Mystery Box)",
        "ru": "Коробка Удачи (Mystery Box)",
        "en": "Mystery Box",
        "es": "Caja Misteriosa (Mystery Box)",
        "tr": "Gizemli Kutu (Mystery Box)"
    },
    "btn_coin_flip": {
        "uz": "Tanga Tashlash (Coin Flip)",
        "ru": "Бросок монеты (Coin Flip)",
        "en": "Coin Flip (PvP)",
        "es": "Lanzamiento de Moneda (Coin Flip)",
        "tr": "Yazı Tura (Coin Flip)"
    },
    "btn_lottery": {
        "uz": "Sovg'ali Lotereya",
        "ru": "Призовая Лотерея",
        "en": "Prize Lottery",
        "es": "Lotería con Premios",
        "tr": "Ödüllü Piyango"
    },

    # ==================== CHANNEL & VIDEO SUITE ====================
    "btn_full_stats": {
        "uz": "To'liq statistika",
        "ru": "Полная статистика",
        "en": "Full Statistics",
        "es": "Estadísticas completas",
        "tr": "Tam İstatistikler"
    },
    "btn_subs": {
        "uz": "Obunachilar",
        "ru": "Подписчики",
        "en": "Subscribers",
        "es": "Suscriptores",
        "tr": "Aboneler"
    },
    "btn_recent_videos": {
        "uz": "So'nggi videolar",
        "ru": "Последние видео",
        "en": "Recent Videos",
        "es": "Videos recientes",
        "tr": "Son Videolar"
    },
    "btn_popular_videos": {
        "uz": "Ommabop videolar",
        "ru": "Популярные видео",
        "en": "Popular Videos",
        "es": "Videos populares",
        "tr": "Popüler Videolar"
    },
    "btn_playlists": {
        "uz": "Pleylistlar",
        "ru": "Плейлисты",
        "en": "Playlists",
        "es": "Listas de reproducción",
        "tr": "Oynatma Listeleri"
    },
    "btn_about_channel": {
        "uz": "Kanal haqida",
        "ru": "О канале",
        "en": "About Channel",
        "es": "Sobre el canal",
        "tr": "Kanal Hakkında"
    },
    "btn_banner_avatar": {
        "uz": "Banner/Avatar",
        "ru": "Баннер/Аватар",
        "en": "Banner/Avatar",
        "es": "Banner/Avatar",
        "tr": "Afiş/Profil"
    },
    "btn_keywords": {
        "uz": "Kalit so'zlar",
        "ru": "Ключевые слова",
        "en": "Keywords & Tags",
        "es": "Palabras clave",
        "tr": "Anahtar Kelimeler"
    },
    "btn_upload_freq": {
        "uz": "Upload chastotasi",
        "ru": "Частота загрузок",
        "en": "Upload Frequency",
        "es": "Frecuencia de subida",
        "tr": "Yükleme Sıklığı"
    },
    "btn_earnings_est": {
        "uz": "Daromad taxmini",
        "ru": "Оценка дохода",
        "en": "Estimated Earnings",
        "es": "Ingresos estimados",
        "tr": "Tahmini Gelir"
    },
    "btn_likes": {
        "uz": "Likelar",
        "ru": "Лайки",
        "en": "Likes",
        "es": "Me gusta",
        "tr": "Beğeniler"
    },
    "btn_comments": {
        "uz": "Izohlar",
        "ru": "Комментарии",
        "en": "Comments",
        "es": "Comentarios",
        "tr": "Yorumlar"
    },
    "btn_tags": {
        "uz": "Teglar",
        "ru": "Теги",
        "en": "Tags",
        "es": "Etiquetas",
        "tr": "Etiketler"
    },
    "btn_thumbnail": {
        "uz": "Thumbnail",
        "ru": "Миниатюра",
        "en": "Thumbnail",
        "es": "Miniatura",
        "tr": "Küçük Resim"
    },
    "btn_description": {
        "uz": "Tavsif",
        "ru": "Описание",
        "en": "Description",
        "es": "Descripción",
        "tr": "Açıklama"
    },
    "btn_engagement": {
        "uz": "Engagement",
        "ru": "Вовлеченность",
        "en": "Engagement",
        "es": "Compromiso",
        "tr": "Etkileşim"
    },
    "btn_duration": {
        "uz": "Davomiyligi",
        "ru": "Длительность",
        "en": "Duration",
        "es": "Duración",
        "tr": "Süre"
    },
    "btn_growth_analysis": {
        "uz": "O'sish tahlili",
        "ru": "Анализ роста",
        "en": "Growth Analysis",
        "es": "Análisis de crecimiento",
        "tr": "Büyüme Analizi"
    },
    "btn_compare": {
        "uz": "Solishtirish",
        "ru": "Сравнение",
        "en": "Compare",
        "es": "Comparar",
        "tr": "Karşılaştır"
    },
    "btn_avg_views": {
        "uz": "O'rtacha ko'rishlar",
        "ru": "Средние просмотры",
        "en": "Average Views",
        "es": "Vistas promedio",
        "tr": "Ortalama İzlenme"
    },
    "btn_top_videos": {
        "uz": "Top videolar",
        "ru": "Топ видео",
        "en": "Top Videos",
        "es": "Mejores videos",
        "tr": "En İyi Videolar"
    },
    "btn_bottom_videos": {
        "uz": "Eng kam ko'rilgan",
        "ru": "Меньше всего просмотров",
        "en": "Least Viewed",
        "es": "Menos vistos",
        "tr": "En Az İzlenen"
    },
    "btn_report": {
        "uz": "To'liq hisobot",
        "ru": "Полный отчет",
        "en": "Full Report",
        "es": "Informe completo",
        "tr": "Tam Rapor"
    },
    "btn_upload_rate": {
        "uz": "Upload tezligi",
        "ru": "Скорость загрузки",
        "en": "Upload Velocity",
        "es": "Velocidad de subida",
        "tr": "Yükleme Hızı"
    },
    "btn_secret_coin": {
        "uz": "Yashirin Oltin Tanga",
        "ru": "Секретная Монета",
        "en": "Secret Golden Coin",
        "es": "Moneda de Oro Secreta",
        "tr": "Gizli Altın Para"
    },
    "btn_add_channel": {
        "uz": "Kanal qo'shish",
        "ru": "Добавить канал",
        "en": "Add Channel",
        "es": "Agregar canal",
        "tr": "Kanal Ekle"
    },
    "btn_remove_channel": {
        "uz": "Kanal o'chirish",
        "ru": "Удалить канал",
        "en": "Remove Channel",
        "es": "Eliminar canal",
        "tr": "Kanalı Kaldır"
    },
    "btn_my_list": {
        "uz": "Mening ro'yxatim",
        "ru": "Мой список",
        "en": "My List",
        "es": "Mi lista",
        "tr": "Listem"
    },
    "btn_check_all": {
        "uz": "Barchasini tekshirish",
        "ru": "Проверить все",
        "en": "Check All",
        "es": "Verificar todo",
        "tr": "Hepsini Kontrol Et"
    },
    "btn_url_to_id": {
        "uz": "URL dan ID olish",
        "ru": "Получить ID по URL",
        "en": "Get ID from URL",
        "es": "Obtener ID por URL",
        "tr": "URL'den ID Al"
    },
    "btn_get_thumb": {
        "uz": "Thumbnail olish",
        "ru": "Скачать обложку",
        "en": "Get Thumbnail",
        "es": "Obtener miniatura",
        "tr": "Küçük Resmi Al"
    },
    "btn_calculator": {
        "uz": "Kalkulyator",
        "ru": "Калькулятор",
        "en": "Calculator",
        "es": "Calculadora",
        "tr": "Hesap Makinesi"
    },
    "btn_categories": {
        "uz": "Kategoriyalar",
        "ru": "Категории",
        "en": "Categories",
        "es": "Categorías",
        "tr": "Kategoriler"
    },
    "btn_country_trending": {
        "uz": "Davlat trending",
        "ru": "Тренды стран",
        "en": "Country Trending",
        "es": "Tendencias por país",
        "tr": "Ülke Trendleri"
    },
    "btn_download_video": {
        "uz": "Videoni Yuklab Olish",
        "ru": "Скачать видео",
        "en": "Download Video",
        "es": "Descargar video",
        "tr": "Videoyu İndir"
    },
    "btn_refresh": {
        "uz": "Yangilash",
        "ru": "Обновить",
        "en": "Refresh",
        "es": "Actualizar",
        "tr": "Yenile"
    },
    "btn_my_purchases": {
        "uz": "Mening xaridlarim",
        "ru": "Мои покупки",
        "en": "My Purchases",
        "es": "Mis compras",
        "tr": "Satın Aldıklarım"
    },
    "btn_cancel": {
        "uz": "Bekor qilish",
        "ru": "Отмена",
        "en": "Cancel",
        "es": "Cancelar",
        "tr": "İptal"
    },

    # ==================== SUBMENU INTROS & HEADERS ====================
    "support_desk_menu_text": {
        "uz": "<b>Yordam & Qo'llab-quvvatlash Markazi</b>\n\nKerakli bo'limni tanlang. Sun'iy intellekt yoki Jonli Admin sizga xizmat ko'rsatadi:",
        "ru": "<b>Центр Поддержки и Помощи</b>\n\nВыберите нужный раздел. ИИ или Живой Администратор окажут вам помощь:",
        "en": "<b>Support & Help Desk</b>\n\nSelect a topic below. AI assistant or live agent is ready to assist you:",
        "es": "<b>Centro de Soporte y Ayuda</b>\n\nSelecciona una categoría. El asistente de IA o el Administrador te atenderán:",
        "tr": "<b>Yardım ve Destek Merkezi</b>\n\nAşağıdan bir konu seçin. Yapay Zeka veya Canlı Destek size yardımcı olacaktır:"
    },
    "vouchers_menu_text": {
        "uz": "<b>P2P Shartli Cheklar Tizimi (@wallet uslubida)</b>\n\n💰 <b>Sizning balansingiz:</b> <code>{balance:,} so'm</code>\n\nDo'stlaringiz yoki kanalingiz obunachilari uchun shartli chek yarating. Mablag'ni faqat siz belgilagan homiy kanalga a'zo bo'lganlar qabul qila oladi!",
        "ru": "<b>Система P2P Чеков (в стиле @wallet)</b>\n\n💰 <b>Ваш баланс:</b> <code>{balance:,} сум</code>\n\nСоздавайте подарочные чеки с условием подписки для ваших друзей или подписчиков!",
        "en": "<b>P2P Gift Vouchers (@wallet style)</b>\n\n💰 <b>Your Balance:</b> <code>{balance:,} UZS</code>\n\nCreate conditional gift checks for friends or channel subscribers with sponsored join requirements!",
        "es": "<b>Vales de Regalo P2P (Estilo @wallet)</b>\n\n💰 <b>Tu Saldo:</b> <code>{balance:,} UZS</code>\n\n¡Crea cheques regalo con condiciones de suscripción para tus amigos o seguidores!",
        "tr": "<b>P2P Hediye Kuponları (@wallet tarzı)</b>\n\n💰 <b>Bakiyeniz:</b> <code>{balance:,} UZS</code>\n\nKanal aboneleriniz veya arkadaşlarınız için şartlı hediye çekleri oluşturun!"
    },
    "btn_new_voucher": {
        "uz": "Yangi Chek Yaratish",
        "ru": "Создать новый чек",
        "en": "Create New Voucher",
        "es": "Crear nuevo vale",
        "tr": "Yeni Çek Oluştur"
    },
    "btn_enter_voucher": {
        "uz": "Chekni Faollashtirish (Kodni kiritish)",
        "ru": "Активировать чек (Ввести код)",
        "en": "Redeem Voucher (Enter code)",
        "es": "Canjear vale (Ingresar código)",
        "tr": "Çeki Etkinleştir (Kodu gir)"
    },
    "btn_voucher_guide": {
        "uz": "Cheklar Qo'llanmasi",
        "ru": "Инструкция по чекам",
        "en": "Vouchers Guide",
        "es": "Guía de vales",
        "tr": "Kupon Kılavuzu"
    },
    "ig_cloner_menu_text": {
        "uz": "<b>Instagram Account Auto-Cloner</b>\n\nSiz kiritgan Instagram profilidagi Reels'lar 8-qatlamli unikalizatsiya bilan to'g'ridan-to'g'ri YouTube Shorts ga nusxalanadi.\n\n📋 <b>Kuzatilayotgan profillar:</b>\n{profiles}",
        "ru": "<b>Instagram Account Auto-Cloner</b>\n\nReels из указанных профилей Instagram уникализируются в 8 слоев и клонируются в YouTube Shorts.\n\n📋 <b>Отслеживаемые профили:</b>\n{profiles}",
        "en": "<b>Instagram Account Auto-Cloner</b>\n\nReels from specified Instagram profiles are 8-layer uniquified and automatically posted to YouTube Shorts.\n\n📋 <b>Tracked profiles:</b>\n{profiles}",
        "es": "<b>Auto-Clonador de Instagram</b>\n\nLos Reels de los perfiles de Instagram se unifican y se publican automáticamente en YouTube Shorts.\n\n📋 <b>Perfiles seguidos:</b>\n{profiles}",
        "tr": "<b>Instagram Otomatik Klonlayıcı</b>\n\nBelirtilen Instagram hesaplarındaki Reels videoları 8 katmanlı özgünleştirme ile doğrudan YouTube Shorts'a aktarılır.\n\n📋 <b>Takip edilen profiller:</b>\n{profiles}"
    },
    "btn_add_ig_profile": {
        "uz": "Yangi Profil Qo'shish",
        "ru": "Добавить новый профиль",
        "en": "Add New Profile",
        "es": "Agregar nuevo perfil",
        "tr": "Yeni Profil Ekle"
    },
    "btn_sync_ig": {
        "uz": "Tekshirish & Yuklash",
        "ru": "Проверить и загрузить",
        "en": "Check & Sync",
        "es": "Verificar y sincronizar",
        "tr": "Kontrol Et ve İndir"
    },
    "btn_manage_ig": {
        "uz": "Profillarni Boshqarish",
        "ru": "Управление профилями",
        "en": "Manage Profiles",
        "es": "Administrar perfiles",
        "tr": "Profilleri Yönet"
    },
    "ai_video_menu_text": {
        "uz": "<b>AI Video Studio ($20 / oy)</b>\n\nUshbu xizmat professional sun'iy intellekt orqali to'liq avtomatlashtirilgan video tayyorlash studiyasidir:\n• <b>Flux.1 Ultra AI</b> — 9:16 kinematografik 4K tasvirlar\n• <b>Neural Edge-TTS</b> — 5 ta tilda tabiiy diktor ovozi\n• <b>Ken Burns FX</b> — Dinamik kamera harakati\n• <b>1-Click Shorts Yuklash</b>\n\n💰 <b>Balansingiz:</b> <code>{balance:,} so'm</code>",
        "ru": "<b>AI Video Studio ($20 / мес)</b>\n\nПрофессиональная студия автоматической генерации видео с помощью ИИ:\n• <b>Flux.1 Ultra AI</b> — Кинематографичные 4K кадры 9:16\n• <b>Neural Edge-TTS</b> — Естественная озвучка на 5 языках\n• <b>Ken Burns FX</b> — Динамичная камера\n• <b>Публикация в 1 клик</b>\n\n💰 <b>Ваш баланс:</b> <code>{balance:,} сум</code>",
        "en": "<b>AI Video Studio ($20 / mo)</b>\n\nFully automated professional AI video production studio:\n• <b>Flux.1 Ultra AI</b> — 9:16 cinematic 4K visuals\n• <b>Neural Edge-TTS</b> — Natural voiceover in 5 languages\n• <b>Ken Burns FX</b> — Dynamic camera motion\n• <b>1-Click Shorts Upload</b>\n\n💰 <b>Your Balance:</b> <code>{balance:,} UZS</code>",
        "es": "<b>AI Video Studio ($20 / mes)</b>\n\nEstudio profesional de producción de video totalmente automatizado con IA:\n• <b>Flux.1 Ultra AI</b> — Imágenes cinemáticas 4K 9:16\n• <b>Neural Edge-TTS</b> — Locución natural en 5 idiomas\n• <b>Ken Burns FX</b> — Movimiento de cámara dinámico\n• <b>Publicación en 1 clic</b>\n\n💰 <b>Tu Saldo:</b> <code>{balance:,} UZS</code>",
        "tr": "<b>AI Video Studio ($20 / ay)</b>\n\nYapay zeka ile tam otomatik profesyonel video üretim stüdyosu:\n• <b>Flux.1 Ultra AI</b> — 9:16 sinematik 4K görseller\n• <b>Neural Edge-TTS</b> — 5 dilde doğal seslendirme\n• <b>Ken Burns FX</b> — Dinamik kamera hareketleri\n• <b>Tek Tıkla Shorts Yükleme</b>\n\n💰 <b>Bakiyeniz:</b> <code>{balance:,} UZS</code>"
    },
    "btn_ai_sub": {
        "uz": "Oylik Obuna ($20 - 256,000 so'm)",
        "ru": "Месячная подписка ($20 - 256,000 сум)",
        "en": "Monthly Pass ($20 - 256,000 UZS)",
        "es": "Suscripción mensual ($20 - 256,000 UZS)",
        "tr": "Aylık Abonelik ($20 - 256,000 UZS)"
    },
    "btn_ai_single": {
        "uz": "1 ta Video Yaratish (15,000 so'm)",
        "ru": "Создать 1 видео (15,000 сум)",
        "en": "Generate 1 Video (15,000 UZS)",
        "es": "Crear 1 video (15,000 UZS)",
        "tr": "1 Video Üret (15,000 UZS)"
    },
    "spy_menu_text": {
        "uz": "<b>YouTube Competitor Spy & SEO Stealer</b>\n\nTahlil qilmoqchi bo'lgan YouTube video yoki Shorts havolasini yuboring:",
        "ru": "<b>Шпион конкурентов YouTube и Сбор SEO</b>\n\nОтправьте ссылку на видео или Shorts конкурента для детального анализа:",
        "en": "<b>YouTube Competitor Spy & SEO Stealer</b>\n\nSend a link to any YouTube video or Shorts you want to analyze:",
        "es": "<b>Espía de Competidores de YouTube y SEO</b>\n\nEnvía un enlace de video o Shorts de YouTube para analizarlo:",
        "tr": "<b>YouTube Rakip Casusu ve SEO Analizi</b>\n\nAnaliz etmek istediğiniz YouTube video veya Shorts bağlantısını gönderin:"
    },
    "bundles_menu_text": {
        "uz": "<b>CreatorFlow Super To'plamlar (Bundles)</b>\n\nBir nechta premium xizmatlarni birgalikda 40% gacha chegirma bilan xarid qiling:",
        "ru": "<b>Супер Наборы CreatorFlow (Bundles)</b>\n\nПриобретайте премиум инструменты вместе со скидкой до 40%:",
        "en": "<b>CreatorFlow Super Bundles</b>\n\nGet all essential creator tools bundled together with up to 40% savings:",
        "es": "<b>Súper Paquetes de CreatorFlow (Bundles)</b>\n\nObtén herramientas premium combinadas con hasta un 40% de descuento:",
        "tr": "<b>CreatorFlow Süper Paketleri (Bundles)</b>\n\nEn iyi içerik üretici araçlarını %40'a varan indirimle paket olarak alın:"
    }

}

def t(key: str, lang: str = "en", **kwargs) -> str:
    """Xabarni tanlangan tilda formatlab qaytarish (default: en)"""
    safe_lang = lang if lang in SUPPORTED_LANGUAGES else "en"
    item = TRANSLATIONS.get(key, {})
    text = item.get(safe_lang) or item.get("en") or item.get("uz") or key
    if "{name}" in text and "name" not in kwargs:
        kwargs["name"] = "Foydalanuvchi"
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

# Extra menu & navigation keys
TRANSLATIONS.update({'menu_channel_header': {'uz': '**Kanal tahlili**\n\nKanal nomini yoki URL ni buyruq bilan yuboring:', 'ru': '**Анализ канала**\n\nОтправьте название или URL канала с командой:', 'en': '**Channel Analytics**\n\nSend channel name or URL with a command:', 'es': '**Análisis del Canal**\n\nEnvía el nombre o URL del canal con un comando:', 'tr': "**Kanal Analizi**\n\nKomutla birlikte kanal adını veya URL'sini gönderin:"}, 'menu_video_header': {'uz': '**Video tahlili**\n\nVideo URL ni buyruq bilan yuboring:', 'ru': '**Анализ видео**\n\nОтправьте URL видео с командой:', 'en': '**Video Analytics**\n\nSend video URL with a command:', 'es': '**Análisis de Video**\n\nEnvía la URL del video con un comando:', 'tr': "**Video Analizi**\n\nKomutla birlikte video URL'sini gönderin:"}, 'menu_analytics_header': {'uz': "**Analitika va O'sish**\n\nKanal nomini buyruq bilan yuboring:", 'ru': '**Аналитика и Рост**\n\nОтправьте название канала с командой:', 'en': '**Analytics & Growth**\n\nSend channel name with a command:', 'es': '**Analítica y Crecimiento**\n\nEnvía el nombre del canal con un comando:', 'tr': '**Analitik ve Büyüme**\n\nKomutla birlikte kanal adını gönderin:'}, 'menu_search_header': {'uz': "**Qidiruv**\n\nQidiruv so'zini buyruq bilan yuboring:", 'ru': '**Поиск**\n\nОтправьте поисковый запрос с командой:', 'en': '**Search**\n\nSend search keyword with a command:', 'es': '**Búsqueda**\n\nEnvía la palabra de búsqueda con un comando:', 'tr': '**Arama**\n\nArama terimini bir komutla gönderin:'}, 'menu_tracking_header': {'uz': '**Kanal kuzatuvi**\n\nKanallarni kuzatib boring:', 'ru': '**Отслеживание каналов**\n\nОтслеживайте выбранные каналы:', 'en': '**Channel Tracking**\n\nTrack selected channels:', 'es': '**Seguimiento de Canales**\n\nSigue los canales seleccionados:', 'tr': '**Kanal Takibi**\n\nSeçilen kanalları takip edin:'}, 'menu_tools_header': {'uz': '**Asboblar**\n\nTurli foydali vositalar:', 'ru': '**Инструменты**\n\nРазличные полезные утилиты:', 'en': '**Tools**\n\nUseful utility tools:', 'es': '**Herramientas**\n\nUtilidades y herramientas útiles:', 'tr': '**Araçlar**\n\nFaydalı araçlar ve yardımcı programlar:'}, 'menu_trending_header': {'uz': '**Trending**\n\nDavlatni tanlang:', 'ru': '**Тренды**\n\nВыберите страну:', 'en': '**Trending**\n\nSelect a country:', 'es': '**Tendencias**\n\nSelecciona un país:', 'tr': '**Trendler**\n\nBir ülke seçin:'}, 'menu_help_header': {'uz': '**Yordam**\n\nKategoriyani tanlang:', 'ru': '**Помощь**\n\nВыберите категорию:', 'en': '**Help**\n\nSelect a category:', 'es': '**Ayuda**\n\nSelecciona una categoría:', 'tr': '**Yardım**\n\nBir kategori seçin:'}, 'btn_search_video': {'uz': 'Video qidirish', 'ru': 'Поиск видео', 'en': 'Search Video', 'es': 'Buscar Video', 'tr': 'Video Ara'}, 'btn_search_channel': {'uz': 'Kanal qidirish', 'ru': 'Поиск канала', 'en': 'Search Channel', 'es': 'Buscar Canal', 'tr': 'Kanal Ara'}, 'btn_search_playlist': {'uz': 'Pleylist qidirish', 'ru': 'Поиск плейлистов', 'en': 'Search Playlist', 'es': 'Buscar Playlist', 'tr': 'Oynatma Listesi Ara'}, 'btn_milestone': {'uz': 'Milestone', 'ru': 'Вехи (Milestone)', 'en': 'Milestones', 'es': 'Hitos', 'tr': 'Kilometre Taşları'}, 'btn_nft_market': {'uz': 'NFT Kolleksiya (Bozor)', 'ru': 'Коллекция NFT (Рынок)', 'en': 'NFT Collection (Market)', 'es': 'Colección NFT (Mercado)', 'tr': 'NFT Koleksiyonu (Pazar)'}, 'btn_nft_my': {'uz': 'Mening NFT larim', 'ru': 'Мои NFT', 'en': 'My NFTs', 'es': 'Mis NFTs', 'tr': "NFT'lerim"}, 'btn_cashout_stars': {'uz': 'Telegram Stars orqali', 'ru': 'Через Telegram Stars', 'en': 'Via Telegram Stars', 'es': 'Vía Telegram Stars', 'tr': 'Telegram Stars ile'}, 'btn_cashout_ton': {'uz': 'TON Kriptovalyuta orqali', 'ru': 'Через криптовалюту TON', 'en': 'Via TON Cryptocurrency', 'es': 'Vía Criptomoneda TON', 'tr': 'TON Kripto ile'}, 'cashout_menu_text': {'uz': 'Hisobdan Pul Yechish (Cashout)\n\nPul yechish usulini tanlang:', 'ru': 'Вывод средств (Cashout)\n\nВыберите способ вывода средств:', 'en': 'Funds Withdrawal (Cashout)\n\nSelect a withdrawal method:', 'es': 'Retiro de Fondos (Cashout)\n\nSelecciona el método de retiro:', 'tr': 'Para Çekme (Cashout)\n\nÇekim yöntemini seçin:'}})
