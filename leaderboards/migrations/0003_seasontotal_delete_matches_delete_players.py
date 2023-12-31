# Generated by Django 4.2 on 2023-04-11 04:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leaderboards', '0002_log_match_player_stat'),
    ]

    operations = [
        migrations.CreateModel(
            name='SeasonTotal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('season_id', models.IntegerField()),
                ('div_name', models.CharField(max_length=64)),
                ('team_id', models.IntegerField()),
                ('player_id', models.CharField(max_length=50)),
                ('games_played', models.CharField(max_length=64)),
                ('time_played', models.IntegerField()),
                ('kills', models.IntegerField()),
                ('deaths', models.IntegerField()),
                ('assists', models.IntegerField()),
                ('dapm', models.IntegerField()),
                ('heal', models.IntegerField()),
                ('ubers', models.IntegerField()),
                ('drops', models.IntegerField()),
                ('headshots', models.IntegerField()),
                ('headshots_hit', models.IntegerField()),
                ('backstabds', models.IntegerField()),
            ],
        ),
        migrations.DeleteModel(
            name='Matches',
        ),
        migrations.DeleteModel(
            name='Players',
        ),
    ]
