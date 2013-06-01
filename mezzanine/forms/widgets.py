"""
Extended Textara class
"""

from django.forms.util import flatatt
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.forms.widgets import Textarea

class TextareaEx(Textarea):
    def __init__(self, attrs=None):
        # The 'rows' and 'cols' attributes are required for HTML correctness.
        default_attrs = {'cols': '100', 'rows': '3'}
        if attrs:
            default_attrs.update(attrs)
        super(Textarea, self).__init__(default_attrs)

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        return mark_safe(u'<textarea%s>%s</textarea>' % (flatatt(final_attrs),
                conditional_escape(force_unicode(value))))