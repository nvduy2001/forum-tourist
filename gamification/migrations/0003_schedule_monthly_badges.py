from django.db import migrations

TASK_NAME = 'award-monthly-badges'
TASK_PATH = 'gamification.tasks.award_monthly_badges'


def create_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0', hour='2', day_of_month='1', month_of_year='*', day_of_week='*',
    )
    PeriodicTask.objects.get_or_create(
        name=TASK_NAME,
        defaults={'task': TASK_PATH, 'crontab': schedule},
    )


def remove_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('gamification', '0002_schedule_close_expired_missions'),
        ('django_celery_beat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
