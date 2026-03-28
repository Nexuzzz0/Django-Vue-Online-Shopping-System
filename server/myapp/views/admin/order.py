# Create your views here.
from rest_framework.decorators import api_view, authentication_classes

from myapp.auth.authentication import AdminTokenAuthtication
from myapp.handler import APIResponse
from django.db import transaction

from myapp.models import Order, Thing
from myapp.serializers import OrderSerializer


@api_view(['GET'])
@authentication_classes([AdminTokenAuthtication])
def list_api(request):
    if request.method == 'GET':
        page = request.GET.get('page', None)
        pageSize = request.GET.get('pageSize', None)
        try:
            page_int = int(page) if page is not None else None
            page_size_int = int(pageSize) if pageSize is not None else None
        except Exception:
            return APIResponse(code=1, msg='分页参数错误')

        orders = Order.objects.select_related('user', 'thing').all().order_by('-order_time')
        total = orders.count()

        # 兼容：不传分页参数时，保持老的返回结构（list）
        if page_int is None or page_size_int is None:
            serializer = OrderSerializer(orders, many=True)
            return APIResponse(code=0, msg='查询成功', data=serializer.data)

        if page_int < 1:
            page_int = 1
        if page_size_int < 1:
            page_size_int = 10
        if page_size_int > 100:
            page_size_int = 100

        start = (page_int - 1) * page_size_int
        end = start + page_size_int
        serializer = OrderSerializer(orders[start:end], many=True)
        return APIResponse(code=0, msg='查询成功', data={
            'list': serializer.data,
            'total': total,
            'page': page_int,
            'pageSize': page_size_int,
        })


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def create(request):

    serializer = OrderSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='创建成功', data=serializer.data)

    return APIResponse(code=1, msg='创建失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
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
@authentication_classes([AdminTokenAuthtication])
def delete(request):
    try:
        ids = request.GET.get('ids')
        ids_arr = ids.split(',')
        Order.objects.filter(id__in=ids_arr).delete()
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    return APIResponse(code=0, msg='删除成功')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def cancel_order(request):
    """后台取消订单：将订单状态更新为已取消(7)"""
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    if str(order.status) == '7':
        return APIResponse(code=0, msg='订单已取消', data=OrderSerializer(order).data)

    # 演示：允许管理员从任意非终态取消（已完成/已退款不允许）
    if str(order.status) in ['4', '6']:
        return APIResponse(code=1, msg='当前状态不可取消')

    serializer = OrderSerializer(order, data={'status': '7'}, partial=True)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='取消成功', data=serializer.data)
    return APIResponse(code=1, msg='取消失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def ship(request):
    """发货：已支付(2) -> 已发货(3)"""
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    if str(order.status) != '2':
        return APIResponse(code=1, msg='当前状态不可发货')

    serializer = OrderSerializer(order, data={'status': '3'}, partial=True)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='发货成功', data=serializer.data)
    return APIResponse(code=1, msg='发货失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def refund_approve(request):
    """同意退款：退款中(5) -> 已退款(6)，并回补库存"""
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    if str(order.status) != '5':
        return APIResponse(code=1, msg='当前状态不可退款')

    try:
        with transaction.atomic():
            thing = Thing.objects.select_for_update().get(pk=order.thing_id)
            refund_count = int(order.count or 0)
            if refund_count <= 0:
                return APIResponse(code=1, msg='退款数量错误')

            thing.repertory = int(thing.repertory or 0) + refund_count
            thing.save()

            serializer = OrderSerializer(order, data={'status': '6'}, partial=True)
            if serializer.is_valid():
                serializer.save()
                return APIResponse(code=0, msg='退款成功', data=serializer.data)
            return APIResponse(code=1, msg='退款失败')
    except Thing.DoesNotExist:
        return APIResponse(code=1, msg='商品不存在')
    except Exception as e:
        print(e)
        return APIResponse(code=1, msg='退款失败')


@api_view(['POST'])
@authentication_classes([AdminTokenAuthtication])
def refund_reject(request):
    """拒绝退款：退款中(5) -> 待发货(2)（演示简化）"""
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    if str(order.status) != '5':
        return APIResponse(code=1, msg='当前状态不可拒绝退款')

    serializer = OrderSerializer(order, data={'status': '2'}, partial=True)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='已拒绝退款', data=serializer.data)
    return APIResponse(code=1, msg='操作失败')
