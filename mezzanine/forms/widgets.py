"""
Extended Textara class
"""

from django.forms.util import flatatt
from django.utils.html import conditional_escape, escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.forms.widgets import Textarea, ClearableFileInput
from django.utils.translation import ugettext_lazy

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

class ClearableFileInputEx(ClearableFileInput):
    initial_text = ugettext_lazy('')
    input_text = ugettext_lazy('')
    clear_checkbox_label = ugettext_lazy('')

    template_with_initial = u'%(clear_template)s %(input)s'

    template_with_clear = u'<label class="hide" for="%(clear_checkbox_id)s">%(clear)s  %(clear_checkbox_label)s</label>'


