from django import template

register = template.Library()


@register.filter
def loc_name(obj, lang_code):
    return obj.localized_name(lang_code)


@register.filter
def loc_desc(obj, lang_code):
    return obj.localized_description(lang_code)
