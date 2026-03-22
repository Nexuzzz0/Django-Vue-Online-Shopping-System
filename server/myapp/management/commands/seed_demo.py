from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings as dj_settings
from django.utils import timezone

import json
import os
import re
from pathlib import Path
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import quote_plus
import random

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from myapp import utils
from myapp.models import (
    User,
    Classification,
    Tag,
    Thing,
    Comment,
    Order,
    OrderLog,
    Record,
    Address,
    Banner,
    Ad,
    Notice,
)


class Command(BaseCommand):
    help = "Seed demo data for local development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--remote-images",
            action="store_true",
            help="Download royalty-free images into demo_images (best-effort, falls back if offline).",
        )
        parser.add_argument(
            "--force-remote-images",
            action="store_true",
            help="Force re-download remote images and overwrite existing demo_images.",
        )
        parser.add_argument(
            "--ignore-product-images",
            action="store_true",
            help="Ignore demo_images/products even if present; use built-in product templates only.",
        )

    def _list_images(self, directory: Path, *, recursive: bool = False):
        if not directory.exists() or not directory.is_dir():
            return []
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        it = directory.rglob("*") if recursive else directory.iterdir()
        assets = [p for p in it if p.is_file() and p.suffix.lower() in exts]
        assets.sort(key=lambda p: str(p).lower())
        return assets

    def _get_local_assets(self):
        """Backward-compatible: flat images directly under demo_images/"""
        assets_dir = Path(dj_settings.BASE_DIR) / "demo_images"
        return self._list_images(assets_dir, recursive=False)

    def _get_bucket_assets(self, *, assets_dir: Path, bucket: str, classification_title: str | None = None):
        """Prefer user-prepared images under demo_images/<bucket>/...; fall back to generic ones."""
        classification_slug_map = {
            "数码": "digital",
            "家居": "home",
            "书籍": "book",
        }

        # Allow remote downloads to live under demo_images/_remote without interfering with user images.
        generic = []
        generic += self._list_images(assets_dir, recursive=False)
        generic += self._list_images(assets_dir / "_remote", recursive=True)

        bucket_dir = assets_dir / bucket
        picked = []
        if classification_title:
            slug = classification_slug_map.get(classification_title)
            if slug:
                picked += self._list_images(bucket_dir / slug, recursive=True)
        picked += self._list_images(bucket_dir, recursive=True)

        return picked if picked else generic

    def _category_title_from_dirname(self, name: str) -> str | None:
        n = (name or "").strip().lower()
        mapping = {
            "digital": "数码",
            "digitals": "数码",
            "electronics": "数码",
            "数码": "数码",
            "3c": "数码",
            "home": "家居",
            "house": "家居",
            "家居": "家居",
            "book": "书籍",
            "books": "书籍",
            "书籍": "书籍",
        }
        return mapping.get(n)

    def _read_sidecar_meta(self, image_path: Path) -> dict | None:
        meta_path = image_path.with_suffix(".json")
        if not meta_path.exists() or not meta_path.is_file():
            return None
        try:
            text = meta_path.read_text(encoding="utf-8")
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _parse_filename_tokens(self, stem: str) -> list[str]:
        raw = (stem or "").strip()
        # Prefer double-underscore delimiter; fallback to hyphen/underscore.
        if "__" in raw:
            parts = [p.strip() for p in raw.split("__") if p.strip()]
        else:
            parts = re.split(r"[-_\s]+", raw)
            parts = [p.strip() for p in parts if p.strip()]
        return parts

    def _infer_price(self, category_title: str) -> str:
        if category_title == "数码":
            return str(random.choice([99, 149, 199, 299, 399, 599, 899, 1299, 1999, 2999]))
        if category_title == "家居":
            return str(random.choice([29, 39, 49, 59, 79, 99, 129, 159, 199, 299, 399]))
        if category_title == "书籍":
            return str(random.choice([29, 39, 49, 59, 69, 79, 89, 99]))
        return str(random.choice([49, 99, 199]))

    def _build_product_from_image(self, *, image_path: Path, category_title: str | None) -> dict | None:
        meta = self._read_sidecar_meta(image_path) or {}
        # category: meta overrides folder
        category = meta.get("classification") or category_title
        if category:
            category = str(category).strip()
        if category not in {"数码", "家居", "书籍"}:
            category = category_title or "数码"

        # Support explicit title/subtitle/specs/highlights in meta
        title = (meta.get("title") or "").strip()
        subtitle = (meta.get("subtitle") or "").strip()
        price = str(meta.get("price") or "").strip()
        repertory = meta.get("repertory")

        tokens = self._parse_filename_tokens(image_path.stem)
        joined = " ".join(tokens)
        # Remove obvious price tokens from semantic parsing so titles don't include "¥599".
        tokens_clean = [
            t
            for t in tokens
            if not re.fullmatch(r"(?:¥|￥)?\s*\d{2,5}(?:\s*元)?", str(t).strip())
        ]

        # Allow price embedded like 199/1999/¥199
        if not price:
            for t in tokens:
                s = str(t).strip()
                m1 = re.search(r"(?:¥|￥)\s*(\d{2,5})", s)
                if m1:
                    price = m1.group(1)
                    break
                m2 = re.search(r"^(\d{2,5})\s*元$", s)
                if m2:
                    price = m2.group(1)
                    break
        if not price:
            price = self._infer_price(category)

        if repertory is None:
            repertory = random.randint(12, 88)
        try:
            repertory = int(repertory)
        except (TypeError, ValueError):
            repertory = random.randint(12, 88)

        brand = str(meta.get("brand") or "").strip()
        model = str(meta.get("model") or "").strip()
        variant = str(meta.get("variant") or "").strip()

        # If user didn't provide structured meta, use filename tokens.
        if not brand and tokens_clean:
            brand = tokens_clean[0]
        if not model and len(tokens_clean) >= 2:
            model = tokens_clean[1]
        if not variant and len(tokens_clean) >= 3:
            # Best-effort join the rest; keep it short.
            variant = " ".join(tokens_clean[2:5]).strip()

        if not title:
            if category == "书籍":
                # Prefer bracketed/quoted book name in filename
                book_name = "".join(tokens_clean[:3]).strip() if tokens_clean else image_path.stem
                book_name = book_name.replace("《", "").replace("》", "").strip()
                title = f"《{book_name}》"
            else:
                left = " ".join([p for p in [brand, model, variant] if p]).strip()
                title = left if left else image_path.stem

        if not subtitle:
            if category == "数码":
                subtitle = "正品渠道｜现货速发｜一年质保（演示）"
            elif category == "家居":
                subtitle = "精选材质｜易清洁｜居家好物（演示）"
            else:
                subtitle = "正版图书｜全新塑封｜48小时发货（演示）"

        specs = meta.get("specs")
        if isinstance(specs, dict):
            specs_list = [f"{k}：{v}" for k, v in specs.items()]
        elif isinstance(specs, list):
            specs_list = [str(s) for s in specs if str(s).strip()]
        else:
            # Heuristic specs from tokens
            specs_list = []
            if category == "数码":
                if model:
                    specs_list.append(f"型号：{model}")
                if variant:
                    specs_list.append(f"版本：{variant}")
                specs_list += ["发货：48小时内发货（演示）", "售后：7天无理由（演示）"]
            elif category == "家居":
                if model:
                    specs_list.append(f"品名：{model}")
                if variant:
                    specs_list.append(f"规格：{variant}")
                specs_list += ["材质：以实物为准（演示）", "发货：48小时内发货（演示）"]
            else:
                book_name = title.strip("《》")
                specs_list += [f"书名：{book_name}", "版本：全新正版（演示）", "装帧：平装/精装随机（演示）"]

        highlights = meta.get("highlights")
        if isinstance(highlights, list):
            highlights_list = [str(h) for h in highlights if str(h).strip()]
        else:
            if category == "数码":
                highlights_list = ["性能稳定，日常够用", "包装完好，配件齐全（演示）", "支持多种场景使用"]
            elif category == "家居":
                highlights_list = ["颜值在线，提升氛围感", "做工细致，使用顺手", "收纳/清洁更省心"]
            else:
                highlights_list = ["内容系统，适合进阶", "配套案例/练习更易上手", "适合收藏与送礼"]

        tag_titles = meta.get("tag_titles")
        if not isinstance(tag_titles, list):
            tag_titles = ["包邮"]
        tag_titles = [str(t) for t in tag_titles if str(t).strip()]

        return {
            "title": title.strip(),
            "subtitle": subtitle.strip(),
            "classification": category,
            "price": str(price).strip(),
            "repertory": repertory,
            "tag_titles": tag_titles,
            "specs": specs_list,
            "highlights": highlights_list,
            "_image_asset": image_path,
        }

    def _load_products_from_user_images(self, *, assets_dir: Path, limit: int = 60) -> list[dict]:
        products_dir = assets_dir / "products"
        if not products_dir.exists() or not products_dir.is_dir():
            return []

        items: list[dict] = []
        # One category per folder: products/digital|home|book (also allow Chinese folder names).
        for category_dir in sorted([p for p in products_dir.iterdir() if p.is_dir()], key=lambda p: str(p).lower()):
            category_title = self._category_title_from_dirname(category_dir.name)
            for img in self._list_images(category_dir, recursive=True):
                product = self._build_product_from_image(image_path=img, category_title=category_title)
                if product:
                    items.append(product)
                    if len(items) >= limit:
                        return items
        return items

    def _download_bytes(self, url: str, timeout: int = 20):
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()

    def _looks_like_nature(self, img: Image.Image) -> bool:
        """Very small heuristic to reject pure landscapes (lots of saturated green/blue)."""
        small = img.convert("RGB").resize((64, 64))
        pixels = small.getdata()
        total = 64 * 64
        natureish = 0
        for r, g, b in pixels:
            # ignore very dark/light
            mx = max(r, g, b)
            mn = min(r, g, b)
            if mx < 35 or mx > 245:
                continue
            sat = (mx - mn) / max(1, mx)
            if sat < 0.22:
                continue
            # green or blue dominance
            if (g > r + 18 and g > b + 8) or (b > r + 18 and b > g + 8):
                natureish += 1
        return (natureish / max(1, total)) > 0.40

    def _ensure_remote_assets(self, *, target_dir: Path, count: int = 18, force: bool = False):
        # Keep remote assets isolated so user-prepared images are not overwritten.
        target_dir = target_dir / "_remote"
        target_dir.mkdir(parents=True, exist_ok=True)

        # If user already provided local images, don't overwrite.
        existing = [p for p in target_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        if (not force) and len(existing) >= max(6, count // 2):
            return

        # Prefer Unsplash Source (royalty-free). Fallback to Picsum if blocked.
        queries = [
            # packshot / studio / white background biased
            "smartphone packshot white background",
            "laptop packshot white background",
            "headphones packshot white background",
            "camera packshot white background",
            "keyboard packshot white background",
            "mouse packshot white background",
            "smartwatch packshot white background",
            "usb charger packshot white background",
            "desk lamp packshot white background",
            "electric kettle packshot white background",
            "humidifier packshot white background",
            "storage box packshot white background",
            "pillow packshot white background",
            "book cover isolated on white",
            "notebook stationery isolated on white",
            "backpack isolated on white",
            "chair isolated on white",
            "home appliance packshot white background",
        ]

        downloaded = 0
        picks = queries[:count]
        for i, q in enumerate(picks, start=1):
            safe_q = quote_plus(q)
            out = target_dir / f"remote_{i:02d}.jpg"
            if (not force) and out.exists() and out.stat().st_size > 10_000:
                downloaded += 1
                continue

            # Try a few times to avoid nature/landscape results.
            ok = False
            for attempt in range(1, 5):
                sig = random.randint(1, 10_000_000)
                unsplash_url = f"https://source.unsplash.com/1600x1200/?{safe_q}&sig={sig}"
                picsum_url = f"https://picsum.photos/seed/demo-shop-{i}-{attempt}/1600/1200"

                for url in (unsplash_url, picsum_url):
                    try:
                        data = self._download_bytes(url)
                        if not data or len(data) <= 10_000:
                            continue
                        img = Image.open(BytesIO(data)).convert("RGB")
                        if self._looks_like_nature(img):
                            continue
                        out.write_bytes(data)
                        downloaded += 1
                        ok = True
                        break
                    except (URLError, HTTPError, TimeoutError, ValueError, OSError):
                        continue
                if ok:
                    break

            # Worst-case: accept the last successfully downloaded one even if it looks like nature.
            if not ok:
                try:
                    data = self._download_bytes(f"https://picsum.photos/seed/demo-shop-fallback-{i}/1600/1200")
                    if data and len(data) > 10_000:
                        out.write_bytes(data)
                        downloaded += 1
                except (URLError, HTTPError, TimeoutError, ValueError):
                    pass

        if downloaded:
            self.stdout.write(self.style.WARNING(f"Downloaded {downloaded} remote demo images into {target_dir}"))

    def _make_image_bytes_from_asset(
        self,
        *,
        asset_path: Path,
        size,
        title,
        subtitle="",
        title_size=64,
        sub_size=30,
        accent=(59, 130, 246),
        draw_text: bool = True,
    ):
        src = Image.open(str(asset_path)).convert("RGB")
        w, h = size
        base = Image.new("RGB", (w, h), (255, 255, 255))

        # Build a washed/blurred background so even non-white photos look like packshots.
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        bg = ImageOps.fit(src, (w, h), method=resample, centering=(0.5, 0.5)).filter(ImageFilter.GaussianBlur(radius=14))
        bg = Image.blend(bg, Image.new("RGB", (w, h), (255, 255, 255)), 0.65)
        base.paste(bg, (0, 0))

        # Foreground image placed on white canvas with shadow.
        fg_w = int(w * 0.64)
        fg_h = int(h * 0.64)
        fg = ImageOps.fit(src, (fg_w, fg_h), method=resample, centering=(0.5, 0.5))

        # Rounded mask
        radius = 24
        mask = Image.new("L", (fg_w, fg_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, fg_w, fg_h], radius=radius, fill=255)

        # Shadow
        shadow = Image.new("RGBA", (fg_w + 20, fg_h + 20), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle([10, 10, fg_w + 10, fg_h + 10], radius=radius, fill=(0, 0, 0, 70))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))

        x = (w - fg_w) // 2
        y = int(h * 0.12)
        base_rgba = base.convert("RGBA")
        base_rgba.alpha_composite(shadow, (x - 10, y - 4))
        base_rgba.paste(fg.convert("RGBA"), (x, y), mask)

        if draw_text and (title or subtitle):
            draw = ImageDraw.Draw(base_rgba)
            font_title = self._load_font(title_size)
            font_sub = self._load_font(sub_size)

            # Accent bar + text at bottom
            bar_h = int(h * 0.12)
            draw.rectangle([0, h - bar_h, w, h], fill=(255, 255, 255, 220))
            draw.rectangle([0, h - bar_h, 10, h], fill=accent)

            padding = 22
            text_y = h - bar_h + 10
            if title:
                draw.text((padding + 12, text_y), title, fill=(15, 23, 42), font=font_title)
            if subtitle:
                draw.text((padding + 12, text_y + title_size + 2), subtitle, fill=(71, 85, 105), font=font_sub)

        out = base_rgba.convert("RGB")
        buf = BytesIO()
        out.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    def _load_font(self, size):
        candidates = [
            (r"C:\\Windows\\Fonts\\msyh.ttc", {"index": 0}),
            (r"C:\\Windows\\Fonts\\msyh.ttf", {}),
            (r"C:\\Windows\\Fonts\\simhei.ttf", {}),
            (r"C:\\Windows\\Fonts\\arial.ttf", {}),
        ]
        for path, kwargs in candidates:
            if not os.path.exists(path):
                continue
            try:
                return ImageFont.truetype(path, size=size, **kwargs)
            except Exception:
                continue
        return ImageFont.load_default()

    def _make_image_bytes(self, *, size, bg_color, title, subtitle="", title_size=56, sub_size=28, accent=(59, 130, 246), draw_text: bool = True):
        img = Image.new("RGB", size, bg_color)
        draw = ImageDraw.Draw(img)
        font_title = self._load_font(title_size)
        font_sub = self._load_font(sub_size)
        font_small = self._load_font(22)

        padding = 34
        text_color = (15, 23, 42)
        muted = (100, 116, 139)

        w, h = size

        # accent blocks (make thumbnails readable)
        draw.rectangle([0, 0, w, 10], fill=accent)
        draw.rectangle([0, 0, 14, h], fill=accent)

        if draw_text and (title or subtitle):
            # big title
            draw.text((padding, padding), title, fill=text_color, font=font_title)

            if subtitle:
                draw.text((padding, padding + title_size + 8), subtitle, fill=muted, font=font_sub)

            # bottom badge
            badge_h = 64
            draw.rectangle([padding, h - badge_h - padding, w - padding, h - padding], fill=(255, 255, 255), outline=(226, 232, 240), width=2)
            draw.text((padding + 18, h - badge_h - padding + 18), "DEMO DATA", fill=accent, font=font_small)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()

    def handle(self, *args, **options):
        now = timezone.now()

        assets_dir = Path(dj_settings.BASE_DIR) / "demo_images"
        if options.get("remote_images"):
            self._ensure_remote_assets(
                target_dir=assets_dir,
                count=14,
                force=bool(options.get("force_remote_images")),
            )

        # Flat assets for backward compatibility; bucketed assets are preferred where available.
        assets = self._get_local_assets()

        # Hide legacy demo items that mention "二手" so the storefront only shows new products.
        Thing.objects.filter(title__contains="二手").update(status="1")
        Thing.objects.filter(description__contains="二手").update(status="1")

        # Purge legacy banners/ads so old scenic placeholders do not remain in the carousel.
        for b in Banner.objects.all():
            if b.image and str(b.image.name).startswith("banner/"):
                b.image.delete(save=False)
        Banner.objects.all().delete()

        for a in Ad.objects.all():
            if a.image and str(a.image.name).startswith("ad/"):
                a.image.delete(save=False)
        Ad.objects.all().delete()

        admin, _ = User.objects.get_or_create(
            username="admin111",
            defaults={
                "password": utils.md5value("admin111"),
                "role": "1",
                "status": "0",
                "nickname": "管理员",
                "create_time": now,
            },
        )

        user_templates = [
            {
                "username": "user01",
                "nickname": "小明",
                "mobile": "13800000001",
                "email": "user01@example.com",
                "gender": "M",
                "description": "热爱网购",
            },
            {
                "username": "user02",
                "nickname": "小红",
                "mobile": "13800000002",
                "email": "user02@example.com",
                "gender": "F",
                "description": "喜欢收藏好物",
            },
            {
                "username": "user03",
                "nickname": "小华",
                "mobile": "13800000003",
                "email": "user03@example.com",
                "gender": "M",
                "description": "喜欢数码产品",
            },
            {
                "username": "user04",
                "nickname": "小芳",
                "mobile": "13800000004",
                "email": "user04@example.com",
                "gender": "F",
                "description": "爱读书",
            },
            {
                "username": "user05",
                "nickname": "小强",
                "mobile": "13800000005",
                "email": "user05@example.com",
                "gender": "M",
                "description": "关注家居好物",
            },
        ]
        users = []
        for tpl in user_templates:
            user, _ = User.objects.get_or_create(
                username=tpl["username"],
                defaults={
                    "password": utils.md5value("123456"),
                    "role": "2",
                    "status": "0",
                    "nickname": tpl["nickname"],
                    "mobile": tpl["mobile"],
                    "email": tpl["email"],
                    "gender": tpl["gender"],
                    "description": tpl["description"],
                    "create_time": now,
                },
            )
            # avatar
            if user.avatar and str(user.avatar.name).startswith("avatar/"):
                user.avatar.delete(save=False)
            if not user.avatar:
                avatar_bytes = self._make_image_bytes(
                    size=(512, 512),
                    bg_color=(240, 249, 255),
                    title=tpl["nickname"],
                    subtitle="会员头像（演示）",
                    title_size=64,
                    sub_size=32,
                    accent=(14, 165, 233),
                )
                user.avatar.save(f"avatar_{user.username}.jpg", ContentFile(avatar_bytes), save=True)
            users.append(user)

        class_titles = ["数码", "书籍", "家居"]
        classifications = []
        for title in class_titles:
            obj, _ = Classification.objects.get_or_create(
                title=title,
                defaults={"pid": -1, "create_time": now},
            )
            classifications.append(obj)

        tag_titles = ["成色新", "限时优惠", "包邮", "热门"]
        tags = []
        for title in tag_titles:
            obj, _ = Tag.objects.get_or_create(title=title, defaults={"create_time": now})
            tags.append(obj)

        tag_map = {t.title: t for t in tags}

        def build_desc(subtitle: str, specs: list[str], highlights: list[str]) -> str:
            lines = [subtitle.strip(), "", "【规格参数】"]
            lines += [f"- {s}" for s in specs]
            lines += ["", "【卖点】"]
            lines += [f"- {h}" for h in highlights]
            lines += ["", "【服务保障】", "- 7天无理由退换（演示）", "- 48小时内发货（演示）", "- 官方正品渠道（演示）"]
            text = "\n".join(lines)
            # keep within model limit
            return text[:980]

        classification_map = {c.title: c for c in classifications}

        # Optional: if user prepared product images, prefer them to generate items that match the photos.
        user_image_products: list[dict] = []
        if not options.get("ignore_product_images"):
            user_image_products = self._load_products_from_user_images(assets_dir=assets_dir, limit=60)

        user_product_assets: list[Path] = []
        for p in user_image_products:
            ap = p.get("_image_asset")
            if isinstance(ap, Path) and ap.exists():
                user_product_assets.append(ap)

        # If user provided product images, keep the storefront clean:
        # show only these products (status=0) and hide/cleanup older demo items.
        kept_titles: set[str] = set()
        if user_image_products:
            kept_titles = {str(p.get("title") or "").strip() for p in user_image_products if str(p.get("title") or "").strip()}
            if kept_titles:
                stale_qs = Thing.objects.exclude(title__in=list(kept_titles))
                stale_ids = list(stale_qs.values_list("id", flat=True))

                # Delete related demo data so pages don't show random old items.
                if stale_ids:
                    Comment.objects.filter(thing_id__in=stale_ids).delete()
                    OrderLog.objects.filter(thing_id__in=stale_ids).delete()
                    Order.objects.filter(thing_id__in=stale_ids).delete()
                    Record.objects.filter(thing_id__in=stale_ids).delete()

                # Down-shelf and remove old cover files.
                for t in stale_qs.select_related(None):
                    if t.cover and str(t.cover.name).startswith("cover/"):
                        t.cover.delete(save=False)
                    t.cover = None
                    t.status = "1"
                    t.save(update_fields=["cover", "status"])

        products = user_image_products if user_image_products else [
            # 数码
            {
                "title": "Aurora A3 真无线降噪耳机",
                "subtitle": "蓝牙5.3｜主动降噪｜游戏低延迟",
                "classification": "数码",
                "price": "199",
                "repertory": 32,
                "tag_titles": ["热门", "包邮"],
                "specs": ["连接：Bluetooth 5.3", "续航：单次6h，配充电盒约30h", "防护：IPX4", "接口：Type-C"],
                "highlights": ["通勤降噪更安静", "双麦通话更清晰", "开盖即连，操作简单"],
            },
            {
                "title": "Nebula 20000mAh 快充充电宝 22.5W",
                "subtitle": "PD快充｜双向快充｜三口输出",
                "classification": "数码",
                "price": "149",
                "repertory": 58,
                "tag_titles": ["限时优惠", "包邮"],
                "specs": ["容量：20000mAh", "输出：最大22.5W", "接口：USB-A*2 + Type-C*1", "重量：约390g"],
                "highlights": ["上班通勤一天够用", "支持多设备同时充电", "安全芯片，过充保护"],
            },
            {
                "title": "Polar K87 机械键盘 87键",
                "subtitle": "PBT键帽｜热插拔｜白光背光",
                "classification": "数码",
                "price": "269",
                "repertory": 25,
                "tag_titles": ["热门"],
                "specs": ["布局：87键（TKL）", "连接：USB有线", "键帽：PBT双色注塑", "轴体：线性轴（可热插拔）"],
                "highlights": ["打字手感清脆，办公游戏两用", "热插拔更易维护", "键帽耐磨不打油"],
            },
            {
                "title": "Orbit 6合1 Type-C 扩展坞",
                "subtitle": "HDMI 4K｜千兆网口｜PD供电",
                "classification": "数码",
                "price": "129",
                "repertory": 80,
                "tag_titles": ["包邮"],
                "specs": ["接口：HDMI*1 + USB3.0*2 + 网口*1 + 读卡*1 + PD*1", "分辨率：最高4K@30Hz", "材质：铝合金外壳", "线长：约15cm"],
                "highlights": ["一线扩展，笔记本更省心", "散热更好不易发烫", "会议投屏更稳定"],
            },
            {
                "title": "Vega 27W GaN 氮化镓快充套装",
                "subtitle": "双口输出｜折叠插脚｜兼容多协议",
                "classification": "数码",
                "price": "89",
                "repertory": 120,
                "tag_titles": ["限时优惠"],
                "specs": ["功率：最大27W", "接口：USB-C*1 + USB-A*1", "协议：PD/QC/AFC", "尺寸：约45×35×30mm"],
                "highlights": ["体积小，出差更方便", "多协议兼容手机/平板", "智能分流更安全"],
            },
            {
                "title": "Nova 1TB 移动固态硬盘",
                "subtitle": "USB3.2｜高速读写｜铝合金外壳",
                "classification": "数码",
                "price": "399",
                "repertory": 18,
                "tag_titles": ["热门", "包邮"],
                "specs": ["容量：1TB", "接口：USB 3.2 Gen2 Type-C", "速度：最高1050MB/s（演示）", "兼容：Windows/macOS"],
                "highlights": ["大文件传输更快", "金属外壳散热更稳", "支持手机直连（需OTG）"],
            },
            {
                "title": "Stella 10.2英寸 蓝光护眼平板",
                "subtitle": "学习办公｜分屏多任务｜护眼模式",
                "classification": "数码",
                "price": "899",
                "repertory": 9,
                "tag_titles": ["热门"],
                "specs": ["屏幕：10.2英寸", "内存：6GB+128GB", "网络：Wi-Fi", "续航：约10小时（演示）"],
                "highlights": ["网课阅读更舒服", "分屏记笔记更高效", "护眼模式更适合长时间使用"],
            },
            {
                "title": "Comet 2K 27英寸 显示器",
                "subtitle": "IPS广色域｜低蓝光｜可升降支架",
                "classification": "数码",
                "price": "1199",
                "repertory": 6,
                "tag_titles": ["包邮"],
                "specs": ["尺寸：27英寸", "分辨率：2560×1440", "面板：IPS", "接口：HDMI/DP"],
                "highlights": ["办公观影更细腻", "支架可调更舒适", "长时间使用更护眼"],
            },

            # 家居
            {
                "title": "NordHome 3L 静音加湿器",
                "subtitle": "细雾加湿｜缺水断电｜卧室适用",
                "classification": "家居",
                "price": "159",
                "repertory": 40,
                "tag_titles": ["热门", "包邮"],
                "specs": ["容量：3L", "噪音：≤35dB（演示）", "续航：约10h", "功能：缺水断电"],
                "highlights": ["夜间不打扰睡眠", "干燥季节更舒适", "上加水更方便"],
            },
            {
                "title": "Mori 1.5L 电热水壶 304不锈钢",
                "subtitle": "快速烧水｜自动断电｜一键开盖",
                "classification": "家居",
                "price": "99",
                "repertory": 65,
                "tag_titles": ["限时优惠", "包邮"],
                "specs": ["容量：1.5L", "功率：1500W", "内胆：304不锈钢", "安全：沸腾断电/干烧保护"],
                "highlights": ["烧水快，早八不迟到", "多重安全保护更放心", "易清洁不残留异味"],
            },
            {
                "title": "Lumen 5W 护眼台灯",
                "subtitle": "无频闪｜三档色温｜触控调光",
                "classification": "家居",
                "price": "79",
                "repertory": 90,
                "tag_titles": ["包邮"],
                "specs": ["功率：5W", "色温：3000K/4500K/6500K", "供电：USB供电", "操作：触控"],
                "highlights": ["学习办公更护眼", "三档色温适配不同场景", "灯臂可调更灵活"],
            },
            {
                "title": "CleanPro 迷你手持吸尘器",
                "subtitle": "强吸力｜一键倒尘｜车家两用",
                "classification": "家居",
                "price": "219",
                "repertory": 22,
                "tag_titles": ["热门"],
                "specs": ["吸力：约8000Pa（演示）", "续航：约25min", "充电：Type-C", "配件：扁吸嘴/毛刷"],
                "highlights": ["桌面键盘灰尘轻松吸", "车内清洁更省力", "滤芯可水洗更环保"],
            },
            {
                "title": "SoftCloud 亲肤四件套 1.5m床",
                "subtitle": "磨毛面料｜不起球｜可机洗",
                "classification": "家居",
                "price": "239",
                "repertory": 14,
                "tag_titles": ["包邮"],
                "specs": ["尺寸：1.5m床适用", "面料：亲肤磨毛", "工艺：活性印染", "清洗：可机洗"],
                "highlights": ["触感柔软更舒适", "耐洗不易褪色", "简约风更百搭"],
            },
            {
                "title": "StackBox 收纳箱 40L（带盖）",
                "subtitle": "可叠放｜透明可视｜防尘防潮",
                "classification": "家居",
                "price": "59",
                "repertory": 160,
                "tag_titles": ["限时优惠"],
                "specs": ["容量：40L", "材质：PP", "特点：可叠放/带盖", "适用：衣物/杂物"],
                "highlights": ["收纳更整洁", "可视化取物更方便", "叠放省空间"],
            },
            {
                "title": "ThermoCup 500ml 保温杯",
                "subtitle": "长效保温｜一键弹盖｜防漏设计",
                "classification": "家居",
                "price": "69",
                "repertory": 110,
                "tag_titles": ["热门", "包邮"],
                "specs": ["容量：500ml", "材质：304不锈钢", "保温：约6-8h（演示）", "杯盖：一键开盖"],
                "highlights": ["通勤携带更方便", "防漏设计不怕倒", "杯口顺滑更好喝"],
            },
            {
                "title": "PureAir 桌面净化器",
                "subtitle": "HEPA滤芯｜低噪运行｜USB供电",
                "classification": "家居",
                "price": "129",
                "repertory": 35,
                "tag_titles": ["包邮"],
                "specs": ["滤芯：HEPA（演示）", "噪音：≤38dB（演示）", "供电：USB", "适用：桌面/小空间"],
                "highlights": ["办公桌更清新", "低噪运行不打扰", "滤芯更换更简单"],
            },

            # 书籍
            {
                "title": "《Python Web 开发实战》 第3版",
                "subtitle": "Django/REST/部署｜案例驱动",
                "classification": "书籍",
                "price": "88",
                "repertory": 45,
                "tag_titles": ["热门", "包邮"],
                "specs": ["装帧：平装", "页数：约520页（演示）", "适读：入门-进阶", "附赠：源码/示例（演示）"],
                "highlights": ["覆盖后端常见模块与实战", "适合做课设/毕设参考", "章节结构清晰便于查阅"],
            },
            {
                "title": "《Vue 2 企业级项目开发》",
                "subtitle": "路由/Vuex/组件化｜从0到1",
                "classification": "书籍",
                "price": "79",
                "repertory": 38,
                "tag_titles": ["包邮"],
                "specs": ["装帧：平装", "页数：约420页（演示）", "适读：有基础更佳", "内容：工程化/性能优化"],
                "highlights": ["前端工程化思路更系统", "案例丰富更贴近实际", "适合配合项目边学边做"],
            },
            {
                "title": "《MySQL 必知必会》 图解版",
                "subtitle": "SQL入门｜索引优化｜常见坑",
                "classification": "书籍",
                "price": "69",
                "repertory": 52,
                "tag_titles": ["限时优惠", "包邮"],
                "specs": ["装帧：平装", "页数：约360页（演示）", "适读：入门", "配套：示例数据（演示）"],
                "highlights": ["图解更易理解", "适合数据库课程与项目", "常用 SQL 模板可直接套用"],
            },
            {
                "title": "《算法与数据结构笔记》",
                "subtitle": "手写推导｜面试题型｜复杂度分析",
                "classification": "书籍",
                "price": "59",
                "repertory": 70,
                "tag_titles": ["热门"],
                "specs": ["装帧：平装", "页数：约280页（演示）", "适读：基础", "内容：链表/树/图/DP"],
                "highlights": ["知识点梳理更清晰", "题型覆盖更全面", "适合期末复习与练习"],
            },
            {
                "title": "《毕业论文写作与排版规范》",
                "subtitle": "结构模板｜图表规范｜查重建议",
                "classification": "书籍",
                "price": "45",
                "repertory": 90,
                "tag_titles": ["热门", "包邮"],
                "specs": ["装帧：平装", "页数：约220页（演示）", "适读：本科/专科", "附录：常用模板（演示）"],
                "highlights": ["章节结构一目了然", "图表/公式规范更易过审", "适合边写边对照"],
            },
            {
                "title": "《计算机网络自学指南》",
                "subtitle": "TCP/IP｜HTTP｜抓包实践",
                "classification": "书籍",
                "price": "66",
                "repertory": 44,
                "tag_titles": ["包邮"],
                "specs": ["装帧：平装", "页数：约400页（演示）", "适读：入门-进阶", "配套：实验案例（演示）"],
                "highlights": ["协议讲解更通俗", "配套抓包更直观", "适合做接口/部署排障"],
            },
            {
                "title": "《软件工程：需求到上线》",
                "subtitle": "需求分析｜设计文档｜测试流程",
                "classification": "书籍",
                "price": "72",
                "repertory": 33,
                "tag_titles": ["热门"],
                "specs": ["装帧：平装", "页数：约460页（演示）", "适读：项目实践", "内容：迭代/评审/上线"],
                "highlights": ["适合写第5/6章实现与测试", "流程图模板可直接套用", "文档规范更接近企业"],
            },
            {
                "title": "《UI 设计与配色速查》",
                "subtitle": "布局原则｜字体层级｜组件规范",
                "classification": "书籍",
                "price": "54",
                "repertory": 60,
                "tag_titles": ["限时优惠"],
                "specs": ["装帧：平装", "页数：约260页（演示）", "适读：入门", "内容：色彩/排版/组件"],
                "highlights": ["适合优化前端页面美观", "配色方案更好抄作业（正向）", "组件规范更统一"],
            },
        ]

        things_data = []
        for idx, p in enumerate(products, start=1):
            c = classification_map[p["classification"]]
            things_data.append(
                {
                    "title": p["title"],
                    "classification": c,
                    "price": p["price"],
                    "description": build_desc(p["subtitle"], p["specs"], p["highlights"]),
                    "status": "0",
                    "repertory": int(p["repertory"]),
                    "score": 4 + (idx % 2),
                    "pv": 200 + idx * 13,
                    "tag_titles": p.get("tag_titles", ["包邮"]),
                    "_image_asset": p.get("_image_asset"),
                }
            )

        things = []
        for item in things_data:
            obj, created = Thing.objects.get_or_create(
                title=item["title"],
                defaults={
                    "classification": item["classification"],
                    "price": item["price"],
                    "description": item["description"],
                    "status": item["status"],
                    "repertory": item["repertory"],
                    "score": item["score"],
                    "pv": item["pv"],
                    "create_time": now,
                },
            )
            if not created:
                obj.classification = item["classification"]
                obj.price = item["price"]
                obj.description = item["description"]
                obj.status = item["status"]
                obj.repertory = item["repertory"]
                obj.score = item["score"]
                obj.pv = item["pv"]
                obj.create_time = now
                obj.save(update_fields=[
                    "classification",
                    "price",
                    "description",
                    "status",
                    "repertory",
                    "score",
                    "pv",
                    "create_time",
                ])
            picked_tags = [tag_map[t] for t in item.get("tag_titles", []) if t in tag_map]
            obj.tag.set(picked_tags if picked_tags else tags[:2])

            # cover
            if obj.cover and str(obj.cover.name).startswith("cover/"):
                obj.cover.delete(save=False)
            chosen_asset = item.get("_image_asset")
            if chosen_asset and isinstance(chosen_asset, Path) and chosen_asset.exists():
                cover_bytes = self._make_image_bytes_from_asset(
                    asset_path=chosen_asset,
                    size=(1200, 800),
                    title=obj.title,
                    subtitle=f"¥{obj.price} · {obj.classification.title} · 支持7天无理由",
                    title_size=64,
                    sub_size=30,
                    accent=(59, 130, 246),
                    draw_text=False,
                )
            else:
                cover_assets = self._get_bucket_assets(
                    assets_dir=assets_dir,
                    bucket="cover",
                    classification_title=obj.classification.title,
                )
                if cover_assets:
                    asset = cover_assets[(obj.id or 1) % len(cover_assets)]
                    cover_bytes = self._make_image_bytes_from_asset(
                        asset_path=asset,
                        size=(1200, 800),
                        title=obj.title,
                        subtitle=f"¥{obj.price} · {obj.classification.title} · 支持7天无理由",
                        title_size=64,
                        sub_size=30,
                        accent=(59, 130, 246),
                        draw_text=False,
                    )
                else:
                    cover_bytes = self._make_image_bytes(
                        size=(1200, 800),
                        bg_color=(248, 250, 252),
                        title=obj.title,
                        subtitle=f"¥{obj.price} · {obj.classification.title} · 支持7天无理由",
                        title_size=64,
                        sub_size=30,
                        accent=(59, 130, 246),
                        draw_text=False,
                    )
            obj.cover.save(f"cover_{obj.id}.jpg", ContentFile(cover_bytes), save=True)
            things.append(obj)

        # If user provided product images, remove orphan cover files under upload/cover.
        if user_image_products:
            keep_names = {str(t.cover.name) for t in things if t.cover and t.cover.name}
            cover_dir = Path(dj_settings.MEDIA_ROOT) / "cover"
            for p in self._list_images(cover_dir, recursive=False):
                rel = f"cover/{p.name}".replace("\\", "/")
                if rel not in keep_names:
                    try:
                        p.unlink(missing_ok=True)
                    except TypeError:
                        # Python < 3.8 fallback
                        if p.exists():
                            p.unlink()

        things[0].wish.set(users[:2])
        things[0].wish_count = things[0].wish.count()
        things[0].collect.set(users[:1])
        things[0].collect_count = things[0].collect.count()
        things[0].save(update_fields=["wish_count", "collect_count"])

        Notice.objects.get_or_create(
            title="欢迎使用",
            defaults={"content": "欢迎体验在线商城系统", "create_time": now},
        )
        Notice.objects.get_or_create(
            title="发货说明",
            defaults={"content": "默认48小时内发货", "create_time": now},
        )

        ad_templates = [
            {
                "link": "https://example.com/promo",
                "title": "限时活动",
                "subtitle": "全场满减 · 包邮专区（演示）",
                "accent": (37, 99, 235),
                "bg": (219, 234, 254),
                "filename": "ad_demo_1.jpg",
            },
            {
                "link": "https://example.com/new",
                "title": "新品上新",
                "subtitle": "数码/家居/书籍 · 新品直达（演示）",
                "accent": (16, 185, 129),
                "bg": (220, 252, 231),
                "filename": "ad_demo_2.jpg",
            },
        ]

        for tpl in ad_templates:
            ad, _ = Ad.objects.get_or_create(link=tpl["link"], defaults={"create_time": now})
            if ad.image and str(ad.image.name).startswith("ad/"):
                ad.image.delete(save=False)
            ad_assets = self._get_bucket_assets(assets_dir=assets_dir, bucket="ad")
            if ad_assets:
                asset = ad_assets[(ad.id or 1) % len(ad_assets)]
                ad_bytes = self._make_image_bytes_from_asset(
                    asset_path=asset,
                    size=(1200, 480),
                    title=tpl["title"],
                    subtitle=tpl["subtitle"],
                    title_size=72,
                    sub_size=34,
                    accent=tpl["accent"],
                    draw_text=False,
                )
            elif user_product_assets:
                asset = user_product_assets[(ad.id or 1) % len(user_product_assets)]
                ad_bytes = self._make_image_bytes_from_asset(
                    asset_path=asset,
                    size=(1200, 480),
                    title="",
                    subtitle="",
                    title_size=72,
                    sub_size=34,
                    accent=tpl["accent"],
                    draw_text=False,
                )
            else:
                ad_bytes = self._make_image_bytes(
                    size=(1200, 480),
                    bg_color=tpl["bg"],
                    title=tpl["title"],
                    subtitle=tpl["subtitle"],
                    title_size=72,
                    sub_size=34,
                    accent=tpl["accent"],
                    draw_text=False,
                )
            ad.image.save(tpl["filename"], ContentFile(ad_bytes), save=True)

        # Seed multiple banners so carousel actually scrolls.
        banner_count = min(5, len(things))
        for idx in range(banner_count):
            thing = things[idx]
            banner, _ = Banner.objects.get_or_create(thing=thing, defaults={"create_time": now})
            if banner.image and str(banner.image.name).startswith("banner/"):
                banner.image.delete(save=False)
            accent = (99, 102, 241) if idx % 2 == 0 else (245, 158, 11)
            banner_assets = self._get_bucket_assets(assets_dir=assets_dir, bucket="banner")
            if banner_assets:
                asset = banner_assets[(idx * 3) % len(banner_assets)]
                banner_bytes = self._make_image_bytes_from_asset(
                    asset_path=asset,
                    size=(1600, 520),
                    title="精选推荐" if idx == 0 else "热门上新",
                    subtitle=f"爆款直降 · {thing.title}",
                    title_size=84,
                    sub_size=36,
                    accent=accent,
                    draw_text=False,
                )
            elif user_product_assets:
                asset = user_product_assets[(idx * 3) % len(user_product_assets)]
                banner_bytes = self._make_image_bytes_from_asset(
                    asset_path=asset,
                    size=(1600, 520),
                    title="",
                    subtitle="",
                    title_size=84,
                    sub_size=36,
                    accent=accent,
                    draw_text=False,
                )
            else:
                banner_bytes = self._make_image_bytes(
                    size=(1600, 520),
                    bg_color=(224, 231, 255) if idx % 2 == 0 else (254, 249, 195),
                    title="精选推荐" if idx == 0 else "热门上新",
                    subtitle=f"爆款直降 · {thing.title}",
                    title_size=84,
                    sub_size=36,
                    accent=accent,
                    draw_text=False,
                )
            banner.image.save(f"banner_demo_{idx + 1}.jpg", ContentFile(banner_bytes), save=True)

        for idx in range(5):
            Comment.objects.get_or_create(
                user=users[idx % len(users)],
                thing=things[idx],
                defaults={
                    "content": f"商品{idx + 1}不错，已下单",
                    "comment_time": now,
                    "like_count": 1 + (idx % 4),
                },
            )

        for idx in range(3):
            order_number = f"20240128{idx + 1:04d}"
            Order.objects.get_or_create(
                order_number=order_number,
                defaults={
                    "user": users[idx % len(users)],
                    "thing": things[idx],
                    "count": 1,
                    "status": "2",
                    "order_time": now,
                    "pay_time": now,
                    "receiver_name": users[idx % len(users)].nickname or "用户",
                    "receiver_address": "北京市海淀区",
                    "receiver_phone": users[idx % len(users)].mobile or "13800000000",
                    "remark": "尽快发货",
                },
            )

            OrderLog.objects.get_or_create(
                user=users[idx % len(users)],
                thing=things[idx],
                action="2",
                defaults={"log_time": now},
            )

            Record.objects.get_or_create(
                user=users[idx % len(users)],
                thing=things[idx],
                classification=things[idx].classification,
                defaults={"title": things[idx].title, "record_time": now},
            )

        Address.objects.get_or_create(
            user=users[0],
            defaults={
                "name": users[0].nickname or "用户",
                "mobile": users[0].mobile or "13800000001",
                "desc": "北京市海淀区某街道",
                "default": True,
                "create_time": now,
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
