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

  const renderContent = () => {
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
          loading="lazy"
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
        background: '#111114',
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
