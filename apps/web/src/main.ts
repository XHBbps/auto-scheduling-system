import { createApp } from 'vue'
import {
  ElAside,
  ElBreadcrumb,
  ElBreadcrumbItem,
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
  ElCol,
  ElContainer,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDivider,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElHeader,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElPagination,
  ElPopconfirm,
  ElPopover,
  ElRow,
  ElSelect,
  ElSubMenu,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTooltip,
  ElLoadingDirective,
  provideGlobalConfig,
} from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/es/components/aside/style/css'
import 'element-plus/es/components/breadcrumb/style/css'
import 'element-plus/es/components/breadcrumb-item/style/css'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/checkbox/style/css'
import 'element-plus/es/components/checkbox-group/style/css'
import 'element-plus/es/components/col/style/css'
import 'element-plus/es/components/container/style/css'
import 'element-plus/es/components/date-picker/style/css'
import 'element-plus/es/components/descriptions/style/css'
import 'element-plus/es/components/descriptions-item/style/css'
import 'element-plus/es/components/dialog/style/css'
import 'element-plus/es/components/divider/style/css'
import 'element-plus/es/components/drawer/style/css'
import 'element-plus/es/components/form/style/css'
import 'element-plus/es/components/form-item/style/css'
import 'element-plus/es/components/header/style/css'
import 'element-plus/es/components/icon/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/input-number/style/css'
import 'element-plus/es/components/loading/style/css'
import 'element-plus/es/components/main/style/css'
import 'element-plus/es/components/menu/style/css'
import 'element-plus/es/components/menu-item/style/css'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/option/style/css'
import 'element-plus/es/components/pagination/style/css'
import 'element-plus/es/components/popconfirm/style/css'
import 'element-plus/es/components/popover/style/css'
import 'element-plus/es/components/row/style/css'
import 'element-plus/es/components/select/style/css'
import 'element-plus/es/components/sub-menu/style/css'
import 'element-plus/es/components/switch/style/css'
import 'element-plus/es/components/table/style/css'
import 'element-plus/es/components/table-column/style/css'
import 'element-plus/es/components/tab-pane/style/css'
import 'element-plus/es/components/tabs/style/css'
import 'element-plus/es/components/tag/style/css'
import 'element-plus/es/components/tooltip/style/css'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

;[
  ElAside,
  ElBreadcrumb,
  ElBreadcrumbItem,
  ElButton,
  ElCheckbox,
  ElCheckboxGroup,
  ElCol,
  ElContainer,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDivider,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElHeader,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElPagination,
  ElPopconfirm,
  ElPopover,
  ElRow,
  ElSelect,
  ElSubMenu,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
  ElTooltip,
].forEach((component) => {
  if (component.name) {
    app.component(component.name, component)
  }
})

app.directive('loading', ElLoadingDirective)
provideGlobalConfig({ locale: zhCn }, app, true)
app.use(router)

app.mount('#app')
