/**
 * index ad api (public)
 */
import axios from '@/utils/request.js'

const api = {
  // note: backend currently exposes ad list under admin without auth for GET
  listApi: '/myapp/admin/ad/list'
}

export const listApi = function (params) {
  return axios({
    url: api.listApi,
    method: 'get',
    params
  })
}
