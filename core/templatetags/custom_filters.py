from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary using key"""
    if dictionary:
        # Convert key to int if it's a string number
        try:
            key = int(key)
        except (ValueError, TypeError):
            pass
        return dictionary.get(key, [])
    return []