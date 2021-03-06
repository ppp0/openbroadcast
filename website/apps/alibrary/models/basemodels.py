# python
import datetime
import uuid
import shutil
import sys

# django
from django.db import models
from django import forms
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
#from taggit.managers import TaggableManager
from django_countries import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from easy_thumbnails.files import get_thumbnailer

import tagging
import reversion 

# model extensions
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField 
from multilingual.translation import TranslationModel
from multilingual.manager import MultilingualManager

# django-extensions (http://packages.python.org/django-extensions/)
from django_extensions.db.fields import UUIDField, AutoSlugField

from l10n.models import AdminArea, Country


# logging
import logging
logger = logging.getLogger(__name__)


################
from alibrary.models import *
from alibrary.util.signals import library_post_save
from alibrary.util.slug import unique_slugify

from lib.fields import extra


    

class MigrationMixin(models.Model):
    
    legacy_id = models.IntegerField(null=True, blank=True, editable=False)
    migrated = models.DateField(null=True, blank=True, editable=False)
    
    
    class Meta:
        abstract = True
        app_label = 'alibrary'
        verbose_name = _('MigrationMixin')
        verbose_name_plural = _('MigrationMixins')
        ordering = ('pk', )
    
    



class Distributor(MPTTModel, MigrationMixin):

    # core fields
    uuid = UUIDField(primary_key=False)
    name = models.CharField(max_length=400)
    slug = AutoSlugField(populate_from='name', editable=True, blank=True, overwrite=True)
    
    code = models.CharField(max_length=50)
    country = models.ForeignKey(Country, blank=True, null=True)
    
    address = models.TextField(blank=True, null=True)
    
    email = models.EmailField(blank=True, null=True)
    phone = PhoneNumberField(blank=True, null=True)
    fax = PhoneNumberField(blank=True, null=True)
    
    description = extra.MarkdownTextField(blank=True, null=True)
    
    first_placeholder = PlaceholderField('first_placeholder')
    
    # auto-update
    created = models.DateField(auto_now_add=True, editable=False)
    updated = models.DateField(auto_now=True, editable=False)
    
    # relations
    parent = TreeForeignKey('self', null=True, blank=True, related_name='label_children')

    labels = models.ManyToManyField('Label', through='DistributorLabel', blank=True, null=True, related_name="distributors")
    
    # user relations
    owner = models.ForeignKey(User, blank=True, null=True, related_name="distributors_owner", on_delete=models.SET_NULL)
    creator = models.ForeignKey(User, blank=True, null=True, related_name="distributors_creator", on_delete=models.SET_NULL)
    publisher = models.ForeignKey(User, blank=True, null=True, related_name="distributors_publisher", on_delete=models.SET_NULL)
    
    TYPE_CHOICES = (
        ('unknown', _('Unknown')),
        ('major', _('Major Label')),
        ('indy', _('Independent Label')),
        ('net', _('Netlabel')),
    )
    
    type = models.CharField(verbose_name="Distributor type", max_length=12, default='unknown', choices=TYPE_CHOICES)


    # relations a.k.a. links
    relations = generic.GenericRelation('Relation')
    
    # tagging (d_tags = "display tags")
    d_tags = tagging.fields.TagField(max_length=1024, verbose_name="Tags", blank=True, null=True)
 
    
    # manager
    objects = models.Manager()

    # meta
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Distributor')
        verbose_name_plural = _('Distributors')
        ordering = ('name', )

    class MPTTMeta:
        order_insertion_by = ['name']
    
    def __unicode__(self):
        return self.name



    @models.permalink
    def get_absolute_url(self):
        if self.disable_link:
            return None
        
        return ('alibrary-label-detail', [self.slug])

    @models.permalink
    def get_edit_url(self):
        return ('alibrary-label-edit', [self.pk])
    

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        
        # update d_tags
        t_tags = ''
        for tag in self.tags:
            t_tags += '%s, ' % tag    
        
        self.tags = t_tags;
        self.d_tags = t_tags;
        
        super(Distributor, self).save(*args, **kwargs)

       
    
        
try:
    tagging.register(Distributor)
except:
    pass     
        
        

class DistributorLabel(models.Model):
    distributor = models.ForeignKey('Distributor')
    label = models.ForeignKey('Label')
    exclusive = models.BooleanField(default=False)
    countries = models.ManyToManyField(Country, related_name="distribution_countries")
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Labels in catalog')
        verbose_name_plural = _('Labels in catalog')
        
        

class License(MPTTModel, MigrationMixin):
    
    name = models.CharField(max_length=200)
    
    slug = models.SlugField(max_length=100, unique=False)
    uuid = models.CharField(max_length=36, unique=False, default=str(uuid.uuid4()), editable=False)
    
    key = models.CharField(verbose_name=_("License key"), help_text=_("used e.g. for the icon-names"), max_length=36, blank=True, null=True)
    
    link = models.URLField(null=True, blank=True)
    
    restricted = models.NullBooleanField(null=True, blank=True)
    
    is_default = models.BooleanField(default=False)
    

    class Translation(TranslationModel):
        
        name_translated = models.CharField(max_length=200)
        excerpt = models.TextField(blank=True, null=True)  
        license_text = models.TextField(blank=True, null=True) 
    
    
    # auto-update
    created = models.DateField(auto_now_add=True, editable=False)
    updated = models.DateField(auto_now=True, editable=False)
    
    # relations
    parent = TreeForeignKey('self', null=True, blank=True, related_name='license_children')
    
    # manager
    objects = MultilingualManager()

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
    
    @models.permalink
    def get_absolute_url(self):
        return ('alibrary-license-detail', [self.slug])

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
    
    
    
class DaypartManager(models.Manager):
    
    def active(self):
        return self.get_query_set().filter(active=True)
       
class Daypart(models.Model):
    
    
    active = models.BooleanField(default=True)
    
    DAY_CHOICES = (
        (0, _('Mon')),
        (1, _('Tue')),
        (2, _('Wed')),
        (3, _('Thu')),
        (4, _('Fri')),
        (5, _('Sat')),
        (6, _('Sun')),
    )
    day = models.PositiveIntegerField(max_length=1, default=0, null=True, choices=DAY_CHOICES)
    time_start = models.TimeField()
    time_end = models.TimeField()
    
    
    
    # manager
    objects = DaypartManager()

    # meta
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Daypart')
        verbose_name_plural = _('Dayparts')
        ordering = ('day', 'time_start' )
    
    def __unicode__(self):
        return "%s | %s - %s" % (self.get_day_display(), self.time_start, self.time_end)
    
    def playlist_count(self):
        return self.daypart_plalists.count()
    
    



class Service(models.Model):
    
    name = models.CharField(max_length=200)
    key = models.CharField(max_length=200, blank=True, null=True)
    pattern = models.CharField(max_length=256, null=True, blank=True, help_text='Regex to match url against. eg ""')
    
    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Service')
        verbose_name_plural = _('Services')
        ordering = ('name', )
    
    def __unicode__(self):
        return '%s - "%s"' % (self.name, self.pattern)
    
    

class RelationManager(models.Manager):

    def generic(self):
        return self.get_query_set().filter(service='generic')

    def specific(self, key=None):
        
        if not key:
            services = Service.objects.values_list('key', 'pattern',)
        
        return self.get_query_set().exclude(service='generic')

    """
    def generic(self):
        return self.get_query_set().filter(service='generic')

    def specific(self):
        return self.get_query_set().exclude(service='generic')
    """
    
class Relation(models.Model):
    
    name = models.CharField(max_length=200, blank=True, null=True, help_text=(_('Additionally override the name.')))
    url = models.URLField(max_length=512)

    content_type = models.ForeignKey(ContentType)
    #object_id = models.PositiveIntegerField()
    object_id = UUIDField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')


    SERVICE_CHOICES = (
        ('generic', _('Generic')),
        ('facebook', _('Facebook')),
        ('youtube', _('YouTube')),
        ('discogs', _('Discogs')),
        ('discogs_master', _('Discogs | master-release')),
        ('wikipedia', _('Wikipedia')),
        ('musicbrainz', _('Musicbrainz')),
        ('bandcamp', _('Bandcamp')),
        ('itunes', _('iTunes')),
        ('official', _('Official website')),
    )
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES, blank=True, null=True, editable=False)

    ACTION_CHOICES = (
        ('information', _('Information')),
        ('buy', _('Buy')),
    )
    action = models.CharField(max_length=50, default='information', choices=ACTION_CHOICES)

    @property
    def _service(cls):
        return cls.service


    
    # auto-update
    created = models.DateField(auto_now_add=True, editable=False)
    updated = models.DateField(auto_now=True, editable=False)
    
    # manager
    objects = RelationManager()

    class Meta:
        app_label = 'alibrary'
        verbose_name = _('Relation')
        verbose_name_plural = _('Relations')
        ordering = ('url', )
        #unique_together = ('content_type', 'object_id')
    
    def __unicode__(self):
        return self.url
    
    """"""
    def save(self, *args, **kwargs):

        
        if self.url.find('facebook.com') != -1:
            self.service = 'facebook'
            
        if self.url.find('youtube.com') != -1:
            self.service = 'youtube' 
                   
        if self.url.find('discogs.com') != -1:
            if self.url.find('/master/') != -1:
                self.service = 'discogs_master'
            else:
                self.service = 'discogs'
                   
        if self.url.find('wikipedia.org') != -1:
            self.service = 'wikipedia'
                   
        if self.url.find('musicbrainz.org') != -1:
            self.service = 'musicbrainz'
                   
        if self.url.find('bandcamp.com') != -1:
            self.service = 'bandcamp'
                   
        if self.url.find('itunes.apple.com') != -1:
            self.service = 'itunes'
            
        # find already assigned services and delete them
        if self.service != 'generic':
            # TODO: fix unique problem
            reld = Relation.objects.filter(service=self.service, content_type=self.content_type, object_id=self.object_id).delete()
        
        super(Relation, self).save(*args, **kwargs)    
        
    
    
class __old_Relation__(models.Model):
    
    name = models.CharField(max_length=200, blank=True, null=True, help_text=(_('Additionally override the name.')))
    url = models.URLField(max_length=512)

    content_type = models.ForeignKey(ContentType)
    #object_id = models.PositiveIntegerField()
    object_id = UUIDField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')


    SERVICE_CHOICES = (
        ('generic', _('Generic')),
        ('facebook', _('Facebook')),
        ('youtube', _('YouTube')),
        ('discogs', _('Discogs')),
        ('discogs_master', _('Discogs | master-release')),
        ('wikipedia', _('Wikipedia')),
        ('musicbrainz', _('Musicbrainz')),
        ('bandcamp', _('Bandcamp')),
        ('itunes', _('iTunes')),
        ('official', _('Official website')),
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
        #unique_together = ('content_type', 'object_id')
    
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
            if self.url.find('/master/') != -1:
                self.service = 'discogs_master'
            else:
                self.service = 'discogs'
                   
        if self.url.find('wikipedia.org') != -1:
            self.service = 'wikipedia'
                   
        if self.url.find('musicbrainz.org') != -1:
            self.service = 'musicbrainz'
                   
        if self.url.find('bandcamp.com') != -1:
            self.service = 'bandcamp'
                   
        if self.url.find('itunes.apple.com') != -1:
            self.service = 'itunes'
            
        # find already assigned services and delete them
        if self.service != 'generic':
            # TODO: fix unique problem
            reld = Relation.objects.filter(service=self.service, content_type=self.content_type, object_id=self.object_id).delete()

        super(Relation, self).save(*args, **kwargs)
    



# some helpers...
def generate_uuid():
    return str(uuid.uuid4())
