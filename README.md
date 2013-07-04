Django Trigger Happy : Service Evernote
=======================================

This service provide a way to (actually) store note from data coming from a service of your choice (like RSS)

for example a new RSS item is published, django-th-evernote will store them by creating a note on your Evernote account

Requirements :
-------------
* django_th 0.4.0
* evernote 1.23.2
* httplib2 0.8
* oauth2 1.5.211
* ordereddict 1.1
* South 0.7.6
* PyTidylib : 0.2.1

Installation:
------------
to get the project, from your virtualenv, do :
```python
pip install django-th-evernote
```
then do
```python
python manage.py syncdb
```
to startup the database

Parameters :
------------
As usual you will setup the database parameters.

Important parts are the settings of the available services :

### Settings.py 

#### INSTALLED_APPS

add the module th_evernote to INSTALLED_APPS

#### TH_SERVICES 

TH_SERVICES is a list of the services we put in django_th/services directory

```python
TH_SERVICES = (
    'th_evernote.my_evernote.ServiceEvernote',
)
```
Wizard Template :

#### TH_WIZARD_TPL
TH_WIZARD_TPL = {
    'my_evernote':
    'my_evernote/evernote-form.html',
}

##### TH_EVERNOTE
TH_EVERNOTE is the settings you will need to be able to add/read data in/from Evernote.
```python
TH_EVERNOTE = {
    'sandbox': True,
    'consumer_key': 'abcdefghijklmnopqrstuvwxyz',
    'consumer_secret': 'abcdefghijklmnopqrstuvwxyz',
}
```
set sandbox to False in production and provide your consummer_key and consumer_secret you'd requested from http://dev.evernote.com/



Setting up : Administration
---------------------------

once the module is installed, go to the admin panel and activate it.

All you can decide here is to tell if the service requires an external authentication or not. For django-th-evernote, set it to on.

Once they are activated. User can use them.


