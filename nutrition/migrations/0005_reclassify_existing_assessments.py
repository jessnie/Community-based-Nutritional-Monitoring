from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('nutrition', '0004_nutritionassessment_assessed_by_and_more'),
        ('residents', '0003_resident_created_by'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]