# import django_tables2 as tables
# from .models import SeasonTotal, models

# class SeasonTableManager(models.Manager):
#     _default_manager = models.Manager()


# class SeasonTable(tables.Table):
#     player = tables.LinkColumn('stat', args=[tables.A('pk')])
#     games_played = tables.Column(verbose_name='GP')
#     total_time = tables.Column(verbose_name='Time')
#     kills = tables.Column()
#     assists = tables.Column()
#     deaths = tables.Column()
#     dapm = tables.Column()
#     heal = tables.Column()
#     ubers = tables.Column()
#     drops = tables.Column()
#     headshots = tables.Column()
#     headshots_hit = tables.Column(verbose_name='HS Hit')
#     backstabs = tables.Column(verbose_name='Backstabs')
#     class Meta:
#         model = SeasonTotal
#         fields =  ('games_played', 'total_time', 'kills', 'assists', 'deaths', 'dapm', 'heal', 'ubers', 'drops', 'headshots', 'headshots_hit', 'backstabs')
    
#     objects = SeasonTableManager()