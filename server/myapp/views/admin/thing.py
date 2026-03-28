# Create your views here.
from rest_framework.decorators import api_view, authentication_classes

from myapp import utils
from myapp.auth.authentication import AdminTokenAuthtication
from myapp.handler import APIResponse
from myapp.models import Classification, Thing, Tag
from myapp.permission.permission import isDemoAdminUser
from myapp.serializers import ThingSerializer, UpdateThingSerializer


@api_view(['GET'])
def list_api(request):
    if request.method == 'GET':
        keyword = request.GET.get("keyword", None)
        c = request.GET.get("c", None)
        tag = request.GET.get("tag", None)
        page = request.GET.get('page', None)
        pageSize = request.GET.get('pageSize', None)

        try:
            page_int = int(page) if page is not None else None
            page_size_int = int(pageSize) if pageSize is not None else None
        except Exception:
            return APIResponse(code=1, msg='分页参数错误')

        if keyword:
            things = Thing.objects.filter(title__contains=keyword).order_by('-create_time')
        elif c:
            classification = Classification.objects.get(pk=c)
            things = classification.classification_thing.all().order_by('-create_time')
        elif tag:
            tag = Tag.objects.get(id=tag)
            print(tag)
            things = tag.thing_set.all().order_by('-create_time')
        else:
            things = Thing.objects.all().order_by('-create_time')

        total = things.count()
        # 兼容：不传分页参数时，保持老的返回结构（list）
        if page_int is None or page_size_int is None:
            serializer = ThingSerializer(things, many=True)
            return APIResponse(code=0, msg='查询成功', data=serializer.data)

        if page_int < 1:
            page_int = 1
        if page_size_int < 1:
            page_size_int = 10
        if page_size_int > 100:
            page_size_int = 100

        start = (page_int - 1) * page_size_int
        end = start + page_size_int
        serializer = ThingSerializer(things[start:end], many=True)
        return APIResponse(code=0, msg='查询成功', data={
            'list': serializer.data,
            'total': total,
            'page': page_int,
            'pageSize': page_size_int,
        })


@api_view(['GET'])
def detail(request):

    try:
        pk = request.GET.get('id', -1)
        thing = Thing.objects.get(pk=pk)
    except Thing.DoesNotExist:
        utils.log_error(request, '对象不存在')
        return APIResponse(code=1, msg='对象不存在')

    if request.method == 'GET':
        serializer = ThingSerializer(thing)
        return APIResponse(code=0, msg='查询成功', data=serializer.data)


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def create(request):

    if isDemoAdminUser(request):
        return APIResponse(code=1, msg='演示帐号无法操作')

    serializer = ThingSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='创建成功', data=serializer.data)
    else:
        print(serializer.errors)
        utils.log_error(request, '参数错误')

    return APIResponse(code=1, msg='创建失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def update(request):

    if isDemoAdminUser(request):
        return APIResponse(code=1, msg='演示帐号无法操作')

    try:
        pk = request.GET.get('id', -1)
        thing = Thing.objects.get(pk=pk)
    except Thing.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    serializer = UpdateThingSerializer(thing, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='查询成功', data=serializer.data)
    else:
        print(serializer.errors)
        utils.log_error(request, '参数错误')

    return APIResponse(code=1, msg='更新失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def delete(request):

    if isDemoAdminUser(request):
        return APIResponse(code=1, msg='演示帐号无法操作')

    try:
        ids = request.GET.get('ids')
        ids_arr = ids.split(',')
        Thing.objects.filter(id__in=ids_arr).delete()
    except Thing.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')
    return APIResponse(code=0, msg='删除成功')
