import React, { useCallback, useEffect, useState } from 'react';
import { GiftMedia } from '../components/GiftMedia.jsx';
import { IconCheck, IconSearch } from '../components/Icons.jsx';
import { apiFetchJson, safeOpenExternal } from '../lib/auth.js';
import { loadLottiePlayer } from '../lib/lazyScripts.js';

export function NftsPage({ user, onRefreshUser, navigate, t }) {
  const uid = user?.id || 0;
  const [gifts, setGifts] = useState([]);
  const [nfts, setNfts] = useState([]);
  const [rate, setRate] = useState({ rate_text: '1 TON = Live Market Rate' });
  const [search, setSearch] = useState('');
  const [filterSlug, setFilterSlug] = useState('all');
  const [visible, setVisible] = useState(36);
  const [loading, setLoading] = useState(false);
  const [buyingSlug, setBuyingSlug] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    loadLottiePlayer();
  }, []);

  const loadMarket = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await apiFetchJson('/api/stars/marketplace-nfts');
      if (data?.ok) {
        if (Array.isArray(data.items)) setNfts(data.items);
        if (data.rate) setRate(data.rate);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const loadInventory = useCallback(async () => {
    if (!uid) return;
    const { data } = await apiFetchJson(`/api/stars/user-inventory?user_id=${encodeURIComponent(uid)}`);
    if (data?.ok && Array.isArray(data.gifts)) {
      setGifts(data.gifts);
    }
  }, [uid]);

  useEffect(() => {
    loadMarket();
    loadInventory();
  }, [loadMarket, loadInventory]);

  const handleWithdraw = async (g) => {
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
      setNotice(data.message || 'Gift queued for Telegram delivery.');
      loadInventory();
      onRefreshUser?.(true);
    } else {
      setNotice(data?.error || 'Could not withdraw gift.');
    }
  };

  const handleRecycle = async (g) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    const stars = Number(g.prize_stars || g.stars || 15);
    const refund = Math.round(stars * 0.75 * 400);
    if (!window.confirm(`Sell "${g.prize_name || g.name}" for ${refund.toLocaleString()} UZS (75% cashback)?`)) return;
    const { data } = await apiFetchJson('/api/stars/recycle-gift', {
      method: 'POST',
      body: JSON.stringify({ user_id: uid, record_id: g.id, prize_stars: stars }),
    });
    if (data?.ok) {
      setNotice(`Converted to +${Number(data.refund_uzs || refund).toLocaleString()} UZS.`);
      loadInventory();
      onRefreshUser?.(true);
    } else {
      setNotice(data?.error || 'Could not convert gift.');
    }
  };

  const handleBuyNft = async (nft, method) => {
    if (!uid) {
      navigate('/login');
      return;
    }
    if (method === 'stars') {
      setBuyingSlug(nft.slug);
      try {
        const { data } = await apiFetchJson('/api/stars/marketplace/buy-invoice', {
          method: 'POST',
          body: JSON.stringify({ user_id: uid, slug: nft.slug }),
        });
        if (data?.ok && data?.invoice_link) {
          if (window.Telegram?.WebApp?.openInvoice) {
            window.Telegram.WebApp.openInvoice(data.invoice_link, (status) => {
              if (status === 'paid') {
                setNotice(`Purchased ${nft.name} with Telegram Stars!`);
                loadMarket();
                onRefreshUser?.(true);
              }
            });
          } else {
            safeOpenExternal(data.invoice_link);
          }
        } else {
          setNotice(data?.error || 'Invoice unavailable for this item.');
        }
      } finally {
        setBuyingSlug('');
      }
      return;
    }

    const uzsPrice = Number(nft.price_uzs || 150000);
    if (!window.confirm(`Purchase ${nft.name} (${nft.edition || ''}) for ${uzsPrice.toLocaleString()} UZS?`)) return;
    setBuyingSlug(nft.slug);
    try {
      const { data } = await apiFetchJson('/api/stars/marketplace/buy', {
        method: 'POST',
        body: JSON.stringify({ user_id: uid, slug: nft.slug, payment_method: 'uzs' }),
      });
      if (data?.ok) {
        setNotice(data.message || `Purchased ${nft.name}.`);
        loadMarket();
        loadInventory();
        onRefreshUser?.(true);
      } else {
        setNotice(data?.error || 'Could not complete purchase.');
      }
    } finally {
      setBuyingSlug('');
    }
  };

  const collectionMap = new Map();
  nfts.forEach((n) => {
    if (!n.collection_slug) return;
    const prev = collectionMap.get(n.collection_slug) || {
      slug: n.collection_slug,
      name: n.collection || n.collection_slug,
      count: 0,
    };
    prev.count += 1;
    collectionMap.set(n.collection_slug, prev);
  });
  const collections = Array.from(collectionMap.values());

  const q = search.trim().toLowerCase();
  const filtered = nfts.filter((n) => {
    if (filterSlug !== 'all' && n.collection_slug !== filterSlug) return false;
    if (!q) return true;
    return (
      String(n.name || '').toLowerCase().includes(q) ||
      String(n.edition || '').toLowerCase().includes(q) ||
      String(n.collection || '').toLowerCase().includes(q)
    );
  });

  return (
    <main className="md-container md-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 14, marginBottom: 24 }}>
        <div>
          <div className="md-eyebrow" style={{ marginBottom: 10 }}>
            <span className="md-dot" />
            <span>TON BLOCKCHAIN &amp; FRAGMENT COLLECTIBLES</span>
          </div>
          <h1 className="md-h2">{t('nftsTitle')}</h1>
        </div>
        <div className="md-card md-mono" style={{ padding: '8px 14px', borderRadius: 999, fontSize: 12 }}>
          {rate?.rate_text || 'TON Live'} &middot; Stock: {nfts.length.toLocaleString()} NFTs
        </div>
      </div>

      {notice && (
        <div className="md-card" style={{ padding: '12px 16px', marginBottom: 20, borderColor: 'var(--ink)', fontSize: 13 }}>
          {notice}
        </div>
      )}

      {uid > 0 && (
        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600, marginBottom: 12 }}>
            Your Gift Inventory ({gifts.length})
          </h2>
          {gifts.length === 0 ? (
            <div className="md-card" style={{ color: 'var(--muted)', fontSize: 13.5 }}>
              No gifts in inventory yet. Open a case to collect Telegram gifts.
            </div>
          ) : (
            <div className="md-grid-3">
              {gifts.map((g, i) => (
                <article key={g.id || i} className="md-card" style={{ padding: 16, display: 'grid', gap: 12 }}>
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
                      <div className="md-mono" style={{ fontSize: 12, color: 'var(--accent)' }}>{g.prize_stars || g.stars} Stars</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button type="button" className="md-btn md-btn-primary md-btn-sm" style={{ flex: 1 }} onClick={() => handleWithdraw(g)}>
                      {t('withdraw')}
                    </button>
                    <button type="button" className="md-btn md-btn-sm" style={{ flex: 1 }} onClick={() => handleRecycle(g)}>
                      {t('recycle')} (75%)
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      <section style={{ display: 'grid', gap: 16 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            type="text"
            aria-label="Search NFTs"
            className="md-input"
            style={{ flex: '1 1 260px' }}
            placeholder="Search Fragment NFT by name, collection, or #number (e.g. #11627, cigar, watch)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="button" className="md-btn md-btn-sm" disabled={loading} onClick={loadMarket}>
            <IconSearch size={13} />
            <span>{loading ? t('loading') : 'Sync Market'}</span>
          </button>
        </div>

        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 6 }}>
          <button
            type="button"
            className={`md-btn md-btn-sm${filterSlug === 'all' ? ' md-btn-primary' : ''}`}
            onClick={() => {
              setFilterSlug('all');
              setVisible(36);
            }}
          >
            All ({nfts.length})
          </button>
          {collections.map((c) => (
            <button
              key={c.slug}
              type="button"
              className={`md-btn md-btn-sm${filterSlug === c.slug ? ' md-btn-primary' : ''}`}
              onClick={() => {
                setFilterSlug(c.slug);
                setVisible(36);
              }}
            >
              {c.name} ({c.count})
            </button>
          ))}
        </div>

        <div className="md-grid-cards">
          {filtered.slice(0, visible).map((nft, i) => {
            const busy = buyingSlug === nft.slug;
            return (
              <article key={nft.slug || nft.id || i} className="md-card md-card-interactive" style={{ padding: 16, display: 'grid', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="md-mono" style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase' }}>
                    {nft.rarity || 'COLLECTIBLE'}
                  </span>
                  <span className="md-mono" style={{ fontSize: 11, color: 'var(--muted)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <IconCheck size={12} color="var(--ink)" />
                    <span>{nft.ton_price ? `${nft.ton_price} TON` : 'Fragment'}</span>
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <GiftMedia
                    imageUrl={nft.image_url}
                    slug={nft.slug}
                    name={nft.name}
                    size={160}
                    hoverOnly
                    animateHover
                  />
                </div>

                <div>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 15.5, fontWeight: 600 }}>{nft.name}</h3>
                  <p className="md-mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                    {nft.collection} {nft.edition ? `· ${nft.edition}` : ''}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    disabled={busy}
                    className="md-btn md-btn-primary md-btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => handleBuyNft(nft, 'uzs')}
                  >
                    {Number(nft.price_uzs || 150000).toLocaleString()} UZS
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    className="md-btn md-btn-accent md-btn-sm"
                    onClick={() => handleBuyNft(nft, 'stars')}
                  >
                    Stars
                  </button>
                </div>
              </article>
            );
          })}
        </div>

        {filtered.length > visible && (
          <div style={{ textAlign: 'center', marginTop: 8 }}>
            <button type="button" className="md-btn" onClick={() => setVisible((v) => v + 36)}>
              Load more ({filtered.length - visible} remaining)
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
export default NftsPage;
