from django.db import migrations, models
import django.db.models.deletion


def copy_question_course_from_lesson(apps, schema_editor):
    Question = apps.get_model('onlinecourse', 'Question')
    for question in Question.objects.select_related('lesson').iterator():
        question.course_id = question.lesson.course_id
        question.save(update_fields=['course'])


class Migration(migrations.Migration):

    dependencies = [
        ('onlinecourse', '0002_align_assessment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='course',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='onlinecourse.course',
            ),
        ),
        migrations.RunPython(
            copy_question_course_from_lesson,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='question',
            name='course',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='onlinecourse.course',
            ),
        ),
        migrations.RemoveField(
            model_name='question',
            name='lesson',
        ),
        migrations.RenameField(
            model_name='question',
            old_name='question',
            new_name='question_text',
        ),
        migrations.RenameField(
            model_name='choice',
            old_name='choice',
            new_name='choice_text',
        ),
        migrations.AlterField(
            model_name='question',
            name='grade',
            field=models.IntegerField(default=50),
        ),
        migrations.AlterField(
            model_name='choice',
            name='choice_text',
            field=models.TextField(),
        ),
        migrations.AlterModelOptions(
            name='question',
            options={'ordering': ('id',)},
        ),
    ]
