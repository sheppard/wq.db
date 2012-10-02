from djangorestframework import views, status, response
from wq.db.renderers import JSONRenderer, XMLRenderer, HTMLRenderer, AMDRenderer

from django.contrib.contenttypes.models import ContentType
from wq.db.annotate.models import Annotation, AnnotatedModel, AnnotationType
from wq.db import resources

from django.conf import settings
from wq.db.util import get_config, has_perm, geturlbase, user_dict

from django.contrib.auth import authenticate, login, logout

_FORBIDDEN_RESPONSE = "Sorry %s, you do not have permission to %s this %s."
_RENDERERS = [HTMLRenderer, JSONRenderer, XMLRenderer, AMDRenderer]

class View(views.View):
    renderers = _RENDERERS

class InstanceModelView(views.InstanceModelView):
    renderers = _RENDERERS
    def put(self, request, *args, **kwargs):
        ct = ContentType.objects.get_for_model(self.resource.model)
        if not has_perm(request.user, ct, 'change'):
            forbid(request.user, ct, 'change')

        res = super(InstanceModelView, self).put(request, *args, **kwargs)

        if issubclass(self.resource.model, AnnotatedModel):
            atypes = AnnotationType.objects.filter(contenttype=ct)
            for at in atypes:
                fname = 'annotation-%s' % at.pk
                if fname in self.CONTENT:
                    annot, isnew = Annotation.objects.get_or_create(
                        type=at, content_type=ct, object_id=res.pk)
                    annot.value = self.CONTENT[fname]
                    annot.save()
        return res

    def delete(self, request, *args, **kwargs):
        ct = ContentType.objects.get_for_model(self.resource.model)
        if not has_perm(request.user, ct, 'delete'):
            forbid(request.user, ct, 'delete')
        return super(InstanceModelView, delete).put(request, *args, **kwargs)

class ListOrCreateModelView(views.ListOrCreateModelView):
    renderers = _RENDERERS
    annotations = {}
    def get_query_kwargs(self, *args, **kwargs):
        for key, val in self.request.GET.items():
            if key in '_':
                continue
            kwargs[key] = val if isinstance(val, unicode) else val[0]
        kwargs = super(ListOrCreateModelView, self).get_query_kwargs(*args, **kwargs)
        return kwargs

    @property
    def CONTENT(self):
        content = super(ListOrCreateModelView, self).CONTENT
        if issubclass(self.resource.model, AnnotatedModel):
            ct = ContentType.objects.get_for_model(self.resource.model)
            atypes = AnnotationType.objects.filter(contenttype=ct)
            for at in atypes:
                fname = 'annotation-%s' % at.pk
                if fname in content:
                    self.annotations[at] = content[fname]
                    del content[fname]
                else:
                    self.annotations[at] = ""
        return content

    def get(self, request, *args, **kwargs):
        ct = ContentType.objects.get_for_model(self.resource.model)
        if not has_perm(request.user, ct, 'view'):
            forbid(request.user, ct, 'view')
        return super(ListOrCreateModelView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ct = ContentType.objects.get_for_model(self.resource.model)
        if not has_perm(request.user, ct, 'add'):
            forbid(request.user, ct, 'add')
        res = super(ListOrCreateModelView, self).post(request, *args, **kwargs)

        if issubclass(self.resource.model, AnnotatedModel):
            for at, val in self.annotations.iteritems():
                annot, isnew = Annotation.objects.get_or_create(
                type=at, content_type=ct, object_id=res.raw_content.id)
                annot.value = val
                annot.save()
        return res

class ConfigView(View):
    def get(self, request, *args, **kwargs):
        return get_config(request.user)

class LoginView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return {
                'user':   user_dict(request.user),
                'config': get_config(request.user)
            }
        else:
            return {}

    def post(self, request, *args, **kwargs):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return {
                'user':   user_dict(user),
                'config': get_config(user)
            }
        else:
            return {}

class LogoutView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            logout(request)
            return True
        else:
            return {}

def forbid(user, ct, perm):
    raise response.ErrorResponse(status.HTTP_403_FORBIDDEN, {
        'details': _FORBIDDEN_RESPONSE % (user, perm, ct)
    })