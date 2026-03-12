# Create your views here.
from rest_framework.decorators import api_view

from myapp.handler import APIResponse
from myapp.models import Order
from myapp.serializers import OrderSerializer


@api_view(['GET'])
def list_api(request):
    if request.method == 'GET':
        order = Order.objects.all()
        serializer = OrderSerializer(order, many=True)
        return APIResponse(code=0, msg='查询成功', data=serializer.data)


@api_view(['POST'])
def create(request):

    serializer = OrderSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='创建成功', data=serializer.data)

    return APIResponse(code=1, msg='创建失败')


@api_view(['POST'])
def update(request):
    try:
        pk = request.GET.get('id', -1)
        records = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    serializer = OrderSerializer(records, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='更新成功', data=serializer.data)

    return APIResponse(code=1, msg='更新失败')


@api_view(['POST'])
def delete(request):
    try:
        ids = request.GET.get('ids')
        ids_arr = ids.split(',')
        Order.objects.filter(id__in=ids_arr).delete()
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    return APIResponse(code=0, msg='删除成功')
