import Vue from 'vue'
import {BASE_URL} from '@/store/constants'
import placeholderThing from '@/assets/images/placeholder-thing.svg'

function isAbsoluteUrl (value) {
  return /^https?:\/\//i.test(value) || /^data:/i.test(value) || /^blob:/i.test(value)
}

function joinUrl (baseUrl, path) {
  if (!baseUrl) return path
  if (!path) return baseUrl
  if (baseUrl.endsWith('/') && path.startsWith('/')) return baseUrl + path.slice(1)
  if (!baseUrl.endsWith('/') && !path.startsWith('/')) return baseUrl + '/' + path
  return baseUrl + path
}

Vue.prototype.$img = function (path, fallback = placeholderThing) {
  if (!path) return fallback
  if (isAbsoluteUrl(path)) return path
  return joinUrl(this.$BASE_URL, path)
}

Vue.directive('img-fallback', {
  bind (el, binding) {
    const fallback = binding && binding.value ? binding.value : placeholderThing
    el.addEventListener('error', () => {
      if (el.getAttribute('data-fallback-applied') === '1') return
      el.setAttribute('data-fallback-applied', '1')
      el.src = fallback
    })
  }
})
switch (process.env.NODE_ENV) {
  case 'development':
    Vue.prototype.$BASE_URL = BASE_URL
    break
  case 'production':
    Vue.prototype.$BASE_URL = BASE_URL
    break
  default:
    Vue.prototype.$BASE_URL = BASE_URL
    break
}
