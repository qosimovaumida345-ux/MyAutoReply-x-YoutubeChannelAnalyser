"""
HUMO SMS Parser Module for @HUMOcardbot & P2P Banking SMS
Tushum xabarlaridan summa, karta, yuboruvchi va RRN kodini 100% aniqlikda ajratadi.
"""
import re
from typing import Optional, Dict, Any

def parse_humo_sms(text: str) -> Optional[Dict[str, Any]]:
    """
    @HUMOcardbot yoki bank SMS xabarlarini tahlil qiladi.
    Tushum (income) bo'lsa, dictionary qaytaradi, aks holda None.
    """
    if not text or not isinstance(text, str):
        return None

    clean_text = text.strip()
    text_lower = clean_text.lower()
    
    # 1. Tushum (kirim) ekanligini tekshirish
    income_markers = [
        "tushum", "popolneniye", "пополнение", "qabul qilindi", "o'tkazma",
        "otkazma", "karta to'ldirildi", "prihod", "приход", "zachisleniye",
        "зачисление", "karta hisobiga", "kirim", "+", "to'ldirish", "🎉", "➕"
    ]
    expense_markers = [
        "oplata", "оплата", "yechildi", "spisaniye", "списание", "spisano",
        "chiqim", "to'lov", "tolov", "xarid", "pokupka", "покупка"
    ]
    
    is_income = any(m in text_lower for m in income_markers)
    is_expense = any(m in text_lower for m in expense_markers)
    
    if is_expense and not any(k in text_lower for k in ["+", "tushum", "popolneniye", "пополнение", "qabul qilindi", "to'ldirish", "➕"]):
        return None
    
    if not is_income and "+" not in clean_text and "➕" not in clean_text:
        return None

    # 2. Summani ajratish
    amount_uzs = 0
    # Old and new formats mixed: "+50 014.00 UZS" or "➕ 1.001,00 UZS"
    amount_match = re.search(
        r"(?:summa|сумма|tushum|popolneniye|пополнение|miqdor)?[:\s]*[+➕]?\s*([\d\s\.,]+)\s*(?:uzs|so['’`]?m|сум)",
        clean_text,
        re.IGNORECASE
    )
    if amount_match:
        raw_amt = amount_match.group(1).replace(" ", "")
        if "," in raw_amt and "." in raw_amt:
            # e.g. 1.001,00 -> 1001.00
            raw_amt = raw_amt.replace(".", "").replace(",", ".")
        elif "," in raw_amt:
            # 1001,00 -> 1001.00, or 1,001 -> 1001
            if re.search(r",\d{1,2}$", raw_amt):
                raw_amt = raw_amt.replace(",", ".")
            else:
                raw_amt = raw_amt.replace(",", "")
        elif "." in raw_amt:
            # 1001.00 -> 1001.00, or 1.001 -> 1001
            if re.search(r"\.\d{1,2}$", raw_amt):
                pass
            else:
                raw_amt = raw_amt.replace(".", "")
        
        try:
            amount_uzs = int(float(raw_amt))
        except ValueError:
            amount_uzs = 0

    if amount_uzs <= 0:
        return None

    # 3. Karta oxirgi 4 raqami (Qabul qiluvchi karta)
    card_last4 = None
    card_line_match = re.search(r"(?:💳|karta[a-z]*|карт[а-я]*|card[s]?)[:\s]*(?:HUMOCARD)?\s*\*?([^\n\r💰🕒📍]+)", clean_text, re.IGNORECASE)
    if card_line_match:
        card_digits = re.findall(r"\d{4}", card_line_match.group(1))
        if card_digits:
            card_last4 = card_digits[-1]
        else:
            alt_digits = re.findall(r"\d+", card_line_match.group(1))
            if alt_digits and len(alt_digits[-1]) >= 4:
                card_last4 = alt_digits[-1][-4:]

    # 4. Yuboruvchining kartasi (Kimdan) yoki nomi
    sender_card_last4 = None
    sender_name = None
    sender_match = re.search(r"(?:📍|kimdan|ot|от|yuboruvchi|ot kogo)[:\s]+([^\n\r💳💰🕒]+)", clean_text, re.IGNORECASE)
    if sender_match:
        sender_raw = sender_match.group(1).strip()
        card_in_sender = re.findall(r"\d{4}", sender_raw)
        if card_in_sender:
            sender_card_last4 = card_in_sender[-1]
        else:
            sender_name = sender_raw[:60].strip()

    # 5. RRN / Tranzaksiya kodi
    rrn_code = None
    rrn_match = re.search(r"(?:rrn|kod|код|code|terminal|терминал|id|check|chek)[:\s#]*([A-Za-z0-9]+)", clean_text, re.IGNORECASE)
    if rrn_match:
        rrn_code = rrn_match.group(1).strip()

    # 6. Qoldiq (Balance)
    balance_uzs = None
    bal_match = re.search(r"(?:💰|qoldiq|ostatok|остаток|balans|баланс)[:\s]*([\d\s\.,]+)\s*(?:uzs|so['’`]?m|сум)", clean_text, re.IGNORECASE)
    if bal_match:
        raw_bal = bal_match.group(1).replace(" ", "")
        if "," in raw_bal and "." in raw_bal:
            raw_bal = raw_bal.replace(".", "").replace(",", ".")
        elif "," in raw_bal:
            if re.search(r",\d{1,2}$", raw_bal):
                raw_bal = raw_bal.replace(",", ".")
            else:
                raw_bal = raw_bal.replace(",", "")
        elif "." in raw_bal:
            if not re.search(r"\.\d{1,2}$", raw_bal):
                raw_bal = raw_bal.replace(".", "")
        try:
            balance_uzs = int(float(raw_bal))
        except ValueError:
            balance_uzs = None

    # 7. Sana / Vaqt (New emoji format: 🕒 15:37 11.09.2026)
    date_str = None
    date_match = re.search(r"(?:🕒)?\s*(\d{2}[\./-]\d{2}[\./-]\d{2,4}\s+\d{2}:\d{2}(?::\d{2})?|\d{2}:\d{2}(?::\d{2})?\s+\d{2}[\./-]\d{2}[\./-]\d{2,4})", clean_text)
    if date_match:
        date_str = date_match.group(1).strip()

    return {
        "amount_uzs": amount_uzs,
        "card_last4": card_last4,
        "sender_card_last4": sender_card_last4,
        "sender_name": sender_name,
        "rrn_code": rrn_code,
        "balance_uzs": balance_uzs,
        "date_str": date_str,
        "raw_text": clean_text
    }


if __name__ == "__main__":
    # Test cases
    test_sms_1 = """
    O'tkazma qabul qilindi
    Karta: 9860 35** **** 1234
    Summa: +50 014.00 UZS
    Kimdan: 8600 **** **** 4492
    Qoldiq: 1 450 014.00 UZS
    Sana: 10.09.2026 23:15:42
    RRN: 84920194
    """
    res1 = parse_humo_sms(test_sms_1)
    print("Test 1 Result:", res1)
    assert res1["amount_uzs"] == 50014
    assert res1["card_last4"] == "1234"
    assert res1["sender_card_last4"] == "4492"
    assert res1["rrn_code"] == "84920194"
    
    test_sms_2 = """
    Пополнение карты *1234
    +10003 UZS
    От: RUSTAMOV B.
    Остаток: 250000 UZS
    Код: 771239
    """
    res2 = parse_humo_sms(test_sms_2)
    print("Test 2 Result (amount):", res2["amount_uzs"])
    assert res2["amount_uzs"] == 10003
    assert res2["card_last4"] == "1234"
    assert res2["sender_name"] == "RUSTAMOV B."
    assert res2["rrn_code"] == "771239"
    print("All Parser tests passed successfully!")
