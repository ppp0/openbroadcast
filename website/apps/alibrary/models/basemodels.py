# python
import datetime
import uuid
import shutil
import sys

# django
from django.db import models
from django.db.models.signals import post_save
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.core.files import File as DjangoFile
from django.core.urlresolvers import reverse

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from django.http import HttpResponse # needed for absolute url

from settings import *


# cms
# from cms.models import CMSPlugin, Page
from cms.models.fields import PlaceholderField
from cms.utils.placeholder import get_page_from_placeholder_if_exists

# filer
from filer.models.filemodels import *
from filer.models.foldermodels import *
from filer.models.audiomodels import *
from filer.models.imagemodels import *
from filer.fields.image import FilerImageField
from filer.fields.audio import FilerAudioField
from filer.fields.file import FilerFileField

# modules
from taggit.managers import TaggableManager
from django_countries import CountryField
from easy_thumbnails.files import get_thumbnailer

# model extensions
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField 


# logging
import logging
logger = logging.getLogger(__name__)


################
from alibrary.models import *


class MigrationMixin(models.Model):
    
    legacy_id = models.IntegerField(null=True, blank=True, editable=False)
    migrated = models.DateField(null=True, blank=True, editable=False)
    
    
    class Meta:
        abstract = True
        app_label = 'alibrary'
        verbose_name = _('MigrationMixin')
        verbose_name_plural = _('MigrationMixins')
        ordering = ('pk', )
    
    




class Label(MPTTModel, MigrationMixin):
    
    
    
    name = models.CharField(max_length=200)
    
    slug = models.SlugField(max_length=100, unique=False)
    uuid = models.CharField(max_length=36, unique=False, default=str(uuid.uuid4()), editable=False)
    
    labelcode = models.CharField(max_length=50)
    country = CountryField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    email_main = models.EmailField(blank=True, null=True)
    
    first_placeholder = PlaceholderField('first_placeholder')
    
    # auto-update
    created = models.DateField(auto_now_add=True, editable=False)
    updated = models.DateField(auto_now=True, editable=False)
    
    # relations
    parent = TreeForeignKey('self', null=True, blank=True, related_name='label_children')
    folder = models.ForeignKey(Folder, blank=True, null=True, related_name='label_folder')
    
    # manager
    objects = models.Manager()

    # meta
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Label')
        verbose_name_plural = _('Labels')
        ordering = ('name', )

    class MPTTMeta:
        order_insertion_by = ['name']
    
    def __unicode__(self):
        return self.name

    
    def get_folder(self, name):
        folder, created = Folder.objects.get_or_create(name=name, parent=self.folder)
        return folder
        
        
    def save(self, *args, **kwargs):
        
        folder_name = self.name
        
        if not self.folder:
            folder, created = Folder.objects.get_or_create(name=folder_name)
            self.folder = folder 
            
        super(Label, self).save(*args, **kwargs)

class License(MPTTModel):
    
    name = models.CharField(max_length=200)
    
    slug = models.SlugField(max_length=100, unique=False)
    uuid = models.CharField(max_length=36, unique=False, default=str(uuid.uuid4()), editable=False)
    
    link = models.URLField(null=True, blank=True)
    
    restricted = models.NullBooleanField(null=True, blank=True)
    
    excerpt = models.TextField(blank=True, null=True)  
    license_text = models.TextField(blank=True, null=True) 
    
    # auto-update
    created = models.DateField(auto_now_add=True, editable=False)
    updated = models.DateField(auto_now=True, editable=False)
    
    # relations
    parent = TreeForeignKey('self', null=True, blank=True, related_name='license_children')
    
    # manager
    objects = models.Manager()

    # meta
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('License')
        verbose_name_plural = _('Licenses')
        ordering = ('name', )

    class MPTTMeta:
        order_insertion_by = ['name']
    
    def __unicode__(self):
        return self.name

class ProfessionManager(models.Manager):

    def listed(self):
        return self.get_query_set().filter(in_listing=True)
    
    
class Profession(models.Model):
    
    name = models.CharField(max_length=200)
    
    in_listing = models.BooleanField(default=True, verbose_name='Include in listings')
    
    excerpt = models.TextField(blank=True, null=True)  
    
    # auto-update
    created = models.DateField(auto_now_add=True, editable=False)
    updated = models.DateField(auto_now=True, editable=False)
    
    # manager
    objects = ProfessionManager()

    # meta
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Role/Profession')
        verbose_name_plural = _('Roles/Profession')
        ordering = ('name', )
    
    def __unicode__(self):
        return self.name
    
    
class Mediaformat(models.Model):
    
    name = models.CharField(max_length=50)
    excerpt = models.TextField(blank=True, null=True) 
    in_listing = models.BooleanField(default=True, verbose_name='Include in listings')
    
    # manager
    objects = models.Manager()

    # meta
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Mediaformat')
        verbose_name_plural = _('Mediaformat')
        ordering = ('name', )
    
    def __unicode__(self):
        return self.name
    
    

class RelationManager(models.Manager):

    def generic(self):
        return self.get_query_set().filter(service='generic')

    def specific(self):
        return self.get_query_set().exclude(service='generic')
    
    
class Relation(models.Model):
    
    name = models.CharField(max_length=200, blank=True, null=True, help_text=(_('Additionally override the name.')))
    url = models.URLField(max_length=512)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')


    SERVICE_CHOICES = (
        ('generic', _('Generic')),
        ('facebook', _('Facebook')),
        ('youtube', _('YouTube')),
        ('discogs', _('Discogs')),
        ('wikipedia', _('Wikipedia')),
        ('musicbrainz', _('Musicbrainz')),
        ('bandcamp', _('Bandcamp')),
    )
    service = models.CharField(max_length=50, default='generic', choices=SERVICE_CHOICES)
    
    ACTION_CHOICES = (
        ('information', _('Information')),
        ('buy', _('Buy')),
    )
    action = models.CharField(max_length=50, default='information', choices=ACTION_CHOICES)

    
    # auto-update
    created = models.DateField(auto_now_add=True, editable=False)
    updated = models.DateField(auto_now=True, editable=False)
    
    # manager
    objects = RelationManager()

    # meta
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Relation')
        verbose_name_plural = _('Relations')
        ordering = ('url', )
    
    def __unicode__(self):
        return self.url
    
    
    def save(self, *args, **kwargs):
        """
        try to extract service
        """
               
        if self.url.find('facebook.com') != -1:
            self.service = 'facebook'
            
        if self.url.find('youtube.com') != -1:
            self.service = 'youtube' 
                   
        if self.url.find('discogs.com') != -1:
            self.service = 'discogs'
                   
        if self.url.find('wikipedia.org') != -1:
            self.service = 'wikipedia'
                   
        if self.url.find('musicbrainz.org') != -1:
            self.service = 'musicbrainz'
                   
        if self.url.find('bandcamp.com') != -1:
            self.service = 'bandcamp'

        super(Relation, self).save(*args, **kwargs)
    



# some helpers...
def generate_uuid():
    return str(uuid.uuid4())