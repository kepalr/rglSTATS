from django.test import TestCase

# Create your tests here.
# make a test for when there are two logs to s mathc, one thatv is 1-0, and one that is 0-0
# bc total score is the same as one of the match halves, you run into some issues

## if a player joins a different team in the same division and then faces off against their old team, they will have been considered on both teams during the match
## no way to date check when a player was on the team

## my initial solution did not work, for example the mud play against SWMG early in the season, quirka leaves the mud to play for SWMG at end of season, in that math they had quirka would
## be considered on SWMG because it was his latest team, not the team he played for in the logs

## gonna have to check team mates and cross reference with threshold who has most team mates