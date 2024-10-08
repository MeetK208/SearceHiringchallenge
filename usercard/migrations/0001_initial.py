# Generated by Django 5.1.1 on 2024-09-13 16:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projectcard', '0009_project_last_edited_by'),
        ('register', '0003_alter_user_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectCardUser',
            fields=[
                ('carduserId', models.AutoField(primary_key=True, serialize=False)),
                ('designation', models.CharField(default='CEO', max_length=50)),
                ('department', models.CharField(default='CEO', max_length=50)),
                ('budget', models.CharField(default='CEO', max_length=50)),
                ('location', models.CharField(default='CEO', max_length=50)),
                ('last_updated_timestamp', models.DateTimeField(auto_now=True)),
                ('last_edited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='edited_projectcards', to='register.user')),
                ('projectCard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_projects', to='projectcard.project')),
            ],
        ),
    ]
