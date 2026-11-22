import React, { useEffect, useRef, useState } from 'react';
import { loadLottiePlayer } from '../lib/lazyScripts.js';

const LOTTIE_JSON_CACHE = new Map();
const LOTTIE_CACHE_MAX = 64;

function cacheLottieText(url, jsonText) {
  if (LOTTIE_JSON_CACHE.has(url)) return;
  if (LOTTIE_JSON_CACHE.size >= LOTTIE_CACHE_MAX) {
    const oldest = LOTTIE_JSON_CACHE.keys().next().value;
    if (oldest !== undefined) LOTTIE_JSON_CACHE.delete(oldest);
  }
  LOTTIE_JSON_CACHE.set(url, jsonText);
}

function LottieRenderBox({ src, style, onError }) {
  const containerRef = useRef(null);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  useEffect(() => {
    let cancelled = false;
    let animInstance = null;
    const controller = new AbortController();

    async function mountAnimation() {
      try {
        await loadLottiePlayer();
        if (cancelled) return;
        const lottie = typeof window !== 'undefined' ? window.lottie : null;
        if (!lottie || typeof lottie.loadAnimation !== 'function') {
          if (!cancelled) onErrorRef.current?.();
          return;
        }

        let jsonText = LOTTIE_JSON_CACHE.get(src);
        if (!jsonText) {
          const res = await fetch(src, { signal: controller.signal });
          if (cancelled) return;
          if (!res.ok) {
            onErrorRef.current?.();
            return;
          }
          const ctype = (res.headers.get('content-type') || '').toLowerCase();
          if (ctype && !ctype.includes('json') && !ctype.includes('text/plain') && !ctype.includes('octet-stream')) {
            onErrorRef.current?.();
            return;
          }
          jsonText = await res.text();
          if (cancelled) return;
          cacheLottieText(src, jsonText);
        }

        const animationData = JSON.parse(jsonText);
        if (!animationData || (!Array.isArray(animationData.layers) && !animationData.v)) {
          if (!cancelled) onErrorRef.current?.();
          return;
        }

        const el = containerRef.current;
        if (cancelled || !el || !el.isConnected) return;
        el.innerHTML = '';

        animInstance = lottie.loadAnimation({
          container: el,
          renderer: 'svg',
          loop: true,
          autoplay: true,
          animationData,
        });
      } catch (err) {
        if (!cancelled && err?.name !== 'AbortError') {
          onErrorRef.current?.();
        }
      }
    }

    mountAnimation();

    return () => {
      cancelled = true;
      controller.abort();
      if (animInstance) {
        try {
          animInstance.stop?.();
          animInstance.destroy?.();
        } catch {
          // Ignore unmount teardown errors from third-party animation frames
        }
        animInstance = null;
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, [src]);

  return <div ref={containerRef} style={style} aria-hidden="true" />;
}

const FRAGMENT_FALLBACK_IMAGES = {
  cake: '/api/nft/image/delicious_cake.webp',
  champagne: '/api/nft/image/champagne_bottle.webp',
  shampan: '/api/nft/image/champagne_bottle.webp',
  bouquet: '/api/nft/image/gift_bouquet.webp',
  flower: '/api/nft/image/gift_bouquet.webp',
  gul: '/api/nft/image/gift_bouquet.webp',
  rose: '/api/nft/image/gift_bouquet.webp',
  trophy: '/api/nft/image/star_trophy.webp',
  kubok: '/api/nft/image/star_trophy.webp',
  rocket: '/api/nft/image/gift_rocket.webp',
  raketa: '/api/nft/image/gift_rocket.webp',
  ring: '/api/nft/image/diamond_ring.webp',
  diamond: '/api/nft/image/diamond_ring.webp',
  uzuk: '/api/nft/image/diamond_ring.webp',
  star: '/api/nft/image/gift_star.webp',
  cap: 'https://nft.fragment.com/gift/durovscap-3226.medium.jpg',
  durovscap: 'https://nft.fragment.com/gift/durovscap-3226.medium.jpg',
  kepka: 'https://nft.fragment.com/gift/durovscap-3226.medium.jpg',
  locket: 'https://nft.fragment.com/gift/heartlocket-416.medium.jpg',
  heartlocket: 'https://nft.fragment.com/gift/heartlocket-416.medium.jpg',
  watch: 'https://nft.fragment.com/gift/swisswatch-19581.medium.jpg',
  swisswatch: 'https://nft.fragment.com/gift/swisswatch-19581.medium.jpg',
  cigar: 'https://nft.fragment.com/gift/snoopcigar-56790.medium.jpg',
  snoopcigar: 'https://nft.fragment.com/gift/snoopcigar-56790.medium.jpg',
  chillflame: 'https://nft.fragment.com/gift/chillflame-102714.medium.jpg',
  flame: 'https://nft.fragment.com/gift/chillflame-102714.medium.jpg',
  candle: 'https://nft.fragment.com/gift/bdaycandle-149535.medium.jpg',
  bdaycandle: 'https://nft.fragment.com/gift/bdaycandle-149535.medium.jpg',
  tamagadget: 'https://nft.fragment.com/gift/tamagadget-10816.medium.jpg',
  gadget: 'https://nft.fragment.com/gift/tamagadget-10816.medium.jpg',
  calendar: 'https://nft.fragment.com/gift/deskcalendar-269416.medium.jpg',
  deskcalendar: 'https://nft.fragment.com/gift/deskcalendar-269416.medium.jpg',
  cat: 'https://nft.fragment.com/gift/scaredcat-15008.medium.jpg',
  scaredcat: 'https://nft.fragment.com/gift/scaredcat-15008.medium.jpg',
  cookie: 'https://nft.fragment.com/gift/gingercookie-148929.medium.jpg',
  gingercookie: 'https://nft.fragment.com/gift/gingercookie-148929.medium.jpg',
  potion: 'https://nft.fragment.com/gift/magicpotion-1036.medium.jpg',
  magicpotion: 'https://nft.fragment.com/gift/magicpotion-1036.medium.jpg',
  pepe: 'https://nft.fragment.com/gift/plushpepe-2163.medium.jpg',
  plushpepe: 'https://nft.fragment.com/gift/plushpepe-2163.medium.jpg',
  bear: 'https://nft.fragment.com/gift/toybear-7605.medium.jpg',
  toybear: 'https://nft.fragment.com/gift/toybear-7605.medium.jpg',
  ramen: 'https://nft.fragment.com/gift/instantramen-108551.medium.jpg',
  instantramen: 'https://nft.fragment.com/gift/instantramen-108551.medium.jpg',
  icecream: 'https://nft.fragment.com/gift/icecream-101191.medium.jpg',
  lolpop: 'https://nft.fragment.com/gift/lolpop-118917.medium.jpg',
  stocking: 'https://nft.fragment.com/gift/xmasstocking-112520.medium.jpg',
  premium: '/api/nft/image/TG_PREMIUM.webp',
  tg_premium: '/api/nft/image/TG_PREMIUM.webp',
  package: 'https://nft.fragment.com/gift/tamagadget-10816.medium.jpg',
  box: 'https://nft.fragment.com/gift/tamagadget-10816.medium.jpg',
  gift: '/api/nft/image/delicious_cake.webp',
};

export function resolveFallbackImage(icon, name) {
  const key = `${icon || ''} ${name || ''} package`.toLowerCase();
  for (const [k, url] of Object.entries(FRAGMENT_FALLBACK_IMAGES)) {
    if (key.includes(k)) return url;
  }
  return FRAGMENT_FALLBACK_IMAGES.package;
}

function renderServiceVectorLogo(icon, name, imageUrl, sz) {
  const raw = `${icon || ''} ${name || ''} ${imageUrl || ''}`.toLowerCase();
  if (raw.includes('autopost') || raw.includes('auto-post') || raw.includes('service_autopost')) {
    return (
      <svg width={sz} height={sz} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="gm-ap-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0F172A" />
            <stop offset="100%" stopColor="#090D16" />
          </linearGradient>
          <linearGradient id="gm-ap-top" x1="12" y1="12" x2="52" y2="24" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#0284C7" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#gm-ap-bg)" />
        <rect x="11" y="15" width="42" height="38" rx="9" fill="#1E293B" stroke="#38BDF8" strokeOpacity="0.35" strokeWidth="1.5" />
        <path d="M11 24C11 19.03 15.03 15 20 15H44C48.97 15 53 19.03 53 24V26H11V24Z" fill="url(#gm-ap-top)" />
        <rect x="20" y="10" width="4" height="8" rx="2" fill="#E2E8F0" />
        <rect x="40" y="10" width="4" height="8" rx="2" fill="#E2E8F0" />
        <circle cx="32" cy="39" r="10.5" fill="#0F172A" stroke="#38BDF8" strokeWidth="2" />
        <path d="M29.5 34.8L36.8 39L29.5 43.2V34.8Z" fill="#FF5A1F" />
      </svg>
    );
  }
  if (raw.includes('autostream') || raw.includes('service_autostream') || raw.includes('live stream')) {
    return (
      <svg width={sz} height={sz} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="gm-as-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#2A0A18" />
            <stop offset="100%" stopColor="#120712" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#gm-as-bg)" />
        <path d="M16 21C11 27 11 37 16 43" stroke="#FB7185" strokeWidth="2.5" strokeLinecap="round" strokeOpacity="0.65" />
        <path d="M48 21C53 27 53 37 48 43" stroke="#FB7185" strokeWidth="2.5" strokeLinecap="round" strokeOpacity="0.65" />
        <rect x="18" y="18" width="28" height="24" rx="6" fill="#1F122B" stroke="#F43F5E" strokeWidth="1.8" />
        <path d="M29 25.5L38 30L29 34.5V25.5Z" fill="#FB7185" />
        <rect x="21" y="46" width="22" height="7" rx="3.5" fill="#F43F5E" />
        <circle cx="26" cy="49.5" r="1.6" fill="#FFFFFF" />
        <path d="M30 48.2H39" stroke="#FFFFFF" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    );
  }
  if (raw.includes('seo') || raw.includes('service_seo') || raw.includes('teglar')) {
    return (
      <svg width={sz} height={sz} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="gm-seo-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#052E2B" />
            <stop offset="100%" stopColor="#07191A" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#gm-seo-bg)" />
        <rect x="13" y="34" width="7" height="16" rx="2.5" fill="#10B981" fillOpacity="0.85" />
        <rect x="23" y="27" width="7" height="23" rx="2.5" fill="#34D399" />
        <rect x="33" y="21" width="7" height="29" rx="2.5" fill="#22D3EE" />
        <rect x="43" y="14" width="7" height="36" rx="2.5" fill="#818CF8" />
        <path d="M14 35L26 24L36 27L48 14" stroke="#FACC15" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="48" cy="14" r="4" fill="#FACC15" stroke="#07191A" strokeWidth="1.5" />
      </svg>
    );
  }
  if (raw.includes('uniquify') || raw.includes('unikal') || raw.includes('service_uniquify')) {
    return (
      <svg width={sz} height={sz} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="gm-uq-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1E103C" />
            <stop offset="100%" stopColor="#0C081E" />
          </linearGradient>
          <linearGradient id="gm-uq-sh" x1="16" y1="12" x2="48" y2="52" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#A78BFA" />
            <stop offset="100%" stopColor="#6366F1" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#gm-uq-bg)" />
        <path d="M32 11L49 18V31C49 42.2 41.7 50.6 32 54C22.3 50.6 15 42.2 15 31V18L32 11Z" fill="#2E1A5E" stroke="url(#gm-uq-sh)" strokeWidth="2.2" />
        <path d="M25.5 32.5L30 37L39.5 27" stroke="#34D399" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (raw.includes('script') || raw.includes('skript') || raw.includes('service_scripts')) {
    return (
      <svg width={sz} height={sz} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="gm-sc-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#2B1F09" />
            <stop offset="100%" stopColor="#140E04" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#gm-sc-bg)" />
        <rect x="16" y="13" width="28" height="36" rx="5" fill="#FEF3C7" stroke="#F59E0B" strokeWidth="1.6" />
        <path d="M22 22H36M22 29H38M22 36H32" stroke="#92400E" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="44" cy="43" r="9" fill="#FF5A1F" stroke="#140E04" strokeWidth="2" />
        <path d="M44 38.5L42 43H45.5L43.5 47.5" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (raw.includes('gift_star') || raw.includes('stars bonus') || raw.includes('stars bonusi')) {
    return (
      <svg width={sz} height={sz} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="gm-st-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#062B20" />
            <stop offset="100%" stopColor="#041712" />
          </linearGradient>
          <linearGradient id="gm-st-fill" x1="16" y1="12" x2="48" y2="52" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FDE047" />
            <stop offset="100%" stopColor="#F59E0B" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#gm-st-bg)" />
        <path d="M32 12L37.8 23.8L50.8 25.7L41.4 34.8L43.6 47.8L32 41.7L20.4 47.8L22.6 34.8L13.2 25.7L26.2 23.8L32 12Z" fill="url(#gm-st-fill)" stroke="#FEF9C3" strokeWidth="1.2" strokeLinejoin="round" />
      </svg>
    );
  }
  return null;
}

function getCaseBackdropTheme(imageUrl, name) {
  const s = `${imageUrl || ''} ${name || ''}`.toLowerCase();
  if (s.includes('bronze')) return 'linear-gradient(135deg, #2D1B10 0%, #140D09 100%)';
  if (s.includes('silver')) return 'linear-gradient(135deg, #272B33 0%, #12141A 100%)';
  if (s.includes('gold')) return 'linear-gradient(135deg, #33240B 0%, #161006 100%)';
  if (s.includes('platinum')) return 'linear-gradient(135deg, #0E2B36 0%, #09131A 100%)';
  if (s.includes('galaxy') || s.includes('diamond')) return 'linear-gradient(135deg, #29123B 0%, #12081C 100%)';
  return '#141418';
}

export function GiftMedia({
  fileId = '',
  fileType = '',
  imageUrl = '',
  videoUrl = '',
  icon = '',
  slug = '',
  name = '',
  size = 64,
  animateHover = false,
  hoverOnly = false,
}) {
  const [fileError, setFileError] = useState(false);
  const [slugError, setSlugError] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    setFileError(false);
    setSlugError(false);
    setHasError(false);
  }, [fileId, slug, imageUrl]);

  const sz = typeof size === 'number' ? `${size}px` : size;
  const mediaStyle = {
    width: sz,
    height: sz,
    objectFit: 'contain',
    display: 'block',
    pointerEvents: 'none',
    borderRadius: 12,
  };

  const isPremiumItem = Boolean(
    (slug && String(slug).startsWith('tg-premium')) ||
      (icon && String(icon).includes('premium')) ||
      (imageUrl && String(imageUrl).includes('TG_PREMIUM'))
  );

  const safeFileId = fileId ? encodeURIComponent(String(fileId)) : '';
  const safeSlug = slug ? encodeURIComponent(String(slug)) : '';
  const fallbackSrc = resolveFallbackImage(icon, name);
  const serviceLogo = !safeFileId && !safeSlug ? renderServiceVectorLogo(icon, name, imageUrl, sz) : null;
  const isCaseThumb = Boolean(imageUrl && String(imageUrl).includes('case_'));
  const boxBg = getCaseBackdropTheme(imageUrl, name);

  const renderContent = () => {
    if (serviceLogo) {
      return serviceLogo;
    }

    if (safeFileId && !isPremiumItem && !fileError) {
      const src = `/api/telegram-file/${safeFileId}`;
      if (fileType === 'video' || (typeof fileId === 'string' && fileId.endsWith('.webm'))) {
        const posterSrc = imageUrl || (safeSlug ? `/api/nft/image/${safeSlug}.webp` : src);
        return (
          <img
            src={posterSrc}
            alt={name || 'Gift'}
            loading="lazy"
            decoding="async"
            style={mediaStyle}
            onError={(e) => {
              if (imageUrl && !e.currentTarget.dataset.fallbackApplied) {
                e.currentTarget.dataset.fallbackApplied = '1';
                e.currentTarget.src = imageUrl;
              } else {
                setFileError(true);
              }
            }}
          />
        );
      }

      if (fileType !== 'webp' && fileType !== 'png' && fileType !== 'jpg' && fileType !== 'image') {
        return (
          <LottieRenderBox
            key={`tg-lottie-${fileId}`}
            src={src}
            style={mediaStyle}
            onError={() => setFileError(true)}
          />
        );
      }
    }

    if (safeSlug && !isPremiumItem && (!hoverOnly || isHovered) && !slugError) {
      return (
        <LottieRenderBox
          key={`nft-lottie-${slug}`}
          src={`/api/nft/animation/${safeSlug}`}
          style={mediaStyle}
          onError={() => setSlugError(true)}
        />
      );
    }

    if (videoUrl && !isPremiumItem && !hasError) {
      const poster = imageUrl || (safeSlug ? `/api/nft/image/${safeSlug}.webp` : fallbackSrc);
      return (
        <img
          src={poster}
          alt={name || 'Gift'}
          loading="lazy"
          decoding="async"
          style={mediaStyle}
          onError={() => setHasError(true)}
        />
      );
    }

    if (imageUrl) {
      return (
        <img
          src={imageUrl}
          alt={name || 'Gift'}
          loading={isCaseThumb ? 'eager' : 'lazy'}
          fetchPriority={isCaseThumb ? 'high' : 'auto'}
          decoding="async"
          style={mediaStyle}
          onError={(e) => {
            if (e.currentTarget.dataset.fallbackApplied) return;
            e.currentTarget.dataset.fallbackApplied = '1';
            e.currentTarget.src = safeSlug ? `/api/nft/fragment-image/${safeSlug}` : fallbackSrc;
          }}
        />
      );
    }

    return (
      <img
        src={safeSlug ? `/api/nft/fragment-image/${safeSlug}` : fallbackSrc}
        alt={name || 'Gift'}
        loading="lazy"
        decoding="async"
        style={mediaStyle}
        onError={(e) => {
          if (e.currentTarget.dataset.fallbackApplied) return;
          e.currentTarget.dataset.fallbackApplied = '1';
          e.currentTarget.src = fallbackSrc;
        }}
      />
    );
  };

  return (
    <div
      onMouseEnter={() => (animateHover || hoverOnly) && setIsHovered(true)}
      onMouseLeave={() => (animateHover || hoverOnly) && setIsHovered(false)}
      style={{
        width: sz,
        height: sz,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 12,
        background: boxBg,
        border: '1px solid var(--border)',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {renderContent()}
    </div>
  );
}
export default GiftMedia;
