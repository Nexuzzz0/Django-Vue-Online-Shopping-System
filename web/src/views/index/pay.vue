<template>
  <div>
    <Header/>
    <div class="pay-content">
      <div class="title">订单提交成功</div>
      <div class="text time-margin">
        <span>请在 </span>
        <span class="time">{{ddlTime}}</span>
        <span> 之前付款，超时订单将自动取消</span>
      </div>
      <div class="text">支付金额</div>
      <div class="price">
        <span class="num">{{ amount }}</span>
        <span>元</span>
      </div>
      <div class="pay-choose-view" style="">
        <div class="pay-choose-box flex-view">
          <div class="choose-box" :class="{ 'choose-box-active': payType === 'wx' }" @click="selectPay('wx')">
            <img src="@/assets/images/wx-pay-icon.svg">
            <span>微信支付</span>
          </div>
          <div class="choose-box" :class="{ 'choose-box-active': payType === 'ali' }" @click="selectPay('ali')">
            <img src="@/assets/images/ali-pay-icon.svg">
            <span>支付宝</span>
          </div>
        </div>
        <div class="tips">请选择任意一种支付方式</div>
        <button class="pay-btn" :class="{ 'pay-btn-active': !!payType }" @click="handlePay()">确认支付</button>
      </div>
      <div class="pay-qr-view" style="display: none;">
        <div class="loading-tip" style="">正在生成安全支付二维码</div>
        <div class="qr-box" style="display: none;">
          <div id="qrCode" class="qr">
            <img src="blob:https://www.ituring.com.cn/0928e0e9-71a0-4882-8df9-22367772364e" width="140" height="140">
          </div>
          <div class="tips">请打开微信扫一扫进行支付</div>
          <button class="pay-finish-btn">支付完成</button>
          <button class="back-pay-btn">选择其他支付方式</button>
        </div>
      </div>
    </div>
  </div>

</template>

<script>
import Header from '@/views/index/components/header'
import Footer from '@/views/index/components/footer'
import { confirmOrderApi } from '@/api/index/order'

export default {
  components: {
    Footer,
    Header
  },
  data () {
    return {
      ddlTime: undefined,
      amount: undefined,
      payType: 'wx',
      orderIds: []
    }
  },
  mounted () {
    this.amount = this.$route.query.amount

    const raw = this.$route.query.orderIds
    if (raw) {
      this.orderIds = String(raw)
        .split(',')
        .map(s => Number(String(s).trim()))
        .filter(Boolean)
    }

    const now = Date.now()
    const ddl = now + 30 * 60 * 1000
    this.ddlTime = this.formatDate(ddl, 'YY-MM-DD hh:mm:ss')

  },
  methods: {
    selectPay (type) {
      this.payType = type
    },
    loadPayMethodMap () {
      try {
        const raw = localStorage.getItem('demo_shop_pay_method_map_v1') || '{}'
        const parsed = JSON.parse(raw)
        return parsed && typeof parsed === 'object' ? parsed : {}
      } catch (e) {
        return {}
      }
    },
    savePayMethodMap (map) {
      try {
        localStorage.setItem('demo_shop_pay_method_map_v1', JSON.stringify(map || {}))
      } catch (e) {
        // ignore
      }
    },
    handlePay () {
      if (!this.payType) {
        this.$message.warn('请选择支付方式')
        return
      }
      const label = this.payType === 'ali' ? '支付宝' : '微信'

      const afterPaid = () => {
        if (this.orderIds && this.orderIds.length) {
          const map = this.loadPayMethodMap()
          this.orderIds.forEach(id => {
            map[String(id)] = this.payType
          })
          this.savePayMethodMap(map)
        }
        this.$message.success(`${label}支付成功`)
        this.$router.push({ name: 'orderView' })
      }

      if (!this.orderIds || !this.orderIds.length) {
        afterPaid()
        return
      }

      Promise.all(this.orderIds.map(id => confirmOrderApi({ id })))
        .then(() => afterPaid())
        .catch(err => {
          this.$message.error(err.msg || '支付确认失败')
        })
    },
    formatDate (time, format = 'YY-MM-DD hh:mm:ss') {
      const date = new Date(time)

      const pad2 = (n) => String(n).padStart(2, '0')
      const year = date.getFullYear()
      const month = pad2(date.getMonth() + 1)
      const day = pad2(date.getDate())
      const hour = pad2(date.getHours())
      const min = pad2(date.getMinutes())
      const sec = pad2(date.getSeconds())

      return format
        .replace(/YY/g, String(year))
        .replace(/MM/g, month)
        .replace(/DD/g, day)
        .replace(/hh/g, hour)
        .replace(/mm/g, min)
        .replace(/ss/g, sec)
    }
  }
}
</script>

<style scoped lang="less">
.flex-view {
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
}

.pay-content {
  position: relative;
  margin: 120px auto 0;
  width: 500px;
  background: #fff;
  overflow: hidden;

  .title {
    color: #152844;
    font-weight: 500;
    font-size: 24px;
    line-height: 22px;
    height: 22px;
    text-align: center;
    margin-bottom: 11px;
  }

  .time-margin {
    margin: 11px 0 24px;
  }

  .text {
    height: 22px;
    line-height: 22px;
    font-size: 14px;
    text-align: center;
    color: #152844;
  }

  .time {
    color: #f62a2a;
  }

  .text {
    height: 22px;
    line-height: 22px;
    font-size: 14px;
    text-align: center;
    color: #152844;
  }

  .price {
    color: #ff8a00;
    font-weight: 500;
    font-size: 16px;
    height: 36px;
    line-height: 36px;
    text-align: center;

    .num {
      font-size: 28px;
    }
  }

  .pay-choose-view {
    margin-top: 24px;

    .choose-box {
      width: 140px;
      height: 126px;
      border: 1px solid #cedce4;
      border-radius: 4px;
      text-align: center;
      cursor: pointer;
    }

    .pay-choose-box {
      -webkit-box-pack: justify;
      -ms-flex-pack: justify;
      justify-content: space-between;
      max-width: 300px;
      margin: 0 auto;

      img {
        height: 40px;
        margin: 24px auto 16px;
        display: block;
      }
    }

    .tips {
      color: #6f6f6f;
      font-size: 14px;
      line-height: 22px;
      height: 22px;
      text-align: center;
      margin: 16px 0 24px;
    }

    .choose-box-active {
      border: 1px solid #4684e2;
    }

    .tips {
      color: #6f6f6f;
      font-size: 14px;
      line-height: 22px;
      height: 22px;
      text-align: center;
      margin: 16px 0 24px;
    }

    .pay-btn {
      cursor: pointer;
      background: #c3c9d5;
      border-radius: 32px;
      width: 104px;
      height: 32px;
      line-height: 32px;
      border: none;
      outline: none;
      font-size: 14px;
      color: #fff;
      text-align: center;
      display: block;
      margin: 0 auto;
    }

    .pay-btn-active {
      background: #4684e2;
    }
  }
}

</style>
