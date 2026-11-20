import React, { useCallback, useEffect, useRef, useState } from 'react';
import { GiftMedia } from '../components/GiftMedia.jsx';
import { IconBox, IconCheck, IconShield } from '../components/Icons.jsx';
import { Modal } from '../components/Modal.jsx';
import { apiFetchJson, safeOpenExternal } from '../lib/auth.js';
import { loadConfetti, loadLottiePlayer } from '../lib/lazyScripts.js';

const DEFAULT_CASES = [
  {
    id: 'tier_1',
    name: 'Bronze Starter Case',
    price_stars: 25,
    price_uzs: 10000,
    image_url: '/api/nft/image/case_bronze_3d.webp?v=20261017_3d_v3',
    badge: '25 Stars',
    drops: [
      { stars: 15, name: 'Delicious Cake', rarity: 'common', icon: 'cake', file_id: 'CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E', file_type: 'tgs', is_nft: false },
      { stars: 25, name: 'Green Star', rarity: 'rare', icon: 'star', file_id: 'CAACAgIAAxUAAWrS2uM0EZJ7Dun5N1H-6YKcZfl3AAKNSAACsU84SMuB4ge7V_wGPQQ', file_type: 'tgs', is_nft: false },
      { stars: 50, name: 'Teddy Bear', rarity: 'legendary', icon: 'teddy', file_id: 'CAACAgIAAxUAAWrS2uO_yFyaqnGsGU2Rb6B3zOCwAAKtVAACmj_pSnvPkDQv_sivPQQ', file_type: 'tgs', is_nft: false },
    ],
  },
  {
    id: 'tier_2',
    name: 'Silver Creator Case',
    price_stars: 75,
    price_uzs: 30000,
    image_url: '/api/nft/image/case_silver_3d.webp?v=20261017_3d_v3',
    badge: '75 Stars',
    drops: [
      { stars: 50, name: 'Bouquet of Flowers', rarity: 'common', icon: 'bouquet', file_id: 'CAACAgIAAxUAAWrS2uNt8sIHLaoAAZeEbczG8VU45QAC3iUAAkUg4ErI5hOgFM9DXj0E', file_type: 'tgs', is_nft: false },
      { stars: 100, name: 'Champagne Bottle', rarity: 'rare', icon: 'champagne', file_id: 'CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ', file_type: 'tgs', is_nft: false },
      { stars: 250, name: 'Diamond Ring', rarity: 'legendary', icon: 'diamond_ring', file_id: 'CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ', file_type: 'tgs', is_nft: false },
    ],
  },
  {
    id: 'tier_3',
    name: 'Gold Pro Studio Case',
    price_stars: 250,
    price_uzs: 100000,
    image_url: '/api/nft/image/case_gold_3d.webp?v=20261017_3d_v3',
    badge: '250 Stars',
    drops: [
      { stars: 100, name: 'Champagne Bottle', rarity: 'common', icon: 'champagne', file_id: 'CAACAgIAAxUAAWrS2uMx4JgUgDH02-Jwj0U2KxJcAALXGAACy0WJSqKYQ7cuIwaJPQQ', file_type: 'tgs', is_nft: false },
      { stars: 250, name: 'Diamond Ring', rarity: 'rare', icon: 'diamond_ring', file_id: 'CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ', file_type: 'tgs', is_nft: false },
      { stars: 500, name: 'Golden Trophy', rarity: 'legendary', icon: 'trophy', file_id: 'CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ', file_type: 'tgs', is_nft: false },
    ],
  },
  {
    id: 'tier_4',
    name: 'Platinum VIP Master Case',
    price_stars: 750,
    price_uzs: 300000,
    image_url: '/api/nft/image/case_platinum_3d.webp?v=20261017_3d_v3',
    badge: '750 Stars',
    drops: [
      { stars: 500, name: 'Golden Trophy', rarity: 'common', icon: 'trophy', file_id: 'CAACAgIAAxUAAWrS2uMFG7qgWfi13TTbrx2ii_xcAAKZGwACzagQS38R6izkF899PQQ', file_type: 'tgs', is_nft: false },
      { stars: 1000, name: 'Space Rocket', rarity: 'rare', icon: 'rocket', file_id: 'CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ', file_type: 'tgs', is_nft: false },
      { stars: 1100, name: 'Telegram Premium (3 Oylik)', rarity: 'legendary', icon: 'telegram_premium', is_nft: false, is_premium: true, image_url: '/api/nft/image/TG_PREMIUM.webp?v=20261017_3d_v3' },
    ],
  },
  {
    id: 'tier_5',
    name: 'Diamond Galaxy Case',
    price_stars: 2500,
    price_uzs: 1000000,
    image_url: '/api/nft/image/case_galaxy_3d.webp?v=20261017_3d_v3',
    badge: '2,500 Stars',
    drops: [
      { stars: 1000, name: 'Space Rocket', rarity: 'common', icon: 'rocket', file_id: 'CAACAgIAAxUAAWrS2uPbTElMd6flAcykOHYcFzHFAALLGwAC14mRSzvrMNfF90DPPQQ', file_type: 'tgs', is_nft: false },
      { stars: 1500, name: 'Plush Collectible', rarity: 'rare', icon: 'plush', file_id: 'CAACAgIAAxUAAWrS2uNcxJcCHL0czrh7bzrdly-gAALoTwACJx74Ss1NNn7ovmiePQQ', file_type: 'tgs', is_nft: true },
      { stars: 2150, name: 'Telegram Premium (6 Oylik)', rarity: 'legendary', icon: 'telegram_premium', is_nft: false, is_premium: true, image_url: '/api/nft/image/TG_PREMIUM.webp?v=20261017_3d_v3' },
    ],
  },
];

const DEFAULT_STREAK_REWARDS = [
  { day: 1, title: '5 ta AI YouTube SEO', icon: 'seo', image_url: '/api/nft/image/service_seo.webp' },
  { day: 2, title: '10 ta AI Teglar & Tavsif', icon: 'seo', image_url: '/api/nft/image/service_seo.webp' },
  { day: 3, title: '3 ta Video Unikalizatsiya VIP', icon: 'uniquify', image_url: '/api/nft/image/service_uniquify.webp' },
  { day: 4, title: "10 ta AI Video Skript & G'oyalar", icon: 'scripts', image_url: '/api/nft/image/service_scripts.webp' },
  { day: 5, title: '5 ta Video Unikalizatsiya VIP', icon: 'uniquify', image_url: '/api/nft/image/service_uniquify.webp' },
  { day: 6, title: '12 Soatlik 24/7 Autostream VIP', icon: 'autostream', image_url: '/api/nft/image/service_autostream.webp' },
  { day: 7, title: '100 Telegram Stars Bonusi', icon: 'star', image_url: '/api/nft/image/gift_star.webp' },
];

const DEFAULT_SCRATCH_SLOTS = [
  { icon: 'zap', title: 'Auto-Post Pro', label: '1 Oylik Kvota', image_url: '/api/nft/image/service_autopost.webp' },
  { icon: 'sparkles', title: 'AI SEO Suite', label: '25 ta YouTube', image_url: '/api/nft/image/service_seo.webp' },
  { icon: 'rocket', title: 'Video Unikal VIP', label: '10 ta Video', image_url: '/api/nft/image/service_uniquify.webp' },
];

const REDEEM_SERVICES = [
  { id: 'video_autopost_30', title: 'Video Auto-Post Pro (1 Oylik)', desc: "YouTube va TikTok uchun to'liq avtomatik jadval bo'yicha posting.", stars: 350, icon: 'autopost', image_url: '/api/nft/image/service_autopost.webp', tag: 'POPULAR' },
  { id: 'autostream_24h', title: '24/7 YouTube Autostream (24 Soat)', desc: 'Serverda 24 soat uzluksiz video jonli efir strim qilish kvotasi.', stars: 250, icon: 'autostream', image_url: '/api/nft/image/service_autostream.webp', tag: 'LIVE STREAM' },
  { id: 'ai_seo_50', title: '50 ta Video uchun AI SEO Suite', desc: 'YouTube algoritmi uchun High-CTR sarlavha, tavsif va teglar paketi.', stars: 100, icon: 'seo', image_url: '/api/nft/image/service_seo.webp', tag: 'AI SPEED' },
  { id: 'video_unikal_10', title: '10 ta Video Unikalizatsiya VIP', desc: "8-qatlamli Anti-Copyright himoyasi bilan to'liq unikalizatsiya.", stars: 150, icon: 'uniquify', image_url: '/api/nft/image/service_uniquify.webp', tag: '4K VIP' },
  { id: 'ai_scripts_100', title: "100 ta Viral Video Skript & G'oyalar", desc: "Shorts va uzun videolar uchun to'liq viral ssenariy va hooklar.", stars: 200, icon: 'scripts', image_url: '/api/nft/image/service_scripts.webp', tag: 'VIRAL HOOKS' },
];

const DEFAULT_TARGET_GIFT = {
  id: '5170144170496491616',
  name: 'Delicious Cake',
  stars: 50,
  icon: 'cake',
  file_id: 'CAACAgIAAxUAAWrS2uMNAAEndT73SuyOCoLmhF990QACgRgAApWfiUpqxk-ZAWRQxj0E',
  slug: 'delicious-cake',
  file_type: 'tgs',
  image_url: '/api/nft/image/delicious_cake.webp',
  is_nft: false,
};

const UPGRADER_MULTIPLIERS = [1.5, 2, 3, 5, 10, 20, 50, 100];

export function CasesPage({ user, userStats, onRefreshUser, navigate, t }) {
  const uid = user?.id || 0;
  const [subTab, setSubTab] = useState('cases');
  const [cases, setCases] = useState(DEFAULT_CASES);
  const [drops, setDrops] = useState([]);
  const [battles, setBattles] = useState([]);
  const [userGifts, setUserGifts] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [streakData, setStreakData] = useState(null);
  const [feedback, setFeedback] = useState('');

  // Unboxing & 5.5s CS:GO Reel states
  const [activeCase, setActiveCase] = useState(null);
  const [rolling, setRolling] = useState(false);
  const [unboxPrize, setUnboxPrize] = useState(null);
  const [reelItems, setReelItems] = useState([]);
  const [reelTranslate, setReelTranslate] = useState(0);
  const [reelTransition, setReelTransition] = useState('none');
  const [winningHighlight, setWinningHighlight] = useState(false);
  const [oddsCase, setOddsCase] = useState(null);
  const reelContainerRef = useRef(null);
  const reelTimersRef = useRef([]);
  const reelCancelledRef = useRef(false);

  // PvP Duel modal state
  const [activeBattle, setActiveBattle] = useState(null);
  const [battleRolling, setBattleRolling] = useState(false);
  const [battleWinner, setBattleWinner] = useState('');

  // Controlled Upgrader state
  const [srcGift, setSrcGift] = useState(null);
  const [mult, setMult] = useState(2.0);
  const [upgraderTarget, setUpgraderTarget] = useState(DEFAULT_TARGET_GIFT);
  const [needleDeg, setNeedleDeg] = useState(0);
  const [upgrading, setUpgrading] = useState(false);
  const [upgradeResult, setUpgradeResult] = useState(null);
  const needleRef = useRef(0);
  const rafRef = useRef(null);

  // Daily Streak & Redeem Modals
  const [streakClaimedModal, setStreakClaimedModal] = useState(null);
  const [redeemModal, setRedeemModal] = useState(null);

  // Scratch card state
  const [scratchData, setScratchData] = useState({ won: false, slots: DEFAULT_SCRATCH_SLOTS, prize: null });
  const [scratchedCleared, setScratchedCleared] = useState(false);
  const canvasRef = useRef(null);
  const scratchedSlotsRef = useRef(new Set());

  // Shared AudioContext for authentic wheel/reel feedback
  const audioCtxRef = useRef(null);
  const lastTickTimeRef = useRef(0);

  const getAudioCtx = () => {
    try {
      if (!audioCtxRef.current) {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (Ctx) audioCtxRef.current = new Ctx();
      }
      if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
        audioCtxRef.current.resume().catch(() => {});
      }
      return audioCtxRef.current;
    } catch {
      return null;
    }
  };

  const playTickSound = () => {
    try {
      const now = performance.now();
      if (now - lastTickTimeRef.current < 85) return;
      lastTickTimeRef.current = now;
      const ctx = getAudioCtx();
      if (!ctx || ctx.state === 'suspended') return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(750, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(250, ctx.currentTime + 0.03);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.03);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.03);
    } catch {}
  };

  const playWinFanfare = () => {
    try {
      const ctx = getAudioCtx();
      if (!ctx) return;
      [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(f, ctx.currentTime + i * 0.09);
        gain.gain.setValueAtTime(0.18, ctx.currentTime + i * 0.09);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.09 + 0.45);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.09);
        osc.stop(ctx.currentTime + i * 0.09 + 0.45);
      });
    } catch {}
  };

  const playLossSound = () => {
    try {
      const ctx = getAudioCtx();
      if (!ctx) return;
      [310, 235, 165].forEach((f, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(f, ctx.currentTime + i * 0.13);
        osc.frequency.exponentialRampToValueAtTime(Math.max(60, f * 0.65), ctx.currentTime + i * 0.13 + 0.25);
        gain.gain.setValueAtTime(0.12, ctx.currentTime + i * 0.13);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.13 + 0.26);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(ctx.currentTime + i * 0.13);
        osc.stop(ctx.currentTime + i * 0.13 + 0.27);
      });
    } catch {}
  };

  const clearReelTimers = () => {
    reelCancelledRef.current = true;
    reelTimersRef.current.forEach((id) => clearTimeout(id));
    reelTimersRef.current = [];
  };

  useEffect(() => {
    loadLottiePlayer();
    loadConfetti();
    return () => {
      clearReelTimers();
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const getMatchingTargets = useCallback((baseStars, multiplier, invCatalog) => {
    if (!invCatalog || invCatalog.length === 0) return [DEFAULT_TARGET_GIFT];
    const desired = Math.round(Math.max(15, Number(baseStars || 15)) * Number(multiplier || 2));
    return [...invCatalog]
      .sort(
        (a, b) =>
          Math.abs(Number(a.stars || a.stars_value || 50) - desired) -
          Math.abs(Number(b.stars || b.stars_value || 50) - desired)
      )
      .slice(0, 6);
  }, []);

  const syncTarget = useCallback(
    (sourceItem, multiplier, invCatalog) => {
      const base = Number(sourceItem?.prize_stars || sourceItem?.stars || 15);
      const list = getMatchingTargets(base, multiplier, invCatalog || catalog);
      const desired = Math.round(base * Number(multiplier || 2));
      if (list.length > 0) {
        const best = list[0];
        setUpgraderTarget({
          ...best,
          name: best.name || best.gift_name || 'Telegram Gift',
          stars: desired,
          catalog_stars: Number(best.stars || best.stars_value || desired),
        });
      }
    },
    [catalog, getMatchingTargets]
  );

  const loadPublic = useCallback(async () => {
    const [cRes, dRes, bRes, upgRes] = await Promise.all([
      apiFetchJson('/api/stars/cases'),
      apiFetchJson('/api/stars/recent-drops'),
      apiFetchJson('/api/stars/pvp-battles'),
      apiFetchJson('/api/stars/upgrader/inventory'),
    ]);
    if (cRes.data?.ok && Array.isArray(cRes.data.cases) && cRes.data.cases.length > 0) {
      setCases(cRes.data.cases);
    }
    if (dRes.data?.ok && Array.isArray(dRes.data.drops)) {
      setDrops(dRes.data.drops);
    }
    if (bRes.data?.ok && Array.isArray(bRes.data.battles)) {
      setBattles(bRes.data.battles);
    }
    if (upgRes.data?.ok && Array.isArray(upgRes.data.inventory) && upgRes.data.inventory.length > 0) {
      setCatalog(upgRes.data.inventory);
    }
  }, []);

  const loadUserScoped = useCallback(async () => {
    const [invRes, stRes] = await Promise.all([
      uid > 0 ? apiFetchJson(`/api/stars/user-inventory?user_id=${encodeURIComponent(uid)}`) : Promise.resolve({}),
      apiFetchJson(`/api/stars/daily-streak?user_id=${encodeURIComponent(uid)}`),
    ]);
    if (invRes?.data?.ok && Array.isArray(invRes.data.gifts)) {
      setUserGifts(invRes.data.gifts);
      setSrcGift((prev) => {
        if (prev?.id && invRes.data.gifts.some((g) => g.id === prev.id)) {
          return invRes.data.gifts.find((g) => g.id === prev.id);
        }
        return invRes.data.gifts[0] || null;
      });
    }
    if (stRes?.data?.ok) {
      setStreakData(stRes.data);
    }
  }, [uid]);

  useEffect(() => {
    loadPublic();
    loadUserScoped();
  }, [loadPublic, loadUserScoped]);

  useEffect(() => {
    if (srcGift && catalog.length > 0) {
      syncTarget(srcGift, mult, catalog);
    }
  }, [srcGift, mult, catalog, syncTarget]);

  const buildReelStrip = (caseObj, winCandidate) => {
    const pool = caseObj?.drops?.length ? caseObj.drops : DEFAULT_CASES[0].drops;
    const strip = [];
    for (let i = 0; i < 46; i += 1) {
      if (i === 38) {
        strip.push({ ...winCandidate, isWinningCard: true });
      } else {
        strip.push({ ...pool[Math.floor(Math.random() * pool.length)], isWinningCard: false });
      }
    }
    return strip;
  };

  const runReelAnimation = (strip, resultPromise, onComplete) => {
    clearReelTimers();
    reelCancelledRef.current = false;
    setReelItems(strip);
    setReelTransition('none');
    setReelTranslate(0);
    setWinningHighlight(false);
    setRolling(true);

    const TARGET_INDEX = 38;
    const cardStep = 122;
    const cardWidth = 110;

    const tickDelays = [50, 50, 55, 60, 65, 70, 75, 80, 90, 105, 120, 140, 165, 195, 230, 275, 330, 400, 490, 600, 740, 920];
    let elapsed = 0;
    tickDelays.forEach((d) => {
      elapsed += d;
      if (elapsed <= 5400) {
        reelTimersRef.current.push(
          setTimeout(() => {
            if (!reelCancelledRef.current) playTickSound();
          }, elapsed)
        );
      }
    });

    reelTimersRef.current.push(
      setTimeout(() => {
        if (reelCancelledRef.current) return;
        const w = reelContainerRef.current?.clientWidth > 0 ? reelContainerRef.current.clientWidth : 460;
        const jitter = (Math.random() - 0.5) * 14;
        const targetX = -(TARGET_INDEX * cardStep + cardWidth / 2 - w / 2) + jitter;
        setReelTransition('transform 5.5s cubic-bezier(0.12, 0.8, 0.33, 1)');
        setReelTranslate(targetX);
      }, 50)
    );

    let resolved = null;
    resultPromise
      .then((res) => {
        if (reelCancelledRef.current) return;
        const data = res?.data ?? res;
        if (!data || !data.ok) {
          clearReelTimers();
          setRolling(false);
          setActiveCase(null);
          setFeedback(data?.error || 'Could not open case.');
          return;
        }
        resolved = data;
        setReelItems((prev) => {
          const next = [...prev];
          if (next.length > TARGET_INDEX) next[TARGET_INDEX] = { ...data, isWinningCard: true };
          return next;
        });
      })
      .catch(() => {
        if (reelCancelledRef.current) return;
        clearReelTimers();
        setRolling(false);
        setActiveCase(null);
        setFeedback('Server communication error while opening case.');
      });

    reelTimersRef.current.push(
      setTimeout(() => {
        if (reelCancelledRef.current) return;
        const finish = () => {
          if (reelCancelledRef.current) return;
          playTickSound();
          setWinningHighlight(true);
          reelTimersRef.current.push(
            setTimeout(() => {
              if (reelCancelledRef.current) return;
              setRolling(false);
              onComplete?.(resolved);
            }, 480)
          );
        };
        if (resolved) finish();
        else {
          resultPromise.then((res) => {
            const d = res?.data ?? res;
            if (d?.ok && !reelCancelledRef.current) finish();
          });
        }
      }, 5500)
    );
  };

  const handleOpenCase = async (c, method) => {
    if (rolling) return;
    if (method === 'demo') {
      const pool = c.drops?.length ? c.drops : DEFAULT_CASES[0].drops;
      const weights = pool.map((d) => d.weight || 1);
      const totalW = weights.reduce((a, b) => a + b, 0);
      let r = Math.random() * totalW;
      let picked = pool[0];
      for (const d of pool) {
        r -= d.weight || 1;
        if (r <= 0) {
          picked = d;
          break;
        }
      }
      const demoRes = { ...picked, ok: true, prize_name: picked.name, prize_stars: picked.stars, isDemo: true };
      setActiveCase({ ...c, isDemo: true });
      setUnboxPrize(null);
      runReelAnimation(buildReelStrip(c, demoRes), Promise.resolve({ data: demoRes }), (prize) => {
        setUnboxPrize(prize);
        playWinFanfare();
        if (window.confetti) window.confetti({ particleCount: 80, spread: 65 });
      });
      return;
    }

    if (!uid) {
      navigate('/login');
      return;
    }

    if (method === 'stars_invoice') {
      const { data } = await apiFetchJson('/api/stars/create-invoice', {
        method: 'POST',
        body: JSON.stringify({ user_id: uid, tier_id: c.id }),
      });
      if (data?.ok && data?.invoice_link) {
        if (window.Telegram?.WebApp?.openInvoice) {
          window.Telegram.WebApp.openInvoice(data.invoice_link, (status) => {
            if (status === 'paid') handleOpenCase(c, 'stars');
          });
        } else {
          safeOpenExternal(data.invoice_link);
        }
      } else {
        setFeedback(data?.error || 'Could not create Stars invoice.');
      }
      return;
    }

    const priceUzs = Number(c.price_uzs || c.price_stars * 400);
    if (method === 'uzs' && Number(userStats?.balance_uzs || 0) < priceUzs) {
      setFeedback(
        `Insufficient UZS balance. Case costs ${priceUzs.toLocaleString()} UZS, current balance: ${Number(
          userStats?.balance_uzs || 0
        ).toLocaleString()} UZS.`
      );
      return;
    }

    const pool = c.drops?.length ? c.drops : DEFAULT_CASES[0].drops;
    const candidate = pool[Math.floor(Math.random() * pool.length)];
    const endpoint = method === 'uzs' ? '/api/stars/open-case-uzs' : '/api/stars/open-case';
    setActiveCase(c);
    setUnboxPrize(null);
    const reqPromise = apiFetchJson(endpoint, {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, tier_id: c.id }),
    });
    runReelAnimation(buildReelStrip(c, candidate), reqPromise, (prize) => {
      setUnboxPrize(prize);
      setUserGifts((prev) => [{ ...prize, date: 'Now' }, ...prev]);
      playWinFanfare();
      if (window.confetti) window.confetti({ particleCount: 120, spread: 80 });
      onRefreshUser?.(true);
      loadUserScoped();
      loadPublic();
    });
  };

  const handleWithdrawGift = async (g) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const name = g.prize_name || g.name || 'Gift';
    if (!window.confirm(`Withdraw "${name}" to your Telegram profile?`)) return;
    const { data } = await apiFetchJson('/api/stars/withdraw-gift', {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, record_id: g.id }),
    });
    if (data?.ok) {
      setFeedback(data.message || `${name} queued for Telegram withdrawal.`);
      loadUserScoped();
      onRefreshUser?.(true);
    } else {
      setFeedback(data?.error || 'Withdrawal failed.');
    }
  };

  const handleRecycleGift = async (g) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const stars = Number(g.prize_stars || g.stars || 15);
    const refund = Math.round(stars * 0.75 * 400);
    if (!window.confirm(`Convert "${g.prize_name || g.name}" for ${refund.toLocaleString()} UZS (75% cashback)?`)) return;
    const { data } = await apiFetchJson('/api/stars/recycle-gift', {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, record_id: g.id, prize_stars: stars }),
    });
    if (data?.ok) {
      setFeedback(`Sold gift for +${Number(data.refund_uzs || refund).toLocaleString()} UZS.`);
      loadUserScoped();
      onRefreshUser?.(true);
    } else {
      setFeedback(data?.error || 'Could not convert gift.');
    }
  };

  const handleCreateBattle = async (tierId) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const uName = user?.username ? `@${user.username}` : user?.first_name || 'Creator';
    const { data } = await apiFetchJson('/api/stars/pvp-battle/create', {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, user_name: uName, tier_id: tierId }),
    });
    if (data?.ok) {
      setFeedback('PvP duel created! Waiting for opponent.');
      loadPublic();
      onRefreshUser?.(true);
    } else {
      setFeedback(data?.error || 'Could not create battle.');
    }
  };

  const handleJoinBattle = async (b) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const uName = user?.username ? `@${user.username}` : user?.first_name || 'Challenger';
    setActiveBattle(b);
    setBattleRolling(true);
    setBattleWinner('');
    const tickTimer = setInterval(playTickSound, 130);
    try {
      const { data } = await apiFetchJson('/api/stars/pvp-battle/join', {
        method: 'POST',
        body: JSON.stringify({ battle_id: b.id, user_id: uid, user_name: uName }),
      });
      setTimeout(() => {
        clearInterval(tickTimer);
        setBattleRolling(false);
        if (data?.ok && data.battle) {
          setActiveBattle(data.battle);
          setBattleWinner(data.battle.winner_name || 'Winner');
          playWinFanfare();
          if (window.confetti) window.confetti({ particleCount: 120, spread: 85 });
          onRefreshUser?.(true);
          loadPublic();
        } else {
          setActiveBattle(null);
          setFeedback(data?.error || 'Could not join battle.');
        }
      }, 2800);
    } catch {
      clearInterval(tickTimer);
      setBattleRolling(false);
      setActiveBattle(null);
      setFeedback('Network error joining battle.');
    }
  };

  const handleCancelBattle = async (battleId) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    if (!window.confirm('Cancel this PvP battle for a 100% UZS refund?')) return;
    const { data } = await apiFetchJson('/api/stars/pvp-battle/cancel', {
      method: 'POST',
      body: JSON.stringify({ battle_id: battleId, user_id: uid }),
    });
    if (data?.ok) {
      setFeedback(data.message || 'PvP duel cancelled and 100% refunded.');
      loadPublic();
      onRefreshUser?.(true);
    } else {
      setFeedback(data?.error || 'Could not cancel battle.');
    }
  };

  const handleRunUpgrade = async () => {
    if (upgrading) return;
    if (!uid) {
      navigate('/login');
      return;
    }
    if (!srcGift?.id) {
      setFeedback('Select a gift from your inventory first (open a Case to win one).');
      return;
    }
    const baseStars = Number(srcGift.prize_stars || srcGift.stars || 15);
    const desiredStars = Math.round(baseStars * Number(mult || 2.0));

    setUpgrading(true);
    setUpgradeResult(null);
    setFeedback('');

    const abortController = new AbortController();
    const safetyTimer = setTimeout(() => {
      try { abortController.abort(); } catch {}
    }, 15000);

    try {
      const { status, data } = await apiFetchJson('/api/stars/upgrader', {
        method: 'POST',
        signal: abortController.signal,
        body: JSON.stringify({
          user_id: uid,
          source_inventory_id: srcGift.id,
          item_stars: baseStars,
          multiplier: Number(mult),
          target_stars: desiredStars,
          target_name: upgraderTarget?.name || `${mult}x Gift`,
          target_icon: upgraderTarget?.icon || 'star',
          target_slug: upgraderTarget?.slug || upgraderTarget?.id || '',
          target_inventory_id: null,
        }),
      });
      clearTimeout(safetyTimer);
      if (status === 429) {
        setUpgrading(false);
        setFeedback('Rate limited (429). Wait 3 seconds and retry.');
        return;
      }
      if (!data?.ok || data.final_angle === undefined) {
        setUpgrading(false);
        setFeedback(data?.error || 'Upgrade failed.');
        return;
      }

      const startDeg = needleRef.current;
      const curMod = ((startDeg % 360) + 360) % 360;
      const diff = (Number(data.final_angle) - curMod + 360) % 360;
      const endDeg = startDeg + 1080 + diff;
      const t0 = performance.now();
      const duration = 3000;
      let lastTickDeg = startDeg;

      const frame = (now) => {
        const p = Math.min(1, (now - t0) / duration);
        const ease = 1 - Math.pow(1 - p, 3.8);
        const deg = startDeg + (endDeg - startDeg) * ease;
        if (Math.abs(deg - lastTickDeg) >= 28) {
          playTickSound();
          lastTickDeg = deg;
        }
        needleRef.current = deg;
        setNeedleDeg(deg);
        if (p < 1) {
          rafRef.current = requestAnimationFrame(frame);
        } else {
          setUpgrading(false);
          setUpgradeResult(data);
          if (data.won) {
            playWinFanfare();
            if (window.confetti) window.confetti({ particleCount: 130, spread: 80 });
          } else {
            playLossSound();
          }
          loadUserScoped();
          loadPublic();
          onRefreshUser?.(true);
        }
      };
      rafRef.current = requestAnimationFrame(frame);
    } catch {
      clearTimeout(safetyTimer);
      setUpgrading(false);
      setFeedback('Upgrader request timed out or network failed.');
    }
  };

  const drawFoil = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = '#0A0A0A';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(255,255,255,0.14)';
    ctx.lineWidth = 2;
    for (let x = -40; x < canvas.width + 40; x += 22) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x + 60, canvas.height);
      ctx.stroke();
    }
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '600 13px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('SCRATCH FOIL TO REVEAL', canvas.width / 2, canvas.height / 2 - 4);
    ctx.fillStyle = '#FF5A1F';
    ctx.font = '600 11px "IBM Plex Mono", monospace';
    ctx.fillText('3 MATCHING TOOLS = INSTANT WIN', canvas.width / 2, canvas.height / 2 + 16);
  }, []);

  useEffect(() => {
    if (subTab === 'scratch') {
      setScratchedCleared(false);
      scratchedSlotsRef.current.clear();
      setTimeout(drawFoil, 50);
    }
  }, [subTab, drawFoil]);

  const handlePlayScratch = async () => {
    if (!uid) {
      navigate('/login');
      return;
    }
    setScratchedCleared(false);
    scratchedSlotsRef.current.clear();
    const { data } = await apiFetchJson('/api/stars/scratch-card/play', {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, tg_user_id: uid }),
    });
    if (data?.ok) {
      setScratchData(data);
      onRefreshUser?.(true);
      setTimeout(drawFoil, 50);
    } else {
      setFeedback(data?.error || 'Could not start scratch card.');
    }
  };

  const handleRevealScratch = () => {
    const canvas = canvasRef.current;
    if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    setScratchedCleared(true);
    if (scratchData?.won) {
      playWinFanfare();
      if (window.confetti) window.confetti({ particleCount: 100, spread: 70 });
    }
  };

  const handleScratchPointer = (e) => {
    if (scratchedCleared) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const pt = e.touches?.[0] || e;
    const x = ((pt.clientX - rect.left) * canvas.width) / rect.width;
    const y = ((pt.clientY - rect.top) * canvas.height) / rect.height;
    const ctx = canvas.getContext('2d');
    ctx.globalCompositeOperation = 'destination-out';
    ctx.beginPath();
    ctx.arc(x, y, 26, 0, Math.PI * 2);
    ctx.fill();
    playTickSound();

    let slotIdx = -1;
    if (x < canvas.width * 0.34) slotIdx = 0;
    else if (x < canvas.width * 0.67) slotIdx = 1;
    else slotIdx = 2;
    scratchedSlotsRef.current.add(slotIdx);
    if (scratchedSlotsRef.current.size >= 3) {
      setTimeout(handleRevealScratch, 220);
    }
  };

  const handleClaimStreak = async () => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const { data } = await apiFetchJson('/api/stars/daily-streak/claim', {
      method: 'POST',
      body: JSON.stringify({ user_id: uid }),
    });
    if (data?.ok) {
      setStreakClaimedModal(data.reward || { title: 'Daily Reward' });
      playWinFanfare();
      if (window.confetti) window.confetti({ particleCount: 90, spread: 65 });
      loadUserScoped();
      loadPublic();
    } else {
      setFeedback(data?.error || 'Daily reward already claimed.');
    }
  };

  const handleRedeem = async (srvId) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const { data } = await apiFetchJson('/api/stars/redeem-service', {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, service_id: srvId }),
    });
    if (data?.ok) {
      setRedeemModal(data);
      playWinFanfare();
      if (window.confetti) window.confetti({ particleCount: 90, spread: 65 });
      onRefreshUser?.(true);
    } else {
      setFeedback(data?.error || 'Insufficient balance to redeem service.');
    }
  };

  const sourceStars = Number(srcGift?.prize_stars || srcGift?.stars || 15);
  const targetStars = Math.round(sourceStars * Number(mult || 2.0));
  const matchedTargets = getMatchingTargets(sourceStars, mult, catalog);
  const winPercent = Number(Math.min(75, Math.max(1, 100 / Number(mult || 2))).toFixed(1));
  const winSliceDeg = Math.max(6, Math.min(270, Math.round((winPercent / 100) * 360)));

  const tabs = [
    { id: 'cases', label: 'Mystery Cases' },
    { id: 'battles', label: 'PvP Case Battles' },
    { id: 'upgrader', label: 'Gift Upgrader' },
    { id: 'streak', label: '7-Day Streak' },
    { id: 'scratch', label: 'Scratch Cards' },
    { id: 'redeem', label: 'Redeem Store' },
  ];

  const streakRewards = streakData?.rewards?.length ? streakData.rewards : DEFAULT_STREAK_REWARDS;

  return (
    <main className="md-container md-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 14, marginBottom: 22 }}>
        <div>
          <div className="md-eyebrow" style={{ marginBottom: 10 }}>
            <span className="md-dot" />
            <span>TELEGRAM STARS ECOSYSTEM</span>
          </div>
          <h1 className="md-h2">{t('casesTitle')}</h1>
        </div>
        <div className="md-card" style={{ padding: '8px 14px', borderRadius: 999 }}>
          <span style={{ fontSize: 12, color: 'var(--muted)', marginRight: 8 }}>{t('balance')}:</span>
          <span className="md-mono" style={{ fontSize: 13, fontWeight: 600 }}>
            {Number(userStats?.balance_uzs || 0).toLocaleString()} UZS
          </span>
        </div>
      </div>

      {/* Live Drops Strip */}
      {drops.length > 0 && (
        <div
          className="md-card"
          style={{
            padding: '10px 14px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            overflowX: 'auto',
            background: '#0A0A0A',
            color: '#FFFFFF',
          }}
        >
          <span className="md-mono" style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, flexShrink: 0 }}>
            LIVE DROPS
          </span>
          {drops.slice(0, 10).map((d, i) => (
            <span
              key={i}
              className="md-mono"
              style={{
                fontSize: 11.5,
                whiteSpace: 'nowrap',
                padding: '3px 10px',
                borderRadius: 999,
                border: '1px solid rgba(255,255,255,0.14)',
              }}
            >
              {d.user} &rarr; {d.item} ({d.stars}&#9733;)
            </span>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 24 }}>
        {tabs.map((tb) => (
          <button
            key={tb.id}
            type="button"
            onClick={() => {
              setSubTab(tb.id);
              setFeedback('');
            }}
            className={`md-btn md-btn-sm${subTab === tb.id ? ' md-btn-primary' : ''}`}
          >
            {tb.label}
          </button>
        ))}
      </div>

      {feedback && (
        <div className="md-card" style={{ padding: '12px 16px', marginBottom: 20, borderColor: 'var(--ink)', fontSize: 13.5, fontWeight: 500 }}>
          {feedback}
        </div>
      )}

      {/* ==================== 1. MYSTERY CASES & USER INVENTORY ==================== */}
      {subTab === 'cases' && (
        <div style={{ display: 'grid', gap: 36 }}>
          <section className="md-grid-cards">
            {cases.map((c) => {
              const uzs = Number(c.price_uzs || c.price_stars * 400);
              return (
                <article key={c.id} className="md-card" style={{ display: 'grid', gap: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                    <GiftMedia imageUrl={c.image_url} icon={c.icon} name={c.name} size={72} />
                    <span className="md-mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)' }}>
                      {c.price_stars} Stars
                    </span>
                  </div>
                  <div>
                    <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600 }}>{c.name}</h2>
                    <p className="md-mono" style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {uzs.toLocaleString()} UZS &middot; {(c.drops || []).length} drops
                    </p>
                  </div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    <button type="button" className="md-btn md-btn-primary md-btn-sm" onClick={() => handleOpenCase(c, 'uzs')}>
                      {t('buyUzs')} ({uzs.toLocaleString()} UZS)
                    </button>
                    <button type="button" className="md-btn md-btn-accent md-btn-sm" onClick={() => handleOpenCase(c, 'stars_invoice')}>
                      {t('buyStars')} ({c.price_stars} Stars)
                    </button>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button type="button" className="md-btn md-btn-sm" style={{ flex: 1 }} onClick={() => handleOpenCase(c, 'demo')}>
                        Demo Spin
                      </button>
                      <button type="button" className="md-btn md-btn-sm" style={{ flex: 1 }} onClick={() => setOddsCase(c)}>
                        Drop Odds
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </section>

          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
              <h2 className="md-h2">Personal Gift Inventory ({userGifts.length})</h2>
              {!uid && (
                <button type="button" className="md-btn md-btn-sm" onClick={() => navigate('/login')}>
                  {t('signIn')} to inspect inventory
                </button>
              )}
            </div>

            {userGifts.length === 0 ? (
              <div className="md-card" style={{ textAlign: 'center', color: 'var(--muted)', padding: '28px 16px' }}>
                No gifts won yet. Open a Mystery Case or test Demo Spin above.
              </div>
            ) : (
              <div className="md-grid-3">
                {userGifts.map((g, gIdx) => (
                  <article key={g.id || gIdx} className="md-card" style={{ padding: 16, display: 'grid', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <GiftMedia
                        fileId={g.file_id}
                        fileType={g.file_type || 'tgs'}
                        imageUrl={g.image_url}
                        slug={g.slug}
                        icon={g.icon}
                        name={g.prize_name || g.name}
                        size={52}
                      />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{g.prize_name || g.name}</div>
                        <div className="md-mono" style={{ fontSize: 12, color: 'var(--accent)' }}>
                          {g.prize_stars || g.stars} Stars &middot; {g.rarity || 'gift'}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button type="button" className="md-btn md-btn-primary md-btn-sm" style={{ flex: 1 }} onClick={() => handleWithdrawGift(g)}>
                        {t('withdraw')}
                      </button>
                      <button type="button" className="md-btn md-btn-sm" style={{ flex: 1 }} onClick={() => handleRecycleGift(g)}>
                        {t('recycle')} (75%)
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* ==================== 2. PVP CASE BATTLES ==================== */}
      {subTab === 'battles' && (
        <section style={{ display: 'grid', gap: 18 }}>
          <div className="md-card" style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 600 }}>Create 1v1 PvP Case Duel</h2>
              <p style={{ fontSize: 13, color: 'var(--muted)' }}>Winner takes the total combined Stars pot minus 10% platform commission.</p>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {cases.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className="md-btn md-btn-sm md-btn-primary"
                  onClick={() => handleCreateBattle(c.id)}
                >
                  + {c.price_stars}&#9733; Duel
                </button>
              ))}
            </div>
          </div>

          <div className="md-grid-3">
            {battles.length === 0 ? (
              <div className="md-card" style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'var(--muted)' }}>
                No open duels right now. Create one above and invite challengers!
              </div>
            ) : (
              battles.map((b) => (
                <article key={b.id} className="md-card" style={{ display: 'grid', gap: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{b.host_name || 'Creator'}</strong>
                    <span className="md-mono" style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>
                      {b.cost_stars} Stars
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <GiftMedia icon={b.case_icon} name={b.case_name} size={40} />
                    <div>
                      <div style={{ fontSize: 13.5, fontWeight: 600 }}>{b.case_name}</div>
                      <div className="md-mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                        Pot: {b.pot_stars} Stars ({Number(b.pot_uzs || b.pot_stars * 400).toLocaleString()} UZS)
                      </div>
                    </div>
                  </div>
                  {b.host_id === uid ? (
                    <button type="button" className="md-btn md-btn-sm" onClick={() => handleCancelBattle(b.id)}>
                      Cancel &amp; 100% Refund ({Number(b.cost_uzs || b.cost_stars * 400).toLocaleString()} UZS)
                    </button>
                  ) : (
                    <button type="button" className="md-btn md-btn-primary md-btn-sm" onClick={() => handleJoinBattle(b)}>
                      Join Duel ({Number(b.cost_uzs || b.cost_stars * 400).toLocaleString()} UZS)
                    </button>
                  )}
                </article>
              ))
            )}
          </div>
        </section>
      )}

      {/* ==================== 3. CONTROLLED UPGRADER ==================== */}
      {subTab === 'upgrader' && (
        <section className="md-card" style={{ background: '#0A0A0A', color: '#FFFFFF', display: 'grid', gap: 24 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 28, alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ position: 'relative', width: 210, height: 210, margin: '0 auto' }}>
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  borderRadius: '50%',
                  background: `conic-gradient(#FF5A1F 0deg ${winSliceDeg}deg, #1E1E22 ${winSliceDeg}deg 360deg)`,
                  padding: 18,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    borderRadius: '50%',
                    background: '#0A0A0A',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <span className="md-mono" style={{ fontSize: 22, fontWeight: 700 }}>{winPercent}%</span>
                  <span className="md-mono" style={{ fontSize: 11, color: '#A1A1AA' }}>{mult}x WIN SECTOR</span>
                </div>
              </div>
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  transform: `rotate(${needleDeg}deg)`,
                  pointerEvents: 'none',
                }}
              >
                <div style={{ width: 4, height: 24, background: '#FFFFFF', margin: '-6px auto 0', borderRadius: 2 }} />
              </div>
            </div>

            <div style={{ flex: '1 1 300px', display: 'grid', gap: 12 }}>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20 }}>Gift Upgrader</h2>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {UPGRADER_MULTIPLIERS.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => {
                      setMult(m);
                      syncTarget(srcGift, m, catalog);
                    }}
                    className={`md-btn md-btn-sm${mult === m ? ' md-btn-accent' : ''}`}
                    style={mult === m ? undefined : { background: '#16161A', color: '#FFFFFF', borderColor: '#2E2E35' }}
                  >
                    {m}x
                  </button>
                ))}
              </div>
              <p className="md-mono" style={{ fontSize: 12, color: '#A1A1AA' }}>
                Source: {srcGift ? `${srcGift.prize_name || srcGift.name} (${sourceStars}★)` : 'None'} &rarr; Target: {upgraderTarget.name} (~{targetStars.toLocaleString()}&#9733;)
              </p>
              <button type="button" disabled={upgrading} className="md-btn md-btn-accent" onClick={handleRunUpgrade}>
                {upgrading ? 'Spinning...' : 'Spin Upgrade Wheel'}
              </button>
              {upgradeResult && (
                <p className="md-mono" style={{ fontSize: 13, color: upgradeResult.won ? '#22C55E' : '#F87171' }}>
                  {upgradeResult.won ? `Won: ${upgradeResult.prize_name || upgraderTarget.name}` : 'Landed outside target sector.'}
                </p>
              )}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
            <div style={{ background: '#111114', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14, padding: 14 }}>
              <div className="md-mono" style={{ fontSize: 11, color: '#A1A1AA', marginBottom: 10 }}>
                1. YOUR INVENTORY GIFT
              </div>
              {userGifts.length === 0 ? (
                <div style={{ fontSize: 12.5, color: '#71717A' }}>Open a case to add gifts to your inventory.</div>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {userGifts.map((g, i) => (
                    <button
                      key={g.id || i}
                      type="button"
                      onClick={() => setSrcGift(g)}
                      className="md-btn md-btn-sm"
                      style={{
                        background: srcGift?.id === g.id ? '#FF5A1F' : '#18181B',
                        color: '#FFFFFF',
                        borderColor: srcGift?.id === g.id ? '#FF5A1F' : '#27272A',
                      }}
                    >
                      {g.prize_name || g.name} ({g.prize_stars}&#9733;)
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ background: '#111114', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14, padding: 14 }}>
              <div className="md-mono" style={{ fontSize: 11, color: '#A1A1AA', marginBottom: 10 }}>
                2. TARGET GIFT (~{targetStars.toLocaleString()}&#9733;)
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {matchedTargets.map((cand, idx) => {
                  const sel =
                    (upgraderTarget?.slug && upgraderTarget.slug === cand.slug) || upgraderTarget?.name === cand.name;
                  return (
                    <button
                      key={cand.slug || cand.id || idx}
                      type="button"
                      onClick={() => setUpgraderTarget({ ...cand, stars: targetStars })}
                      className="md-btn md-btn-sm"
                      style={{
                        background: sel ? '#FFFFFF' : '#18181B',
                        color: sel ? '#0A0A0A' : '#FFFFFF',
                        borderColor: sel ? '#FFFFFF' : '#27272A',
                      }}
                    >
                      {cand.name}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ==================== 4. 7-DAY DAILY STREAK ==================== */}
      {subTab === 'streak' && (
        <section className="md-card" style={{ display: 'grid', gap: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
            <div>
              <h2 className="md-h2">7-Day Creator Streak</h2>
              <p style={{ fontSize: 13.5, color: 'var(--muted)' }}>
                Claim daily AI SEO, Script, Video Uniquify, Autostream, and Stars bonuses.
              </p>
            </div>
            <span className="md-mono" style={{ fontSize: 13, fontWeight: 600 }}>
              {streakData?.streak_days || 0} DAYS ACTIVE
            </span>
          </div>

          <div className="md-grid-cards">
            {streakRewards.map((r, i) => {
              const curr = streakData?.current_day || 1;
              const isClaimed = Boolean(streakData && i + 1 < curr);
              const isToday = Boolean(!streakData ? i === 0 : i + 1 === curr);
              return (
                <div
                  key={i}
                  className="md-card"
                  style={{
                    padding: 16,
                    borderColor: isToday ? 'var(--accent)' : 'var(--border)',
                    background: isToday ? 'var(--accent-soft)' : 'var(--bg)',
                    display: 'grid',
                    gap: 10,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="md-mono" style={{ fontSize: 11, fontWeight: 600, color: isToday ? 'var(--accent)' : 'var(--muted)' }}>
                      DAY {r.day || i + 1}
                    </span>
                    <span className="md-mono" style={{ fontSize: 10.5, fontWeight: 600, color: isClaimed ? 'var(--ok)' : 'var(--muted)' }}>
                      {isClaimed ? 'CLAIMED' : isToday ? 'TODAY' : 'LOCKED'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <GiftMedia imageUrl={r.image_url} icon={r.icon} name={r.title} size={42} />
                    <div style={{ fontSize: 13.5, fontWeight: 600 }}>{r.title}</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div>
            <button
              type="button"
              disabled={Boolean(streakData && !streakData.can_claim)}
              className="md-btn md-btn-primary"
              onClick={handleClaimStreak}
            >
              {streakData && !streakData.can_claim ? "Already Claimed Today" : "Claim Today's Reward"}
            </button>
          </div>
        </section>
      )}

      {/* ==================== 5. INTERACTIVE SCRATCH CARD ==================== */}
      {subTab === 'scratch' && (
        <section className="md-card" style={{ maxWidth: 520, margin: '0 auto', textAlign: 'center', display: 'grid', gap: 16 }}>
          <h2 className="md-h2">Creator Scratch Ticket</h2>
          <p style={{ fontSize: 13.5, color: 'var(--muted)' }}>
            Ticket cost: <strong>1,000 UZS</strong>. Match 3 identical creator rewards to unlock Auto-Post Pro, AI SEO, or Stars.
          </p>
          <div style={{ position: 'relative', width: '100%', height: 156, borderRadius: 12, overflow: 'hidden', border: '1px solid var(--border-strong)', background: 'var(--bg)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', height: '100%', alignItems: 'center', padding: 12, gap: 8 }}>
              {(scratchData?.slots || DEFAULT_SCRATCH_SLOTS).map((s, idx) => (
                <div key={idx} style={{ display: 'grid', justifyItems: 'center', gap: 6 }}>
                  <GiftMedia imageUrl={s.image_url} icon={s.icon} name={s.title || s.name} size={42} />
                  <div style={{ fontSize: 12, fontWeight: 600 }}>{s.title || s.name || s}</div>
                </div>
              ))}
            </div>
            <canvas
              ref={canvasRef}
              width={460}
              height={156}
              onMouseMove={(e) => e.buttons === 1 && handleScratchPointer(e)}
              onTouchMove={handleScratchPointer}
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', cursor: 'crosshair' }}
            />
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button type="button" className="md-btn md-btn-primary" onClick={handlePlayScratch}>
              New Ticket (1,000 UZS)
            </button>
            <button type="button" className="md-btn" onClick={handleRevealScratch}>
              Instant Reveal
            </button>
          </div>
          {scratchedCleared && (
            <p className="md-mono" style={{ fontSize: 13, fontWeight: 600, color: scratchData?.won ? 'var(--ok)' : 'var(--accent)' }}>
              {scratchData?.won
                ? `Won: ${scratchData?.prize?.title || scratchData?.prize?.name || 'Reward'}`
                : 'No 3-of-a-kind match. Grab another ticket!'}
            </p>
          )}
        </section>
      )}

      {/* ==================== 6. CREATOR REDEEM STORE ==================== */}
      {subTab === 'redeem' && (
        <section className="md-grid-cards">
          {REDEEM_SERVICES.map((srv) => (
            <article key={srv.id} className="md-card" style={{ display: 'grid', gap: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <GiftMedia imageUrl={srv.image_url} icon={srv.icon} name={srv.title} size={52} />
                <span className="md-mono" style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600 }}>
                  {srv.tag}
                </span>
              </div>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 16.5, fontWeight: 600 }}>{srv.title}</h3>
              <p style={{ fontSize: 13, color: 'var(--muted)' }}>{srv.desc}</p>
              <button type="button" className="md-btn md-btn-primary md-btn-sm" onClick={() => handleRedeem(srv.id)}>
                Redeem &middot; {srv.stars} Stars ({(srv.stars * 400).toLocaleString()} UZS)
              </button>
            </article>
          ))}
        </section>
      )}

      {/* CS:GO 5.5s Decelerating Case Unboxing Modal */}
      <Modal
        open={Boolean(activeCase)}
        onClose={() => {
          if (!rolling) {
            clearReelTimers();
            setActiveCase(null);
            setUnboxPrize(null);
          }
        }}
        title={activeCase?.name || 'Unboxing'}
        maxWidth={560}
      >
        <div style={{ display: 'grid', gap: 18 }}>
          <div
            ref={reelContainerRef}
            style={{
              position: 'relative',
              width: '100%',
              height: 132,
              overflow: 'hidden',
              background: '#0A0A0A',
              borderRadius: 12,
              border: '1px solid var(--border-strong)',
            }}
          >
            {/* Center #FF5A1F Needle */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: '50%',
                width: 3,
                background: '#FF5A1F',
                transform: 'translateX(-50%)',
                zIndex: 10,
              }}
            />

            <div
              style={{
                display: 'flex',
                gap: 12,
                padding: '16px 0',
                transform: `translate3d(${reelTranslate}px, 0, 0)`,
                transition: reelTransition,
                willChange: 'transform',
              }}
            >
              {reelItems.map((item, idx) => {
                const isWinnerCard = Boolean(winningHighlight && idx === 38);
                return (
                  <div
                    key={idx}
                    style={{
                      width: 110,
                      height: 100,
                      flexShrink: 0,
                      borderRadius: 10,
                      background: '#141417',
                      border: isWinnerCard ? '2px solid #FF5A1F' : '1px solid rgba(255,255,255,0.12)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: 6,
                      color: '#FFFFFF',
                    }}
                  >
                    <GiftMedia
                      fileId={item.file_id}
                      fileType={item.file_type}
                      imageUrl={item.image_url}
                      slug={item.slug}
                      icon={item.icon}
                      name={item.prize_name || item.name}
                      size={48}
                    />
                    <span style={{ fontSize: 10, marginTop: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%' }}>
                      {item.prize_name || item.name}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {unboxPrize && !rolling && (
            <div style={{ textAlign: 'center', display: 'grid', gap: 10 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 12, color: 'var(--accent)' }} className="md-mono">
                <IconCheck size={14} />
                <span>{unboxPrize.isDemo ? 'DEMO OUTCOME' : 'ADDED TO INVENTORY'}</span>
              </div>
              <h3 className="md-h2">{unboxPrize.prize_name || unboxPrize.name}</h3>
              <p className="md-mono" style={{ fontSize: 13, color: 'var(--muted)' }}>
                Value: {unboxPrize.prize_stars || unboxPrize.stars || 0} Stars
              </p>
              <button
                type="button"
                className="md-btn md-btn-primary"
                onClick={() => {
                  setActiveCase(null);
                  setUnboxPrize(null);
                }}
              >
                Collect
              </button>
            </div>
          )}
        </div>
      </Modal>

      {/* Case Drop Odds Modal */}
      <Modal open={Boolean(oddsCase)} onClose={() => setOddsCase(null)} title={`${oddsCase?.name || ''} — Drop Table`}>
        <div style={{ display: 'grid', gap: 8 }}>
          {(oddsCase?.drops || []).map((d, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 12px',
                borderRadius: 8,
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                fontSize: 13,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <GiftMedia fileId={d.file_id} fileType={d.file_type} imageUrl={d.image_url} icon={d.icon} name={d.name} size={32} />
                <span>{d.name}</span>
              </div>
              <span className="md-mono" style={{ fontWeight: 600 }}>{d.stars} Stars &middot; {d.rarity || 'common'}</span>
            </div>
          ))}
        </div>
      </Modal>

      {/* 1v1 PvP Duel Roll Modal */}
      <Modal
        open={Boolean(activeBattle)}
        onClose={() => !battleRolling && setActiveBattle(null)}
        title={`1v1 PvP Duel — ${activeBattle?.case_name || ''}`}
      >
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 14, alignItems: 'center', textAlign: 'center', marginBottom: 18 }}>
          <div className="md-card" style={{ padding: 14 }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 10 }}>{activeBattle?.host_name || 'Host'}</div>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
              <GiftMedia
                icon={activeBattle?.host_roll?.icon || activeBattle?.case_icon}
                fileId={activeBattle?.host_roll?.file_id}
                fileType={activeBattle?.host_roll?.file_type}
                name={activeBattle?.host_roll?.prize_name || activeBattle?.case_name}
                size={56}
              />
            </div>
            <div className="md-mono" style={{ fontSize: 12, color: 'var(--accent)' }}>
              {battleRolling ? 'Rolling...' : activeBattle?.host_roll ? `${activeBattle.host_roll.prize_name} (${activeBattle.host_roll.prize_stars}★)` : 'Ready'}
            </div>
          </div>

          <span className="md-mono" style={{ fontWeight: 700, fontSize: 16, color: 'var(--accent)' }}>VS</span>

          <div className="md-card" style={{ padding: 14 }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 10 }}>{activeBattle?.guest_name || 'You'}</div>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
              <GiftMedia
                icon={activeBattle?.guest_roll?.icon || activeBattle?.case_icon}
                fileId={activeBattle?.guest_roll?.file_id}
                fileType={activeBattle?.guest_roll?.file_type}
                name={activeBattle?.guest_roll?.prize_name || activeBattle?.case_name}
                size={56}
              />
            </div>
            <div className="md-mono" style={{ fontSize: 12, color: 'var(--accent)' }}>
              {battleRolling ? 'Rolling...' : activeBattle?.guest_roll ? `${activeBattle.guest_roll.prize_name} (${activeBattle.guest_roll.prize_stars}★)` : 'Ready'}
            </div>
          </div>
        </div>

        {!battleRolling && battleWinner && (
          <div className="md-card" style={{ background: 'var(--accent-soft)', borderColor: 'var(--accent)', textAlign: 'center', marginBottom: 14 }}>
            <div className="md-mono" style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)' }}>
              WINNER: {battleWinner}
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--ink-2)', marginTop: 4 }}>
              Net Prize Pool: {(activeBattle?.pot_stars || 0) - (activeBattle?.house_commission || 0)} Stars
            </div>
          </div>
        )}
      </Modal>

      {/* Streak Claimed Modal (with license key) */}
      <Modal open={Boolean(streakClaimedModal)} onClose={() => setStreakClaimedModal(null)} title="Daily Streak Claimed">
        <div style={{ textAlign: 'center', display: 'grid', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <GiftMedia icon={streakClaimedModal?.icon || 'package'} imageUrl={streakClaimedModal?.image_url} name={streakClaimedModal?.title || 'Reward'} size={56} />
          </div>
          <p style={{ fontSize: 15, fontWeight: 600 }}>{streakClaimedModal?.title || streakClaimedModal?.name}</p>
          {streakClaimedModal?.license_key && (
            <div className="md-card" style={{ background: 'var(--bg)', padding: 12 }}>
              <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>ACTIVATION KEY</div>
              <div className="md-mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--accent)', marginTop: 4 }}>
                {streakClaimedModal.license_key}
              </div>
            </div>
          )}
          <button type="button" className="md-btn md-btn-primary" onClick={() => setStreakClaimedModal(null)}>
            Done
          </button>
        </div>
      </Modal>

      {/* Service Redeem Modal (with license key) */}
      <Modal open={Boolean(redeemModal)} onClose={() => setRedeemModal(null)} title="Service Redeemed">
        <div style={{ textAlign: 'center', display: 'grid', gap: 12 }}>
          <IconShield size={28} color="var(--accent)" />
          <p style={{ fontSize: 14.5 }}>{redeemModal?.message || 'Service activated on your account.'}</p>
          {redeemModal?.license_key && (
            <div className="md-card" style={{ background: 'var(--bg)', padding: 12 }}>
              <div className="md-mono" style={{ fontSize: 11, color: 'var(--muted)' }}>LICENSE KEY</div>
              <div className="md-mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--accent)', marginTop: 4 }}>
                {redeemModal.license_key}
              </div>
            </div>
          )}
          <button type="button" className="md-btn md-btn-primary" onClick={() => setRedeemModal(null)}>
            Close
          </button>
        </div>
      </Modal>
    </main>
  );
}
export default CasesPage;
