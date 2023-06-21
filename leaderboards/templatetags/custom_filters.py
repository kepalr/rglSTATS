from django import template
from django.template.defaulttags import register
import string

register = template.Library()

@register.filter
def format_time(time):
    mins = int(time / 60)
    secs = time % 60
    return f'{mins}m {secs}s'

@register.filter
def indexof(list, value):
    return list.index(value)

@register.filter
def get_item(dictionary, key):
    val = dictionary.get(str(key))
    if val is None:
        return key
    return val

@register.filter
def get_items_item(dictionary, key):
    val = dictionary.get(str(key)).items()
    if val is None:
        return key
    return val


@register.filter
def format_header(header):
    convert = {
        'dapm': 'DPM',
        'heal': 'HPM',
        'season_id': 'Season',
        'div_name': 'Division',
    }
    try: 
        return convert[header]
    except:
        return  string.capwords(header.replace('_', ' '))

@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr)