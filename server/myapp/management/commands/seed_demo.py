from django.core.management.base import BaseCommand
from django.utils import timezone

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

    def handle(self, *args, **options):
        now = timezone.now()

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
                "description": "热爱二手交易",
            },
            {
                "username": "user02",
                "nickname": "小红",
                "mobile": "13800000002",
                "email": "user02@example.com",
                "gender": "F",
                "description": "喜欢收藏",
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
                    "title": f"二手商品-{idx:02d}",
                    "classification": classification,
                    "price": str(price),
                    "description": f"商品{idx}，成色良好，欢迎咨询。",
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
            things.append(obj)

        things[0].wish.set(users[:2])
        things[0].wish_count = things[0].wish.count()
        things[0].collect.set(users[:1])
        things[0].collect_count = things[0].collect.count()
        things[0].save(update_fields=["wish_count", "collect_count"])

        Notice.objects.get_or_create(
            title="欢迎使用",
            defaults={"content": "欢迎体验二手交易平台", "create_time": now},
        )
        Notice.objects.get_or_create(
            title="发货说明",
            defaults={"content": "默认48小时内发货", "create_time": now},
        )

        Ad.objects.get_or_create(
            link="https://example.com/promo",
            defaults={"create_time": now},
        )

        Banner.objects.get_or_create(
            thing=things[0],
            defaults={"create_time": now},
        )

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
