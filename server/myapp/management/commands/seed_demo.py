from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings as dj_settings
from django.utils import timezone

import os
from pathlib import Path
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from PIL import Image, ImageDraw, ImageFont, ImageOps

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

    def _get_local_assets(self):
        assets_dir = Path(dj_settings.BASE_DIR) / "demo_images"
        if not assets_dir.exists() or not assets_dir.is_dir():
            return []
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        assets = [p for p in assets_dir.iterdir() if p.is_file() and p.suffix.lower() in exts]
        assets.sort(key=lambda p: p.name.lower())
        return assets

    def _download_bytes(self, url: str, timeout: int = 20):
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()

    def _ensure_remote_assets(self, *, target_dir: Path, count: int = 14, force: bool = False):
        target_dir.mkdir(parents=True, exist_ok=True)

        # If user already provided local images, don't overwrite.
        existing = [p for p in target_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        if (not force) and len(existing) >= max(6, count // 2):
            return

        # Prefer Unsplash Source (royalty-free). Fallback to Picsum if blocked.
        queries = [
            "smartphone product",
            "laptop product",
            "headphones product",
            "camera product",
            "keyboard product",
            "mouse product",
            "smartwatch product",
            "book product",
            "stationery product",
            "backpack product",
            "chair product",
            "sofa product",
            "home appliance product",
            "kitchen appliance product",
        ]

        downloaded = 0
        for i, q in enumerate(queries[:count], start=1):
            out = target_dir / f"remote_{i:02d}_{q}.jpg"
            if (not force) and out.exists() and out.stat().st_size > 10_000:
                downloaded += 1
                continue

            unsplash_url = f"https://source.unsplash.com/1600x1200/?{q}"  # redirects to an image
            picsum_url = f"https://picsum.photos/seed/demo-shop-{i}/1600/1200"

            try:
                data = self._download_bytes(unsplash_url)
                if data and len(data) > 10_000:
                    out.write_bytes(data)
                    downloaded += 1
                    continue
            except (URLError, HTTPError, TimeoutError, ValueError):
                pass

            try:
                data = self._download_bytes(picsum_url)
                if data and len(data) > 10_000:
                    out.write_bytes(data)
                    downloaded += 1
                    continue
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
    ):
        img = Image.open(str(asset_path)).convert("RGB")
        # crop-fit to target size
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        img = ImageOps.fit(img, size, method=resample, centering=(0.5, 0.5))

        draw = ImageDraw.Draw(img)
        font_title = self._load_font(title_size)
        font_sub = self._load_font(sub_size)
        w, h = size

        # bottom gradient-ish overlay for readable text
        overlay_h = int(h * 0.32)
        for i in range(overlay_h):
            alpha = int(180 * (i / overlay_h))
            y = h - overlay_h + i
            draw.rectangle([0, y, w, y + 1], fill=(0, 0, 0, alpha))

        # accent bar
        draw.rectangle([0, h - overlay_h, 10, h], fill=accent)

        padding = 24
        text_y = h - overlay_h + 18
        draw.text((padding + 12, text_y), title, fill=(255, 255, 255), font=font_title)
        if subtitle:
            draw.text((padding + 12, text_y + title_size + 6), subtitle, fill=(226, 232, 240), font=font_sub)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
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

    def _make_image_bytes(self, *, size, bg_color, title, subtitle="", title_size=56, sub_size=28, accent=(59, 130, 246)):
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

        assets = self._get_local_assets()

        # Hide legacy demo items that mention "二手" so the storefront only shows new products.
        Thing.objects.filter(title__startswith="二手商品").update(status="1")

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

        things_data = []
        for idx in range(1, 21):
            classification = classifications[(idx - 1) % len(classifications)]
            price = 29 + idx * 5
            things_data.append(
                {
                    "title": f"新品商品-{idx:02d}",
                    "classification": classification,
                    "price": str(price),
                    "description": f"商品{idx}，全新现货，支持7天无理由（演示数据）。",
                    "status": "0",
                    "repertory": 1 + (idx % 10),
                    "score": 3 + (idx % 3),
                    "pv": 50 + idx * 7,
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
                obj.save(update_fields=[
                    "classification",
                    "price",
                    "description",
                    "status",
                    "repertory",
                    "score",
                    "pv",
                ])
            obj.tag.set(tags[:2])

            # cover
            if obj.cover and str(obj.cover.name).startswith("cover/"):
                obj.cover.delete(save=False)
            if assets:
                asset = assets[(obj.id or 1) % len(assets)]
                cover_bytes = self._make_image_bytes_from_asset(
                    asset_path=asset,
                    size=(1200, 800),
                    title=obj.title,
                    subtitle=f"¥{obj.price} · {obj.classification.title} · 支持7天无理由",
                    title_size=64,
                    sub_size=30,
                    accent=(59, 130, 246),
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
                )
            obj.cover.save(f"cover_{obj.id}.jpg", ContentFile(cover_bytes), save=True)
            things.append(obj)

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
            if assets:
                asset = assets[(ad.id or 1) % len(assets)]
                ad_bytes = self._make_image_bytes_from_asset(
                    asset_path=asset,
                    size=(1200, 480),
                    title=tpl["title"],
                    subtitle=tpl["subtitle"],
                    title_size=72,
                    sub_size=34,
                    accent=tpl["accent"],
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
            if assets:
                asset = assets[(idx * 3) % len(assets)]
                banner_bytes = self._make_image_bytes_from_asset(
                    asset_path=asset,
                    size=(1600, 520),
                    title="精选推荐" if idx == 0 else "热门上新",
                    subtitle=f"爆款直降 · {thing.title}",
                    title_size=84,
                    sub_size=36,
                    accent=accent,
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
