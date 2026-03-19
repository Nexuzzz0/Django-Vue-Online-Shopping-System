const path = require('path')
const webpack = require('webpack')
const buildDate = JSON.stringify(new Date().toLocaleString())

function resolve (dir) {
  return path.join(__dirname, dir)
}

const isProd = process.env.NODE_ENV === 'production'

const assetsCDN = {
}

// vue.config.js
const vueConfig = {
  runtimeCompiler: true,
  publicPath: './',
  configureWebpack: {
    // webpack plugins
    plugins: [
    ],
    // if prod, add externals
    externals: isProd ? assetsCDN.externals : {}
  },

  chainWebpack: config => {
    config.resolve.alias.set('@$', resolve('src'))
  },


  css: {
    loaderOptions: {
      less: {
        lessOptions: {
          modifyVars: {
            // less vars，customize ant design theme
            'primary-color': '#4684E2',
            'link-color': '#4684E2',
            'border-radius-base': '8px',
            'border-radius-sm': '6px',
            'layout-body-background': '#f5f7fa',
            'layout-header-background': '#ffffff',
          },
          // DO NOT REMOVE THIS LINE
          javascriptEnabled: true
        }
      }
    }
  },

  // disable source map in production
  productionSourceMap: false,
  lintOnSave: undefined,
  // babel-loader no-ignore node_modules/*
  transpileDependencies: []
}

module.exports = vueConfig
