from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib import admin

class Identifier(models.Model):
    name       = models.CharField(max_length=255)
    slug       = models.SlugField()
    authority  = models.ForeignKey('Authority', blank=True, null=True)
    is_primary = models.BooleanField()
    valid_from = models.DateField(blank=True, null=True)
    valid_to   = models.DateField(blank=True, null=True)

    # Identifer can contain a pointer to any model
    content_type   = models.ForeignKey(ContentType)
    object_id      = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    def __unicode__(self):
        return self.name

class IdentifiedModelManager(models.Manager):
    def get_by_identifier(self, identifier):
        return self.get(identifiers__name = identifier)
    def filter_by_identifier(self, identifier):
        return self.filter(identifiers__name = identifier)

class IdentifiedModel(models.Model):
    identifiers = generic.GenericRelation(Identifier)
    objects     = IdentifiedModelManager()

    def fallback_identifier(self):
        if hasattr(self, 'name'):
            return self.name
        else:
            return ContentType.objects.get_for_model(self).name

    def __unicode__(self):
        ids = self.identifiers.filter(is_primary=True)
        if (len(ids) > 0):
            return ', '.join(map(str, ids))
        else:
            return self.fallback_identifier()

    class Meta:
        abstract = True

class Authority(models.Model):
    name = models.CharField(max_length=255)
    class Meta:
        verbose_name_plural = 'authorities'

    def __unicode__(self):
        return self.name

# Admin interface
class IdentifierInline(generic.GenericTabularInline):
    model = Identifier
    prepopulated_fields = {"slug": ("name",)}
    extra = 0

class IdentifiedModelAdmin(admin.ModelAdmin):
    inlines = [
        IdentifierInline
    ]

admin.site.register(Authority)
