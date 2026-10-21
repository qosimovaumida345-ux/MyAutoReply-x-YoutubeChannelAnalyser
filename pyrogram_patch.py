"""
Pyrogram 64-bit Telegram Channel & Exception Safety Patch
Fixes:
1. ValueError: Peer id invalid: -1004493034300 (Pyrogram 2.0.106 hardcoded 32-bit MIN_CHANNEL_ID).
2. Unhandled Task exception in Client.handle_updates() when unknown or private peers fail to resolve.
"""

import logging
import asyncio

logger = logging.getLogger("pyrogram.patch")

def apply_pyrogram_patches():
    try:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        import pyrogram.utils as u
        from pyrogram.client import Client

        # 1. Expand MIN_CHANNEL_ID for modern 64-bit Telegram channel IDs
        u.MIN_CHANNEL_ID = -1009999999999999

        # 2. Safe get_peer_type that never raises ValueError for channel IDs
        _orig_get_peer_type = u.get_peer_type
        def _safe_get_peer_type(peer_id: int) -> str:
            if isinstance(peer_id, int) and peer_id < 0:
                if peer_id >= u.MIN_CHAT_ID:
                    return "chat"
                if peer_id < u.MAX_CHANNEL_ID:
                    return "channel"
            return _orig_get_peer_type(peer_id)

        u.get_peer_type = _safe_get_peer_type

        # 3. Safe handle_updates wrapper to prevent background task death
        _orig_handle_updates = Client.handle_updates
        async def _safe_handle_updates(self, updates):
            try:
                return await _orig_handle_updates(self, updates)
            except Exception as e:
                logger.warning(f"[pyrogram_patch] Suppressed update dispatch error: {e}")

        Client.handle_updates = _safe_handle_updates
        logger.info("[pyrogram_patch] Pyrogram 64-bit channel & update safety patches applied successfully.")
    except Exception as e:
        logger.error(f"[pyrogram_patch] Failed to apply patches: {e}")

# Apply immediately on import
apply_pyrogram_patches()
