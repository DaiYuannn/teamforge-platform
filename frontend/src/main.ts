import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './styles/index.scss'
// 注册全局权限指令
import { permissionDirective } from './directives/permission'
import { applyThemePreference } from './utils/theme'
import { i18n } from './i18n'

// Apply the signed-out/system default before Vue mounts to avoid a light-theme flash.
applyThemePreference()

// 创建 Vue 应用实例
const app = createApp(App)

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册全局指令
app.directive('permission', permissionDirective)

// 注册 Pinia 状态管理
app.use(createPinia())

// 注册 Vue Router
app.use(router)

// 注册 Element Plus UI 库
app.use(ElementPlus)
app.use(i18n)

// 挂载应用
app.mount('#app')
