"""
Worker Client — video vazifalarini bajaruvchi tizimga so'rov yuborish.
1. Agar WORKER_API_URL sozlangan bo'lsa va ishlayotgan bo'lsa — unga HTTP POST yuboradi.
2. Agar WORKER_API_URL sozlanmagan yoki javob bermasa — avtomatik tarzda GitHub Actions 7 GB RAM runnerini ishga tushiradi!
"""

import os
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("worker_client")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "qosimovaumida345-ux/MyAutoReply-x-YoutubeChannelAnalyser").strip()
WORKER_API_URL = os.getenv("WORKER_API_URL", "").strip().rstrip("/")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


async def dispatch_task(
    task_type: str,
    url: str,
    chat_id: int,
    format: str = "720",
    caption: str = "",
    cookies_text: Optional[str] = None,
    proxy: Optional[str] = None,
    bot_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Video yuklash, unikalizatsiya yoki kesish vazifasini ishga tushirish.
    Avval mavjud bo'lsa HTTP workerga, bo'lmasa 24/7 GitHub Actions 7 GB RAM runneriga yuboradi.
    """
    token_to_use = bot_token or BOT_TOKEN or os.getenv("BOT_TOKEN", "").strip()

    # 1. HTTP Worker (agar mavjud bo'lsa)
    if WORKER_API_URL:
        try:
            endpoint = f"{WORKER_API_URL}/{task_type}"
            payload = {
                "url": url,
                "chat_id": chat_id,
                "format": format,
                "caption": caption,
                "cookies_text": cookies_text,
                "proxy": proxy,
                "bot_token": token_to_use
            }
            logger.info(f"HTTP Worker ga yuborilmoqda: {endpoint}")
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code == 200:
                    return {"ok": True, "provider": "http"}
                else:
                    logger.warning(f"HTTP Worker xatolik qaytardi: {resp.status_code}, GitHub Actions'ga o'tilmoqda...")
        except Exception as http_err:
            logger.warning(f"HTTP Worker ga ulanib bo'lmadi ({http_err}), GitHub Actions'ga o'tilmoqda...")

    # 2. GitHub Actions 24/7 Serverless Runner (7 GB RAM)
    gh_token = GITHUB_TOKEN
    if not gh_token:
        return {"ok": False, "error": "GITHUB_TOKEN yoki Worker server topilmadi."}

    url_api = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/worker.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "ref": "main",
        "inputs": {
            "task_type": task_type,
            "url": url,
            "chat_id": str(chat_id),
            "format": format,
            "caption": caption or "",
            "proxy": proxy or "",
            "bot_token": token_to_use
        }
    }

    try:
        logger.info(f"GitHub Actions ga dispatch yuborilmoqda: task={task_type}, chat_id={chat_id}")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url_api, headers=headers, json=payload)

        if resp.status_code == 204:
            logger.info(f"GitHub Actions muvaffaqiyatli navbatga qo'yildi (204 No Content)")
            return {"ok": True, "provider": "github"}
        else:
            logger.error(f"GitHub Actions API xatosi: {resp.status_code} - {resp.text}")
            return {"ok": False, "error": f"GitHub API {resp.status_code}: {resp.text[:150]}"}
    except Exception as gh_err:
        logger.error(f"GitHub Actions dispatch xatosi: {gh_err}")
        return {"ok": False, "error": str(gh_err)}
