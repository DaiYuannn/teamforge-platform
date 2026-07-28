<template>
  <div class="page-container">
    <PageHeader title="个人中心" subtitle="查看与编辑个人信息" />

    <section v-loading="loading" class="surface-panel profile-content">
      <!-- 左侧：头像与概览 -->
      <aside class="profile-aside">
        <AvatarWithName
          :name="form.name || userInfo?.name || ''"
          :avatar-url="userInfo?.avatar"
          :size="96"
          :show-name="false"
          class="profile-avatar"
        />
        <el-upload
          :show-file-list="false"
          :before-upload="handleAvatarUpload"
          accept="image/jpeg,image/png,image/gif,image/webp"
        >
          <el-button size="small" :icon="Upload" :loading="uploadingAvatar">更换头像</el-button>
        </el-upload>
        <span class="avatar-tip">支持 JPG/PNG/GIF/WebP，最大 5MB</span>
        <h3 class="profile-name">{{ userInfo?.name || '用户' }}</h3>
        <el-tag :type="getRoleTagType(userStore.role) as any" size="small" effect="light">
          {{ getRoleLabel(userStore.role) }}
        </el-tag>
        <el-divider />
        <div class="profile-meta">
          <div class="meta-row">
            <span class="meta-label">账号</span>
            <span class="meta-value">{{ userInfo?.username || '-' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">邮箱</span>
            <span class="meta-value">{{ userInfo?.email || '-' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">注册时间</span>
            <span class="meta-value">{{ formatDate(userInfo?.date_joined) }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">最近登录</span>
            <span class="meta-value">{{ formatDateTime(userInfo?.last_login) }}</span>
          </div>
        </div>
      </aside>

      <!-- 右侧：编辑表单 -->
      <div class="profile-main">
        <div class="section-header">
          <h2>编辑资料</h2>
          <span>更新可公开的基本联系信息</span>
        </div>
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          :label-width="isMobile ? 'auto' : '84px'"
          :label-position="isMobile ? 'top' : 'right'"
          class="profile-form"
        >
          <el-form-item label="姓名" prop="name">
            <el-input v-model="form.name" placeholder="请输入姓名" maxlength="30" show-word-limit />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="form.phone" placeholder="请输入手机号" maxlength="20" />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="请输入邮箱" maxlength="64" />
          </el-form-item>
          <el-form-item label="学校">
            <el-input v-model="form.school" placeholder="请输入学校" maxlength="150" />
          </el-form-item>
          <el-form-item label="年级">
            <el-input v-model="form.grade" placeholder="例如 2024级" maxlength="50" />
          </el-form-item>
          <el-form-item label="专业">
            <el-input v-model="form.major" placeholder="请输入专业" maxlength="100" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">保存修改</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { formatDate, formatDateTime, getRoleLabel, getRoleTagType } from '@/utils/format'
import type { UpdateProfileParams } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import AvatarWithName from '@/components/AvatarWithName.vue'
import { Upload } from '@element-plus/icons-vue'
import { useDevice } from '@/composables/useDevice'

const { isMobile } = useDevice()

/**
 * 个人中心页面（需求G）
 * 展示并编辑当前登录用户的基本信息
 */
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const uploadingAvatar = ref(false)
const formRef = ref<FormInstance>()

const userInfo = ref(userStore.userInfo)

// 表单数据
const form = reactive<UpdateProfileParams>({
  name: '',
  phone: '',
  email: '',
  school: '',
  grade: '',
  major: '',
})

// 校验规则
const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] }],
}

// 同步用户信息到表单
function syncForm(): void {
  const u = userStore.userInfo
  if (!u) return
  userInfo.value = u
  form.name = u.name || ''
  form.phone = u.phone || ''
  form.email = u.email || ''
  form.school = u.school || ''
  form.grade = u.grade || ''
  form.major = u.major || ''
}

// 加载用户信息
async function loadProfile(): Promise<void> {
  loading.value = true
  try {
    await userStore.fetchProfile()
    syncForm()
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 头像上传
async function handleAvatarUpload(file: File): Promise<boolean> {
  // 客户端校验
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('仅支持 JPG/PNG/GIF/WebP 格式')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 5MB')
    return false
  }

  uploadingAvatar.value = true
  try {
    const { uploadAvatar } = await import('@/api/auth')
    const res = await uploadAvatar(file)
    // 更新本地用户信息
    if (userStore.userInfo) {
      userStore.userInfo.avatar = res.avatar
    }
    userInfo.value = userStore.userInfo
    ElMessage.success('头像上传成功')
  } catch {
    // 错误已由拦截器处理
  } finally {
    uploadingAvatar.value = false
  }
  return false
}

// 提交修改
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data: UpdateProfileParams = {
        name: form.name,
        phone: form.phone,
        email: form.email,
        school: form.school,
        grade: form.grade,
        major: form.major,
      }
      await userStore.updateProfile(data)
      userInfo.value = userStore.userInfo
      ElMessage.success('保存成功')
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 重置表单
function handleReset(): void {
  syncForm()
  formRef.value?.clearValidate()
}

onMounted(() => {
  // 若已有用户信息则直接同步，否则拉取
  if (userStore.userInfo) {
    syncForm()
  } else {
    loadProfile()
  }
})
</script>

<style lang="scss" scoped>
.profile-content {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  align-items: stretch;
  padding: 0;
  overflow: hidden;

  .profile-aside {
    min-width: 0;
    padding: 24px 20px;
    text-align: center;
    background: var(--color-surface-subtle);
    border-right: 1px solid var(--color-border-light);

    .profile-avatar {
      justify-content: center;
      margin-bottom: 8px;
    }
    .avatar-tip {
      display: block;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 4px;
    }

    .profile-name {
      font-size: 18px;
      font-weight: 600;
      color: var(--color-text);
      margin: 14px 0 8px;
    }

    .profile-meta {
      text-align: left;

      .meta-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 13px;
        padding: 6px 0;

        .meta-label {
          color: var(--color-text-muted);
        }

        .meta-value {
          color: var(--color-text);
          max-width: 160px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }
  }

  .profile-main {
    min-width: 0;
    padding: 24px;

    .section-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 14px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--color-border-light);

      h2 {
        margin: 0;
        color: var(--color-text);
        font-size: 16px;
        font-weight: 600;
      }

      span {
        color: var(--color-text-muted);
        font-size: 12px;
      }
    }

    .profile-form {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0 16px;
      max-width: 720px;

      :deep(.el-form-item:nth-child(3)),
      :deep(.el-form-item:last-child) {
        grid-column: 1 / -1;
      }
    }
  }
}

@media screen and (max-width: 768px) {
  .profile-content {
    grid-template-columns: 1fr;

    .profile-aside {
      width: 100%;
      padding: 20px 16px;
      border-right: 0;
      border-bottom: 1px solid var(--color-border-light);

      .profile-meta {
        max-width: 420px;
        margin: 0 auto;
      }
    }

    .profile-main {
      padding: 16px 12px;

      .section-header {
        align-items: flex-start;
        flex-direction: column;
        gap: 3px;
        margin-bottom: 14px;
      }

      .profile-form {
        display: block;
        max-width: none;

        :deep(.el-form-item__label) {
          margin-bottom: 4px;
        }
      }
    }
  }
}
</style>
