"""
Multi-Language (i18n) Engine for Mono Deck Studio Bot
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
            "⚡ <b>Mono Deck Studio | YouTube AI Suite</b>\n"
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
            "⚡ <b>Mono Deck Studio | YouTube AI Suite</b>\n"
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
            "⚡ <b>Mono Deck Studio | YouTube AI Suite</b>\n"
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
            "⚡ <b>Mono Deck Studio | YouTube AI Suite</b>\n"
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
            "⚡ <b>Mono Deck Studio | YouTube AI Suite</b>\n"
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
            '• 💎 <b>Crypto (Binance Pay / @CryptoBot / TON — istalgan summa)</b>\n'
            '• 💳 <b>HUMO / Uzcard (UZS)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Sovg\'a Vaucherlari (/redeem)</b>\n\n'
            "<i>Balansni to'ldirish uchun kerakli to'lov usulini tanlang:</i>"
        ),
        "ru": (
            '💰 <b>Ваш Баланс:</b> <code>{balance:,} сум</code>\n\n'
            "Способы пополнения:\n"
            '• 💎 <b>Crypto (Binance Pay / @CryptoBot / TON — любая сумма)</b>\n'
            '• 💳 <b>HUMO / Uzcard (UZS)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Подарочные Ваучеры (/redeem)</b>\n\n'
            "<i>Выберите удобный способ оплаты для пополнения:</i>"
        ),
        "en": (
            '💰 <b>Your Balance:</b> <code>{balance:,} UZS</code>\n\n'
            "Payment methods:\n"
            '• 💎 <b>Crypto (Binance Pay / @CryptoBot / TON — Custom Amount)</b>\n'
            '• 💳 <b>HUMO / Uzcard (UZS)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Gift Vouchers (/redeem)</b>\n\n'
            "<i>Choose your preferred payment method below:</i>"
        ),
        "es": (
            '💰 <b>Tu Saldo:</b> <code>{balance:,} UZS</code>\n\n'
            "Métodos de pago:\n"
            '• 💎 <b>Crypto (Binance Pay / @CryptoBot / TON — Monto Libre)</b>\n'
            '• 💳 <b>HUMO / Uzcard (UZS)</b>\n'
            '• ⭐ <b>Telegram Stars</b>\n'
            '• 🎁 <b>Vales de Regalo (/redeem)</b>\n\n'
            "<i>Elige tu método de pago preferido a continuación:</i>"
        ),
        "tr": (
            '💰 <b>Bakiyeniz:</b> <code>{balance:,} UZS</code>\n\n'
            "Ödeme Yöntemleri:\n"
            '• 💎 <b>Kripto (Binance Pay / @CryptoBot / TON — Özel Tutar)</b>\n'
            '• 💳 <b>HUMO / Uzcard (UZS)</b>\n'
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
    "btn_pay_binance": {
        "uz": "Binance / USDT orqali to'ldirish",
        "ru": "Пополнить через Binance / USDT",
        "en": "Deposit via Binance / USDT",
        "es": "Depositar con Binance / USDT",
        "tr": "Binance / USDT ile Yükle"
    },
    "btn_pay_cryptobot": {
        "uz": "@CryptoBot orqali to'ldirish",
        "ru": "Пополнить через @CryptoBot",
        "en": "Deposit via @CryptoBot",
        "es": "Depositar con @CryptoBot",
        "tr": "@CryptoBot ile Yükle"
    },
    "btn_pay_ton": {
        "uz": "TON (The Open Network) orqali",
        "ru": "Пополнить через TON",
        "en": "Deposit via TON",
        "es": "Depositar con TON",
        "tr": "TON ile Yükle"
    },
    "btn_open_binance_order": {
        "uz": "Binance Buyurtma Ochish",
        "ru": "Открыть ордер Binance",
        "en": "Open Binance Order",
        "es": "Abrir orden Binance",
        "tr": "Binance Siparişi Aç"
    },
    "btn_open_cryptobot_order": {
        "uz": "@CryptoBot Buyurtma Ochish",
        "ru": "Открыть ордер @CryptoBot",
        "en": "Open @CryptoBot Order",
        "es": "Abrir orden @CryptoBot",
        "tr": "@CryptoBot Siparişi Aç"
    },
    "btn_open_ton_order": {
        "uz": "TON Buyurtma Ochish",
        "ru": "Открыть ордер TON",
        "en": "Open TON Order",
        "es": "Abrir orden TON",
        "tr": "TON Siparişi Aç"
    },
    "btn_verify_binance_order": {
        "uz": "Order ID / TxID bilan tasdiqlash",
        "ru": "Проверить по Order ID / TxID",
        "en": "Verify with Order ID / TxID",
        "es": "Verificar con Order ID / TxID",
        "tr": "Order ID / TxID ile Doğrula"
    },
    "btn_verify_ton_order": {
        "uz": "TxID / Hash bilan tasdiqlash",
        "ru": "Проверить по TxID / Hash",
        "en": "Verify with TxID / Hash",
        "es": "Verificar con TxID / Hash",
        "tr": "TxID / Hash ile Doğrula"
    },
    "btn_verify_cryptobot": {
        "uz": "To'lovni tekshirish",
        "ru": "Проверить оплату",
        "en": "Verify Payment",
        "es": "Verificar pago",
        "tr": "Ödemeyi Doğrula"
    },
    "btn_pay_cryptobot_link": {
        "uz": "@CryptoBot orqali to'lash (${amount})",
        "ru": "Оплатить через @CryptoBot (${amount})",
        "en": "Pay via @CryptoBot (${amount})",
        "es": "Pagar por @CryptoBot (${amount})",
        "tr": "@CryptoBot ile Öde (${amount})"
    },
    "btn_cancel_order": {
        "uz": "Buyurtmani bekor qilish",
        "ru": "Отменить ордер",
        "en": "Cancel Order",
        "es": "Cancelar orden",
        "tr": "Siparişi İptal Et"
    },
    "btn_back_wallet": {
        "uz": "Hamyonga qaytish",
        "ru": "Назад в кошелек",
        "en": "Back to Wallet",
        "es": "Volver a la billetera",
        "tr": "Cüzdana Dön"
    },
    "crypto_confirm_open_binance": {
        "uz": (
            "<b>Binance Pay / USDT Depozit Buyurtmasi</b>\n\n"
            "Binance Pay UID yoki USDT (TRC20 / BEP20) orqali balans to'ldirish uchun yangi buyurtma (order) ochaymi?\n\n"
            "<i>Keyingi qadamda aniq qancha summa tashlashingizni yozasiz va Binance Order ID / TxID orqali tasdiqlaysiz.</i>"
        ),
        "ru": (
            "<b>Ордер на пополнение Binance Pay / USDT</b>\n\n"
            "Открыть новый ордер для пополнения через Binance Pay UID или USDT (TRC20 / BEP20)?\n\n"
            "<i>На следующем шаге вы укажете точную сумму и подтвердите платеж по Binance Order ID / TxID.</i>"
        ),
        "en": (
            "<b>Binance Pay / USDT Deposit Order</b>\n\n"
            "Would you like to open a new deposit order for Binance Pay UID or USDT (TRC20 / BEP20)?\n\n"
            "<i>Next, you'll enter your exact deposit amount and verify the transfer using your Binance Order ID / TxID.</i>"
        ),
        "es": (
            "<b>Orden de depósito Binance Pay / USDT</b>\n\n"
            "¿Deseas abrir una nueva orden de depósito para Binance Pay UID o USDT (TRC20 / BEP20)?\n\n"
            "<i>En el siguiente paso indicarás el monto exacto y lo verificarás con tu Binance Order ID / TxID.</i>"
        ),
        "tr": (
            "<b>Binance Pay / USDT Yatırım Siparişi</b>\n\n"
            "Binance Pay UID veya USDT (TRC20 / BEP20) ile bakiye yüklemek için yeni bir sipariş açalım mı?\n\n"
            "<i>Bir sonraki adımda tam tutarı yazıp Binance Order ID / TxID ile doğrulayacaksınız.</i>"
        )
    },
    "crypto_confirm_open_ton": {
        "uz": (
            "<b>TON (The Open Network) Depozit Buyurtmasi</b>\n\n"
            "TON tarmog'i orqali hisob to'ldirish uchun yangi buyurtma (order) ochaymi?\n\n"
            "<i>Keyingi qadamda aniq qancha summa tashlashingizni yozasiz, so'ngra manzil, Memo va TxID tekshiruvi beriladi.</i>"
        ),
        "ru": (
            "<b>Ордер на пополнение TON (The Open Network)</b>\n\n"
            "Открыть новый ордер для пополнения через сеть TON?\n\n"
            "<i>На следующем шаге вы укажете точную сумму, после чего получите адрес, Memo и кнопку проверки TxID.</i>"
        ),
        "en": (
            "<b>TON (The Open Network) Deposit Order</b>\n\n"
            "Would you like to open a new TON network deposit order?\n\n"
            "<i>Next, you'll enter the exact amount to deposit and receive the TON address, Memo tag, and TxID verification button.</i>"
        ),
        "es": (
            "<b>Orden de depósito TON (The Open Network)</b>\n\n"
            "¿Deseas abrir una nueva orden de depósito en la red TON?\n\n"
            "<i>A continuación escribirás el monto exacto y recibirás la dirección TON, Memo y verificación por TxID.</i>"
        ),
        "tr": (
            "<b>TON (The Open Network) Yatırım Siparişi</b>\n\n"
            "TON ağı üzerinden bakiye yüklemek için yeni bir sipariş açalım mı?\n\n"
            "<i>Sonraki adımda yatıracağınız tutarı yazacak, ardından TON adresini, Memo etiketini ve TxID doğrulamasını alacaksınız.</i>"
        )
    },
    "crypto_confirm_open_cryptobot": {
        "uz": (
            "<b>@CryptoBot (Multi-Coin) To'lov Buyurtmasi</b>\n\n"
            "@CryptoBot orqali istalgan koin (USDT, TON, BTC, ETH, TRX, BNB) bilan avtomatik to'lov buyurtmasi ochaymi?\n\n"
            "<i>Keyingi qadamda aniq $ USD summani yozasiz va 1 bosishli @CryptoBot to'lov cheki yaratiladi.</i>"
        ),
        "ru": (
            "<b>Ордер оплаты через @CryptoBot (Multi-Coin)</b>\n\n"
            "Открыть новый ордер для автоматической оплаты через @CryptoBot (USDT, TON, BTC, ETH, TRX, BNB)?\n\n"
            "<i>На следующем шаге введите сумму в $ USD, и бот создаст мгновенный счет @CryptoBot.</i>"
        ),
        "en": (
            "<b>@CryptoBot (Multi-Coin) Deposit Order</b>\n\n"
            "Would you like to open a new @CryptoBot order (supports USDT, TON, BTC, ETH, TRX, BNB, LTC, USDC)?\n\n"
            "<i>Next, enter the exact $ USD amount you want to deposit and we'll generate your instant @CryptoBot invoice.</i>"
        ),
        "es": (
            "<b>Orden de pago @CryptoBot (Multi-Coin)</b>\n\n"
            "¿Deseas abrir una nueva orden con @CryptoBot (acepta USDT, TON, BTC, ETH, TRX, BNB)?\n\n"
            "<i>Luego ingresa el monto exacto en $ USD para generar tu factura instantánea de @CryptoBot.</i>"
        ),
        "tr": (
            "<b>@CryptoBot (Multi-Coin) Ödeme Siparişi</b>\n\n"
            "@CryptoBot üzerinden (USDT, TON, BTC, ETH, TRX, BNB) otomatik ödeme siparişi açalım mı?\n\n"
            "<i>Sonraki adımda tam $ USD tutarını yazın, anında @CryptoBot faturanızı oluşturalım.</i>"
        )
    },
    "crypto_ask_amount_binance": {
        "uz": (
            "<b>Binance / USDT — Summani Kiriting</b>\n\n"
            "💵 <b>Joriy kurs:</b> <code>1 USD ≈ {rate:,} so'm</code>\n\n"
            "Aniq qancha <b>$ USD / USDT</b> o'tkazmoqchisiz?\n"
            "<i>Masalan: <code>2.5</code>, <code>10</code>, <code>25</code> (Min: $0.50 — Max: $5,000)</i>"
        ),
        "ru": (
            "<b>Binance / USDT — Введите сумму</b>\n\n"
            "💵 <b>Текущий курс:</b> <code>1 USD ≈ {rate:,} сум</code>\n\n"
            "Какую точную сумму в <b>$ USD / USDT</b> вы отправите?\n"
            "<i>Например: <code>2.5</code>, <code>10</code>, <code>25</code> (Мин: $0.50 — Макс: $5,000)</i>"
        ),
        "en": (
            "<b>Binance / USDT — Enter Exact Amount</b>\n\n"
            "💵 <b>Live Rate:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "How much exact <b>$ USD / USDT</b> are you going to send?\n"
            "<i>Example: <code>2.5</code>, <code>10</code>, <code>25</code> (Min: $0.50 — Max: $5,000)</i>"
        ),
        "es": (
            "<b>Binance / USDT — Ingresa el monto exacto</b>\n\n"
            "💵 <b>Tasa actual:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "¿Cuánto exactamente en <b>$ USD / USDT</b> vas a enviar?\n"
            "<i>Ejemplo: <code>2.5</code>, <code>10</code>, <code>25</code> (Mín: $0.50 — Máx: $5,000)</i>"
        ),
        "tr": (
            "<b>Binance / USDT — Tam Tutarı Girin</b>\n\n"
            "💵 <b>Güncel Kur:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "Tam olarak kaç <b>$ USD / USDT</b> göndereceksiniz?\n"
            "<i>Örnek: <code>2.5</code>, <code>10</code>, <code>25</code> (Min: $0.50 — Maks: $5,000)</i>"
        )
    },
    "crypto_ask_amount_ton": {
        "uz": (
            "<b>TON Depozit — Summani Kiriting</b>\n\n"
            "💵 <b>Joriy kurs:</b> <code>1 USD ≈ {rate:,} so'm</code>\n\n"
            "Taxminan qancha <b>$ USD</b> ekvivalentida TON yubormoqchisiz?\n"
            "<i>Masalan: <code>2</code>, <code>5</code>, <code>15</code> (Min: $0.50 — Max: $5,000. Yakuniy balans haqiqiy kelgan TON miqdoriga qarab hisoblanadi.)</i>"
        ),
        "ru": (
            "<b>Депозит TON — Введите сумму</b>\n\n"
            "💵 <b>Текущий курс:</b> <code>1 USD ≈ {rate:,} сум</code>\n\n"
            "На какую сумму в <b>$ USD</b> (в TON) вы планируете пополнение?\n"
            "<i>Например: <code>2</code>, <code>5</code>, <code>15</code> (Мин: $0.50 — Макс: $5,000. Итог начисляется по фактически зачисленным TON.)</i>"
        ),
        "en": (
            "<b>TON Deposit — Enter Exact Amount</b>\n\n"
            "💵 <b>Live Rate:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "How much in <b>$ USD</b> equivalent (paid in TON) are you depositing?\n"
            "<i>Example: <code>2</code>, <code>5</code>, <code>15</code> (Min: $0.50 — Max: $5,000. Final UZS credit is calculated from actual credited TON.)</i>"
        ),
        "es": (
            "<b>Depósito TON — Ingresa el monto</b>\n\n"
            "💵 <b>Tasa actual:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "¿Cuánto equivalente en <b>$ USD</b> (en TON) vas a depositar?\n"
            "<i>Ejemplo: <code>2</code>, <code>5</code>, <code>15</code> (Mín: $0.50 — Máx: $5,000)</i>"
        ),
        "tr": (
            "<b>TON Yatırımı — Tutarı Girin</b>\n\n"
            "💵 <b>Güncel Kur:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "TON olarak kaç <b>$ USD</b> karşılığı yatırım yapacaksınız?\n"
            "<i>Örnek: <code>2</code>, <code>5</code>, <code>15</code> (Min: $0.50 — Maks: $5,000)</i>"
        )
    },
    "crypto_ask_amount_cryptobot": {
        "uz": (
            "<b>@CryptoBot — Summani Kiriting</b>\n\n"
            "💵 <b>Joriy kurs:</b> <code>1 USD ≈ {rate:,} so'm</code>\n\n"
            "Hisobingizni necha <b>$ USD</b> ga to'ldirmoqchisiz?\n"
            "<i>Masalan: <code>1.5</code>, <code>5</code>, <code>20</code> (Keyin @CryptoBot da USDT, TON, BTC, ETH, TRX, BNB bilan to'laysiz. Min: $0.50)</i>"
        ),
        "ru": (
            "<b>@CryptoBot — Введите сумму</b>\n\n"
            "💵 <b>Текущий курс:</b> <code>1 USD ≈ {rate:,} сум</code>\n\n"
            "На какую сумму в <b>$ USD</b> хотите пополнить баланс?\n"
            "<i>Например: <code>1.5</code>, <code>5</code>, <code>20</code> (В @CryptoBot можно оплатить USDT, TON, BTC, ETH, TRX, BNB. Мин: $0.50)</i>"
        ),
        "en": (
            "<b>@CryptoBot — Enter Exact Amount</b>\n\n"
            "💵 <b>Live Rate:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "How much <b>$ USD</b> would you like to deposit?\n"
            "<i>Example: <code>1.5</code>, <code>5</code>, <code>20</code> (Pay inside @CryptoBot with USDT, TON, BTC, ETH, TRX, BNB. Min: $0.50)</i>"
        ),
        "es": (
            "<b>@CryptoBot — Ingresa el monto</b>\n\n"
            "💵 <b>Tasa actual:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "¿Cuánto en <b>$ USD</b> deseas depositar?\n"
            "<i>Ejemplo: <code>1.5</code>, <code>5</code>, <code>20</code> (Paga con USDT, TON, BTC, ETH, TRX, BNB. Mín: $0.50)</i>"
        ),
        "tr": (
            "<b>@CryptoBot — Tutarı Girin</b>\n\n"
            "💵 <b>Güncel Kur:</b> <code>1 USD ≈ {rate:,} UZS</code>\n\n"
            "Bakiyenize kaç <b>$ USD</b> yüklemek istersiniz?\n"
            "<i>Örnek: <code>1.5</code>, <code>5</code>, <code>20</code> (USDT, TON, BTC, ETH, TRX, BNB desteklenir. Min: $0.50)</i>"
        )
    },
    "crypto_invalid_amount": {
        "uz": "Iltimos, faqat to'g'ri raqam kiriting (masalan: <code>2.5</code> yoki <code>10</code>).",
        "ru": "Пожалуйста, введите корректное число (например: <code>2.5</code> или <code>10</code>).",
        "en": "Please enter a valid number (for example: <code>2.5</code> or <code>10</code>).",
        "es": "Por favor, ingresa un número válido (por ejemplo: <code>2.5</code> o <code>10</code>).",
        "tr": "Lütfen geçerli bir sayı girin (örneğin: <code>2.5</code> veya <code>10</code>)."
    },
    "crypto_amount_range_err": {
        "uz": "Summa <b>$0.50</b> dan <b>$5,000</b> gacha bo'lishi kerak.",
        "ru": "Сумма должна быть от <b>$0.50</b> до <b>$5,000</b>.",
        "en": "Amount must be between <b>$0.50</b> and <b>$5,000</b>.",
        "es": "El monto debe estar entre <b>$0.50</b> y <b>$5,000</b>.",
        "tr": "Tutar <b>$0.50</b> ile <b>$5,000</b> arasında olmalıdır."
    },
    "crypto_not_configured": {
        "uz": "Ushbu to'lov usuli hozircha .env orqali sozlanmagan.",
        "ru": "Этот способ оплаты пока не настроен в .env.",
        "en": "This payment method is not configured in .env yet.",
        "es": "Este método de pago aún no está configurado en .env.",
        "tr": "Bu ödeme yöntemi henüz .env üzerinden yapılandırılmamış."
    },
    "crypto_order_card_binance": {
        "uz": (
            "<b>Binance Pay / USDT Buyurtma #{order_id}</b>\n\n"
            "💵 <b>Summa:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} so'm</code>)\n\n"
            "<b>Quyidagi manzillardan biriga to'lov qiling:</b>\n"
            "{addr_block}\n\n"
            "<i>To'lagach, Binance Pay <b>Order ID</b> yoki blockchain <b>TxID</b> ni tekshirish uchun pastdagi tugmani bosing.</i>"
        ),
        "ru": (
            "<b>Ордер Binance Pay / USDT #{order_id}</b>\n\n"
            "💵 <b>Сумма:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} сум</code>)\n\n"
            "<b>Переведите средства на один из реквизитов:</b>\n"
            "{addr_block}\n\n"
            "<i>После оплаты нажмите кнопку ниже и отправьте Binance <b>Order ID</b> или <b>TxID</b>.</i>"
        ),
        "en": (
            "<b>Binance Pay / USDT Order #{order_id}</b>\n\n"
            "💵 <b>Amount:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n\n"
            "<b>Send your payment to one of these addresses:</b>\n"
            "{addr_block}\n\n"
            "<i>Once sent, click below to verify with your Binance Pay <b>Order ID</b> or blockchain <b>TxID</b>.</i>"
        ),
        "es": (
            "<b>Orden Binance Pay / USDT #{order_id}</b>\n\n"
            "💵 <b>Monto:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n\n"
            "<b>Envía tu pago a una de estas direcciones:</b>\n"
            "{addr_block}\n\n"
            "<i>Después de pagar, pulsa abajo para verificar con tu <b>Order ID</b> o <b>TxID</b>.</i>"
        ),
        "tr": (
            "<b>Binance Pay / USDT Sipariş #{order_id}</b>\n\n"
            "💵 <b>Tutar:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n\n"
            "<b>Ödemeyi aşağıdaki adreslerden birine gönderin:</b>\n"
            "{addr_block}\n\n"
            "<i>Ödemeden sonra Binance <b>Order ID</b> veya <b>TxID</b> ile doğrulamak için aşağıya dokunun.</i>"
        )
    },
    "crypto_order_card_ton": {
        "uz": (
            "<b>TON Depozit Buyurtma #{order_id}</b>\n\n"
            "💵 <b>Summa:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} so'm</code>)\n\n"
            "<b>Quyidagi TON rekvizitlariga o'tkazing:</b>\n"
            "{addr_block}\n\n"
            "<i>To'lov tasdiqlangach, pastdagi tugma orqali <b>TxID / TxHash</b> ni yuboring.</i>"
        ),
        "ru": (
            "<b>Ордер TON #{order_id}</b>\n\n"
            "💵 <b>Сумма:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} сум</code>)\n\n"
            "<b>Отправьте TON по следующим реквизитам:</b>\n"
            "{addr_block}\n\n"
            "<i>После отправки нажмите кнопку ниже и укажите <b>TxID / TxHash</b>.</i>"
        ),
        "en": (
            "<b>TON Deposit Order #{order_id}</b>\n\n"
            "💵 <b>Amount:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n\n"
            "<b>Send TON using the details below:</b>\n"
            "{addr_block}\n\n"
            "<i>Once sent, click below to verify using your <b>TxID / TxHash</b>.</i>"
        ),
        "es": (
            "<b>Orden TON #{order_id}</b>\n\n"
            "💵 <b>Monto:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n\n"
            "<b>Envía TON a los siguientes datos:</b>\n"
            "{addr_block}\n\n"
            "<i>Luego pulsa abajo para verificar con tu <b>TxID / TxHash</b>.</i>"
        ),
        "tr": (
            "<b>TON Yatırım Siparişi #{order_id}</b>\n\n"
            "💵 <b>Tutar:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n\n"
            "<b>Aşağıdaki TON bilgilerine gönderim yapın:</b>\n"
            "{addr_block}\n\n"
            "<i>Gönderdikten sonra <b>TxID / TxHash</b> ile doğrulamak için aşağıya dokunun.</i>"
        )
    },
    "crypto_order_card_cryptobot": {
        "uz": (
            "<b>@CryptoBot Buyurtma #{order_id}</b>\n\n"
            "💵 <b>Summa:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} so'm</code>)\n"
            "🧾 <b>Invoice:</b> <code>#{invoice_id}</code>\n"
            "🪙 <b>Qo'llab-quvvatlanadigan koinlar:</b> <code>USDT, TON, BTC, ETH, TRX, BNB, LTC, USDC</code>\n\n"
            "<i>1-tugma orqali to'lang, so'ngra 2-tugma bilan tekshiring (yoki bekor qiling).</i>"
        ),
        "ru": (
            "<b>Ордер @CryptoBot #{order_id}</b>\n\n"
            "💵 <b>Сумма:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} сум</code>)\n"
            "🧾 <b>Счет:</b> <code>#{invoice_id}</code>\n"
            "🪙 <b>Доступные монеты:</b> <code>USDT, TON, BTC, ETH, TRX, BNB, LTC, USDC</code>\n\n"
            "<i>Оплатите по 1-й кнопке и нажмите 2-ю для проверки (либо отмените ордер).</i>"
        ),
        "en": (
            "<b>@CryptoBot Order #{order_id}</b>\n\n"
            "💵 <b>Amount:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n"
            "🧾 <b>Invoice:</b> <code>#{invoice_id}</code>\n"
            "🪙 <b>Accepted Coins:</b> <code>USDT, TON, BTC, ETH, TRX, BNB, LTC, USDC</code>\n\n"
            "<i>Pay with button 1, then click button 2 to verify (or cancel order).</i>"
        ),
        "es": (
            "<b>Orden @CryptoBot #{order_id}</b>\n\n"
            "💵 <b>Monto:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n"
            "🧾 <b>Factura:</b> <code>#{invoice_id}</code>\n"
            "🪙 <b>Monedas aceptadas:</b> <code>USDT, TON, BTC, ETH, TRX, BNB, LTC, USDC</code>\n\n"
            "<i>Paga con el botón 1 y verifica con el botón 2 (o cancela la orden).</i>"
        ),
        "tr": (
            "<b>@CryptoBot Sipariş #{order_id}</b>\n\n"
            "💵 <b>Tutar:</b> <code>${amount_usd} USD</code> (≈ <code>{amount_uzs:,} UZS</code>)\n"
            "🧾 <b>Fatura:</b> <code>#{invoice_id}</code>\n"
            "🪙 <b>Desteklenen Coinler:</b> <code>USDT, TON, BTC, ETH, TRX, BNB, LTC, USDC</code>\n\n"
            "<i>1. buton ile ödeyip 2. butonla doğrulayın (veya iptal edin).</i>"
        )
    },
    "crypto_ask_txid": {
        "uz": (
            "<b>Buyurtma #{order_id} — Order ID / TxID yuboring</b>\n\n"
            "To'lov chekidagi <b>Binance Pay Order ID</b> (masalan: <code>338192045678123456</code>) yoki blockchain <b>TxID / TxHash</b> ni shu chatga yozib yuboring.\n\n"
            "<i>Tizim haqiqiy tushgan summani tekshirib darhol balansingizga qo'shadi.</i>"
        ),
        "ru": (
            "<b>Ордер #{order_id} — Отправьте Order ID / TxID</b>\n\n"
            "Отправьте в чат <b>Binance Pay Order ID</b> (например: <code>338192045678123456</code>) или <b>TxID / TxHash</b> транзакции.\n\n"
            "<i>Система проверит фактически полученную сумму и мгновенно зачислит ее на баланс.</i>"
        ),
        "en": (
            "<b>Order #{order_id} — Send Order ID / TxID</b>\n\n"
            "Reply with your <b>Binance Pay Order ID</b> (e.g., <code>338192045678123456</code>) or blockchain <b>TxID / TxHash</b>.\n\n"
            "<i>We will verify the exact received amount and credit your balance immediately.</i>"
        ),
        "es": (
            "<b>Orden #{order_id} — Envía Order ID / TxID</b>\n\n"
            "Responde con tu <b>Binance Pay Order ID</b> o <b>TxID / TxHash</b>.\n\n"
            "<i>Verificaremos el monto exacto recibido y lo acreditaremos al instante.</i>"
        ),
        "tr": (
            "<b>Sipariş #{order_id} — Order ID / TxID Gönderin</b>\n\n"
            "Lütfen <b>Binance Pay Order ID</b> veya blockchain <b>TxID / TxHash</b> bilgisini bu sohbete gönderin.\n\n"
            "<i>Gelen tutar doğrulanıp bakiyenize anında eklenecektir.</i>"
        )
    },
    "crypto_order_cancelled": {
        "uz": "<b>Buyurtma #{order_id} bekor qilindi.</b>\n\nIstagan vaqtda hamyondan yangi buyurtma ochishingiz mumkin.",
        "ru": "<b>Ордер #{order_id} отменен.</b>\n\nВы можете в любой момент открыть новый ордер в кошельке.",
        "en": "<b>Order #{order_id} has been cancelled.</b>\n\nYou can open a new order anytime from your wallet.",
        "es": "<b>La orden #{order_id} ha sido cancelada.</b>\n\nPuedes abrir una nueva orden cuando quieras desde tu billetera.",
        "tr": "<b>Sipariş #{order_id} iptal edildi.</b>\n\nCüzdanınızdan istediğiniz zaman yeni sipariş açabilirsiniz."
    },
    "crypto_order_not_found": {
        "uz": "Faol buyurtma topilmadi yoki allaqachon yakunlangan.",
        "ru": "Активный ордер не найден или уже завершен.",
        "en": "Active order not found or already closed.",
        "es": "No se encontró ninguna orden activa o ya fue cerrada.",
        "tr": "Aktif sipariş bulunamadı veya zaten kapatılmış."
    },
    "crypto_checking_tx": {
        "uz": "<b>Tranzaksiya tekshirilmoqda (Binance / Blockchain)...</b>",
        "ru": "<b>Проверка транзакции (Binance / Blockchain)...</b>",
        "en": "<b>Verifying transaction (Binance / Blockchain)...</b>",
        "es": "<b>Verificando transacción (Binance / Blockchain)...</b>",
        "tr": "<b>İşlem doğrulanıyor (Binance / Blockchain)...</b>"
    },
    "crypto_tx_failed": {
        "uz": "<b>To'lov tasdiqlanmadi:</b>\n{error}\n\nQayta urinish uchun buyurtmadan Order ID / TxID tugmasini bosing.",
        "ru": "<b>Платеж не подтвержден:</b>\n{error}\n\nНажмите кнопку проверки Order ID / TxID в ордере еще раз.",
        "en": "<b>Payment verification failed:</b>\n{error}\n\nRe-open your order in Wallet to try again or cancel it.",
        "es": "<b>Error al verificar el pago:</b>\n{error}\n\nVuelve a tu orden en la billetera para reintentar o cancelar.",
        "tr": "<b>Ödeme doğrulanamadı:</b>\n{error}\n\nTekrar denemek veya iptal etmek için cüzdanınızdaki siparişi açın."
    },
    "crypto_tx_success": {
        "uz": (
            "<b>KRIPTO TO'LOV TASDIQLANDI! (Buyurtma #{order_id})</b>\n\n"
            "🌐 <b>Tarmoq:</b> <code>{network}</code>\n"
            "🪙 <b>Summa:</b> <code>{amount_crypto} {asset}</code> (~${usd_value})\n"
            "💰 <b>Hisobga qo'shildi:</b> <code>+{amount_uzs:,} so'm</code>\n"
            "⚖️ <b>Yangi balans:</b> <code>{new_balance:,} so'm</code>\n"
            "🧾 <b>TxID:</b> <code>{tx_short}</code>"
        ),
        "ru": (
            "<b>КРИПТО-ПЛАТЕЖ ПОДТВЕРЖДЕН! (Ордер #{order_id})</b>\n\n"
            "🌐 <b>Сеть:</b> <code>{network}</code>\n"
            "🪙 <b>Сумма:</b> <code>{amount_crypto} {asset}</code> (~${usd_value})\n"
            "💰 <b>Зачислено:</b> <code>+{amount_uzs:,} сум</code>\n"
            "⚖️ <b>Новый баланс:</b> <code>{new_balance:,} сум</code>\n"
            "🧾 <b>TxID:</b> <code>{tx_short}</code>"
        ),
        "en": (
            "<b>CRYPTO PAYMENT CONFIRMED! (Order #{order_id})</b>\n\n"
            "🌐 <b>Network:</b> <code>{network}</code>\n"
            "🪙 <b>Amount:</b> <code>{amount_crypto} {asset}</code> (~${usd_value})\n"
            "💰 <b>Credited:</b> <code>+{amount_uzs:,} UZS</code>\n"
            "⚖️ <b>New Balance:</b> <code>{new_balance:,} UZS</code>\n"
            "🧾 <b>TxID:</b> <code>{tx_short}</code>"
        ),
        "es": (
            "<b>¡PAGO CRYPTO CONFIRMADO! (Orden #{order_id})</b>\n\n"
            "🌐 <b>Red:</b> <code>{network}</code>\n"
            "🪙 <b>Monto:</b> <code>{amount_crypto} {asset}</code> (~${usd_value})\n"
            "💰 <b>Acreditado:</b> <code>+{amount_uzs:,} UZS</code>\n"
            "⚖️ <b>Nuevo saldo:</b> <code>{new_balance:,} UZS</code>\n"
            "🧾 <b>TxID:</b> <code>{tx_short}</code>"
        ),
        "tr": (
            "<b>KRİPTO ÖDEME ONAYLANDI! (Sipariş #{order_id})</b>\n\n"
            "🌐 <b>Ağ:</b> <code>{network}</code>\n"
            "🪙 <b>Tutar:</b> <code>{amount_crypto} {asset}</code> (~${usd_value})\n"
            "💰 <b>Eklenen:</b> <code>+{amount_uzs:,} UZS</code>\n"
            "⚖️ <b>Yeni Bakiye:</b> <code>{new_balance:,} UZS</code>\n"
            "🧾 <b>TxID:</b> <code>{tx_short}</code>"
        )
    },
    "cryptobot_invoice_err": {
        "uz": "@CryptoBot cheki yaratib bo'lmadi: {error}",
        "ru": "Не удалось создать счет @CryptoBot: {error}",
        "en": "Failed to create @CryptoBot invoice: {error}",
        "es": "No se pudo crear la factura en @CryptoBot: {error}",
        "tr": "@CryptoBot faturası oluşturulamadı: {error}"
    },
    "cryptobot_not_paid_yet": {
        "uz": "⏳ To'lov hali yakunlanmagan! @CryptoBot orqali to'lab, qayta bosing.",
        "ru": "⏳ Оплата еще не завершена! Оплатите в @CryptoBot и нажмите снова.",
        "en": "⏳ Payment not completed yet! Please pay in @CryptoBot and check again.",
        "es": "⏳ ¡El pago aún no está completo! Paga en @CryptoBot y vuelve a verificar.",
        "tr": "⏳ Ödeme henüz tamamlanmadı! @CryptoBot üzerinden ödeyip tekrar deneyin."
    },
    "cryptobot_already_credited": {
        "uz": "✅ Ushbu @CryptoBot to'lovi allaqachon hisobingizga o'tkazilgan!",
        "ru": "✅ Этот платеж @CryptoBot уже зачислен на ваш баланс!",
        "en": "✅ This @CryptoBot payment has already been credited!",
        "es": "✅ ¡Este pago de @CryptoBot ya fue acreditado!",
        "tr": "✅ Bu @CryptoBot ödemesi zaten hesabınıza eklendi!"
    },
    "cryptobot_paid_success": {
        "uz": (
            "<b>@CryptoBot TO'LOVI TASDIQLANDI!</b>\n\n"
            "🤖 <b>Tizim:</b> @CryptoBot ({asset})\n"
            "💵 <b>Summa:</b> <code>{amount_crypto} {asset}</code>\n"
            "💰 <b>Hisobingizga qo'shildi:</b> <code>+{amount_uzs:,} so'm</code>\n"
            "🧾 <b>Invoice ID:</b> <code>#{invoice_id}</code>"
        ),
        "ru": (
            "<b>ОПЛАТА @CryptoBot ПОДТВЕРЖДЕНА!</b>\n\n"
            "🤖 <b>Система:</b> @CryptoBot ({asset})\n"
            "💵 <b>Сумма:</b> <code>{amount_crypto} {asset}</code>\n"
            "💰 <b>Зачислено:</b> <code>+{amount_uzs:,} сум</code>\n"
            "🧾 <b>Invoice ID:</b> <code>#{invoice_id}</code>"
        ),
        "en": (
            "<b>@CryptoBot PAYMENT CONFIRMED!</b>\n\n"
            "🤖 <b>Method:</b> @CryptoBot ({asset})\n"
            "💵 <b>Amount:</b> <code>{amount_crypto} {asset}</code>\n"
            "💰 <b>Credited:</b> <code>+{amount_uzs:,} UZS</code>\n"
            "🧾 <b>Invoice ID:</b> <code>#{invoice_id}</code>"
        ),
        "es": (
            "<b>¡PAGO DE @CryptoBot CONFIRMADO!</b>\n\n"
            "🤖 <b>Método:</b> @CryptoBot ({asset})\n"
            "💵 <b>Monto:</b> <code>{amount_crypto} {asset}</code>\n"
            "💰 <b>Acreditado:</b> <code>+{amount_uzs:,} UZS</code>\n"
            "🧾 <b>Invoice ID:</b> <code>#{invoice_id}</code>"
        ),
        "tr": (
            "<b>@CryptoBot ÖDEMESİ ONAYLANDI!</b>\n\n"
            "🤖 <b>Yöntem:</b> @CryptoBot ({asset})\n"
            "💵 <b>Tutar:</b> <code>{amount_crypto} {asset}</code>\n"
            "💰 <b>Eklenen:</b> <code>+{amount_uzs:,} UZS</code>\n"
            "🧾 <b>Fatura ID:</b> <code>#{invoice_id}</code>"
        )
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
        "uz": "<b>Mono Deck Studio Super To'plamlar (Bundles)</b>\n\nBir nechta premium xizmatlarni birgalikda 40% gacha chegirma bilan xarid qiling:",
        "ru": "<b>Супер Наборы Mono Deck Studio (Bundles)</b>\n\nПриобретайте премиум инструменты вместе со скидкой до 40%:",
        "en": "<b>Mono Deck Studio Super Bundles</b>\n\nGet all essential creator tools bundled together with up to 40% savings:",
        "es": "<b>Súper Paquetes de Mono Deck Studio (Bundles)</b>\n\nObtén herramientas premium combinadas con hasta un 40% de descuento:",
        "tr": "<b>Mono Deck Studio Süper Paketleri (Bundles)</b>\n\nEn iyi içerik üretici araçlarını %40'a varan indirimle paket olarak alın:"
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


# ==================== COMPREHENSIVE MULTILINGUAL ADDITIONS ====================
EXTRA_I18N = {
    # Marketplace Category Buttons
    "btn_mkt_bundles": {"uz": "Super To'plamlar (Bundles)", "ru": "Супер Наборы (Bundles)", "en": "Super Bundles", "es": "Súper Paquetes", "tr": "Süper Paketler"},
    "btn_mkt_advisor": {"uz": "Aiko AI Maslahatchi", "ru": "Aiko AI Советник", "en": "Aiko AI Advisor", "es": "Asesor Aiko AI", "tr": "Aiko AI Danışmanı"},
    "btn_cat_ai": {"uz": "AI & LLM Modellar", "ru": "AI & LLM Модели", "en": "AI & LLM Models", "es": "Modelos AI & LLM", "tr": "AI & LLM Modelleri"},
    "btn_cat_design": {"uz": "Video & Ovoz Dizayn", "ru": "Видео и Звуковой Дизайн", "en": "Video & Audio Design", "es": "Diseño de Video y Audio", "tr": "Video & Ses Tasarımı"},
    "btn_cat_streaming": {"uz": "Kino & Musiqa Striming", "ru": "Кино и Музыка Стриминг", "en": "Movies & Music Streaming", "es": "Streaming de Películas y Música", "tr": "Film ve Müzik Yayını"},
    "btn_cat_vpn": {"uz": "VPN & Xavfsiz Tarmoq", "ru": "VPN и Безопасная Сеть", "en": "VPN & Security", "es": "VPN y Red Segura", "tr": "VPN ve Güvenli Ağ"},
    "btn_cat_office": {"uz": "Ofis & Ta'lim Dasturlari", "ru": "Офис и Обучение", "en": "Office & Education", "es": "Oficina y Educación", "tr": "Ofis ve Eğitim"},
    "btn_cat_dev": {"uz": "Developer Vositalari", "ru": "Инструменты Разработчика", "en": "Developer Tools", "es": "Herramientas de Desarrollador", "tr": "Geliştirici Araçları"},

    # Marketplace Service Buttons
    "btn_mkt_claudecode": {"uz": "Claude Code / Codex Tekin (15k UZS)", "ru": "Claude Code / Codex Бесплатно (15k UZS)", "en": "Claude Code / Codex Free (15k UZS)", "es": "Claude Code / Codex Gratis (15k UZS)", "tr": "Claude Code / Codex Ücretsiz (15k UZS)"},
    "btn_mkt_proxy": {"uz": "Private Proxy (18k UZS)", "ru": "Приватный Прокси (18k UZS)", "en": "Private Proxy (18k UZS)", "es": "Proxy Privado (18k UZS)", "tr": "Özel Proxy (18k UZS)"},
    "btn_mkt_vip": {"uz": "VIP Cheksiz Pro (69k UZS)", "ru": "VIP Безлимитный Pro (69k UZS)", "en": "VIP Unlimited Pro (69k UZS)", "es": "VIP Ilimitado Pro (69k UZS)", "tr": "VIP Sınırsız Pro (69k UZS)"},
    "btn_mkt_autostream": {"uz": "Autostream Cloud (2.5k/soat)", "ru": "Автострим Облако (2.5k/час)", "en": "Autostream Cloud (2.5k/hr)", "es": "Autostream Cloud (2.5k/h)", "tr": "Autostream Bulut (2.5k/saat)"},
    "btn_mkt_prompts": {"uz": "500+ Prompt Pack (25k UZS)", "ru": "500+ Промпт Пак (25k UZS)", "en": "500+ Prompt Pack (25k UZS)", "es": "Pack 500+ Prompts (25k UZS)", "tr": "500+ Prompt Paketi (25k UZS)"},
    "btn_mkt_openrouter": {"uz": "OpenRouter API (25k UZS)", "ru": "OpenRouter API (25k UZS)", "en": "OpenRouter API (25k UZS)", "es": "OpenRouter API (25k UZS)", "tr": "OpenRouter API (25k UZS)"},
    "btn_mkt_gemini": {"uz": "Gemini API (25k UZS)", "ru": "Gemini API (25k UZS)", "en": "Gemini API (25k UZS)", "es": "Gemini API (25k UZS)", "tr": "Gemini API (25k UZS)"},
    "btn_mkt_groq": {"uz": "Groq Cloud API (18k UZS)", "ru": "Groq Cloud API (18k UZS)", "en": "Groq Cloud API (18k UZS)", "es": "Groq Cloud API (18k UZS)", "tr": "Groq Cloud API (18k UZS)"},
    "btn_mkt_flux": {"uz": "Flux.1 AI Rasm (18k UZS)", "ru": "Flux.1 AI Картинки (18k UZS)", "en": "Flux.1 AI Images (18k UZS)", "es": "Imágenes Flux.1 AI (18k UZS)", "tr": "Flux.1 AI Görsel (18k UZS)"},
    "btn_mkt_clipper": {"uz": "Shorts Kesish (5k UZS)", "ru": "Нарезка Shorts (5k UZS)", "en": "Shorts Clipper (5k UZS)", "es": "Clipper de Shorts (5k UZS)", "tr": "Shorts Kırpıcı (5k UZS)"},
    "btn_mkt_unikal": {"uz": "Video Unikal (500 UZS)", "ru": "Уникализация Видео (500 UZS)", "en": "Video Uniquifier (500 UZS)", "es": "Unificador de Video (500 UZS)", "tr": "Video Özgünleştirici (500 UZS)"},
    "btn_mkt_deeplink": {"uz": "DeepLink & QR (1k UZS)", "ru": "DeepLink и QR (1k UZS)", "en": "DeepLink & QR (1k UZS)", "es": "DeepLink y QR (1k UZS)", "tr": "DeepLink ve QR (1k UZS)"},
    "btn_mkt_referral": {"uz": "Referal & Keshbek (10%)", "ru": "Реферал и Кэшбэк (10%)", "en": "Referral & Cashback (10%)", "es": "Referidos y Cashback (10%)", "tr": "Referans ve Geri Ödeme (%10)"},
    "btn_mkt_like": {"uz": "Layk (500 UZS)", "ru": "Лайк (500 UZS)", "en": "Likes (500 UZS)", "es": "Me gusta (500 UZS)", "tr": "Beğeni (500 UZS)"},
    "btn_mkt_sub": {"uz": "Obuna (1,000 UZS)", "ru": "Подписка (1,000 UZS)", "en": "Subscribe (1,000 UZS)", "es": "Suscripción (1,000 UZS)", "tr": "Abone (1,000 UZS)"},
    "btn_mkt_comment": {"uz": "Izoh (300 UZS)", "ru": "Комментарий (300 UZS)", "en": "Comment (300 UZS)", "es": "Comentario (300 UZS)", "tr": "Yorum (300 UZS)"},
    "btn_top_up_balance": {"uz": "Balansni to'ldirish", "ru": "Пополнить баланс", "en": "Top-up Balance", "es": "Recargar Saldo", "tr": "Bakiye Yükle"},
    "btn_my_orders": {"uz": "Mening xaridlarim", "ru": "Мои покупки", "en": "My Purchases", "es": "Mis compras", "tr": "Satın Alımlarım"},
    "btn_mkt_cancel": {"uz": "Bekor qilish", "ru": "Отмена", "en": "Cancel", "es": "Cancelar", "tr": "İptal"},

    # Action Keyboards
    "btn_recent_videos": {"uz": "So'nggi videolar", "ru": "Последние видео", "en": "Recent Videos", "es": "Videos recientes", "tr": "Son Videolar"},
    "btn_popular_videos": {"uz": "Ommabop", "ru": "Популярные", "en": "Popular Videos", "es": "Videos populares", "tr": "Popüler Videolar"},
    "btn_growth": {"uz": "O'sish", "ru": "Рост", "en": "Growth", "es": "Crecimiento", "tr": "Büyüme"},
    "btn_report": {"uz": "To'liq hisobot", "ru": "Полный отчёт", "en": "Full Report", "es": "Informe completo", "tr": "Tam Rapor"},
    "btn_earnings": {"uz": "Daromad", "ru": "Доход", "en": "Earnings", "es": "Ingresos", "tr": "Kazanç"},
    "btn_track_channel": {"uz": "Kuzatishga olish", "ru": "Отслеживать", "en": "Track Channel", "es": "Seguir Canal", "tr": "Kanalı Takip Et"},
    "btn_refresh": {"uz": "Yangilash", "ru": "Обновить", "en": "Refresh", "es": "Actualizar", "tr": "Yenile"},
    "btn_download_video": {"uz": "Videoni Yuklab Olish", "ru": "Скачать видео", "en": "Download Video", "es": "Descargar video", "tr": "Videoyu İndir"},

    # Games Keyboards
    "btn_games_menu": {"uz": "O'yinlar menyusi", "ru": "Меню игр", "en": "Games Menu", "es": "Menú de Juegos", "tr": "Oyun Menüsü"},
    "btn_free_spin": {"uz": "Bepul aylantirish (Spin)", "ru": "Бесплатное вращение", "en": "Free Spin", "es": "Giro Gratis", "tr": "Ücretsiz Çevirme"},
    "btn_paid_spin": {"uz": "Pullik aylantirish (3,000 so'm)", "ru": "Платное вращение (3,000 сум)", "en": "Paid Spin (3,000 UZS)", "es": "Giro de pago (3,000 UZS)", "tr": "Ücretli Çevirme (3,000 UZS)"},
    "btn_spin_again": {"uz": "Yana aylantirish (3,000 so'm)", "ru": "Крутить снова (3,000 сум)", "en": "Spin Again (3,000 UZS)", "es": "Girar de nuevo (3,000 UZS)", "tr": "Tekrar Çevir (3,000 UZS)"},
    "btn_buy_tickets_1": {"uz": "1 ta bilet (3,000 so'm)", "ru": "1 билет (3,000 сум)", "en": "1 Ticket (3,000 UZS)", "es": "1 Boleto (3,000 UZS)", "tr": "1 Bilet (3,000 UZS)"},
    "btn_buy_tickets_5": {"uz": "5 ta bilet (15,000 so'm)", "ru": "5 билетов (15,000 сум)", "en": "5 Tickets (15,000 UZS)", "es": "5 Boletos (15,000 UZS)", "tr": "5 Bilet (15,000 UZS)"},
    "btn_pick_other_box": {"uz": "Boshqa keys tanlash", "ru": "Выбрать другой кейс", "en": "Choose Another Case", "es": "Elegir otro caso", "tr": "Başka Kasa Seç"},
    "btn_normal_box": {"uz": "Oddiy Quti (6,000 so'm)", "ru": "Обычный кейс (6,000 сум)", "en": "Regular Case (6,000 UZS)", "es": "Caja regular (6,000 UZS)", "tr": "Standart Kasa (6,000 UZS)"},
    "btn_share_contact": {"uz": "📱 Telefon raqamimni ulashish", "ru": "📱 Поделиться номером телефона", "en": "📱 Share My Phone Number", "es": "📱 Compartir mi número", "tr": "📱 Telefon Numaramı Paylaş"},
    "btn_custom_amount": {"uz": "Boshqa summa kiritish", "ru": "Ввести другую сумму", "en": "Enter Custom Amount", "es": "Ingresar otra cantidad", "tr": "Başka Miktar Gir"},
    "btn_wallet_menu": {"uz": "Balans Menyusi", "ru": "Меню баланса", "en": "Wallet Menu", "es": "Menú de Saldo", "tr": "Bakiye Menüsü"},

    # Quantities
    "btn_test_qty_1": {"uz": "1 ta (Test)", "ru": "1 шт (Тест)", "en": "1 item (Test)", "es": "1 ud (Prueba)", "tr": "1 adet (Test)"},
    "btn_test_qty_3": {"uz": "3 ta", "ru": "3 шт", "en": "3 items", "es": "3 uds", "tr": "3 adet"},
    "btn_test_qty_5": {"uz": "5 ta", "ru": "5 шт", "en": "5 items", "es": "5 uds", "tr": "5 adet"},
    "btn_test_qty_10": {"uz": "10 ta", "ru": "10 шт", "en": "10 items", "es": "10 uds", "tr": "10 adet"},
    "btn_test_qty_25": {"uz": "25 ta", "ru": "25 шт", "en": "25 items", "es": "25 uds", "tr": "25 adet"},
    "btn_test_qty_50": {"uz": "50 ta", "ru": "50 шт", "en": "50 items", "es": "50 uds", "tr": "50 adet"},
    "btn_test_qty_100": {"uz": "100 ta", "ru": "100 шт", "en": "100 items", "es": "100 uds", "tr": "100 adet"},

    # Menu texts
    "tariffs_title": {
        "uz": "👑 <b>Mono Deck Studio — Foydalanuvchi Darajalari & Tariflar</b>\n\n{status_line}\n\n• Sharti: {target_ch} kanaliga a'zolik + Telefon raqam ulashilgan\n• Kunlik limit: 15 ta bepul so'rov (video yuklash, audio ajratish)\n• Do'kon: Barcha mahsulot va API kalitlarni sotib olish\n• O'yinlar: Lucky Wheel (kunlik bepul) va Mystery Box\n\n🛡 <b>2. TO'LIQ VERIFIED (FULL 3D BIOMETRIK / BEPUL)</b>\n• Sharti: 3D Face ID skaneri dan o'tish\n• Kunlik limit: 25 ta kengaytirilgan so'rov\n• Ishonchli nishon: Rasmiy tasdiqlangan foydalanuvchi\n\n👑 <b>3. MONO DECK STUDIO VIP STATUS ({vip_price} UZS / OY)</b>\n• Narxi: {vip_price} so'm / 30 kun (yoki {vip_stars} ⭐ Stars)\n• Cheksiz limitlar: Kunlik barcha amallar cheklovlarsiz!\n• 24/7 Ustuvor navbat: Priority Worker va Streamer kuchi\n• Keshbek: Har bir xariddan 10% keshbek\n━━━━━━━━━━━━━━━━━━━━━\n👇 <i>Kerakli amalni tanlang:</i>",
        "ru": "👑 <b>Mono Deck Studio — Уровни пользователей и Тарифы</b>\n\n{status_line}\n\n• Условие: подписка на канал {target_ch} + привязанный номер\n• Дневной лимит: 15 бесплатных запросов (скачивание, аудио)\n• Магазин: Покупка всех сервисов и API ключей\n• Игры: Колесо фортуны и Mystery Box\n\n🛡 <b>2. ПОЛНАЯ ВЕРИФИКАЦИЯ (3D BIOMETRICS / БЕСПЛАТНО)</b>\n• Условие: Прохождение 3D Face ID сканера\n• Дневной лимит: 25 расширенных запросов\n• Значок доверия: Официально подтвержденный пользователь\n\n👑 <b>3. MONO DECK STUDIO VIP СТАТУС ({vip_price} UZS / МЕСЯЦ)</b>\n• Цена: {vip_price} сум / 30 дней (или {vip_stars} ⭐ Stars)\n• Безлимит: Все функции без ограничений!\n• 24/7 Приоритетная очередь обработки\n• Кэшбэк: 10% с каждой покупки\n━━━━━━━━━━━━━━━━━━━━━\n👇 <i>Выберите действие:</i>",
        "en": "👑 <b>Mono Deck Studio — User Tiers & Plans</b>\n\n{status_line}\n\n• Condition: Subscribed to {target_ch} + verified phone\n• Daily limit: 15 free requests (downloads, audio extraction)\n• Marketplace: Buy all digital tools and API keys\n• Games: Daily Lucky Wheel & Mystery Cases\n\n🛡 <b>2. FULLY VERIFIED (3D BIOMETRIC / FREE)</b>\n• Condition: Pass 3D Face ID scan (MediaPipe)\n• Daily limit: 25 enhanced requests\n• Verified badge: Trusted Creator Badge\n\n👑 <b>3. MONO DECK STUDIO VIP STATUS ({vip_price} UZS / MO)</b>\n• Price: {vip_price} UZS / 30 days (or {vip_stars} ⭐ Stars)\n• Unlimited limits: All daily bot actions fully unlimited!\n• 24/7 Priority Queue: Priority worker & fast stream\n• 10% Cashback: On every marketplace purchase\n━━━━━━━━━━━━━━━━━━━━━\n👇 <i>Select an action below:</i>",
        "es": "👑 <b>Mono Deck Studio — Niveles de Usuario y Planes</b>\n\n{status_line}\n\n• Requisito: Suscrito al canal {target_ch} + teléfono verificado\n• Límite diario: 15 solicitudes gratuitas\n• Tienda: Compra de todas las herramientas y claves API\n• Juegos: Ruleta de la Suerte y Mystery Cases\n\n🛡 <b>2. TOTALMENTE VERIFICADO (BIOMÉTRICO 3D / GRATIS)</b>\n• Requisito: Escaneo 3D Face ID\n• Límite diario: 25 solicitudes avanzadas\n\n👑 <b>3. ESTADO MONO DECK STUDIO VIP ({vip_price} UZS / MES)</b>\n• Precio: {vip_price} UZS / 30 días (o {vip_stars} ⭐ Stars)\n• Sin límites: ¡Acciones ilimitadas todos los días!\n• Cola prioritaria 24/7 y 10% de reembolso\n━━━━━━━━━━━━━━━━━━━━━\n👇 <i>Selecciona una acción:</i>",
        "tr": "👑 <b>Mono Deck Studio — Kullanıcı Seviyeleri ve Tarifeler</b>\n\n{status_line}\n\n• Şart: {target_ch} kanalına abonelik + doğrulanmış telefon\n• Günlük limit: 15 ücretsiz istek (video indirme, ses)\n• Mağaza: Tüm dijital araçlar ve API anahtarları\n• Oyunlar: Şans Çarkı ve Gizemli Kasalar\n\n🛡 <b>2. TAM DOĞRULANMIŞ (3D BİYOMETRİK / ÜCRETSİZ)</b>\n• Şart: 3D Face ID taraması\n• Günlük limit: 25 gelişmiş istek\n\n👑 <b>3. MONO DECK STUDIO VIP STATÜSÜ ({vip_price} UZS / AY)</b>\n• Fiyat: {vip_price} UZS / 30 gün (veya {vip_stars} ⭐ Stars)\n• Sınırsız: Tüm günlük işlemler tamamen sınırsız!\n• 24/7 Öncelikli sıra ve %10 geri ödeme\n━━━━━━━━━━━━━━━━━━━━━\n👇 <i>Aşağıdan bir işlem seçin:</i>"
    },
    "status_vip": {
        "uz": "👑 <b>Joriy statusingiz:</b> <b>MONO DECK STUDIO VIP</b> (Tugash: <code>{exp}</code>)",
        "ru": "👑 <b>Ваш статус:</b> <b>MONO DECK STUDIO VIP</b> (Истекает: <code>{exp}</code>)",
        "en": "👑 <b>Your status:</b> <b>MONO DECK STUDIO VIP</b> (Expires: <code>{exp}</code>)",
        "es": "👑 <b>Su estado:</b> <b>MONO DECK STUDIO VIP</b> (Vence: <code>{exp}</code>)",
        "tr": "👑 <b>Mevcut statünüz:</b> <b>MONO DECK STUDIO VIP</b> (Bitiş: <code>{exp}</code>)"
    },
    "status_face": {
        "uz": "🛡 <b>Joriy statusingiz:</b> <b>To'liq Tasdiqlangan (3D Biometrik)</b>",
        "ru": "🛡 <b>Ваш статус:</b> <b>Полностью подтвержден (3D Биометрия)</b>",
        "en": "🛡 <b>Your status:</b> <b>Fully Verified (3D Biometric)</b>",
        "es": "🛡 <b>Su estado:</b> <b>Totalmente verificado (Biometría 3D)</b>",
        "tr": "🛡 <b>Mevcut statünüz:</b> <b>Tam Doğrulanmış (3D Biyometrik)</b>"
    },
    "status_phone": {
        "uz": "✅ <b>Joriy statusingiz:</b> <b>Yarim Tasdiqlangan (Baza)</b>",
        "ru": "✅ <b>Ваш статус:</b> <b>Базовый (Телефон подтвержден)</b>",
        "en": "✅ <b>Your status:</b> <b>Partially Verified (Base)</b>",
        "es": "✅ <b>Su estado:</b> <b>Parcialmente verificado (Base)</b>",
        "tr": "✅ <b>Mevcut statünüz:</b> <b>Temel Doğrulanmış (Telefon)</b>"
    },
    "status_unverified": {
        "uz": "⚠️ <b>Joriy statusingiz:</b> <b>Tasdiqlanmagan</b>",
        "ru": "⚠️ <b>Ваш статус:</b> <b>Не подтвержден</b>",
        "en": "⚠️ <b>Your status:</b> <b>Unverified</b>",
        "es": "⚠️ <b>Su estado:</b> <b>No verificado</b>",
        "tr": "⚠️ <b>Mevcut statünüz:</b> <b>Doğrulanmamış</b>"
    },
    "btn_vip_buy": {
        "uz": "VIP Tarifni Faollashtirish (69,000 UZS)",
        "ru": "Активировать VIP (69,000 UZS)",
        "en": "Activate VIP Tier (69,000 UZS)",
        "es": "Activar Plan VIP (69,000 UZS)",
        "tr": "VIP Planı Aktifleştir (69,000 UZS)"
    },
    "btn_kyc_3d": {
        "uz": "3D KYC (Full Biometrik)",
        "ru": "3D KYC (Полная биометрия)",
        "en": "3D KYC (Full Biometric)",
        "es": "3D KYC (Biometría completa)",
        "tr": "3D KYC (Tam Biyometrik)"
    },
    "forcesub_prompt": {
        "uz": "📢 <b>Mono Deck Studio — Rasmiy Kanalga A'zo Bo'ling!</b>\n\nBot xizmatlaridan to'liq foydalanish va yangiliklarni kuzatish uchun rasmiy <b>@{ch_clean}</b> kanalimizga obuna bo'ling:\n\n⚠️ <i>A'zo bo'lgach, pastdagi «✅ Obunani tekshirish» tugmasini bosing.</i>",
        "ru": "📢 <b>Mono Deck Studio — Подпишитесь на официальный канал!</b>\n\nЧтобы полноценно использовать функции бота, подпишитесь на наш официальный канал <b>@{ch_clean}</b>:\n\n⚠️ <i>После подписки нажмите кнопку «✅ Проверить подписку» ниже.</i>",
        "en": "📢 <b>Mono Deck Studio — Join Our Official Channel!</b>\n\nTo access all bot features, please join our official <b>@{ch_clean}</b> channel:\n\n⚠️ <i>After joining, tap «✅ Check Subscription» below.</i>",
        "es": "📢 <b>Mono Deck Studio — ¡Únete a nuestro canal oficial!</b>\n\nPara acceder a todas las funciones, suscríbete a nuestro canal <b>@{ch_clean}</b>:\n\n⚠️ <i>Luego presiona «✅ Verificar suscripción» abajo.</i>",
        "tr": "📢 <b>Mono Deck Studio — Resmi Kanalımıza Katılın!</b>\n\nTüm bot özelliklerine erişmek için resmi <b>@{ch_clean}</b> kanalımıza abone olun:\n\n⚠️ <i>Katıldıktan sonra aşağıdaki «✅ Aboneliği Kontrol Et» butonuna dokunun.</i>"
    },
    "phone_req_prompt": {
        "uz": "🛡 <b>Xavfsizlik & Kirish Verifikatsiyasi</b>\n\nHurmatli foydalanuvchi, firibgarlikning oldini olish hamda hisobingiz xavfsizligini ta'minlash uchun botdan foydalanishdan avval telefon raqamingizni tasdiqlang!\n\n⚠️ <b>Qo'lda yozilgan raqam qabul qilinmaydi.</b>\nIltimos, pastdagi <b>«📱 Telefon raqamimni ulashish»</b> tugmasini bosing:",
        "ru": "🛡 <b>Безопасность и Входная Верификация</b>\n\nУважаемый пользователь, для предотвращения мошенничества и защиты аккаунта, подтвердите свой номер телефона перед началом работы!\n\n⚠️ <b>Ввод номера вручную не принимается.</b>\nПожалуйста, нажмите кнопку <b>«📱 Поделиться номером»</b> ниже:",
        "en": "🛡 <b>Security & Login Verification</b>\n\nDear user, to prevent fraud and secure your account, please verify your phone number before using the bot!\n\n⚠️ <b>Manual typing is not accepted.</b>\nPlease tap the <b>«📱 Share My Phone Number»</b> button below:",
        "es": "🛡 <b>Seguridad y Verificación de Acceso</b>\n\nEstimado usuario, para prevenir fraudes y proteger su cuenta, verifique su número de teléfono antes de comenzar:\n\n⚠️ <b>No se acepta escribir el número manualmente.</b>\nPresione el botón <b>«📱 Compartir mi teléfono»</b> abajo:",
        "tr": "🛡 <b>Güvenlik ve Giriş Doğrulaması</b>\n\nDeğerli kullanıcı, dolandırıcılığı önlemek ve hesabınızı korumak için lütfen başlamadan önce telefon numaranızı doğrulayın!\n\n⚠️ <b>Numaranın manuel yazılması kabul edilmez.</b>\nLütfen aşağıdaki <b>«📱 Telefon Numaramı Paylaş»</b> butonuna dokunun:"
    },
    "box_menu_text": {
        "uz": "🎁 <b>Omadli Quti & Mystery Cases (Stars & UZS So'm)</b>\n\nKeyslarni <b>Telegram Stars</b> yoki <b>UZS (so'm) balansingiz</b> orqali ochishingiz mumkin!\nHar bir keysdan haqiqiy Telegram sovg'alari yoki Telegram Premium yutib olishingiz mumkin!\n\n💳 <b>Sizning balansingiz:</b> <code>{bal:,} so'm</code>{recent_text}\n\n👇 <i>Ochmoqchi bo'lgan keysingizni tanlang:</i>",
        "ru": "🎁 <b>Таинственные Кейсы и Mystery Boxes (Stars и UZS)</b>\n\nОткрывайте кейсы за <b>Telegram Stars</b> или <b>баланс UZS (сум)</b>!\nИз каждого кейса можно выиграть настоящие Telegram подарки или Telegram Premium!\n\n💳 <b>Ваш баланс:</b> <code>{bal:,} сум</code>{recent_text}\n\n👇 <i>Выберите кейс для открытия:</i>",
        "en": "🎁 <b>Mystery Boxes & Cases (Stars & UZS)</b>\n\nOpen cases using <b>Telegram Stars</b> or your <b>UZS balance</b>!\nEvery case offers real Telegram profile gifts or Telegram Premium subscriptions!\n\n💳 <b>Your balance:</b> <code>{bal:,} UZS</code>{recent_text}\n\n👇 <i>Select a case to open:</i>",
        "es": "🎁 <b>Cajas Misteriosas y Mystery Cases (Stars y UZS)</b>\n\n¡Abre cajas usando <b>Telegram Stars</b> o tu saldo en <b>UZS</b>!\n¡Cada caja incluye regalos reales de perfil de Telegram o Telegram Premium!\n\n💳 <b>Tu saldo:</b> <code>{bal:,} UZS</code>{recent_text}\n\n👇 <i>Selecciona un caso para abrir:</i>",
        "tr": "🎁 <b>Gizemli Kasalar (Stars ve UZS)</b>\n\nKasaları <b>Telegram Stars</b> veya <b>UZS bakiyeniz</b> ile açın!\nHer kasadan gerçek Telegram hediyeleri veya Telegram Premium kazanabilirsiniz!\n\n💳 <b>Bakiyeniz:</b> <code>{bal:,} UZS</code>{recent_text}\n\n👇 <i>Açmak için bir kasa seçin:</i>"
    },
    "wheel_menu_text": {
        "uz": "🎯 <b>Omad G'ildiragi (Wheel of Fortune)</b>\n\nHar kuni 1 marta bepul aylantiring va pul mukofotlari yoki API kalitlarni yutib oling!\n\n{status_text}\n💰 <b>Balansingiz:</b> <code>{bal:,} so'm</code>\n\n🎁 <b>Sovg'alar:</b> 200 so'm, 500 so'm, 1,000 so'm, 2,500 so'm, Groq Cloud API!",
        "ru": "🎯 <b>Колесо Фортуны (Wheel of Fortune)</b>\n\nКрутите бесплатно 1 раз в день и выигрывайте денежные призы или API ключи!\n\n{status_text}\n💰 <b>Ваш баланс:</b> <code>{bal:,} сум</code>\n\n🎁 <b>Призы:</b> 200 сум, 500 сум, 1,000 сум, 2,500 сум, Groq Cloud API!",
        "en": "🎯 <b>Wheel of Fortune</b>\n\nSpin free once every day and win real cash rewards or API keys!\n\n{status_text}\n💰 <b>Your balance:</b> <code>{bal:,} UZS</code>\n\n🎁 <b>Prizes:</b> 200 UZS, 500 UZS, 1,000 UZS, 2,500 UZS, Groq Cloud API!",
        "es": "🎯 <b>Ruleta de la Fortuna (Wheel of Fortune)</b>\n\n¡Gira gratis una vez al día y gana premios en efectivo o claves API!\n\n{status_text}\n💰 <b>Tu saldo:</b> <code>{bal:,} UZS</code>\n\n🎁 <b>Premios:</b> 200 UZS, 500 UZS, 1,000 UZS, 2,500 UZS, Groq Cloud API!",
        "tr": "🎯 <b>Şans Çarkı (Wheel of Fortune)</b>\n\nHer gün 1 kez ücretsiz çevirin ve nakit ödüller veya API anahtarları kazanın!\n\n{status_text}\n💰 <b>Bakiyeniz:</b> <code>{bal:,} UZS</code>\n\n🎁 <b>Ödüller:</b> 200 UZS, 500 UZS, 1,000 UZS, 2,500 UZS, Groq Cloud API!"
    },
    "lottery_menu_text": {
        "uz": "🎟 <b>Jekpot Mega Lotereya (Tiraj #{pool_id})</b>\n\n🎫 <b>1 ta bilet narxi:</b> <code>3,000 so'm</code>\n📊 <b>Sotilgan biletlar:</b> <code>{tickets_sold} ta</code>\n🏆 <b>G'olibga Jekpot:</b> <code>{prize_fund:,} so'm</code>\n💳 <b>Balansingiz:</b> <code>{bal:,} so'm</code>",
        "ru": "🎟 <b>Джекпот Мега Лотерея (Тираж #{pool_id})</b>\n\n🎫 <b>Цена 1 билета:</b> <code>3,000 сум</code>\n📊 <b>Продано билетов:</b> <code>{tickets_sold} шт</code>\n🏆 <b>Джекпот победителю:</b> <code>{prize_fund:,} сум</code>\n💳 <b>Ваш баланс:</b> <code>{bal:,} сум</code>",
        "en": "🎟 <b>Jackpot Mega Lottery (Draw #{pool_id})</b>\n\n🎫 <b>1 Ticket Price:</b> <code>3,000 UZS</code>\n📊 <b>Tickets Sold:</b> <code>{tickets_sold}</code>\n🏆 <b>Winner's Jackpot:</b> <code>{prize_fund:,} UZS</code>\n💳 <b>Your balance:</b> <code>{bal:,} UZS</code>",
        "es": "🎟 <b>Mega Lotería Jackpot (Sorteo #{pool_id})</b>\n\n🎫 <b>Precio por boleto:</b> <code>3,000 UZS</code>\n📊 <b>Boletos vendidos:</b> <code>{tickets_sold}</code>\n🏆 <b>Bote al ganador:</b> <code>{prize_fund:,} UZS</code>\n💳 <b>Tu saldo:</b> <code>{bal:,} UZS</code>",
        "tr": "🎟 <b>Büyük İkramiye Mega Piyango (Çekiliş #{pool_id})</b>\n\n🎫 <b>1 Bilet Fiyatı:</b> <code>3,000 UZS</code>\n📊 <b>Satılan Biletler:</b> <code>{tickets_sold}</code>\n🏆 <b>Büyük İkramiye:</b> <code>{prize_fund:,} UZS</code>\n💳 <b>Bakiyeniz:</b> <code>{bal:,} UZS</code>"
    },
    "duel_menu_text": {
        "uz": "⚔️ <b>PvP Tanga Tashlash (Coin Flip)</b>\n\nBoshqa o'yinchilar bilan garov boylab o'ynang! G'olib jami bankning 90%ini oladi (10% kassa xizmati).\n\nℹ️ <b>Qanday o'ynash kerak:</b>\nChatda <code>/duel &lt;summa&gt; [burgut|panja]</code> buyrug'ini yuboring.\n\n<b>Masalan:</b> <code>/duel 5000 burgut</code>{duels_text}",
        "ru": "⚔️ <b>PvP Бросок Монеты (Coin Flip)</b>\n\nИграйте против других игроков! Победитель забирает 90% банка (10% комиссия сервиса).\n\nℹ️ <b>Как играть:</b>\nОтправьте команду <code>/duel &lt;сумма&gt; [burgut|panja]</code> в чат.\n\n<b>Например:</b> <code>/duel 5000 burgut</code>{duels_text}",
        "en": "⚔️ <b>PvP Coin Flip Duel</b>\n\nBet and play against other real players! Winner takes 90% of the pot (10% fee).\n\nℹ️ <b>How to play:</b>\nSend <code>/duel &lt;amount&gt; [burgut|panja]</code> in the chat.\n\n<b>Example:</b> <code>/duel 5000 burgut</code>{duels_text}",
        "es": "⚔️ <b>Duelo PvP Cara o Cruz (Coin Flip)</b>\n\n¡Apuesta y juega contra otros jugadores! El ganador se lleva el 90% del bote.\n\nℹ️ <b>Cómo jugar:</b>\nEnvía <code>/duel &lt;monto&gt; [burgut|panja]</code> en el chat.\n\n<b>Ejemplo:</b> <code>/duel 5000 burgut</code>{duels_text}",
        "tr": "⚔️ <b>PvP Yazı Tura Düellosu (Coin Flip)</b>\n\nDiğer oyunculara karşı bahis yapın ve oynayın! Kazanan kasanın %90'ını alır.\n\nℹ️ <b>Nasıl oynanır:</b>\nSohbete <code>/duel &lt;miktar&gt; [burgut|panja]</code> komutunu gönderin.\n\n<b>Örnek:</b> <code>/duel 5000 burgut</code>{duels_text}"
    },
    "marketplace_header_text": {
        "uz": "🏪 <b>Mono Deck Studio Raqamli Xizmatlar & Marketplace</b>\n\n💰 <b>Joriy balans:</b> <code>{bal:,} so'm</code>\n\n🌐 <b>Proxy & Server Quvvati:</b>\n• 🌐 <b>Dedicated Private Proxy:</b> 18,000 so'm\n• 📡 <b>24/7 Autostream Cloud Slot:</b> 2,500 so'm / soat\n\n🤖 <b>AI Modellar & Developer Vositalar:</b>\n• 💻 <b>Claude Code / Codex:</b> 15,000 so'm\n• ⚡ <b>OpenRouter API:</b> 25,000 so'm\n• 💎 <b>Google Gemini API:</b> 25,000 so'm\n• 🚀 <b>Groq Cloud API:</b> 18,000 so'm\n\n🎨 <b>Kreativ & Kontent:</b>\n• 🖼 <b>Flux.1 AI Rasm:</b> 18,000 so'm\n• 💡 <b>500+ Viral Prompt Pack:</b> 25,000 so'm\n• 🎬 <b>Vertical Shorts Kesish:</b> 5,000 so'm\n\n🚀 <b>Kanal O'sishi:</b> Layk 500 so'm, Obuna 1,000 so'm, Izoh 300 so'm\n\n📌 <i>Kerakli xizmat yoki toifani tanlang:</i>",
        "ru": "🏪 <b>Цифровые Сервисы и Маркетплейс Mono Deck Studio</b>\n\n💰 <b>Текущий баланс:</b> <code>{bal:,} сум</code>\n\n🌐 <b>Прокси и Серверы:</b>\n• 🌐 <b>Dedicated Private Proxy:</b> 18,000 сум\n• 📡 <b>24/7 Autostream Cloud Slot:</b> 2,500 сум / час\n\n🤖 <b>AI Модели и Инструменты Разработчика:</b>\n• 💻 <b>Claude Code / Codex:</b> 15,000 сум\n• ⚡ <b>OpenRouter API:</b> 25,000 сум\n• 💎 <b>Google Gemini API:</b> 25,000 сум\n• 🚀 <b>Groq Cloud API:</b> 18,000 сум\n\n🎨 <b>Креатив и Контент:</b>\n• 🖼 <b>Flux.1 AI Генерация изображений:</b> 18,000 сум\n• 💡 <b>500+ Вирусных Промптов:</b> 25,000 сум\n• 🎬 <b>Нарезка Shorts:</b> 5,000 сум\n\n🚀 <b>Продвижение каналов:</b> Лайк 500 сум, Подписка 1,000 сум, Комментарий 300 сум\n\n📌 <i>Выберите услугу или категорию ниже:</i>",
        "en": "🏪 <b>Mono Deck Studio Digital Services & Marketplace</b>\n\n💰 <b>Current Balance:</b> <code>{bal:,} UZS</code>\n\n🌐 <b>Proxy & Cloud Power:</b>\n• 🌐 <b>Dedicated Private Proxy:</b> 18,000 UZS\n• 📡 <b>24/7 Autostream Cloud Slot:</b> 2,500 UZS / hour\n\n🤖 <b>AI Models & Developer Tools:</b>\n• 💻 <b>Claude Code / Codex:</b> 15,000 UZS\n• ⚡ <b>OpenRouter API:</b> 25,000 UZS\n• 💎 <b>Google Gemini API:</b> 25,000 UZS\n• 🚀 <b>Groq Cloud API:</b> 18,000 UZS\n\n🎨 <b>Creative & Media:</b>\n• 🖼 <b>Flux.1 AI Image Generation:</b> 18,000 UZS\n• 💡 <b>500+ Viral Prompt Pack:</b> 25,000 UZS\n• 🎬 <b>Vertical Shorts Clipper:</b> 5,000 UZS\n\n🚀 <b>Channel Growth:</b> Likes 500 UZS, Subs 1,000 UZS, Comments 300 UZS\n\n📌 <i>Choose a product or category below:</i>",
        "es": "🏪 <b>Servicios Digitales y Mercado Mono Deck Studio</b>\n\n💰 <b>Saldo actual:</b> <code>{bal:,} UZS</code>\n\n🌐 <b>Proxy y Nube:</b>\n• 🌐 <b>Dedicated Private Proxy:</b> 18,000 UZS\n• 📡 <b>24/7 Autostream Cloud:</b> 2,500 UZS / hora\n\n🤖 <b>Modelos AI y Herramientas:</b>\n• 💻 <b>Claude Code / Codex:</b> 15,000 UZS\n• ⚡ <b>OpenRouter API:</b> 25,000 UZS\n• 💎 <b>Google Gemini API:</b> 25,000 UZS\n• 🚀 <b>Groq Cloud API:</b> 18,000 UZS\n\n🎨 <b>Creatividad y Contenido:</b>\n• 🖼 <b>Flux.1 AI Imágenes:</b> 18,000 UZS\n• 💡 <b>500+ Pack de Prompts Virales:</b> 25,000 UZS\n• 🎬 <b>Recorte de Shorts:</b> 5,000 UZS\n\n🚀 <b>Crecimiento del Canal:</b> Likes 500 UZS, Subs 1,000 UZS, Comentarios 300 UZS\n\n📌 <i>Selecciona un producto o categoría abajo:</i>",
        "tr": "🏪 <b>Mono Deck Studio Dijital Hizmetler ve Mağaza</b>\n\n💰 <b>Mevcut Bakiye:</b> <code>{bal:,} UZS</code>\n\n🌐 <b>Proxy ve Bulut Gücü:</b>\n• 🌐 <b>Dedicated Private Proxy:</b> 18,000 UZS\n• 📡 <b>24/7 Autostream Bulut Slotu:</b> 2,500 UZS / saat\n\n🤖 <b>Yapay Zeka Modelleri ve Geliştirici Araçları:</b>\n• 💻 <b>Claude Code / Codex:</b> 15,000 UZS\n• ⚡ <b>OpenRouter API:</b> 25,000 UZS\n• 💎 <b>Google Gemini API:</b> 25,000 UZS\n• 🚀 <b>Groq Cloud API:</b> 18,000 UZS\n\n🎨 <b>Yaratıcılık ve Medya:</b>\n• 🖼 <b>Flux.1 Yapay Zeka Görsel:</b> 18,000 UZS\n• 💡 <b>500+ Viral Prompt Paketi:</b> 25,000 UZS\n• 🎬 <b>Shorts Kırpıcı:</b> 5,000 UZS\n\n🚀 <b>Kanal Büyütme:</b> Beğeni 500 UZS, Abone 1,000 UZS, Yorum 300 UZS\n\n📌 <i>Aşağıdan bir ürün veya kategori seçin:</i>"
    }
}

TRANSLATIONS.update(EXTRA_I18N)
