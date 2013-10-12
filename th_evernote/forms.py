# -*- coding: utf-8 -*-

from django import forms
from th_evernote.models import Evernote


class EvernoteForm(forms.ModelForm):

    """
        for to handle Evernote service
    """
        
    class Meta:
        model = Evernote
        fields = ('tag', 'notebook', )


class EvernoteConsummerForm(EvernoteForm):
    pass


class EvernoteProviderForm(EvernoteForm):
    pass
