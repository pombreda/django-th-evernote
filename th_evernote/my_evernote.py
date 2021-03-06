# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import arrow

# evernote API
from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
import evernote.edam.type.ttypes as Types

# django classes
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.log import getLogger
from django.utils.translation import ugettext as _

# django_th classes
from django_th.services.services import ServicesMgr
from django_th.models import UserService, ServicesActivated
from th_evernote.models import Evernote
from th_evernote.sanitize import sanitize

"""
    handle process with evernote
    put the following in settings.py

    TH_EVERNOTE = {
        'sandbox': True,
        'consumer_key': 'abcdefghijklmnopqrstuvwxyz',
        'consumer_secret': 'abcdefghijklmnopqrstuvwxyz',
    }
    sanbox set to True to make your test and False for production purpose

    TH_SERVICES = (
        ...
        'th_evernote.my_evernote.ServiceEvernote',
        ...
    )

"""

logger = getLogger('django_th.trigger_happy')


class ServiceEvernote(ServicesMgr):

    def process_data(self, token, trigger_id, date_triggered):
        """
            get the data from the service
        """
        data = []

        if token is not None:
            client = EvernoteClient(
                token=token, sandbox=settings.TH_EVERNOTE['sandbox'])

            note_store = client.get_note_store()

            # get the data from the last time the trigger has been started
            # the filter will use the DateTime format in standard
            new_date_triggered = arrow.get(
                str(date_triggered), 'YYYYMMDDTHHmmss')

            new_date_triggered = str(new_date_triggered).replace(
                ':', '').replace('-', '')
            date_filter = "created:{}".format(new_date_triggered[:-6])

            # filter
            my_filter = NoteStore.NoteFilter()
            my_filter.words = date_filter

            # result spec to tell to evernote
            # what information to include in the response
            spec = NoteStore.NotesMetadataResultSpec()
            spec.includeTitle = True
            spec.includeAttributes = True

            our_note_list = note_store.findNotesMetadata(
                token, my_filter, 0, 100, spec)

            whole_note = ''
            for note in our_note_list.notes:
                whole_note = note_store.getNote(
                    token, note.guid, True, False, False, False)
                data.append(
                    {'title': note.title,
                     'link': whole_note.attributes.sourceURL,
                     'content': whole_note.content})

        return data

    def save_data(self, token, trigger_id, **data):
        """
            let's save the data
            dont want to handle empty title nor content
            otherwise this will produce an Exception by
            the Evernote's API
        """
        content = ''

        if 'content' in data:
            if type(data['content']) is list:
                if 'value' in data['content'][0]:
                    content = data['content'][0].value
            else:
                if 'value' in data['content']:
                    content = data['content']['value']
                else:
                    content = data['content']

        elif 'summary_detail' in data:
            if type(data['summary_detail']) is list:
                if 'value' in data['summary_detail'][0]:
                    content = data['summary_detail'][0].value
            else:
                if 'value' in data['summary_detail']:
                    content = data['summary_detail']['value']
                else:
                    content = data['summary_detail']

        elif 'description' in data:
            content = data['description']

        # if no title provided, fallback to the URL which should be provided
        # by any exiting service
        title = (data['title'] if 'title' in data else data['link'])
        if token and len(title):
            # get the evernote data of this trigger
            trigger = Evernote.objects.get(trigger_id=trigger_id)

            client = EvernoteClient(
                token=token, sandbox=settings.TH_EVERNOTE['sandbox'])
            # user_store = client.get_user_store()
            note_store = client.get_note_store()

            # note object
            note = Types.Note()
            if trigger.notebook:
                notebooks = note_store.listNotebooks()
                listtags = note_store.listTags()
                notebookGuid = 0
                tagGuid = []
                # get the notebookGUID ...
                for notebook in notebooks:
                    if notebook.name.lower() == trigger.notebook.lower():
                        notebookGuid = notebook.guid
                        break
                #... and get the tagGUID if a tag has been provided

                if trigger.tag is not '':
                    # cut the string by piece of tag with comma
                    if ',' in trigger.tag:
                        for my_tag in trigger.tag.split(','):
                            for tag in listtags:
                                # remove space before and after
                                # thus we keep "foo bar"
                                # but not " foo bar" nor "foo bar "
                                if tag.name.lower() == my_tag.lower().lstrip().rstrip():
                                    tagGuid.append(tag.guid)
                                    break
                    else:
                        for tag in listtags:
                            if tag.name.lower() == my_tag.lower():
                                tagGuid.append(tag.guid)
                                break

                # notebookGUID does not exist:
                # create it
                if notebookGuid == 0:
                    new_notebook = Types.Notebook()
                    new_notebook.name = trigger.notebook
                    new_notebook.defaultNotebook = False
                    note.notebookGuid = note_store.createNotebook(
                        new_notebook).guid
                else:
                    note.notebookGuid = notebookGuid
                # tagGUID does not exist:
                # create it if a tag has been provided
                if tagGuid == 0 and trigger.tag is not '':
                    new_tag = Types.Tag()
                    new_tag.name = trigger.tag
                    tagGuid = note_store.createTag(new_tag).guid

                if trigger.tag is not '':
                    # set the tag to the note if a tag has been provided
                    note.tagGuids = tagGuid

                logger.debug("notebook that will be used %s", trigger.notebook)

            if 'link' in data:
                # add the link of the 'source' in the note
                # get a NoteAttributes object
                na = Types.NoteAttributes()
                # add the url
                na.sourceURL = data['link']
                # add the object to the note
                note.attributes = na

                # will add this kind of info in the footer of the note :
                # "provided by FoxMaSk's News from http://domain.com"
                # domain.com will be the link and the text of the link
                provided_by = _('Provided by')
                provided_from = _('from')
                footer_from = "<br/><br/>{} <em>{}</em> {} <a href='{}'>{}</a>"
                footer = footer_from.format(
                    provided_by, trigger.trigger.description, provided_from,
                    data['link'], data['link'])
                content += footer

            # start to build the "note"
            # the title
            note.title = title
            # the body
            prolog = '<?xml version="1.0" encoding="UTF-8"?>'
            prolog += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            note.content = prolog
            # tidy and sanitize content
            enml = sanitize(content)
            note.content += str(enml)
            # create the note !
            try:
                created_note = note_store.createNote(note)
                sentance = str('note %s created') % created_note.guid
                logger.debug(sentance)
            except Exception as e:
                logger.critical(e)

        else:
            sentence = "no token provided for trigger ID {} and title {}"
            logger.critical(sentence.format(trigger_id, title))

    def get_evernote_client(self, token=None):
        """
            get the token from evernote
        """
        if token:
            return EvernoteClient(
                token=token,
                sandbox=settings.TH_EVERNOTE['sandbox'])
        else:
            return EvernoteClient(
                consumer_key=settings.TH_EVERNOTE['consumer_key'],
                consumer_secret=settings.TH_EVERNOTE['consumer_secret'],
                sandbox=settings.TH_EVERNOTE['sandbox'])

    def auth(self, request):
        """
            let's auth the user to the Service
        """
        client = self.get_evernote_client()
        callbackUrl = 'http://%s%s' % (
            request.get_host(), reverse('evernote_callback'))
        request_token = client.get_request_token(callbackUrl)

        # Save the request token information for later
        request.session['oauth_token'] = request_token['oauth_token']
        request.session['oauth_token_secret'] = request_token[
            'oauth_token_secret']

        # Redirect the user to the Evernote authorization URL
        # return the URL string which will be used by redirect()
        # from the calling func
        return client.get_authorize_url(request_token)

    def callback(self, request):
        """
            Called from the Service when the user accept to activate it
        """
        try:
            client = self.get_evernote_client()
            # finally we save the user auth token
            # As we already stored the object ServicesActivated
            # from the UserServiceCreateView now we update the same
            # object to the database so :
            # 1) we get the previous objet
            us = UserService.objects.get(
                user=request.user,
                name=ServicesActivated.objects.get(name='ServiceEvernote'))
            # 2) then get the token
            us.token = client.get_access_token(
                request.session['oauth_token'],
                request.session['oauth_token_secret'],
                request.GET.get('oauth_verifier', '')
            )
            # 3) and save everything
            us.save()
        except KeyError:
            return '/'

        return 'evernote/callback.html'
