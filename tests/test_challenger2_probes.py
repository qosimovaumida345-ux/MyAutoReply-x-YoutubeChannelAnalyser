import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from ventebot_service import VenteBotClient
from main import handle_api_reseller_products

# =====================================================================
# PROBE 1: ventebot_service.get_products()
# Cache pollution & Stable ordering stress tests
# =====================================================================

@pytest.mark.asyncio
async def test_probe1_cache_pollution_adversarial():
    """
    Test whether calling get_products(in_stock_only=True) corrupts or filters
    the cached catalog so that a subsequent call with in_stock_only=False
    erroneously loses 0-stock products.
    """
    client = VenteBotClient()
    client.base_url = "https://fake-vb.com"
    client.api_key = "fake-key"

    sample_products = [
        {"id": 101, "name": "ChatGPT Plus", "price_usd": "20", "stock": 5},
        {"id": 102, "name": "Midjourney Pro", "price_usd": "30", "stock": 0},
        {"id": 103, "name": "Cursor Pro", "price_usd": "20", "stock": None}, # Unmetered/instant
        {"id": 104, "name": "Claude Pro", "price_usd": "20", "stock": -1},   # Depleted/negative
        {"id": 105, "name": "Canva Pro", "price_usd": "10", "stock": 0},    # Zero stock
        {"id": 106, "name": "Netflix 4K", "price_usd": "15", "stock": 12},  # Positive stock
    ]

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"products": sample_products})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session), \
         patch("telemetry_service.get_dynamic_config", return_value=60), \
         patch("currency_service.currency_service.get_usd_to_uzs_rate", AsyncMock(return_value=12850.0)):

        # Clear cache to simulate clean initial state
        client.cache.clear()

        # Step 1: Initial call with in_stock_only=True
        res_stock_only = await client.get_products(force_refresh=True, in_stock_only=True)
        in_stock_ids = [p["id"] for p in res_stock_only["products"]]
        # In-stock items should be: 101 (5), 103 (None), 106 (12)
        assert in_stock_ids == [101, 103, 106], f"Expected [101, 103, 106], got {in_stock_ids}"

        # Step 2: Verify underlying cache still retains ALL products
        cached_entry = client.cache.get("vb_products_uz")
        assert cached_entry is not None, "Cache entry vb_products_uz was not created"
        cached_ids = [p["id"] for p in cached_entry["products"]]
        assert len(cached_ids) == 6, f"Cache was polluted! Expected 6 items, got {len(cached_ids)}"
        assert cached_ids == [101, 103, 106, 102, 104, 105]

        # Step 3: Second call with in_stock_only=False (cache hit)
        res_all = await client.get_products(force_refresh=False, in_stock_only=False)
        all_ids = [p["id"] for p in res_all["products"]]
        assert len(all_ids) == 6, f"Subsequent full call lost items! Got {all_ids}"
        assert all_ids == [101, 103, 106, 102, 104, 105]

        # Step 4: Rapid alternating calls
        for _ in range(5):
            res_sub_true = await client.get_products(force_refresh=False, in_stock_only=True)
            assert len(res_sub_true["products"]) == 3
            res_sub_false = await client.get_products(force_refresh=False, in_stock_only=False)
            assert len(res_sub_false["products"]) == 6


@pytest.mark.asyncio
async def test_probe1_stable_ordering_permutations():
    """
    Stress-test stable ordering under various stock distributions:
    1. All stock > 0
    2. All stock == 0
    3. Mixed stocks (positive, None, zero, negative)
    """
    client = VenteBotClient()
    client.base_url = "https://fake-vb.com"
    client.api_key = "fake-key"

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session), \
         patch("telemetry_service.get_dynamic_config", return_value=60), \
         patch("currency_service.currency_service.get_usd_to_uzs_rate", AsyncMock(return_value=12850.0)):

        # Permutation 1: All products have stock > 0
        all_pos = [
            {"id": 1, "name": "Item A", "price_usd": "10", "stock": 10},
            {"id": 2, "name": "Item B", "price_usd": "15", "stock": 1},
            {"id": 3, "name": "Item C", "price_usd": "20", "stock": 50},
            {"id": 4, "name": "Item D", "price_usd": "25", "stock": 5},
        ]
        mock_resp.json = AsyncMock(return_value={"products": all_pos})
        client.cache.clear()
        res_pos = await client.get_products(force_refresh=True, in_stock_only=False)
        pos_ids = [p["id"] for p in res_pos["products"]]
        assert pos_ids == [1, 2, 3, 4], f"All positive stock order disrupted: {pos_ids}"

        # Permutation 2: All products have stock == 0
        all_zero = [
            {"id": 10, "name": "Zero A", "price_usd": "10", "stock": 0},
            {"id": 11, "name": "Zero B", "price_usd": "15", "stock": 0},
            {"id": 12, "name": "Zero C", "price_usd": "20", "stock": 0},
            {"id": 13, "name": "Zero D", "price_usd": "25", "stock": 0},
        ]
        mock_resp.json = AsyncMock(return_value={"products": all_zero})
        client.cache.clear()
        res_zero = await client.get_products(force_refresh=True, in_stock_only=False)
        zero_ids = [p["id"] for p in res_zero["products"]]
        assert zero_ids == [10, 11, 12, 13], f"All zero stock order disrupted: {zero_ids}"

        # Permutation 3: Mixed stocks with positive, None, zero, negative
        mixed = [
            {"id": 21, "name": "M1 Pos", "price_usd": "10", "stock": 100},       # In-stock (1st)
            {"id": 22, "name": "M2 Zero", "price_usd": "10", "stock": 0},         # Out-of-stock (1st)
            {"id": 23, "name": "M3 None", "price_usd": "10", "stock": None},      # In-stock (2nd)
            {"id": 24, "name": "M4 Neg", "price_usd": "10", "stock": -5},         # Out-of-stock (2nd)
            {"id": 25, "name": "M5 Pos2", "price_usd": "10", "stock": 7},         # In-stock (3rd)
            {"id": 26, "name": "M6 Zero2", "price_usd": "10", "stock": 0},        # Out-of-stock (3rd)
        ]
        mock_resp.json = AsyncMock(return_value={"products": mixed})
        client.cache.clear()
        res_mixed = await client.get_products(force_refresh=True, in_stock_only=False)
        mixed_ids = [p["id"] for p in res_mixed["products"]]
        expected_mixed_ids = [21, 23, 25, 22, 24, 26]
        assert mixed_ids == expected_mixed_ids, f"Mixed stock order disrupted: {mixed_ids}"


@pytest.mark.asyncio
async def test_probe1_string_stock_type_vulnerability():
    """
    ADVERSARIAL VULNERABILITY FINDING TEST:
    Demonstrates that calculate_dynamic_markup_percent raises TypeError
    when stock is passed as a string (e.g. '0' or '5').
    """
    client = VenteBotClient()
    # Direct test of calculate_dynamic_markup_percent
    try:
        client.calculate_dynamic_markup_percent(price_usd=10.0, category="ai", stock="5")
        vulnerable = False
    except TypeError:
        vulnerable = True
    assert vulnerable is True, "calculate_dynamic_markup_percent should raise TypeError with string stock"


# =====================================================================
# PROBE 2: main.py query parameter permutations
# /api/reseller/products?in_stock=...
# =====================================================================

@pytest.mark.asyncio
async def test_probe2_main_query_param_permutations():
    """
    Test how handle_api_reseller_products handles all permutations:
    - Truthy: ?in_stock=true, ?in_stock=1, ?in_stock=yes, ?in_stock=TRUE, ?in_stock=  True
    - Falsy: ?in_stock=false, ?in_stock=0, ?in_stock=no, ?in_stock=FALSE, ?in_stock=NO
    - Empty/Invalid: ?in_stock=, ?in_stock=invalid, ?in_stock=random
    - Omitted: no in_stock parameter
    """
    sample_catalog = [
        {"id": 1, "name": "InStock 1", "stock": 5, "category": "ai", "price_uzs": 50000},
        {"id": 2, "name": "OutOfStock 1", "stock": 0, "category": "ai", "price_uzs": 60000},
        {"id": 3, "name": "InStock 2", "stock": None, "category": "ai", "price_uzs": 70000},
        {"id": 4, "name": "OutOfStock 2", "stock": -2, "category": "ai", "price_uzs": 80000},
    ]

    def create_mock_request(query_params: dict):
        req = MagicMock()
        req.query = query_params
        return req

    with patch("ventebot_service.ventebot_service.get_products", new_callable=AsyncMock) as mock_get_products:
        async def side_effect(lang="uz", force_refresh=False, in_stock_only=False):
            if in_stock_only:
                return {"success": True, "products": [p for p in sample_catalog if p["stock"] is None or p["stock"] > 0]}
            return {"success": True, "products": sample_catalog}

        mock_get_products.side_effect = side_effect

        # Permutations that MUST resolve to in_stock_only=True
        truthy_inputs = ["true", "1", "yes", "TRUE", "True", "YES", "  1  ", "  true  "]
        for val in truthy_inputs:
            req = create_mock_request({"in_stock": val})
            resp = await handle_api_reseller_products(req)
            assert resp.status == 200, f"Failed on {val}"
            last_call = mock_get_products.call_args
            assert last_call.kwargs["in_stock_only"] is True, f"Failed truthy expectation for '{val}': kwargs={last_call.kwargs}"

        # Permutations that MUST resolve to in_stock_only=False
        falsy_inputs = ["false", "0", "no", "FALSE", "False", "NO", "00", "none"]
        for val in falsy_inputs:
            req = create_mock_request({"in_stock": val})
            resp = await handle_api_reseller_products(req)
            assert resp.status == 200, f"Failed on {val}"
            last_call = mock_get_products.call_args
            assert last_call.kwargs["in_stock_only"] is False, f"Failed falsy expectation for '{val}': kwargs={last_call.kwargs}"

        # Empty / invalid string inputs -> MUST resolve to in_stock_only=False
        edge_inputs = ["", "   ", "invalid", "undefined", "null", "2", "-1"]
        for val in edge_inputs:
            req = create_mock_request({"in_stock": val})
            resp = await handle_api_reseller_products(req)
            assert resp.status == 200, f"Failed on {val}"
            last_call = mock_get_products.call_args
            assert last_call.kwargs["in_stock_only"] is False, f"Failed edge expectation for '{val}': kwargs={last_call.kwargs}"

        # No query parameter present -> MUST resolve to in_stock_only=False
        req_none = create_mock_request({})
        resp_none = await handle_api_reseller_products(req_none)
        assert resp_none.status == 200
        last_call = mock_get_products.call_args
        assert last_call.kwargs["in_stock_only"] is False, f"Failed default expectation when query param omitted: kwargs={last_call.kwargs}"


# =====================================================================
# PROBE 3: Telegram bot pagination & header counts (ytbot.py)
# Partitioning and page distribution stress tests
# =====================================================================

def simulate_cb_vb_catalog_logic(cat_products: list, page: int = 0, PAGE_SIZE: int = 8, cat_title: str = "Test Toifa"):
    """
    Exact mirror of ytbot.py lines 8599-8665 logic for testing arbitrary lists.
    """
    def _check_stock(p):
        s = p.get("stock")
        if s is None:
            return True
        try:
            return int(s) > 0
        except (ValueError, TypeError):
            return False

    in_stock_items = [p for p in cat_products if _check_stock(p)]
    out_of_stock_items = [p for p in cat_products if not _check_stock(p)]
    sorted_cat_products = in_stock_items + out_of_stock_items

    available_count = len(in_stock_items)
    out_of_stock_count = len(out_of_stock_items)

    total_items = len(sorted_cat_products)
    total_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)
    clamped_page = min(max(0, page), total_pages - 1)
    page_items = sorted_cat_products[clamped_page * PAGE_SIZE : (clamped_page + 1) * PAGE_SIZE]

    header_text = f"<b>{cat_title}</b> ({available_count} ta mavjud, {out_of_stock_count} ta tugagan)"

    rendered_buttons = []
    for p in page_items:
        p_id = p.get("id")
        name = p.get("name", "Product")
        price_uzs = p.get("price_uzs", 0)
        stock = p.get("stock")
        is_in = _check_stock(p)
        if is_in:
            stock_str = f"({stock} ta)" if stock is not None else ""
            btn_txt = f"{name} | {price_uzs:,} so'm {stock_str}".strip()
            style = "success"
        else:
            btn_txt = f"{name} | {price_uzs:,} so'm (Zaxirada yo'q)"
            style = "warning"
        rendered_buttons.append({"id": p_id, "text": btn_txt, "style": style, "in_stock": is_in})

    return {
        "header": header_text,
        "available_count": available_count,
        "out_of_stock_count": out_of_stock_count,
        "total_items": total_items,
        "total_pages": total_pages,
        "clamped_page": clamped_page,
        "page_items": rendered_buttons,
    }


def test_probe3_scenario_a_10_instock_0_out_of_stock():
    """
    Scenario A: 10 in-stock, 0 out-of-stock.
    Expectations:
    - Header: '(10 ta mavjud, 0 ta tugagan)'
    - Total pages: 2 (PAGE_SIZE=8: Page 0 has 8, Page 1 has 2)
    - All items on Page 0 and Page 1 have style 'success' and no '(Zaxirada yo'q)'
    """
    products = [{"id": i, "name": f"Prod {i}", "price_uzs": 10000 * i, "stock": i} for i in range(1, 11)]

    # Page 0
    p0 = simulate_cb_vb_catalog_logic(products, page=0, PAGE_SIZE=8)
    assert p0["available_count"] == 10
    assert p0["out_of_stock_count"] == 0
    assert "(10 ta mavjud, 0 ta tugagan)" in p0["header"]
    assert p0["total_pages"] == 2
    assert len(p0["page_items"]) == 8
    assert all(item["style"] == "success" for item in p0["page_items"])
    assert all("(Zaxirada yo'q)" not in item["text"] for item in p0["page_items"])

    # Page 1
    p1 = simulate_cb_vb_catalog_logic(products, page=1, PAGE_SIZE=8)
    assert "(10 ta mavjud, 0 ta tugagan)" in p1["header"]
    assert len(p1["page_items"]) == 2
    assert all(item["style"] == "success" for item in p1["page_items"])


def test_probe3_scenario_b_0_instock_10_out_of_stock():
    """
    Scenario B: 0 in-stock, 10 out-of-stock.
    Expectations:
    - Header: '(0 ta mavjud, 10 ta tugagan)'
    - Total pages: 2 (PAGE_SIZE=8: Page 0 has 8, Page 1 has 2)
    - All items on Page 0 and Page 1 have style 'warning' and contain '(Zaxirada yo'q)'
    """
    products = [{"id": i, "name": f"OutProd {i}", "price_uzs": 15000 * i, "stock": 0} for i in range(1, 11)]

    # Page 0
    p0 = simulate_cb_vb_catalog_logic(products, page=0, PAGE_SIZE=8)
    assert p0["available_count"] == 0
    assert p0["out_of_stock_count"] == 10
    assert "(0 ta mavjud, 10 ta tugagan)" in p0["header"]
    assert p0["total_pages"] == 2
    assert len(p0["page_items"]) == 8
    assert all(item["style"] == "warning" for item in p0["page_items"])
    assert all("(Zaxirada yo'q)" in item["text"] for item in p0["page_items"])

    # Page 1
    p1 = simulate_cb_vb_catalog_logic(products, page=1, PAGE_SIZE=8)
    assert "(0 ta mavjud, 10 ta tugagan)" in p1["header"]
    assert len(p1["page_items"]) == 2
    assert all(item["style"] == "warning" for item in p1["page_items"])
    assert all("(Zaxirada yo'q)" in item["text"] for item in p1["page_items"])


def test_probe3_scenario_c_15_instock_5_out_of_stock_across_pages():
    """
    Scenario C: 15 in-stock, 5 out-of-stock across pages (PAGE_SIZE=8).
    Total items = 20 -> 3 pages:
    - Page 0 (indices 0..7): 8 in-stock items
    - Page 1 (indices 8..15): 7 in-stock items (indices 8..14) and 1 out-of-stock item (index 15)
    - Page 2 (indices 16..19): 4 out-of-stock items (indices 16..19)
    """
    in_stock = [{"id": f"IN_{i}", "name": f"InStock {i}", "price_uzs": 20000, "stock": i} for i in range(1, 16)]
    out_of_stock = [{"id": f"OUT_{j}", "name": f"OutOfStock {j}", "price_uzs": 25000, "stock": 0} for j in range(1, 6)]

    mixed_input = out_of_stock[:2] + in_stock[:5] + out_of_stock[2:4] + in_stock[5:] + out_of_stock[4:]
    assert len(mixed_input) == 20

    # Header check across all pages
    for p_idx in [0, 1, 2]:
        p = simulate_cb_vb_catalog_logic(mixed_input, page=p_idx, PAGE_SIZE=8)
        assert p["available_count"] == 15
        assert p["out_of_stock_count"] == 5
        assert "(15 ta mavjud, 5 ta tugagan)" in p["header"]
        assert p["total_pages"] == 3

    # Check Page 0: exactly 8 in-stock items
    p0 = simulate_cb_vb_catalog_logic(mixed_input, page=0, PAGE_SIZE=8)
    assert len(p0["page_items"]) == 8
    assert all(item["in_stock"] is True for item in p0["page_items"])
    assert all(item["style"] == "success" for item in p0["page_items"])
    assert [item["id"] for item in p0["page_items"]] == [f"IN_{i}" for i in range(1, 9)]

    # Check Page 1: exactly 7 in-stock items + 1 out-of-stock item
    p1 = simulate_cb_vb_catalog_logic(mixed_input, page=1, PAGE_SIZE=8)
    assert len(p1["page_items"]) == 8
    p1_in_stock = [item for item in p1["page_items"] if item["in_stock"]]
    p1_out_of_stock = [item for item in p1["page_items"] if not item["in_stock"]]
    assert len(p1_in_stock) == 7
    assert len(p1_out_of_stock) == 1
    assert [item["id"] for item in p1_in_stock] == [f"IN_{i}" for i in range(9, 16)]
    assert p1_out_of_stock[0]["id"] == "OUT_1"
    assert p1_out_of_stock[0]["style"] == "warning"
    assert "(Zaxirada yo'q)" in p1_out_of_stock[0]["text"]

    # Check Page 2: exactly remaining 4 out-of-stock items
    p2 = simulate_cb_vb_catalog_logic(mixed_input, page=2, PAGE_SIZE=8)
    assert len(p2["page_items"]) == 4
    assert all(item["in_stock"] is False for item in p2["page_items"])
    assert all(item["style"] == "warning" for item in p2["page_items"])
    assert [item["id"] for item in p2["page_items"]] == ["OUT_2", "OUT_3", "OUT_4", "OUT_5"]


def test_probe3_page_clamping_boundary():
    """
    Test boundary clamping for negative pages and excessively high pages.
    """
    products = [{"id": i, "name": f"P{i}", "price_uzs": 10000, "stock": 1} for i in range(10)]
    # Negative page
    p_neg = simulate_cb_vb_catalog_logic(products, page=-5, PAGE_SIZE=8)
    assert p_neg["clamped_page"] == 0
    assert len(p_neg["page_items"]) == 8

    # Overflow page
    p_over = simulate_cb_vb_catalog_logic(products, page=999, PAGE_SIZE=8)
    assert p_over["clamped_page"] == 1
    assert len(p_over["page_items"]) == 2
