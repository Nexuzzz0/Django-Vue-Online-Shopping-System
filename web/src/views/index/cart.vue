<template>
  <div>
    <Header/>
    <section class="cart-page flex-view">
      <div class="left-flex">
        <div class="title flex-view">
          <h3>购物车</h3>
          <span class="click-txt" v-if="items.length" @click="handleClear">清空</span>
        </div>

        <div class="cart-list-view">
          <div class="list-th flex-view">
            <span class="line-1">商品名称</span>
            <span class="line-2">价格</span>
            <span class="line-5">数量</span>
            <span class="line-6">操作</span>
          </div>
          <div class="list" v-if="items.length">
            <div class="items flex-view" v-for="it in items" :key="it.id">
              <div class="book flex-view" @click="handleDetail(it)">
                <img :src="it.cover" alt="cover" v-img-fallback>
                <a-tooltip :title="it.title" placement="topLeft">
                  <h2>{{ it.title }}</h2>
                </a-tooltip>
              </div>
              <div class="pay">¥{{ it.price }}</div>
              <a-input-number :value="it.count" :min="1" :max="99" @change="v => onCountChange(it, v)" />
              <img src="@/assets/images/delete-icon.svg" class="delete" @click="handleRemove(it)">
            </div>
          </div>
          <div class="no-data" v-else>购物车为空，去逛逛吧</div>
        </div>
      </div>

      <div class="right-flex">
        <div class="title flex-view">
          <h3>结算</h3>
          <span class="click-txt">合计</span>
        </div>
        <div class="price-view">
          <div class="price-item flex-view">
            <div class="item-name">商品数量</div>
            <div class="price-txt">{{ totalCount }}</div>
          </div>
          <div class="price-item flex-view">
            <div class="item-name">商品总价</div>
            <div class="price-txt">¥{{ amount }}</div>
          </div>
          <div class="total-price-view flex-view">
            <span>合计</span>
            <div class="price">
              <span class="font-big">¥{{ amount }}</span>
            </div>
          </div>
          <div class="btns-view">
            <button class="btn buy" @click="handleBack">继续逛</button>
            <button class="btn pay jiesuan" :disabled="!items.length" @click="handleCheckout">去结算</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import Header from '@/views/index/components/header'
import { getItems, updateCount, removeItem, clearCart, getTotalAmount, getCount } from '@/utils/cart'

export default {
  name: 'Cart',
  components: { Header },
  data () {
    return {
      items: []
    }
  },
  computed: {
    amount () {
      return getTotalAmount()
    },
    totalCount () {
      return getCount()
    }
  },
  mounted () {
    this.reload()
    window.addEventListener('cart:updated', this.reload)
  },
  beforeDestroy () {
    window.removeEventListener('cart:updated', this.reload)
  },
  methods: {
    reload () {
      this.items = getItems().map(it => ({
        ...it,
        cover: this.$img(it.cover)
      }))
    },
    onCountChange (it, value) {
      updateCount(it.id, value)
      this.reload()
    },
    handleRemove (it) {
      removeItem(it.id)
      this.$message.success('已移除')
      this.reload()
    },
    handleClear () {
      clearCart()
      this.$message.success('已清空')
      this.reload()
    },
    handleCheckout () {
      const userId = this.$store.state.user.userId
      if (!userId) {
        this.$message.warn('请先登录！')
        this.$router.push({ name: 'login' })
        return
      }
      this.$router.push({ name: 'confirm', query: { fromCart: '1' } })
    },
    handleBack () {
      this.$router.push({ name: 'portal' })
    },
    handleDetail (it) {
      const text = this.$router.resolve({ name: 'detail', query: { id: it.id } })
      window.open(text.href, '_blank')
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

.cart-page {
  width: 1024px;
  min-height: 50vh;
  margin: 100px auto;
}

.left-flex {
  -webkit-box-flex: 17;
  -ms-flex: 17;
  flex: 17;
  padding-right: 20px;
}

.right-flex {
  -webkit-box-flex: 8;
  -ms-flex: 8;
  flex: 8;
}

.title {
  -webkit-box-pack: justify;
  -ms-flex-pack: justify;
  justify-content: space-between;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;

  h3 {
    font-size: 18px;
    font-weight: 600;
    margin: 0;
  }

  .click-txt {
    color: #4684e2;
    cursor: pointer;
  }
}

.cart-list-view {
  margin-top: 12px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;

  .list-th {
    background: #f6f9fb;
    padding: 12px 16px;
    color: #6f6f6f;
  }

  .line-1 { flex: 1; }
  .line-2 { width: 90px; text-align: left; }
  .line-5 { width: 120px; text-align: left; }
  .line-6 { width: 60px; text-align: center; }

  .items {
    padding: 16px;
    border-top: 1px solid #f0f0f0;
    align-items: center;
  }

  .book {
    flex: 1;
    align-items: center;
    gap: 12px;
    cursor: pointer;

    img {
      width: 56px;
      height: 56px;
      border-radius: 8px;
      object-fit: cover;
      background: #f2f4f7;
    }

    h2 {
      font-size: 14px;
      margin: 0;
      max-width: 520px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .pay {
    width: 90px;
    color: #152844;
  }

  .delete {
    width: 18px;
    height: 18px;
    cursor: pointer;
    opacity: 0.8;
  }

  .no-data {
    padding: 40px 16px;
    text-align: center;
    color: #6f6f6f;
  }
}

.price-view {
  margin-top: 12px;
  background: #fff;
  border-radius: 8px;
  padding: 16px;

  .price-item {
    justify-content: space-between;
    padding: 8px 0;
    color: #152844;
  }

  .total-price-view {
    justify-content: space-between;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;

    .font-big {
      font-size: 20px;
      color: #ff8a00;
      font-weight: 600;
    }
  }

  .btns-view {
    margin-top: 16px;
    display: flex;
    justify-content: space-between;
    gap: 12px;

    .btn {
      flex: 1;
      height: 36px;
      border-radius: 18px;
      border: none;
      cursor: pointer;
    }

    .buy {
      background: #eef2ff;
      color: #3730a3;
    }

    .pay {
      background: #4684e2;
      color: #fff;
    }

    .jiesuan:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

@media (max-width: 1100px) {
  .cart-page {
    width: calc(100% - 24px);
    flex-direction: column;
    gap: 16px;
  }
  .left-flex { padding-right: 0; }
}
</style>
