from django.db import migrations


def reclassify_existing_assessments(apps, schema_editor):
    table_name = 'nutrition_followuprecord'
    column_names = schema_editor.connection.introspection.get_table_description(
        schema_editor.connection.cursor(),
        table_name,
    )
    # The current model queries this later-added column during migration 0007.
    if 'follow_up_method' not in {
        column.name for column in column_names
    }:
        return

    from nutrition.models import NutritionAssessment

    database = schema_editor.connection.alias
    assessments = NutritionAssessment.all_objects.using(database).select_related(
        'resident'
    )

    for assessment in assessments.iterator():
        assessment.save(using=database)


class Migration(migrations.Migration):
    dependencies = [
        ('nutrition', '0006_alter_followuprecord_options_and_more'),
        ('residents', '0004_alter_resident_options_alter_resident_managers_and_more'),
    ]

    operations = [
        migrations.RunPython(
            reclassify_existing_assessments,
            migrations.RunPython.noop,
        ),
    ]
