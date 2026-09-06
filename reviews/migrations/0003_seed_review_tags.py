from django.db import migrations
from django.utils.text import slugify

TAGS = [
    'Đáng tiền', 'Phục vụ chậm', 'Không gian đẹp', 'Đông khách',
    'Sạch sẽ', 'View đẹp', 'Giá cao', 'Nhân viên thân thiện',
]


def seed_tags(apps, schema_editor):
    ReviewTag = apps.get_model('reviews', 'ReviewTag')
    for name in TAGS:
        ReviewTag.objects.get_or_create(slug=slugify(name), defaults={'name': name})


def remove_tags(apps, schema_editor):
    ReviewTag = apps.get_model('reviews', 'ReviewTag')
    ReviewTag.objects.filter(slug__in=[slugify(name) for name in TAGS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('reviews', '0002_reviewtag_comment_parent_review_is_hidden_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_tags, remove_tags),
    ]
