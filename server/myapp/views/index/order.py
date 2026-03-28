# Create your views here.
import datetime

from django.db import transaction
from django.db.models import F
from rest_framework.decorators import api_view, authentication_classes

from myapp import utils
from myapp.auth.authentication import TokenAuthtication
from myapp.handler import APIResponse
from myapp.models import Order, Thing
from myapp.serializers import OrderSerializer


@api_view(['GET'])
def list_api(request):
    if request.method == 'GET':
        userId = request.GET.get('userId', -1)
        orderStatus = request.GET.get('orderStatus', '')

        orders = Order.objects.all().filter(user=userId)
        if orderStatus:
            if orderStatus == 'paid':
                orders = orders.filter(status__in=['2', '3', '4', '5', '6'])
            elif orderStatus == 'unpaid':
                orders = orders.filter(status='1')
            elif orderStatus == 'canceled':
                orders = orders.filter(status='7')
            else:
                orders = orders.filter(status__contains=orderStatus)

        orders = orders.order_by('-order_time')
        serializer = OrderSerializer(orders, many=True)
        return APIResponse(code=0, msg='查询成功', data=serializer.data)


@api_view(['POST'])
@authentication_classes([TokenAuthtication])
def create(request):
    data = request.data.copy()
    if data['user'] is None or data['thing'] is None or data['count'] is None:
        return APIResponse(code=1, msg='参数错误')

    thing = Thing.objects.get(pk=data['thing'])
    count = data['count']
    if thing.repertory < int(count):
        return APIResponse(code=1, msg='库存不足')

    create_time = datetime.datetime.now()
    data['create_time'] = create_time
    data['order_number'] = str(utils.get_timestamp())
    data['status'] = '1'
    serializer = OrderSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        # 减库存(支付后)
        # thing.repertory = thing.repertory - int(count)
        # thing.save()

        return APIResponse(code=0, msg='创建成功', data=serializer.data)
    else:
        print(serializer.errors)
        return APIResponse(code=1, msg='创建失败')


@api_view(['POST'])
@authentication_classes([TokenAuthtication])
def cancel_order(request):
    """
    cancal
    """
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    # 仅允许未支付订单取消（库存扣减发生在支付环节）
    if str(order.status) != '1':
        return APIResponse(code=1, msg='当前状态不可取消')

    data = {
        'status': '7'
    }
    serializer = OrderSerializer(order, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        # 加库存
        # thingId = request.data['thing']
        # thing = Thing.objects.get(pk=thingId)
        # thing.repertory = thing.repertory + 1
        # thing.save()

        # 加积分
        # order.user.score = order.user.score + 1
        # order.user.save()

        return APIResponse(code=0, msg='取消成功', data=serializer.data)
    else:
        print(serializer.errors)
        return APIResponse(code=1, msg='更新失败')


@api_view(['POST'])
@authentication_classes([TokenAuthtication])
def confirm(request):
    """
    confirm
    """
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    # 仅允许未支付订单进行支付确认
    if str(order.status) != '1':
        return APIResponse(code=1, msg='当前状态不可支付')

    # 支付时扣库存：使用事务 + 行锁避免并发超卖
    try:
        with transaction.atomic():
            thing = Thing.objects.select_for_update().get(pk=order.thing_id)
            buy_count = int(order.count or 0)
            if buy_count <= 0:
                return APIResponse(code=1, msg='购买数量错误')
            if int(thing.repertory or 0) < buy_count:
                return APIResponse(code=1, msg='库存不足')

            thing.repertory = int(thing.repertory or 0) - buy_count
            thing.save()

            # 支付成功后计入热度（pv）
            Thing.objects.filter(pk=thing.pk).update(pv=F('pv') + 1)

            data = {
                'status': '2',
                'pay_time': datetime.datetime.now(),
            }
            serializer = OrderSerializer(order, data=data, partial=True)
            if not serializer.is_valid():
                raise ValueError(serializer.errors)
            serializer.save()
            return APIResponse(code=0, msg='付款成功', data=serializer.data)
    except Thing.DoesNotExist:
        return APIResponse(code=1, msg='商品不存在')
    except Exception as e:
        print(e)
        return APIResponse(code=1, msg='更新失败')


@api_view(['POST'])
@authentication_classes([TokenAuthtication])
def complete(request):
    """确认收货：已发货(3) -> 已完成(4)"""
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    if str(order.status) != '3':
        return APIResponse(code=1, msg='当前状态不可确认收货')

    data = {
        'status': '4'
    }
    serializer = OrderSerializer(order, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='确认收货成功', data=serializer.data)
    else:
        print(serializer.errors)
        return APIResponse(code=1, msg='更新失败')


@api_view(['POST'])
@authentication_classes([TokenAuthtication])
def refund_apply(request):
    """申请退款：待发货(2)/待收货(3) -> 退款中(5)"""
    try:
        pk = request.GET.get('id', -1)
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return APIResponse(code=1, msg='对象不存在')

    if str(order.status) not in ['2', '3']:
        return APIResponse(code=1, msg='当前状态不可申请退款')

    serializer = OrderSerializer(order, data={'status': '5'}, partial=True)
    if serializer.is_valid():
        serializer.save()
        return APIResponse(code=0, msg='申请退款成功', data=serializer.data)
    else:
        print(serializer.errors)
        return APIResponse(code=1, msg='更新失败')
