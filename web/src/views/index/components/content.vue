<template>
  <div class="content">
    <div class="content-left">
      <div class="left-search-item">
        <h4>商品分类</h4>
        <a-tree :tree-data="cData" :selected-keys="selectedKeys" @select="onSelect" style="min-height: 220px;">
        </a-tree>
      </div>
      <div class="left-search-item"><h4>热门标签</h4>
        <div class="tag-view tag-flex-view">
            <span class="tag" :class="{'tag-select': selectTagId===item.id}" v-for="item in tagData" :key="item.id"
                  @click="clickTag(item.id)">{{ item.title }}</span>
        </div>
      </div>
    </div>
    <div class="content-right">
      <div class="hero" v-if="bannerData.length || adData.length">
        <div class="hero-left" v-if="bannerData.length">
          <a-carousel autoplay :dots="false">
            <div
              v-for="banner in bannerData"
              :key="banner.id"
              class="banner-slide"
              @click="handleBannerClick(banner)"
            >
              <img :src="banner.image" class="banner-img" alt="banner" v-img-fallback>
            </div>
          </a-carousel>
        </div>
        <div class="hero-right" v-if="adData.length">
          <div
            class="ad-card"
            v-for="ad in adData"
            :key="ad.id"
            @click="handleAdClick(ad)"
          >
            <img :src="ad.image" class="ad-img" alt="ad" v-img-fallback>
          </div>
        </div>
      </div>
      <div class="top-select-view flex-view">
        <div class="order-view">
          <span class="title"></span>
          <span class="tab"
                :class="selectTabIndex===index? 'tab-select':''"
                v-for="(item,index) in tabData"
                :key="index"
                @click="selectTab(index)">
            {{ item }}
          </span>
          <span :style="{left: tabUnderLeft + 'px'}" class="tab-underline"></span>
        </div>
      </div>
      <a-spin :spinning="loading" style="min-height: 200px;">
        <div class="pc-thing-list flex-view">
          <div v-for="item in pageData" :key="item.id" @click="handleDetail(item)" class="thing-item item-column-3"><!---->
            <div class="img-view">
              <img :src="item.cover" class="thing-cover" alt="cover" v-img-fallback></div>
            <div class="info-view">
              <h3 class="thing-name">{{ item.title.substring(0, 12)}}</h3>
              <span>
                <span class="a-price-symbol">¥</span>
                <span class="a-price">{{item.price}}</span>
              </span>
            </div>
          </div>
          <div v-if="pageData.length <= 0 && !loading" class="no-data" style="">暂无数据</div>
        </div>
      </a-spin>
      <div class="page-view" style="">
        <a-pagination v-model="page" size="small" @change="changePage" :hideOnSinglePage="true"
                      :defaultPageSize="pageSize" :total="total"/>
      </div>

    </div>

  </div>
</template>

<script>
import {listApi as listClassificationList} from '@/api/index/classification'
import {listApi as listTagList} from '@/api/index/tag'
import {listApi as listThingList} from '@/api/index/thing'
import {listApi as listBannerList} from '@/api/index/banner'
import {listApi as listAdList} from '@/api/index/ad'

export default {
  name: 'Content',
  data () {
    return {
      selectX: 0,
      selectTagId: -1,
      cData: [],
      selectedKeys: [],
      tagData: [],
      loading: false,

      tabData: ['最新', '最热', '推荐'],
      selectTabIndex: 0,
      tabUnderLeft: 12,

      bannerData: [],
      adData: [],

      thingData: [],
      pageData: [],

      page: 1,
      total: 0,
      pageSize: 12,
    }
  },
  mounted () {
    this.initSider()
    this.initHero()
    this.getThingList({})
  },
  methods: {
    initHero () {
      listBannerList().then(res => {
        const raw = Array.isArray(res.data) ? res.data : []
        this.bannerData = raw
          .filter(item => item && item.image)
          .slice(0, 5)
          .map(item => ({
            ...item,
            image: this.$img(item.image)
          }))
      }).catch(() => {
        this.bannerData = []
      })

      listAdList().then(res => {
        const raw = Array.isArray(res.data) ? res.data : []
        this.adData = raw
          .filter(item => item && item.image)
          .slice(0, 2)
          .map(item => ({
            ...item,
            image: this.$img(item.image)
          }))
      }).catch(() => {
        this.adData = []
      })
    },
    handleBannerClick (banner) {
      if (banner && banner.thing) {
        this.handleDetail({ id: banner.thing })
      }
    },
    handleAdClick (ad) {
      if (ad && ad.link) {
        window.open(ad.link, '_blank')
      }
    },
    initSider () {
      listClassificationList().then(res => {
        this.cData = res.data
      })
      listTagList().then(res => {
        this.tagData = res.data
      })
    },
    getSelectedKey () {
      if (this.selectedKeys.length > 0) {
        return this.selectedKeys[0]
      } else {
        return -1
      }
    },
    onSelect (selectedKeys) {
      this.selectedKeys = selectedKeys
      console.log(this.selectedKeys[0])
      if (this.selectedKeys.length > 0) {
        this.getThingList({c: this.getSelectedKey()})
      }
      this.selectTagId = -1
    },
    clickTag (index) {
      this.selectedKeys = []
      this.selectTagId = index
      this.getThingList({tag: this.selectTagId})
    },
    search () {
      const keyword = this.$refs.keyword.value
      console.log(keyword)
      this.getThingList({'keyword': keyword})
    },
    // clearSearch () {
    //   this.$refs.keyword.value = ''
    //   this.search()
    // },
    // 最新|最热|推荐
    selectTab (index) {
      this.selectTabIndex = index
      this.tabUnderLeft = 12 + 53 * index
      console.log(this.selectTabIndex)
      let sort = (index === 0 ? 'recent' : index === 1 ? 'hot' : 'recommend')
      const data = {sort: sort}
      if (this.selectTagId !== -1) {
        data['tag'] = this.selectTagId
      } else {
        data['c'] = this.getSelectedKey()
      }
      this.getThingList(data)
    },
    handleDetail (item) {
      // 跳转新页面
      let text = this.$router.resolve({name: 'detail', query: {id: item.id}})
      window.open(text.href, '_blank')
    },
    // 分页事件
    changePage (page) {
      this.page = page
      let start = (this.page - 1) * this.pageSize
      this.pageData = this.thingData.slice(start, start + this.pageSize)
      console.log('第' + this.page + '页')
    },
    getThingList (data) {
      this.loading = true
      listThingList(data).then(res => {
        this.loading = false
        res.data.forEach((item, index) => {
          item.cover = this.$img(item.cover)
        })
        console.log(res)
        this.thingData = res.data
        this.total = this.thingData.length
        this.changePage(1)
      }).catch(err => {
        console.log(err)
        this.loading = false
      })
    }
  }
}

</script>

<style scoped lang="less">
.content {
  display: flex;
  flex-direction: row;
  max-width: 1100px;
  width: calc(100% - 32px);
  margin: 72px auto 40px;
  gap: 32px;
}

.content-left {
  width: 220px;
  flex: 0 0 220px;
}

.left-search-item {
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(17, 24, 39, 0.06);
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
  margin-top: 16px;
  padding: 16px;
}

h4 {
  color: #4d4d4d;
  font-weight: 600;
  font-size: 16px;
  line-height: 24px;
  height: 24px;
  margin: 0 0 8px;
}

.category-item {
  cursor: pointer;
  color: #333;
  margin: 12px 0 0;
  padding-left: 16px;
}

ul {
  margin: 0;
  padding: 0;
}

ul {
  list-style-type: none;
}

li {
  margin: 4px 0 0;
  display: list-item;
  text-align: -webkit-match-parent;
}

.child {
  color: #333;
  padding-left: 16px;
}

.child:hover {
  color: #4684e2;
}

.select {
  color: #4684e2;
}

.flex-view {
  -webkit-box-pack: justify;
  -ms-flex-pack: justify;
  //justify-content: space-between;
  display: flex;
}

.name {
  font-size: 14px;
}

.name:hover {
  color: #4684e2;
}

.count {
  font-size: 14px;
  color: #999;
}

.check-item {
  font-size: 0;
  height: 18px;
  line-height: 12px;
  margin: 12px 0 0;
  color: #333;
  cursor: pointer;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;
}

.check-item input {
  cursor: pointer;
}

.check-item label {
  font-size: 14px;
  margin-left: 12px;
  cursor: pointer;
  -webkit-box-flex: 1;
  -ms-flex: 1;
  flex: 1;
}

.tag-view {
  -ms-flex-wrap: wrap;
  flex-wrap: wrap;
  margin-top: 4px;
}

.tag-flex-view {
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
}

.tag {
  background: #fff;
  border: 1px solid #a1adc6;
  -webkit-box-sizing: border-box;
  box-sizing: border-box;
  border-radius: 16px;
  height: 20px;
  line-height: 18px;
  padding: 0 8px;
  margin: 8px 8px 0 0;
  cursor: pointer;
  font-size: 12px;
  color: #152833;
}

.tag:hover {
  background: #4684e3;
  color: #fff;
  border: 1px solid #4684e3;
}

.tag-select {
  background: #4684e3;
  color: #fff;
  border: 1px solid #4684e3;
}

.content-right {
  -webkit-box-flex: 1;
  -ms-flex: 1;
  flex: 1;
  min-width: 0;
  padding-top: 12px;

  .pc-search-view {
    margin: 0 0 24px;
    -webkit-box-align: center;
    -ms-flex-align: center;
    align-items: center;

    .search-icon {
      width: 20px;
      height: 20px;
      -webkit-box-flex: 0;
      -ms-flex: 0 0 20px;
      flex: 0 0 20px;
      margin-right: 16px;
    }

    input {
      outline: none;
      border: 0px;
      -webkit-box-flex: 1;
      -ms-flex: 1;
      flex: 1;
      border-bottom: 1px solid #cedce4;
      color: #152844;
      font-size: 14px;
      height: 22px;
      line-height: 22px;
      -ms-flex-item-align: end;
      align-self: flex-end;
      padding-bottom: 8px;
    }

    .clear-search-icon {
      position: relative;
      left: -20px;
      cursor: pointer;
    }

    button {
      outline: none;
      border: none;
      font-size: 14px;
      color: #fff;
      background: #288dda;
      border-radius: 32px;
      width: 88px;
      height: 32px;
      line-height: 32px;
      margin-left: 2px;
      cursor: pointer;
    }

    .float-count {
      color: #999;
      margin-left: 24px;
    }
  }

  .flex-view {
    display: flex;
  }

  .top-select-view {
    -webkit-box-pack: justify;
    -ms-flex-pack: justify;
    justify-content: space-between;
    -webkit-box-align: center;
    -ms-flex-align: center;
    align-items: center;
    height: 40px;
    line-height: 40px;

    .type-view {
      position: relative;
      font-weight: 400;
      font-size: 18px;
      color: #5f77a6;

      .type-tab {
        margin-right: 32px;
        cursor: pointer;
      }

      .type-tab-select {
        color: #152844;
        font-weight: 600;
        font-size: 20px;
      }

      .tab-underline {
        position: absolute;
        bottom: 0;
        //left: 22px;
        width: 16px;
        height: 4px;
        background: #4684e2;
        -webkit-transition: left .3s;
        transition: left .3s;
      }
    }

    .order-view {
      position: relative;
      color: #6c6c6c;
      font-size: 14px;

      .title {
        margin-right: 8px;
      }

      .tab {
        color: #999;
        margin-right: 20px;
        cursor: pointer;
      }

      .tab-select {
        color: #152844;
      }

      .tab-underline {
        position: absolute;
        bottom: 0;
        left: 84px;
        width: 16px;
        height: 4px;
        background: #4684e2;
        -webkit-transition: left .3s;
        transition: left .3s;
      }
    }

  }

  .hero {
    display: flex;
    gap: 16px;
    margin: 12px 0 18px;
  }

  .hero-left {
    flex: 1;
    min-width: 0;
    height: 180px;
    background: #fff;
    border: 1px solid rgba(17, 24, 39, 0.06);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
  }

  .hero-left /deep/ .slick-slider,
  .hero-left /deep/ .slick-list,
  .hero-left /deep/ .slick-track,
  .hero-left /deep/ .slick-slide,
  .hero-left /deep/ .slick-slide > div {
    height: 180px;
  }

  .banner-slide {
    height: 180px;
    cursor: pointer;
  }

  .banner-img {
    width: 100%;
    height: 180px;
    display: block;
    object-fit: cover;
    background: #f2f4f7;
  }

  .hero-right {
    width: 240px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .ad-card {
    background: #fff;
    border: 1px solid rgba(17, 24, 39, 0.06);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
    cursor: pointer;
  }

  .ad-img {
    width: 100%;
    height: 86px;
    display: block;
    object-fit: cover;
    background: #f2f4f7;
  }

  .pc-thing-list {
    -ms-flex-wrap: wrap;
    flex-wrap: wrap;
    gap: 20px;
    justify-content: flex-start;

    .thing-item {
      width: 255px;
      position: relative;
      flex: 0 0 255px;
      height: fit-content;
      overflow: hidden;
      margin-top: 26px;
      margin-bottom: 36px;
      cursor: pointer;
      background: #fff;
      border: 1px solid rgba(17, 24, 39, 0.06);
      border-radius: 12px;
      box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
      transition: transform 0.15s ease, box-shadow 0.15s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 26px rgba(17, 24, 39, 0.10);
      }

      .img-view {
        //text-align: center;
        height: 180px;
        width: 255px;
        overflow: hidden;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;

        .thing-cover {
          width: 100%;
          height: 100%;
          display: block;
          object-fit: cover;
          background: #f2f4f7;
        }
      }

      .info-view {
        //background: #f6f9fb;
        overflow: hidden;
        padding: 12px 16px 16px;
        .thing-name {
          line-height: 32px;
          margin-top: 0;
          color: #0F1111!important;
          font-size: 15px!important;
          font-weight: 400!important;
          font-style: normal!important;
          text-transform: none!important;
          text-decoration: none!important;
        }

        .price {
          color: #ff7b31;
          font-size: 20px;
          line-height: 20px;
          margin-top: 4px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .translators {
          color: #6f6f6f;
          font-size: 12px;
          line-height: 14px;
          margin-top: 4px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    .no-data {
      height: 200px;
      line-height: 200px;
      text-align: center;
      width: 100%;
      font-size: 16px;
      color: #152844;
    }
  }

  .page-view {
    width: 100%;
    text-align: center;
    margin-top: 48px;
  }
}

@media (max-width: 980px) {
  .content {
    flex-direction: column;
    gap: 16px;
    margin-top: 72px;
  }

  .content-left {
    width: 100%;
    flex: none;
  }

  .content-right {
    padding-top: 0;

    .hero {
      flex-direction: column;
    }

    .hero-right {
      width: 100%;
      flex-direction: row;
    }

    .ad-card {
      flex: 1;
    }
  }
}

@media (max-width: 560px) {
  .content-right {
    .hero-right {
      flex-direction: column;
    }
  }
}

.a-price-symbol {
  top: -0.5em;
  font-size: 12px;
}
.a-price {
  color: #0F1111;
  font-size:21px;
}

</style>
