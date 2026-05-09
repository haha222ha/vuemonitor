import json
import re
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class BaseParser:
    platform: str = "generic"

    def parse(self, raw_text: str, status_code: int, target_id: str) -> dict | None:
        if status_code != 200:
            logger.warning(f"[{self.platform}] Non-200 status: {status_code} for target {target_id}")
            return None
        try:
            return self._extract(raw_text, target_id)
        except Exception as e:
            logger.error(f"[{self.platform}] Parse error for {target_id}: {e}")
            return None

    def _extract(self, raw_text: str, target_id: str) -> dict | None:
        return None


class XHSParser(BaseParser):
    platform = "xhs"

    def _extract(self, raw_text: str, target_id: str) -> dict | None:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return self._extract_html(raw_text, target_id)

        items = []
        if isinstance(data, dict):
            items = data.get("data", data.get("items", []))
            if isinstance(items, dict):
                items = [items]

        for item in items:
            note_id = str(item.get("note_id", item.get("id", "")))
            if note_id == target_id or not target_id:
                return self._parse_note_item(item)

        if items:
            return self._parse_note_item(items[0])

        return None

    def _extract_html(self, raw_text: str, target_id: str) -> dict | None:
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?})\s*</script>', raw_text, re.DOTALL)
        if not state_match:
            return None

        try:
            state = json.loads(state_match.group(1))
            note = state.get("note", state.get("noteDetailMap", {}))
            if isinstance(note, dict):
                detail = note.get("note", note)
                if isinstance(detail, dict):
                    return self._parse_note_item(detail)
        except (json.JSONDecodeError, KeyError):
            pass

        return None

    def _parse_note_item(self, item: dict) -> dict:
        product_name = item.get("title", item.get("display_title", ""))
        if not product_name:
            product_name = item.get("desc", "")[:50] if item.get("desc") else "未知商品"

        interact_info = item.get("interactInfo", {})
        price_str = item.get("price", item.get("xsec_token", ""))

        price = None
        if isinstance(price_str, (int, float)):
            price = Decimal(str(price_str))
        elif isinstance(price_str, str) and price_str:
            price_clean = re.sub(r"[^\d.]", "", price_str)
            if price_clean:
                try:
                    price = Decimal(price_clean)
                except Exception:
                    pass

        return {
            "platform": "xhs",
            "platform_product_id": str(item.get("note_id", item.get("id", ""))),
            "product_name": product_name[:500],
            "shop_name": item.get("user", {}).get("nickname", "") if isinstance(item.get("user"), dict) else None,
            "category": item.get("category", item.get("type", "")),
            "image_url": self._extract_cover(item),
            "product_url": f"https://www.xiaohongshu.com/explore/{item.get('note_id', item.get('id', ''))}",
            "price": float(price) if price else None,
            "sales_count": self._parse_count(interact_info.get("collected_count", item.get("collected_count", 0))),
            "monthly_sales": None,
            "rating": None,
            "review_count": self._parse_count(interact_info.get("comment_count", item.get("comment_count", 0))),
            "favorite_count": self._parse_count(interact_info.get("liked_count", item.get("liked_count", 0))),
        }

    def _extract_cover(self, item: dict) -> str | None:
        cover = item.get("cover", {})
        if isinstance(cover, dict):
            return cover.get("url", cover.get("info_list", [{}])[-1].get("url") if cover.get("info_list") else None)
        if isinstance(cover, str):
            return cover
        image_list = item.get("image_list", [])
        if image_list and isinstance(image_list, list):
            first = image_list[0]
            if isinstance(first, dict):
                return first.get("url", first.get("info_list", [{}])[-1].get("url") if first.get("info_list") else None)
        return None

    @staticmethod
    def _parse_count(val) -> int | None:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            val = val.strip()
            if val.endswith("万"):
                try:
                    return int(float(val[:-1]) * 10000)
                except ValueError:
                    return None
            if val.endswith("w"):
                try:
                    return int(float(val[:-1]) * 10000)
                except ValueError:
                    return None
            try:
                return int(val)
            except ValueError:
                return None
        return None


class DouyinParser(BaseParser):
    platform = "douyin"

    def _extract(self, raw_text: str, target_id: str) -> dict | None:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return self._extract_html(raw_text, target_id)

        aweme = data.get("aweme_detail", data.get("data", {}))
        if not awame:
            return None

        return self._parse_aweme(aweme)

    def _extract_html(self, raw_text: str, target_id: str) -> dict | None:
        render_match = re.search(r'window\._ROUTER_DATA\s*=\s*({.+?})\s*</script>', raw_text, re.DOTALL)
        if not render_match:
            return None
        try:
            router_data = json.loads(render_match.group(1))
            for key in router_data:
                if "detail" in key.lower():
                    aweme = router_data[key].get("awemeDetail", router_data[key])
                    if isinstance(aweme, dict):
                        return self._parse_aweme(aweme)
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _parse_aweme(self, item: dict) -> dict:
        product_name = item.get("desc", "")[:500]
        if not product_name:
            product_name = "抖音商品"

        author = item.get("author", {})
        statistics = item.get("statistics", {})

        product_info = item.get("product_info", {})
        price = None
        if isinstance(product_info, dict) and product_info.get("price"):
            try:
                price = Decimal(str(product_info["price"]).replace(",", ""))
            except Exception:
                pass

        return {
            "platform": "douyin",
            "platform_product_id": str(item.get("aweme_id", item.get("id", ""))),
            "product_name": product_name,
            "shop_name": author.get("nickname", "") if isinstance(author, dict) else None,
            "category": item.get("category", ""),
            "image_url": item.get("cover", {}).get("url_list", [None])[0] if isinstance(item.get("cover"), dict) else None,
            "product_url": f"https://www.douyin.com/video/{item.get('aweme_id', '')}",
            "price": float(price) if price else None,
            "sales_count": None,
            "monthly_sales": None,
            "rating": None,
            "review_count": statistics.get("comment_count"),
            "favorite_count": statistics.get("digg_count"),
        }


class TaobaoParser(BaseParser):
    platform = "taobao"

    def _extract(self, raw_text: str, target_id: str) -> dict | None:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return self._extract_html(raw_text, target_id)

        detail = data.get("data", data.get("item", data))
        if not detail:
            return None

        return self._parse_detail(detail, target_id)

    def _extract_html(self, raw_text: str, target_id: str) -> dict | None:
        item_match = re.search(r'var\s+g_config\s*=\s*({.+?});', raw_text, re.DOTALL)
        if not item_match:
            item_match = re.search(r'"item"\s*:\s*({.+?})', raw_text, re.DOTALL)
        if not item_match:
            return None
        try:
            config = json.loads(item_match.group(1))
            return self._parse_detail(config, target_id)
        except (json.JSONDecodeError, KeyError):
            return None

    def _parse_detail(self, detail: dict, target_id: str) -> dict:
        price = None
        price_info = detail.get("priceInfo", detail.get("priceWap", {}))
        if isinstance(price_info, dict):
            price_str = price_info.get("price", price_info.get("promotionPrice", "0"))
            if isinstance(price_str, str):
                price_clean = re.sub(r"[^\d.]", "", price_str.split("-")[0])
                if price_clean:
                    try:
                        price = Decimal(price_clean)
                    except Exception:
                        pass
            elif isinstance(price_str, (int, float)):
                price = Decimal(str(price_str))

        title = detail.get("title", detail.get("name", ""))

        return {
            "platform": "taobao",
            "platform_product_id": str(detail.get("itemId", detail.get("item_id", target_id))),
            "product_name": title[:500] if title else "淘宝商品",
            "shop_name": detail.get("seller", {}).get("shopName", detail.get("shopName", "")),
            "category": detail.get("category", ""),
            "image_url": detail.get("pic", detail.get("mainPic", "")),
            "product_url": f"https://item.taobao.com/item.htm?id={target_id}",
            "price": float(price) if price else None,
            "sales_count": self._parse_taobao_count(detail.get("sellCount", detail.get("monthSellCount", 0))),
            "monthly_sales": self._parse_taobao_count(detail.get("monthSellCount", 0)),
            "rating": None,
            "review_count": self._parse_taobao_count(detail.get("commentCount", 0)),
            "favorite_count": None,
        }

    @staticmethod
    def _parse_taobao_count(val) -> int | None:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            val = val.strip()
            if val.endswith("万+"):
                try:
                    return int(float(val[:-2]) * 10000)
                except ValueError:
                    return None
            if val.endswith("万"):
                try:
                    return int(float(val[:-1]) * 10000)
                except ValueError:
                    return None
            if val.endswith("+"):
                val = val[:-1]
            try:
                return int(val)
            except ValueError:
                return None
        return None


class JDParser(BaseParser):
    platform = "jd"

    def _extract(self, raw_text: str, target_id: str) -> dict | None:
        return self._extract_html(raw_text, target_id)

    def _extract_html(self, raw_text: str, target_id: str) -> dict | None:
        name_match = re.search(r'<title>(.*?)</title>', raw_text)
        product_name = name_match.group(1).replace(" - 京东", "").strip() if name_match else "京东商品"

        price = None
        price_match = re.search(r'"p"\s*:\s*"([\d.]+)"', raw_text)
        if not price_match:
            price_match = re.search(r'"price"\s*:\s*"([\d.]+)"', raw_text)
        if price_match:
            try:
                price = Decimal(price_match.group(1))
            except Exception:
                pass

        image_url = None
        img_match = re.search(r'"img"\s*:\s*"(//img[^"]+)"', raw_text)
        if img_match:
            image_url = "https:" + img_match.group(1)

        shop_name = None
        shop_match = re.search(r'"shopName"\s*:\s*"([^"]+)"', raw_text)
        if shop_match:
            shop_name = shop_match.group(1)

        comment_count = None
        comment_match = re.search(r'"commentCount"\s*:\s*(\d+)', raw_text)
        if comment_match:
            comment_count = int(comment_match.group(1))

        return {
            "platform": "jd",
            "platform_product_id": target_id,
            "product_name": product_name[:500],
            "shop_name": shop_name,
            "category": None,
            "image_url": image_url,
            "product_url": f"https://item.jd.com/{target_id}.html",
            "price": float(price) if price else None,
            "sales_count": None,
            "monthly_sales": None,
            "rating": None,
            "review_count": comment_count,
            "favorite_count": None,
        }


class PDDParser(BaseParser):
    platform = "pdd"

    def _extract(self, raw_text: str, target_id: str) -> dict | None:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return None

        goods = data.get("goods", data.get("data", data))
        if not goods:
            return None

        return self._parse_goods(goods, target_id)

    def _parse_goods(self, goods: dict, target_id: str) -> dict:
        price = None
        min_price = goods.get("min_group_price", goods.get("price", 0))
        if min_price:
            try:
                price_val = float(min_price) / 100 if float(min_price) > 10000 else float(min_price)
                price = Decimal(str(round(price_val, 2)))
            except Exception:
                pass

        thumb_url = goods.get("thumb_url", goods.get("image_url", ""))
        if thumb_url and not thumb_url.startswith("http"):
            thumb_url = "https:" + thumb_url

        return {
            "platform": "pdd",
            "platform_product_id": str(goods.get("goods_id", target_id)),
            "product_name": goods.get("goods_name", "拼多多商品")[:500],
            "shop_name": goods.get("mall_name", ""),
            "category": str(goods.get("cat_id", "")),
            "image_url": thumb_url,
            "product_url": f"https://mobile.yangkeduo.com/goods.html?goods_id={target_id}",
            "price": float(price) if price else None,
            "sales_count": goods.get("sales_tip", None),
            "monthly_sales": None,
            "rating": None,
            "review_count": goods.get("review_count", None),
            "favorite_count": None,
        }


PARSER_MAP: dict[str, BaseParser] = {
    "xhs": XHSParser(),
    "douyin": DouyinParser(),
    "taobao": TaobaoParser(),
    "jd": JDParser(),
    "pdd": PDDParser(),
}


def get_parser(platform: str) -> BaseParser:
    return PARSER_MAP.get(platform, BaseParser())
