<template>
  <div class="page-view">
    <div class="table-operation">
      <a-space>
<!--        <a-button type="primary" @click="handleMockAdd">模拟新增</a-button>-->
        <a-button @click="handleBatchDelete">批量删除</a-button>
      </a-space>
    </div>
    <div class="table-wrap" ref="tableWrap">
      <a-table
        size="middle"
        rowKey="id"
        :loading="loading"
        :columns="columns"
        :data-source="data"
        :scroll="{ x: 'max-content' }"
        :row-selection="rowSelection()"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <span slot="status" slot-scope="text">
          <a-tag :color="text === '1' ? '#2db7f5' : text === '7' ? '#bfbfbf' : text === '4' ? '#87d068' : text === '6' ? '#b37feb' : text === '5' ? '#ff7875' : '#faad14'">
            {{ text === '1'
              ? '待支付'
              : text === '2'
                ? '待发货'
                : text === '3'
                  ? '待收货'
                  : text === '4'
                    ? '已完成'
                    : text === '5'
                      ? '退款中'
                      : text === '6'
                        ? '已退款'
                    : '已取消' }}
          </a-tag>
        </span>
        <span slot="operation" class="operation" slot-scope="text, record">
          <a-space :size="16">
            <a v-if="record.status === '2'" @click="handleShip(record)">发货</a>
            <a v-if="record.status === '5'" @click="handleRefundApprove(record)">同意退款</a>
            <a v-if="record.status === '5'" @click="handleRefundReject(record)">拒绝退款</a>
            <a @click="handleCancel(record)">取消</a>
            <a @click="handleDelete(record)">删除</a>
          </a-space>
        </span>
      </a-table>
    </div>
  </div>
</template>

<script>
import {
  listApi,
  createApi,
  updateApi,
  cancelOrderApi,
  delayApi,
  deleteApi,
  shipApi,
  refundApproveApi,
  refundRejectApi
} from '@/api/admin/order'

const columns = [
  {
    title: '序号',
    dataIndex: 'index',
    key: 'index',
    align: 'center'
  },
  {
    title: '用户',
    dataIndex: 'username',
    key: 'username',
    align: 'center'
  },
  {
    title: '商品',
    dataIndex: 'title',
    key: 'title',
    align: 'center',
    customRender: (text) => text ? text.substring(0, 10) + '...' : '--'
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    align: 'center',
    scopedSlots: {customRender: 'status'}
  },
  {
    title: '订单时间',
    dataIndex: 'order_time',
    key: 'order_time',
    align: 'center'
  },
  {
    title: '操作',
    dataIndex: 'action',
    align: 'center',
    fixed: 'right',
    width: 140,
    scopedSlots: {customRender: 'operation'}
  }
]

export default {
  name: 'Order',
  data () {
    return {
      loading: false,
      selectedRowKeys: [],
      columns,
      data: [],
      pageSize: 10,
      page: 1,
      total: 0,
      pagination: {
        size: 'default',
        current: 1,
        pageSize: 10,
        total: 0,
        pageSizeOptions: ['10', '20', '30', '40'],
        showSizeChanger: true,
        showTotal: (total) => `共${total}条数据`
      }
    }
  },
  methods: {
    handleTableChange (pagination) {
      const nextPage = pagination && pagination.current ? pagination.current : 1
      const nextSize = pagination && pagination.pageSize ? pagination.pageSize : 10
      this.page = nextPage
      this.pageSize = nextSize
      this.pagination.current = nextPage
      this.pagination.pageSize = nextSize
      this.getList()
    },
    getList () {
      this.loading = true
      listApi({
        page: this.page,
        pageSize: this.pageSize
      }).then(res => {
        this.loading = false
        const payload = res.data
        const list = Array.isArray(payload) ? payload : (payload && payload.list ? payload.list : [])
        const total = Array.isArray(payload) ? list.length : (payload && payload.total ? payload.total : 0)
        this.total = total
        this.pagination.total = total
        this.pagination.current = this.page
        this.pagination.pageSize = this.pageSize

        list.forEach((item, index) => {
          item.index = (this.page - 1) * this.pageSize + index + 1
        })
        this.data = list
      })
    },
    rowSelection () {
      return {
        onChange: (selectedRowKeys, selectedRows) => {
          this.selectedRowKeys = selectedRowKeys
        }
      }
    },
    handleMockAdd () {
      createApi({
        thing: 1,
        user: 2,
        count: 1
      }).then(res => {
        this.getList()
      }).catch(err => {

      })
    },
    // 发货
    handleShip (record) {
      const that = this
      this.$confirm({
        title: '确定发货？',
        onOk () {
          shipApi({ id: record.id }).then(() => {
            that.$message.success('发货成功')
            that.getList()
          }).catch(err => {
            that.$message.error(err.msg || '发货失败')
          })
        }
      })
    },
    // 同意退款
    handleRefundApprove (record) {
      const that = this
      this.$confirm({
        title: '确定同意退款？',
        onOk () {
          refundApproveApi({ id: record.id }).then(() => {
            that.$message.success('退款成功')
            that.getList()
          }).catch(err => {
            that.$message.error(err.msg || '退款失败')
          })
        }
      })
    },
    // 拒绝退款
    handleRefundReject (record) {
      const that = this
      this.$confirm({
        title: '确定拒绝退款？',
        onOk () {
          refundRejectApi({ id: record.id }).then(() => {
            that.$message.success('已拒绝退款')
            that.getList()
          }).catch(err => {
            that.$message.error(err.msg || '操作失败')
          })
        }
      })
    },
    // 取消
    handleCancel (record) {
      const that = this
      this.$confirm({
        title: '确定取消?',
        onOk () {
          cancelOrderApi({
            id: record.id
          }).then(res => {
            that.$message.success('取消成功')
            that.getList()
          }).catch(err => {
            that.$message.error(err.msg || '取消失败')
          })
        }
      })
    },
    // 删除
    handleDelete (record) {
      const that = this
      this.$confirm({
        title: '确定删除?',
        onOk () {
          deleteApi({
            ids: record.id
          }).then(res => {
            that.$message.success('删除成功')
            that.getList()
          }).catch(err => {
            that.$message.error(err.msg || '删除失败')
          })
        }
      })
    },
    // 批量删除
    handleBatchDelete () {
      console.log(this.selectedRowKeys)
      if (this.selectedRowKeys.length <= 0) {
        this.$message.warn('请勾选删除项')
        return
      }
      const that = this
      this.$confirm({
        title: '确定删除?',
        onOk () {
          deleteApi({
            ids: that.selectedRowKeys.join(',')
          }).then(res => {
            that.$message.success('删除成功')
            that.selectedRowKeys = []
            that.getList()
          }).catch(err => {
            that.$message.error(err.msg || '删除失败')
          })
        }
      })
    }
  },
  mounted () {
    this.getList()
  }
}
</script>

<style lang="less" scoped>
.table-wrap {
  flex: 1;
}

.page-view {
  min-height: 100%;
  background: #FFF;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.table-operation {
  height: 50px;
  text-align: right;
}
</style>
