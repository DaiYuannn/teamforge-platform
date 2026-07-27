<template>
  <div class="page-container">
    <PageHeader title="个人设置" subtitle="管理你的账户个性化配置">
      <template #actions>
        <el-button type="primary" :icon="Check" :loading="saving" @click="handleSave">保存设置</el-button>
      </template>
    </PageHeader>

    <div v-loading="loading" class="preference-content">
      <section class="surface-panel settings-panel">
        <div class="settings-grid">
        <section class="settings-section appearance-section">
          <div class="card-header">
            <el-icon><Brush /></el-icon>
            <span>外观设置</span>
          </div>

        <el-form :label-width="formLabelWidth" :label-position="formLabelPosition">
          <!-- 主题色选择 -->
          <el-form-item label="主题色">
            <div class="theme-colors">
              <button
                v-for="item in themeColorOptions"
                :key="item.value"
                type="button"
                class="theme-color-card"
                :class="{ active: normalizedFormColor === item.value }"
                :aria-pressed="normalizedFormColor === item.value"
                @click="selectPrimaryColor(item.value)"
              >
                <span class="color-block" :style="{ backgroundColor: item.value }" />
                <span class="color-label">{{ item.label }}</span>
                <el-icon v-if="normalizedFormColor === item.value" class="check-icon"><Check /></el-icon>
              </button>
            </div>
            <div class="custom-color-row">
              <el-color-picker
                v-model="form.primary_color"
                color-format="hex"
                :predefine="predefinedColors"
                aria-label="选择自定义主色"
                @change="previewPrimaryColor"
              />
              <el-input
                v-model="form.primary_color"
                class="color-input"
                maxlength="7"
                placeholder="#176b73"
                aria-label="主色十六进制值"
                @change="previewPrimaryColor"
              />
              <span class="form-tip">支持任意六位十六进制颜色，保存后随当前账户同步。</span>
            </div>
          </el-form-item>

          <el-form-item label="明暗模式">
            <el-radio-group
              v-model="form.theme_mode"
              class="theme-mode-group"
              aria-label="明暗模式"
              @change="previewThemePreference"
            >
              <el-radio-button
                v-for="item in themeModeOptions"
                :key="item.value"
                :value="item.value"
              >
                {{ item.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="form.theme_mode === 'schedule'" label="深色时段">
            <div class="theme-schedule-row">
              <el-time-select
                v-model="form.schedule_start"
                start="00:00"
                step="00:30"
                end="23:30"
                placeholder="开始时间"
                aria-label="深色模式开始时间"
                @change="previewThemePreference"
              />
              <span>至</span>
              <el-time-select
                v-model="form.schedule_end"
                start="00:00"
                step="00:30"
                end="23:30"
                placeholder="结束时间"
                aria-label="深色模式结束时间"
                @change="previewThemePreference"
              />
            </div>
          </el-form-item>
          <el-form-item label="语言">
            <el-segmented
              v-model="form.language"
              :options="languageOptions"
              @change="setLocale"
            />
          </el-form-item>
        </el-form>
        </section>

      <!-- 界面行为 -->
        <section class="settings-section behavior-section">
          <div class="card-header">
            <el-icon><Monitor /></el-icon>
            <span>界面行为</span>
          </div>

        <el-form :label-width="formLabelWidth" :label-position="formLabelPosition">
          <!-- 默认着陆页 -->
          <el-form-item label="默认着陆页">
            <el-radio-group v-model="form.default_landing">
              <el-radio-button
                v-for="item in landingOptions"
                :key="item.value"
                :value="item.value"
              >
                {{ item.label }}
              </el-radio-button>
            </el-radio-group>
            <span class="form-tip">登录后默认跳转到的页面</span>
          </el-form-item>

          <!-- 每页显示条数 -->
          <el-form-item label="每页显示条数">
            <el-radio-group v-model="form.items_per_page">
              <el-radio-button
                v-for="item in itemsPerPageOptions"
                :key="item"
                :value="item"
              >
                {{ item }} 条
              </el-radio-button>
            </el-radio-group>
            <span class="form-tip">列表页面的默认分页大小</span>
          </el-form-item>

          <el-form-item label="默认数据范围">
            <el-radio-group v-model="form.default_scope">
              <el-radio-button value="mine">与我相关</el-radio-button>
              <el-radio-button value="team">团队全部</el-radio-button>
            </el-radio-group>
            <span class="form-tip">影响项目和任务页面首次打开时的默认范围</span>
          </el-form-item>

          <!-- 侧边栏默认折叠 -->
          <el-form-item label="侧边栏默认折叠">
            <el-switch v-model="form.sidebar_collapsed" />
            <span class="form-tip">开启后侧边栏菜单将默认收起</span>
          </el-form-item>

          <el-form-item label="常用入口">
            <div class="favorite-route-control">
              <el-select
                v-model="form.favorite_routes"
                multiple
                collapse-tags
                collapse-tags-tooltip
                :multiple-limit="MAX_FAVORITE_ROUTES"
                placeholder="选择当前账户的常用入口"
                class="preference-select"
              >
                <el-option
                  v-for="item in favoriteRouteOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                  :disabled="!(form.favorite_routes || []).includes(item.value) && (form.favorite_routes || []).length >= MAX_FAVORITE_ROUTES"
                />
              </el-select>
              <div v-if="selectedFavoriteRoutes.length" class="favorite-route-list">
                <div v-for="(item, index) in selectedFavoriteRoutes" :key="item.path" class="favorite-route-item">
                  <el-icon><component :is="item.icon" /></el-icon>
                  <span>{{ item.title }}</span>
                  <el-button
                    text
                    circle
                    :icon="ArrowUp"
                    :disabled="index === 0"
                    :aria-label="`上移${item.title}`"
                    @click="moveFavoriteRoute(index, -1)"
                  />
                  <el-button
                    text
                    circle
                    :icon="ArrowDown"
                    :disabled="index === selectedFavoriteRoutes.length - 1"
                    :aria-label="`下移${item.title}`"
                    @click="moveFavoriteRoute(index, 1)"
                  />
                  <el-button
                    text
                    circle
                    :icon="Close"
                    :aria-label="`移除${item.title}`"
                    @click="removeFavoriteRoute(item.path)"
                  />
                </div>
              </div>
              <span class="form-tip">最多 8 个；排序会同步到首页和侧边栏，仅对当前账户生效。</span>
            </div>
          </el-form-item>

          <el-form-item label="菜单分组顺序">
            <div class="sidebar-order-list">
              <div v-for="(group, index) in sidebarGroups" :key="group.value" class="sidebar-order-item">
                <span>{{ group.label }}</span>
                <el-button text circle :icon="ArrowUp" :disabled="index === 0" @click="moveSidebarGroup(index, -1)" />
                <el-button text circle :icon="ArrowDown" :disabled="index === sidebarGroups.length - 1" @click="moveSidebarGroup(index, 1)" />
              </div>
            </div>
          </el-form-item>
        </el-form>
        </section>

        <section class="settings-section dashboard-section">
          <div class="card-header">
            <el-icon><Grid /></el-icon>
            <span>工作台布局</span>
          </div>

          <p class="section-description">选择工作台显示的模块，并调整从上到下的排列顺序。</p>
          <div class="dashboard-card-list">
            <div
              v-for="card in dashboardCardOptions"
              :key="card.value"
              class="dashboard-card-option"
              :class="{ disabled: !dashboardCards.includes(card.value) }"
            >
              <el-checkbox
                :model-value="dashboardCards.includes(card.value)"
                @change="toggleDashboardCard(card.value, $event === true)"
              >
                <strong>{{ card.label }}</strong>
                <small>{{ card.description }}</small>
              </el-checkbox>
              <div class="card-order-actions">
                <el-button
                  text
                  circle
                  :icon="ArrowUp"
                  :disabled="dashboardCards.indexOf(card.value) <= 0"
                  :aria-label="`上移${card.label}`"
                  @click="moveDashboardCard(card.value, -1)"
                />
                <el-button
                  text
                  circle
                  :icon="ArrowDown"
                  :disabled="dashboardCards.indexOf(card.value) < 0 || dashboardCards.indexOf(card.value) >= dashboardCards.length - 1"
                  :aria-label="`下移${card.label}`"
                  @click="moveDashboardCard(card.value, 1)"
                />
              </div>
            </div>
          </div>
        </section>

      <!-- 通知设置 -->
        <section class="settings-section notification-section">
          <div class="card-header">
            <el-icon><Bell /></el-icon>
            <span>通知设置</span>
          </div>

        <el-form :label-width="formLabelWidth" :label-position="formLabelPosition">
          <!-- 通知声音 -->
          <el-form-item label="通知声音">
            <el-switch v-model="form.notification_sound" />
            <span class="form-tip">收到新通知时播放提示音</span>
          </el-form-item>

          <el-form-item label="通知类别">
            <el-checkbox-group v-model="enabledNotificationCategories" class="notification-category-grid">
              <el-checkbox v-for="item in notificationCategoryOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item label="接收渠道">
            <el-checkbox v-model="notificationChannels.in_app">站内实时通知</el-checkbox>
            <el-checkbox v-model="notificationChannels.email">邮件通知</el-checkbox>
          </el-form-item>

          <el-form-item label="通知摘要">
            <el-select v-model="notificationDigest" class="preference-select">
              <el-option label="即时通知" value="instant" />
              <el-option label="每日摘要" value="daily" />
              <el-option label="每周摘要" value="weekly" />
            </el-select>
          </el-form-item>

          <el-form-item label="免打扰">
            <el-switch v-model="quietHours.enabled" />
            <el-time-select
              v-model="quietHours.start"
              start="00:00"
              step="00:30"
              end="23:30"
              :disabled="!quietHours.enabled"
              placeholder="开始"
              class="quiet-time"
            />
            <span>至</span>
            <el-time-select
              v-model="quietHours.end"
              start="00:00"
              step="00:30"
              end="23:30"
              :disabled="!quietHours.enabled"
              placeholder="结束"
              class="quiet-time"
            />
          </el-form-item>
        </el-form>
        </section>

        <section class="settings-section privacy-section">
          <div class="card-header">
            <el-icon><View /></el-icon>
            <span>公开资料授权</span>
          </div>
          <el-form :label-width="formLabelWidth" :label-position="formLabelPosition">
            <el-form-item label="公开成员资料">
              <el-switch
                v-model="portalConsent"
                :loading="savingPortalConsent"
                @change="handlePortalConsentChange"
              />
              <span class="form-tip">
                授权后，老师或管理员才可将你的姓名、年级、专业和项目数量发布到团队公开门户；撤回后立即停止公开。
              </span>
            </el-form-item>
          </el-form>
        </section>

      <!-- 安全设置 -->
        <section class="settings-section security-section">
          <div class="card-header">
            <el-icon><Lock /></el-icon>
            <span>安全设置</span>
          </div>

        <el-form
          ref="pwdFormRef"
          :model="pwdForm"
          :rules="pwdRules"
          :label-width="formLabelWidth"
          :label-position="formLabelPosition"
        >
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" class="password-input" />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少8位，包含字母和数字" class="password-input" />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" class="password-input" />
          </el-form-item>
          <el-form-item>
            <el-button type="warning" :loading="changingPwd" @click="handleChangePassword">修改密码</el-button>
            <span class="form-tip">修改成功后需重新登录</span>
          </el-form-item>
        </el-form>
        </section>
        </div>

      <!-- 底部保存按钮 -->
      <div class="footer-actions">
        <el-button :icon="RefreshLeft" @click="loadPreference">重置</el-button>
        <el-button type="primary" :icon="Check" :loading="saving" @click="handleSave">保存设置</el-button>
      </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onBeforeUnmount, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Check, Brush, Monitor, Bell, RefreshLeft, Lock, Grid, ArrowUp, ArrowDown, Close, View } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { getUserPreference, type UserPreferenceData } from '@/api/users'
import { changePassword } from '@/api/auth'
import { getMyPortalConsent, updateMyPortalConsent } from '@/api/dashboard'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { useRouter } from 'vue-router'
import { useDevice } from '@/composables/useDevice'
import {
  MAX_FAVORITE_ROUTES,
  getFavoriteNavigationItems,
  getFavoriteNavigationOptions,
} from '@/config/navigation'
import {
  DEFAULT_PRIMARY_COLOR,
  DEFAULT_SCHEDULE_END,
  DEFAULT_SCHEDULE_START,
  DEFAULT_THEME_MODE,
  PRIMARY_COLOR_OPTIONS,
  applyPrimaryColor,
  isReadablePrimaryColor,
  normalizePrimaryColor,
  normalizeThemePreference,
  type ThemePreference,
} from '@/utils/theme'
import { setLocale } from '@/i18n'

const { isMobile } = useDevice()
const userStore = useUserStore()
const formLabelWidth = computed(() => (isMobile.value ? 'auto' : '124px'))
const formLabelPosition = computed(() => (isMobile.value ? 'top' : 'right'))

// ============ 选项配置 ============

const themeColorOptions = PRIMARY_COLOR_OPTIONS
const predefinedColors = PRIMARY_COLOR_OPTIONS.map((item) => item.value)
const themeModeOptions = [
  { value: 'light', label: '浅色' },
  { value: 'dark', label: '深色' },
  { value: 'system', label: '跟随系统' },
  { value: 'schedule', label: '定时' },
] as const

const landingOptions = [
  { value: 'dashboard', label: '首页驾驶舱' },
  { value: 'projects', label: '项目管理' },
  { value: 'tasks', label: '任务管理' },
  { value: 'notifications', label: '通知中心' },
]

const itemsPerPageOptions: number[] = [10, 20, 50]
const languageOptions = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'en', label: 'English' },
]
const favoriteRouteOptions = computed(() =>
  getFavoriteNavigationOptions(userStore.role, userStore.userInfo?.membership_status)
    .map((item) => ({ value: item.path, label: item.title })),
)
const sidebarGroupOptions = [
  { value: 'workspace', label: '工作台' },
  { value: 'execution', label: '项目执行' },
  { value: 'resources', label: '人员与资源' },
  { value: 'outcomes', label: '成果与审批' },
  { value: 'administration', label: '平台管理' },
]
const sidebarGroups = ref([...sidebarGroupOptions])
const notificationCategoryOptions = [
  { value: 'system', label: '系统与公告' },
  { value: 'task', label: '任务与逾期' },
  { value: 'project', label: '项目更新' },
  { value: 'competition', label: '比赛节点' },
  { value: 'finance', label: '经费动态' },
  { value: 'contribution', label: '贡献与排名' },
  { value: 'schedule', label: '灵活工时' },
  { value: 'approval', label: '审批与敏感资料' },
  { value: 'report', label: '定时报表' },
]
const enabledNotificationCategories = ref(notificationCategoryOptions.map((item) => item.value))
const notificationChannels = reactive({ in_app: true, email: true })
const notificationDigest = ref<'instant' | 'daily' | 'weekly'>('instant')
const quietHours = reactive({ enabled: false, start: '22:00', end: '07:30' })
const dashboardCardOptions = [
  { value: 'signals', label: '今日摘要', description: '任务、项目、审批和风险统计' },
  { value: 'priority', label: '今日工作与风险', description: '待办队列和项目健康提醒' },
  { value: 'delivery', label: '交付概览', description: '项目与任务状态图表' },
  { value: 'business', label: '业务概览', description: '经费、成果、贡献和比赛动态' },
]
const defaultDashboardCards = dashboardCardOptions.map((item) => item.value)

// ============ 状态 ============

const loading = ref(false)
const saving = ref(false)
const portalConsent = ref(false)
const savingPortalConsent = ref(false)

const form = reactive<UserPreferenceData>({
  dashboard_layout: {},
  primary_color: DEFAULT_PRIMARY_COLOR,
  theme_mode: DEFAULT_THEME_MODE,
  schedule_start: DEFAULT_SCHEDULE_START,
  schedule_end: DEFAULT_SCHEDULE_END,
  default_landing: 'dashboard',
  sidebar_collapsed: false,
  notification_sound: true,
  language: 'zh-CN',
  items_per_page: 20,
  default_scope: 'mine',
  sidebar_order: [],
  favorite_routes: [],
  saved_filters: {},
  notification_preferences: {},
})
const dashboardCards = ref<string[]>([...defaultDashboardCards])
const savedPrimaryColor = ref<string | null>(null)
const savedThemePreference = ref<ThemePreference | null>(null)
const normalizedFormColor = computed(() => normalizePrimaryColor(form.primary_color))
const selectedFavoriteRoutes = computed(() =>
  getFavoriteNavigationItems(
    form.favorite_routes || [],
    userStore.role,
    userStore.userInfo?.membership_status,
  ),
)

function selectPrimaryColor(color: string): void {
  if (!isReadablePrimaryColor(color)) return
  form.primary_color = color
  applyPrimaryColor(color)
}

function previewPrimaryColor(color: string | null): void {
  if (color && /^#[0-9a-fA-F]{6}$/.test(color) && isReadablePrimaryColor(color)) {
    form.primary_color = color.toLowerCase()
    applyPrimaryColor(form.primary_color)
  }
}

function formThemePreference(): ThemePreference {
  return normalizeThemePreference({
    theme_mode: form.theme_mode,
    schedule_start: form.schedule_start,
    schedule_end: form.schedule_end,
  })
}

function syncThemeForm(preference: ThemePreference): void {
  form.theme_mode = preference.theme_mode
  form.schedule_start = preference.schedule_start
  form.schedule_end = preference.schedule_end
}

function previewThemePreference(): void {
  appStore.applyThemeSettings(formThemePreference())
}

function normalizeDashboardCards(layout: Record<string, unknown> | undefined): string[] {
  const raw = Array.isArray(layout?.cards) ? layout.cards.map(String) : []
  const aliases: Record<string, string> = {
    stats: 'signals',
    tasks: 'priority',
    timeline: 'delivery',
    gantt: 'delivery',
    finance: 'business',
    competitions: 'business',
  }
  const normalized = raw
    .map((item) => aliases[item] || item)
    .filter((item, index, list) =>
      defaultDashboardCards.includes(item) && list.indexOf(item) === index
    )
  return normalized.length ? normalized : [...defaultDashboardCards]
}

function toggleDashboardCard(card: string, enabled: boolean): void {
  if (enabled) {
    if (!dashboardCards.value.includes(card)) dashboardCards.value.push(card)
    return
  }
  if (dashboardCards.value.length <= 1) {
    ElMessage.warning('工作台至少保留一个模块')
    return
  }
  dashboardCards.value = dashboardCards.value.filter((item) => item !== card)
}

function moveDashboardCard(card: string, offset: -1 | 1): void {
  const currentIndex = dashboardCards.value.indexOf(card)
  const targetIndex = currentIndex + offset
  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= dashboardCards.value.length) return
  const next = [...dashboardCards.value]
  ;[next[currentIndex], next[targetIndex]] = [next[targetIndex], next[currentIndex]]
  dashboardCards.value = next
}

function moveSidebarGroup(index: number, offset: -1 | 1): void {
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= sidebarGroups.value.length) return
  const next = [...sidebarGroups.value]
  ;[next[index], next[targetIndex]] = [next[targetIndex], next[index]]
  sidebarGroups.value = next
}

function moveFavoriteRoute(index: number, offset: -1 | 1): void {
  const routes = form.favorite_routes || []
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= routes.length) return
  const next = [...routes]
  ;[next[index], next[targetIndex]] = [next[targetIndex], next[index]]
  form.favorite_routes = next
}

function removeFavoriteRoute(path: string): void {
  form.favorite_routes = (form.favorite_routes || []).filter((item) => item !== path)
}

// ============ 数据加载 ============

async function loadPreference(): Promise<void> {
  loading.value = true
  try {
    const data = await getUserPreference()
    form.dashboard_layout = data.dashboard_layout || {}
    dashboardCards.value = normalizeDashboardCards(data.dashboard_layout)
    form.primary_color = normalizePrimaryColor(data.primary_color || data.theme_color)
    savedPrimaryColor.value = form.primary_color
    applyPrimaryColor(form.primary_color)
    const themePreference = normalizeThemePreference(data)
    syncThemeForm(themePreference)
    savedThemePreference.value = themePreference
    appStore.applyThemeSettings(themePreference)
    form.default_landing = data.default_landing || 'dashboard'
    form.sidebar_collapsed = data.sidebar_collapsed ?? false
    form.notification_sound = data.notification_sound ?? true
    form.language = data.language === 'en' ? 'en' : 'zh-CN'
    setLocale(form.language)
    form.items_per_page = data.items_per_page || 20
    form.default_scope = data.default_scope === 'team' ? 'team' : 'mine'
    form.favorite_routes = getFavoriteNavigationItems(
      Array.isArray(data.favorite_routes) ? data.favorite_routes : [],
      userStore.role,
      userStore.userInfo?.membership_status,
    ).slice(0, MAX_FAVORITE_ROUTES).map((item) => item.path)
    const configuredOrder = Array.isArray(data.sidebar_order) ? data.sidebar_order : []
    sidebarGroups.value = [...sidebarGroupOptions].sort((left, right) => {
      const leftIndex = configuredOrder.indexOf(left.value)
      const rightIndex = configuredOrder.indexOf(right.value)
      if (leftIndex < 0 && rightIndex < 0) return 0
      if (leftIndex < 0) return 1
      if (rightIndex < 0) return -1
      return leftIndex - rightIndex
    })
    const notificationPreference = data.notification_preferences || {}
    const categories = notificationPreference.categories || {}
    enabledNotificationCategories.value = notificationCategoryOptions
      .filter((item) => categories[item.value] !== false)
      .map((item) => item.value)
    notificationChannels.in_app = notificationPreference.channels?.in_app !== false
    notificationChannels.email = notificationPreference.channels?.email !== false
    notificationDigest.value = notificationPreference.digest || 'instant'
    quietHours.enabled = notificationPreference.quiet_hours?.enabled === true
    quietHours.start = notificationPreference.quiet_hours?.start || '22:00'
    quietHours.end = notificationPreference.quiet_hours?.end || '07:30'
    const consent = await getMyPortalConsent()
    portalConsent.value = consent.consent
  } catch {
    const rollbackColor = savedPrimaryColor.value || userStore.primaryColor
    form.primary_color = rollbackColor
    userStore.syncPrimaryColor(rollbackColor)
    if (savedThemePreference.value) {
      syncThemeForm(savedThemePreference.value)
      appStore.applyThemeSettings(savedThemePreference.value)
    }
  } finally {
    loading.value = false
  }
}

async function handlePortalConsentChange(value: string | number | boolean): Promise<void> {
  savingPortalConsent.value = true
  try {
    const result = await updateMyPortalConsent(value === true)
    portalConsent.value = result.consent
    ElMessage.success(result.consent ? '已授权公开成员资料' : '已撤回公开授权')
  } catch {
    portalConsent.value = value !== true
  } finally {
    savingPortalConsent.value = false
  }
}

// ============ 保存 ============

async function handleSave(): Promise<void> {
  const requestedColor = String(form.primary_color || '').trim()
  if (!/^#[0-9a-fA-F]{6}$/.test(requestedColor)) {
    ElMessage.warning('请输入完整的六位十六进制颜色')
    return
  }
  if (!isReadablePrimaryColor(requestedColor)) {
    ElMessage.warning('主色过浅，请选择能清晰显示白色文字的较深颜色')
    return
  }
  if (form.theme_mode === 'schedule' && form.schedule_start === form.schedule_end) {
    ElMessage.warning('深色模式的开始和结束时间不能相同')
    return
  }
  saving.value = true
  try {
    form.primary_color = requestedColor.toLowerCase()
    const preference = await userStore.savePreference({
      primary_color: form.primary_color,
      theme_mode: form.theme_mode,
      schedule_start: form.schedule_start,
      schedule_end: form.schedule_end,
      default_landing: form.default_landing,
      sidebar_collapsed: form.sidebar_collapsed,
      notification_sound: form.notification_sound,
      language: form.language,
      items_per_page: form.items_per_page,
      dashboard_layout: { cards: dashboardCards.value },
      default_scope: form.default_scope,
      favorite_routes: form.favorite_routes,
      sidebar_order: sidebarGroups.value.map((item) => item.value),
      saved_filters: form.saved_filters || {},
      notification_preferences: {
        categories: Object.fromEntries(
          notificationCategoryOptions.map((item) => [
            item.value,
            enabledNotificationCategories.value.includes(item.value),
          ]),
        ),
        channels: { ...notificationChannels },
        quiet_hours: { ...quietHours },
        digest: notificationDigest.value,
      },
    })
    form.primary_color = normalizePrimaryColor(preference.primary_color)
    savedPrimaryColor.value = form.primary_color
    const savedTheme = normalizeThemePreference(preference)
    syncThemeForm(savedTheme)
    savedThemePreference.value = savedTheme
    ElMessage.success('偏好设置已保存')
  } catch {
    const rollbackColor = savedPrimaryColor.value || userStore.primaryColor
    form.primary_color = rollbackColor
    userStore.syncPrimaryColor(rollbackColor)
    if (savedThemePreference.value) {
      syncThemeForm(savedThemePreference.value)
      appStore.applyThemeSettings(savedThemePreference.value)
    }
  } finally {
    saving.value = false
  }
}

// ============ 修改密码 ============

const pwdFormRef = ref<FormInstance>()
const changingPwd = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== pwdForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

const router = useRouter()
const appStore = useAppStore()

async function handleChangePassword(): Promise<void> {
  if (!pwdFormRef.value) return
  try {
    await pwdFormRef.value.validate()
    changingPwd.value = true
    await changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
      confirm_password: pwdForm.confirm_password,
    })
    ElMessage.success('密码修改成功，即将重新登录')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    // 退出登录并跳转到登录页
    setTimeout(async () => {
      await userStore.logout()
      router.push('/login')
    }, 1500)
  } catch {
    // 错误已处理
  } finally {
    changingPwd.value = false
  }
}

// ============ 初始化 ============

onMounted(() => {
  savedPrimaryColor.value = userStore.primaryColor
  savedThemePreference.value = {
    theme_mode: appStore.themeMode,
    schedule_start: appStore.scheduleStart,
    schedule_end: appStore.scheduleEnd,
  }
  void loadPreference()
})

onBeforeUnmount(() => {
  if (savedPrimaryColor.value && userStore.isLoggedIn) {
    userStore.syncPrimaryColor(savedPrimaryColor.value)
    if (savedThemePreference.value) appStore.applyThemeSettings(savedThemePreference.value)
  }
})
</script>

<style lang="scss" scoped>
.preference-content {
  min-height: 280px;
}

.settings-panel {
  padding: 0;
  overflow: hidden;
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(340px, 0.8fr);
}

.settings-section {
  min-width: 0;
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--color-border-light);

  &:nth-child(odd) {
    border-right: 1px solid var(--color-border-light);
  }

  :deep(.el-form-item:last-child) {
    margin-bottom: 4px;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 14px;
    margin-bottom: 16px;
    border-bottom: 1px solid var(--color-border-light);
    font-size: 15px;
    font-weight: 600;
    color: var(--color-text);

    .el-icon {
      color: var(--color-primary);
    }
  }
}

.theme-colors {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.custom-color-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  width: 100%;
  margin-top: 12px;

  .color-input {
    width: 124px;
  }

  .form-tip {
    margin: 0;
  }
}

.theme-mode-group {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  width: min(100%, 440px);

  :deep(.el-radio-button__inner) {
    width: 100%;
  }
}

.theme-schedule-row {
  display: grid;
  grid-template-columns: minmax(112px, 1fr) auto minmax(112px, 1fr);
  align-items: center;
  gap: 10px;
  width: min(100%, 340px);
}

.theme-color-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 112px;
  padding: 9px 12px;
  color: inherit;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--transition-base), background var(--transition-base);

  &:hover {
    border-color: var(--color-primary);
  }

  &.active {
    border-color: var(--color-primary);
    background: var(--color-primary-soft);
  }

  .color-block {
    width: 22px;
    height: 22px;
    flex: 0 0 auto;
    border-radius: 50%;
    border: 2px solid var(--color-surface);
    outline: 1px solid var(--color-border);
  }

  .color-label {
    font-size: 13px;
    color: var(--color-text-regular);
  }

  .check-icon {
    margin-left: auto;
    color: var(--color-primary);
    font-size: 14px;
  }
}

.form-tip {
  margin-left: 10px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.password-input {
  width: min(100%, 340px);
}

.preference-select {
  width: min(100%, 380px);
}

.favorite-route-control {
  display: grid;
  gap: 8px;
  width: min(100%, 440px);

  .form-tip { margin-left: 0; }
}

.favorite-route-list {
  display: grid;
  gap: 5px;
}

.favorite-route-item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) 32px 32px 32px;
  align-items: center;
  min-height: 38px;
  gap: 2px;
  padding: 1px 4px 1px 10px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  > .el-icon { color: var(--color-primary); }
  > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
}

.sidebar-order-list {
  display: grid;
  gap: 6px;
  width: min(100%, 380px);
}

.sidebar-order-item {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  min-height: 36px;
  padding: 2px 6px 2px 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.notification-category-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  width: min(100%, 420px);
}

.quiet-time {
  width: 112px;
  margin: 0 8px;
}

.section-description {
  margin: -4px 0 12px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.dashboard-card-list {
  display: grid;
  gap: 8px;
}

.dashboard-card-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 54px;
  padding: 8px 10px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  &.disabled {
    opacity: 0.62;
  }

  :deep(.el-checkbox) {
    flex: 1;
    height: auto;
    min-width: 0;
    align-items: flex-start;
  }

  :deep(.el-checkbox__label) {
    display: grid;
    min-width: 0;
    padding-left: 8px;
    white-space: normal;
  }

  strong {
    color: var(--color-text);
    font-size: 13px;
    font-weight: 600;
  }

  small {
    margin-top: 2px;
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

.card-order-actions {
  display: flex;
  flex: 0 0 auto;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  background: var(--color-surface-subtle);
}

@media screen and (max-width: 960px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .settings-section:nth-child(odd) {
    border-right: 0;
  }
}

@media screen and (max-width: 768px) {
  .settings-section {
    padding: 14px 12px 10px;

    .card-header {
      padding-bottom: 10px;
      margin-bottom: 12px;
    }

    :deep(.el-form-item__label) {
      margin-bottom: 4px;
    }
  }

  .theme-colors {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .theme-color-card {
    min-width: 0;
  }

  .form-tip {
    display: block;
    width: 100%;
    margin: 6px 0 0;
  }

  .settings-section :deep(.el-radio-group) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .theme-mode-group {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .settings-section :deep(.el-radio-button__inner) {
    width: 100%;
  }

  .footer-actions {
    position: sticky;
    bottom: 0;
    z-index: 3;
    padding: 10px 12px max(10px, env(safe-area-inset-bottom));
    border-top: 1px solid var(--color-border-light);
  }
}
</style>
