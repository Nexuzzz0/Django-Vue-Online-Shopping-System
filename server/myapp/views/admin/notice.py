# Create your views here.
from rest_framework.decorators import api_view, authentication_classes

from myapp.auth.authentication import AdminTokenAuthtication
from myapp.handler import APIResponse
from myapp.models import Notice
from myapp.permission.permission import isDemoAdminUser
from myapp.serializers import NoticeSerializer


@api_view(['GET'])
def list_api(request):
    if request.method == 'GET':
        page = request.GET.get('page', None)
        pageSize = request.GET.get('pageSize', None)
        try:
            page_int = int(page) if page is not None else None
            page_size_int = int(pageSize) if pageSize is not None else None
        except Exception:
            return APIResponse(code=1, msg='分页参数错误')

        notices = Notice.objects.all().order_by('-create_time')
        total = notices.count()

        # 兼容：不传分页参数时，保持老的返回结构（list）
        if page_int is None or page_size_int is None:
            serializer = NoticeSerializer(notices, many=True)
            return APIResponse(code=0, msg='查询成功', data=serializer.data)

        if page_int < 1:
            page_int = 1
        if page_size_int < 1:
            page_size_int = 10
        if page_size_int > 100:
            page_size_int = 100

        start = (page_int - 1) * page_size_int
        end = start + page_size_int
        serializer = NoticeSerializer(notices[start:end], many=True)
        return APIResponse(code=0, msg='查询成功', data={
            'list': serializer.data,
            'total': total,
            'page': page_int,
            'pageSize': page_size_int,
        })


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def create(request):
    if isDemoAdminUser(request):
        return APIResponse(code=1, msg='演示帐号无法操作')

    serializer = NoticeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='创建成功', data=serializer.data)

    return APIResponse(code=1, msg='创建失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def update(request):
    if isDemoAdminUser(request):
        return APIResponse(code=1, msg='演示帐号无法操作')

    try:
        pk = request.GET.get('id', -1)
        notice = Notice.objects.get(pk=pk)
    except Notice.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    serializer = NoticeSerializer(notice, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='更新成功', data=serializer.data)
    else:
        print(serializer.errors)

    return APIResponse(code=1, msg='更新失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def delete(request):
    if isDemoAdminUser(request):
        return APIResponse(code=1, msg='演示帐号无法操作')

    try:
        ids = request.GET.get('ids')
        ids_arr = ids.split(',')
        Notice.objects.filter(id__in=ids_arr).delete()
    except Notice.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    return APIResponse(code=0, msg='删除成功')
