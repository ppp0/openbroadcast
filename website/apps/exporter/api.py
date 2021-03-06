from django.contrib.auth.models import User
from django.db.models import Count

from tastypie import fields
from tastypie.authentication import *
from tastypie.authorization import *
from tastypie.resources import ModelResource, Resource, ALL, ALL_WITH_RELATIONS

from exporter.models import Export, ExportItem

from alibrary.api import ReleaseResource, ArtistResource
from alibrary.models import Release, Artist

from django.template import defaultfilters as dj_filters
from django.utils import formats


from tastypie.contrib.contenttypes.fields import GenericForeignKeyField


class ExportItemResource(ModelResource):
    
    export_session = fields.ForeignKey('exporter.api.ExportResource', 'export_session', null=True, full=False)
    
    co_to = {
             Release: ReleaseResource,
             Artist: ArtistResource,
             }
    
    content_object = GenericForeignKeyField(to=co_to, attribute='content_object', null=False, full=False)

    class Meta:
        queryset = ExportItem.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'delete']
        resource_name = 'exportitem'
        # excludes = ['type','results_musicbrainz']
        #excludes = ['id',]
        authentication =  MultiAuthentication(SessionAuthentication(), ApiKeyAuthentication())
        authorization = Authorization()
        always_return_data = True
        filtering = {
            'import_session': ALL_WITH_RELATIONS,
            'created': ['exact', 'range', 'gt', 'gte', 'lt', 'lte'],
        }
        
    

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(export_session__user=request.user)

    def obj_create(self, bundle, request, **kwargs):
        
        
        item = bundle.data['item']
        print bundle.data['item']['item_id']
        
        # dummy
        if item['item_type'] == 'release':
            co = Release.objects.get(pk=int(item['item_id']))
            
        bundle.data['content_object'] = co
        
        return super(ExportItemResource, self).obj_create(bundle, request, **kwargs)


class ExportResource(ModelResource):
    
    items = fields.ToManyField('exporter.api.ExportItemResource', 'export_items', full=False, null=True)

    class Meta:
        queryset = Export.objects.all()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'post', 'put', 'delete']
        #list_allowed_methods = ['get',]
        #detail_allowed_methods = ['get',]
        resource_name = 'export'
        excludes = ['updated',]
        include_absolute_url = True
        authentication =  MultiAuthentication(SessionAuthentication(), ApiKeyAuthentication())
        authorization = Authorization()
        always_return_data = True
        filtering = {
            #'channel': ALL_WITH_RELATIONS,
            'created': ['exact', 'range', 'gt', 'gte', 'lt', 'lte'],
            'status': ['exact',],
        }
        
    def obj_create(self, bundle, request=None, **kwargs):
        return super(ExportResource, self).obj_create(bundle, request, user=request.user)
        

    def dehydrate(self, bundle):
        bundle.data['download_url'] = bundle.obj.get_download_url();
        
        # pre-format some values
        try:
            formatted_created = formats.date_format(bundle.obj.created, "SHORT_DATETIME_FORMAT")
        except:
            formatted_created = None
            
        try:
            formatted_downloaded = formats.date_format(bundle.obj.downloaded, "SHORT_DATETIME_FORMAT")
        except:
            formatted_downloaded = None
            
        
        bundle.data['formatted_created']  = formatted_created
        bundle.data['formatted_downloaded']  = formatted_downloaded
        bundle.data['formatted_filesize']  = dj_filters.filesizeformat(bundle.obj.filesize)
        
        return bundle
        
    def save_related(self, obj):
        return True
    

    def apply_authorization_limits(self, request, object_list):
        return object_list.filter(user=request.user)

        

    
    
    

    