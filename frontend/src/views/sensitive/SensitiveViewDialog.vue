<template>
  <el-dialog
    v-model="dialogVisible"
    title="敏感资料查看"
    width="500px"
    :close-on-click-modal="false"
    @open="handleOpen"
    @close="handleClose"
  >
    <div v-loading="loading" class="view-content">
      <!-- 倒计时提醒 -->
      <el-alert v-if="remainingSeconds > 0" type="warning" :closable="false" show-icon class="countdown-alert">
        剩余查看时间：{{ formatCountdown }}
      </el-alert>
      <el-alert v-if="remainingSeconds <= 0 && viewData" type="error" :closable="false" show-icon class="countdown-alert">
        查看时间已到，明文已自动隐藏
      </el-alert>
      <el-descriptions v-if="viewData" :column="1" border>
        <el-descriptions-item label="资料名称">{{ viewData.sensitive_data_title || viewData.title || viewData.label || '暂无名称' }}</el-descriptions-item>
        <el-descriptions-item label="资料类型">
          <el-tag :type="SENSITIVE_DATA_TYPE_MAP[viewData.data_type]?.tagType as any" size="small">
            {{ viewData.data_type_display || SENSITIVE_DATA_TYPE_MAP[viewData.data_type]?.label || viewData.data_type || '未知' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="有效期">
          {{ viewData.access_expires_at ? formatDate(viewData.access_expires_at) : '以审批有效期为准' }}
        </el-descriptions-item>
        <el-descriptions-item label="明文内容">
          <!-- 明文显示区域：带遮罩效果 -->
          <div class="plain-value-wrapper">
            <div v-if="!revealed" class="plain-value-mask" @click="revealed = true">
              <el-icon size="20"><View /></el-icon>
              <span>点击查看明文</span>
            </div>
            <span v-if="revealed && canViewPlaintext" class="plain-value">{{ viewData.plaintext || viewData.plain_value || viewData.value }}</span>
            <span v-if="revealed && !canViewPlaintext" class="plain-value-expired">查看时间已到</span>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </div>
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { viewSensitiveData, viewAccessRequestData } from '@/api/sensitive'
import { SENSITIVE_DATA_TYPE_MAP } from '@/utils/constants'
import { formatDate } from '@/utils/format'
import type { SensitiveAccessRequest } from '@/types'

/**
 * 敏感资料限时查看弹窗
 * 每次打开都调用 view 接口获取明文
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 访问申请数据（通过申请查看时传入） */
  request?: SensitiveAccessRequest | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
}>()

const loading = ref(false)
const viewData = ref<any>(null)
// 剩余查看时间（秒），基于后端返回的 access_expires_at 计算
const remainingSeconds = ref(0)
// 明文是否已揭示（遮罩点击后显示明文）
const revealed = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

// 弹窗可见性
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

// 是否仍可查看明文（基于后端过期时间）
const canViewPlaintext = computed(() => {
  if (remainingSeconds.value > 0) return true
  return false
})

// 格式化倒计时
const formatCountdown = computed(() => {
  const m = Math.floor(remainingSeconds.value / 60)
  const s = remainingSeconds.value % 60
  return `${m}分${s}秒`
})

// 打开弹窗
function handleOpen(): void {
  loadViewData()
}

// 加载明文数据（每次打开弹窗都调用 view 接口）
async function loadViewData(): Promise<void> {
  loading.value = true
  revealed.value = false
  try {
    let res: any
    if (props.request && props.request.id) {
      // 通过申请查看
      res = await viewAccessRequestData(props.request.id)
    } else if (viewData.value?.id) {
      // 直接查看自己的资料
      res = await viewSensitiveData(viewData.value.id)
    }
    viewData.value = res
    // 根据后端返回的 access_expires_at 计算剩余秒数
    if (res?.access_expires_at) {
      const expires = new Date(res.access_expires_at).getTime()
      const now = Date.now()
      const diff = Math.floor((expires - now) / 1000)
      remainingSeconds.value = diff > 0 ? diff : 0
    } else {
      // 后端未返回明确过期时间，默认给 60 秒查看窗口
      remainingSeconds.value = 60
    }
    startCountdown()
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 启动倒计时
function startCountdown(): void {
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    remainingSeconds.value--
    if (remainingSeconds.value <= 0) {
      remainingSeconds.value = 0
      if (timer) clearInterval(timer)
      ElMessage.warning('查看时间已到，窗口将关闭')
      dialogVisible.value = false
    }
  }, 1000)
}

// 关闭弹窗
function handleClose(): void {
  if (timer) clearInterval(timer)
  remainingSeconds.value = 0
  revealed.value = false
  viewData.value = null
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="scss" scoped>
.view-content {
  min-height: 100px;
}

.countdown-alert {
  margin-bottom: 16px;
}

/* 明文显示区域：遮罩效果 */
.plain-value-wrapper {
  position: relative;
  min-height: 40px;
  display: flex;
  align-items: center;

  .plain-value {
    font-size: 16px;
    font-weight: 600;
    color: #f56c6c;
    letter-spacing: 1px;
    word-break: break-all;
  }

  .plain-value-expired {
    font-size: 14px;
    color: #c0c4cc;
  }

  /* 遮罩层：点击后揭示明文 */
  .plain-value-mask {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, #f5f7fa, #e4e7ed);
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    cursor: pointer;
    color: #909399;
    font-size: 13px;
    transition: all 0.2s;
    backdrop-filter: blur(4px);

    &:hover {
      background: linear-gradient(135deg, #ecf5ff, #d9ecff);
      color: #409eff;
    }
  }
}
</style>
