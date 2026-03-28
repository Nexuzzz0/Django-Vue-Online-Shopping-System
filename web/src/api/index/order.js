/**
 * api
 */
import axios from '@/utils/request.js'

const api = {
  listApi: '/myapp/index/order/list',
  createApi: '/myapp/index/order/create',
  cancelOrderApi: '/myapp/index/order/cancel_order',
  delayApi: '/myapp/index/order/delay',
  confirmApi: '/myapp/index/order/confirm',
  completeApi: '/myapp/index/order/complete',
  refundApplyApi: '/myapp/index/order/refund_apply'
}

/**
 * 列表
 */
export const listApi = function (params) {
  return axios({
    url: api.listApi,
    method: 'get',
    params: params
  })
}

/**
 * 新建
 */
export const createApi = function (data) {
  return axios({
    url: api.createApi,
    method: 'post',
    headers: {
      'Content-Type': 'multipart/form-data;charset=utf-8'
    },
    data: data
  })
}

/**
 * 取消
 */
export const cancelOrderApi = function (params) {
  return axios({
    url: api.cancelOrderApi,
    method: 'post',
    headers: {
      'Content-Type': 'multipart/form-data;charset=utf-8'
    },
    params: params,
  })
}

export const confirmOrderApi = function (params) {
  return axios({
    url: api.confirmApi,
    method: 'post',
    headers: {
      'Content-Type': 'multipart/form-data;charset=utf-8'
    },
    params: params,
  })
}

export const completeOrderApi = function (params) {
  return axios({
    url: api.completeApi,
    method: 'post',
    headers: {
      'Content-Type': 'multipart/form-data;charset=utf-8'
    },
    params: params,
  })
}

export const refundApplyApi = function (params) {
  return axios({
    url: api.refundApplyApi,
    method: 'post',
    headers: {
      'Content-Type': 'multipart/form-data;charset=utf-8'
    },
    params: params,
  })
}
/**
 * 延期
 */
export const delayApi = function (params, data) {
  return axios({
    url: api.delayApi,
    method: 'post',
    headers: {
      'Content-Type': 'multipart/form-data;charset=utf-8'
    },
    params: params,
    data: data
  })
}
