<template>
  <div class="page-container">
    <PageHeader title="个人设置" subtitle="管理你的账户个性化配置">
      <template #actions>
        <el-button type="primary" :icon="Check" :loading="saving" @click="handleSave">保存设置</el-button>
      </template>
    </PageHeader>

    <div v-loading="loading" class="preference-content">
      <!-- 外观设置 -->
      <el-card class="pref-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Brush /></el-icon>
            <span>外观设置</span>
          </div>
        </template>

        <el-form label-width="140px" label-position="right">
          <!-- 主题色选择 -->
          <el-form-item label="主题色">
            <div class="theme-colors">
              <div
                v-for="item in themeColorOptions"
                :key="item.value"
                class="theme-color-card"
                :class="{ active: form.theme_color === item.value }"
                @click="form.theme_color = item.value"
              >
                <div class="color-block" :style="{ backgroundColor: item.color }" />
                <span class="color-label">{{ item.label }}</span>
                <el-icon v-if="form.theme_color === item.value" class="check-icon"><Check /></el-icon>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 界面行为 -->
      <el-card class="pref-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Monitor /></el-icon>
            <span>界面行为</span>
          </div>
        </template>

        <el-form label-width="140px" label-position="right">
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

          <!-- 侧边栏默认折叠 -->
          <el-form-item label="侧边栏默认折叠">
            <el-switch v-model="form.sidebar_collapsed" />
            <span class="form-tip">开启后侧边栏菜单将默认收起</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 通知设置 -->
      <el-card class="pref-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Bell /></el-icon>
            <span>通知设置</span>
          </div>
        </template>

        <el-form label-width="140px" label-position="right">
          <!-- 通知声音 -->
          <el-form-item label="通知声音">
            <el-switch v-model="form.notification_sound" />
            <span class="form-tip">收到新通知时播放提示音</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 安全设置 -->
      <el-card class="pref-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Lock /></el-icon>
            <span>安全设置</span>
          </div>
        </template>

        <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="140px" label-position="right">
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" style="width: 300px" />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少8位，包含字母和数字" style="width: 300px" />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" style="width: 300px" />
          </el-form-item>
          <el-form-item>
            <el-button type="warning" :loading="changingPwd" @click="handleChangePassword">修改密码</el-button>
            <span class="form-tip">修改成功后需重新登录</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 底部保存按钮 -->
      <div class="footer-actions">
        <el-button :icon="RefreshLeft" @click="loadPreference">重置</el-button>
        <el-button type="primary" :icon="Check" :loading="saving" @click="handleSave">保存设置</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Check, Brush, Monitor, Bell, RefreshLeft, Lock } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { getUserPreference, updateUserPreference, type UserPreferenceData } from '@/api/users'
import { changePassword } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

// ============ 选项配置 ============

const themeColorOptions = [
  { value: 'blue', label: '经典蓝', color: '#409EFF' },
  { value: 'green', label: '清新绿', color: '#67C23A' },
  { value: 'purple', label: '优雅紫', color: '#9B59B6' },
  { value: 'orange', label: '活力橙', color: '#E6A23C' },
]

const landingOptions = [
  { value: 'dashboard', label: '首页驾驶舱' },
  { value: 'projects', label: '项目管理' },
  { value: 'tasks', label: '任务管理' },
  { value: 'notifications', label: '通知中心' },
]

const itemsPerPageOptions: number[] = [10, 20, 50]

// ============ 状态 ============

const loading = ref(false)
const saving = ref(false)

const form = reactive<UserPreferenceData>({
  dashboard_layout: {},
  theme_color: 'blue',
  default_landing: 'dashboard',
  sidebar_collapsed: false,
  notification_sound: true,
  items_per_page: 20,
})

// ============ 数据加载 ============

async function loadPreference(): Promise<void> {
  loading.value = true
  try {
    const data = await getUserPreference()
    form.dashboard_layout = data.dashboard_layout || {}
    form.theme_color = data.theme_color || 'blue'
    form.default_landing = data.default_landing || 'dashboard'
    form.sidebar_collapsed = data.sidebar_collapsed ?? false
    form.notification_sound = data.notification_sound ?? true
    form.items_per_page = data.items_per_page || 20
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

// ============ 保存 ============

async function handleSave(): Promise<void> {
  saving.value = true
  try {
    await updateUserPreference({
      theme_color: form.theme_color,
      default_landing: form.default_landing,
      sidebar_collapsed: form.sidebar_collapsed,
      notification_sound: form.notification_sound,
      items_per_page: form.items_per_page,
    })
    ElMessage.success('偏好设置已保存')
  } catch {
    // 错误已处理
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
const userStore = useUserStore()

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
  loadPreference()
})
</script>

<style lang="scss" scoped>
.preference-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pref-card {
  border-radius: 8px;

  .card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #303133;
  }
}

.theme-colors {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.theme-color-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 100px;

  &:hover {
    border-color: #c0c4cc;
  }

  &.active {
    border-color: #409eff;
    background-color: #ecf5ff;
  }

  .color-block {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .color-label {
    font-size: 13px;
    color: #606266;
  }

  .check-icon {
    position: absolute;
    top: 6px;
    right: 6px;
    color: #409eff;
    font-size: 16px;
  }
}

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
}
</style>
