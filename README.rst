=======================================
Django Trigger Happy : Service Evernote
=======================================

This service provide a way to (actually) store note from data coming from a service of your choice (like RSS) from Trigger Happy

for example a new RSS item is published, django-th-evernote will store them by creating a note on your Evernote account

Requirements :
==============
* django_th: 0.8.0
* evernote: 1.25.0
* httplib2: 0.8
* pytidylib: 0.2.1


Installation:
=============
to get the project, from your virtualenv, do :

.. code:: python

    pip install django-th-evernote

then do

.. code:: python

    python manage.py syncdb

to startup the database

Parameters :
============
As usual you will setup the database parameters.

Important parts are the settings of the available services :

Settings.py
-----------

INSTALLED_APPS
~~~~~~~~~~~~~~

add the module th_evernote to INSTALLED_APPS

.. code:: python

    INSTALLED_APPS = (
        'th_evernote',
    )


TH_SERVICES 
~~~~~~~~~~~
TH_SERVICES is a list of the services we add to Django Trigger Happy

.. code:: python

    TH_SERVICES = (
        'th_evernote.my_evernote.ServiceEvernote',
    )


TH_EVERNOTE
~~~~~~~~~~~
TH_EVERNOTE is the settings you will need to be able to add/read data in/from Evernote.

.. code:: python

    TH_EVERNOTE = {
        'sandbox': True,
        'consumer_key': 'abcdefghijklmnopqrstuvwxyz',
        'consumer_secret': 'abcdefghijklmnopqrstuvwxyz',
    }
    
set sandbox to False in production and provide your consummer_key and consumer_secret you'd requested from http://dev.evernote.com/



Setting up : Administration
---------------------------

once the module is installed, go to the admin panel and activate it.

All you can decide here is to tell if the service requires an external authentication or not. For django-th-evernote, set it to on.

Once they are activated. User can use them.


