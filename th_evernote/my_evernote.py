# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext as _

# django_th classes
from django_th.services.services import ServicesMgr
from django_th.models import UserService, ServicesActivated, TriggerService
from th_evernote.models import Evernote
from th_evernote.sanitize import sanitize
# evernote classes
from evernote.api.client import EvernoteClient
import evernote.edam.type.ttypes as Types
# django classes
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.log import getLogger


"""
    handle process with evernote
    put the following in settings.py

    TH_EVERNOTE = {
        'sandbox': True,
        'consumer_key': 'abcdefghijklmnopqrstuvwxyz',
        'consumer_secret': 'abcdefghijklmnopqrstuvwxyz',
    }
    sanbox set to True to make your test and False for production purpose
"""

logger = getLogger('django_th.trigger_happy')


class ServiceEvernote(ServicesMgr):

    def process_data(self, trigger_id):
        """
            get the data from the service
        """
        trigger = TriggerService.objects.get(id=trigger_id)

        data = {}

        if trigger.token is not None:
            client = EvernoteClient(
                token=trigger.token, sandbox=settings.TH_EVERNOTE['sandbox'])

            # get the data from the last time the trigger has been started
            # the filter will use the DateTime format in standard
            data = client.findNotesMetadata(
                filter='created:' + trigger.date_triggered)

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
            content = data.content[0].value
        elif 'description' in data:
            content = data.description

        if token and len(data['title']):
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
                tagGuid = 0
                # get the notebookGUID ...
                for notebook in notebooks:
                    if notebook.name.lower() == trigger.notebook.lower():
                        notebookGuid = notebook.guid
                        break
                #... and get the tagGUID if a tag has been provided
                if trigger.tag is not '':
                    for tag in listtags:
                        if tag.name.lower() == trigger.tag.lower():
                            tagGuid = tag.guid
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
                    note.tagGuids = [tagGuid]

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
                footer = "<br/><br/>{} <em>{}</em> {} <a href='{}'>{}</a>".format(
                    provided_by, trigger.trigger.description,
                    provided_from, data['link'], data['link'])
                content += footer

            # start to build the "note"
            # the title
            note.title = data['title'].encode('utf-8', 'xmlcharrefreplace')
            # the body
            note.content = '<?xml version="1.0" encoding="UTF-8"?>'
            note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            # tidy and sanitize content
            enml = sanitize(content)
            note.content += enml.encode('ascii', 'xmlcharrefreplace')
            # create the note !
            created_note = note_store.createNote(note)
            sentance = str('note %s created') % created_note.guid
            logger.debug(sentance)

        else:
            logger.critical(
                "no token provided for trigger ID %s and title %s", trigger_id,
                data['title'])

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

            @todo : manage the user token to see if a token already exist
            smthg like request.user.token with
            client = self.get_evernote_client(request.user.token)
            this will avoid to request a new token
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

        # note_store = client.get_note_store()
        # notebooks = note_store.listNotebooks()

        return 'evernote/callback.html'
