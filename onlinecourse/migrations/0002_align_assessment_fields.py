from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('onlinecourse', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='question',
            old_name='content',
            new_name='question',
        ),
        migrations.AlterField(
            model_name='question',
            name='grade',
            field=models.IntegerField(default=0),
        ),
        migrations.RenameField(
            model_name='choice',
            old_name='content',
            new_name='choice',
        ),
        migrations.AlterField(
            model_name='choice',
            name='choice',
            field=models.TextField(),
        ),
    ]
