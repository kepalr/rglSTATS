from django import forms


class SearchPlayer(forms.Form):
    player_id = forms.CharField(label="Player Id", max_length=50)