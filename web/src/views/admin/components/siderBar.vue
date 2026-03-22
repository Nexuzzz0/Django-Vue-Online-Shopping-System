<template>
  <div style="width: 200px; height: 100%; padding-bottom: 48px; overflow: scroll;">
    <a-menu
      :selected-keys="[$route.path]"
      :open-keys="openKeys"
      @click="handleMenuClick"
      @openChange="onOpenChange"
      theme="light"
      mode="inline"
    >
      <template v-for="item in menuData">
        <a-menu-item v-if="!item.children" :key="item.key">
          <a-icon type="appstore" />
          <span>{{ item.title }}</span>
        </a-menu-item>

        <a-sub-menu v-else :key="item.key">
          <span slot="title">
            <a-icon type="folder" />
            <span>{{ item.title }}</span>
          </span>
          <a-menu-item v-for="child in item.children" :key="child.key">
            <a-icon type="appstore" />
            <span>{{ child.title }}</span>
          </a-menu-item>
        </a-sub-menu>
      </template>
    </a-menu>
  </div>
</template>

<script>
export default {
  name: 'SiderBar',
  data () {
    return {
      openKeys: [],
      menuData: [
        {
          key: '/admin/overview',
          title: '总览'
        },
        {
          key: '/admin/order',
          title: '订单管理'
        },
        {
          key: '/admin/thing',
          title: '商品管理'
        },
        {
          key: '/admin/classification',
          title: '分类管理'
        },
        {
          key: '/admin/tag',
          title: '标签管理'
        },
        {
          key: '/admin/comment',
          title: '评论管理'
        },
        {
          key: '/admin/user',
          title: '用户管理'
        },
        {
          key: 'operation',
          title: '运营管理',
          children: [
            {
              key: '/admin/banner',
              title: '横幅管理'
            },
            {
              key: '/admin/ad',
              title: '广告管理'
            },
            {
              key: '/admin/notice',
              title: '通知公告'
            }
          ]
        },
        {
          key: 'logs',
          title: '日志管理',
          children: [
            {
              key: '/admin/loginLog',
              title: '登录日志'
            },
            {
              key: '/admin/opLog',
              title: '操作日志'
            },
            {
              key: '/admin/errorLog',
              title: '异常日志'
            }
          ]
        },
        {
          key: '/admin/sysInfo',
          title: '系统信息'
        }
      ]
    }
  },
  methods: {
    onOpenChange (keys) {
      this.openKeys = keys
    },
    handleMenuClick ({ item, key, keyPath }) {
      if (key !== this.$route.path) {
        this.$router.push(key)
      }
    }
  }
}
</script>

<style scoped lang="less">
@scroll-bar-size: 6px;

// 定义滚动条高宽及背景 高宽分别对应横竖滚动条的尺寸
::-webkit-scrollbar {
  width: @scroll-bar-size;
  height: @scroll-bar-size;
  background-color: transparent;
}

// 定义滚动条轨道 内阴影+圆角
::-webkit-scrollbar-track {
  border-radius:@scroll-bar-size / 2;
  background-color: transparent;
}

// 定义滑块 内阴影+圆角
::-webkit-scrollbar-thumb {
  border-radius: @scroll-bar-size / 2;
  background-color: rgba(0, 0, 0, .3)
}

</style>
