# Generated by Django 4.2 on 2023-04-05 17:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leaderboards', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('log_id', models.IntegerField()),
                ('match_id', models.IntegerField()),
                ('data', models.JSONField()),
                ('no_log', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('match_id', models.IntegerField()),
                ('data', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player_id', models.CharField(max_length=20)),
                ('data', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='Stat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('season_id', models.IntegerField()),
                ('div_name', models.CharField(max_length=64)),
                ('match_id', models.IntegerField()),
                ('log_id', models.IntegerField()),
                ('team_id', models.IntegerField()),
                ('map', models.CharField(max_length=64)),
                ('player_id', models.CharField(max_length=50)),
                ('data', models.JSONField()),
            ],
        ),
    ]
