from django.db import migrations

TASK_NAME = 'close-expired-seasonal-missions'
TASK_PATH = 'gamification.tasks.close_expired_seasonal_missions'


def create_schedule(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    schedule, _ = IntervalSchedule.objects.get_or_create(every=1, period='days')
    PeriodicTask.objects.get_or_create(
        name=TASK_NAME,
        defaults={'task': TASK_PATH, 'interval': schedule},
    )


def remove_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('gamification', '0001_initial'),
        ('django_celery_beat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
