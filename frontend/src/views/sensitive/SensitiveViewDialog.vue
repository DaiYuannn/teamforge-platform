<template>
  <el-dialog
    v-model="dialogVisible"
    title="安全查看敏感资料"
    width="560px"
    :close-on-click-modal="false"
    @open="handleOpen"
    @close="handleClose"
  >
    <div v-loading="loading" class="view-content">
      <div v-if="viewData" class="security-status" :class="{ 'is-expired': !canViewPlaintext }">
        <el-icon><Timer /></el-icon>
        <div>
          <span>{{ canViewPlaintext ? '授权剩余时间' : '授权已失效' }}</span>
          <strong>{{ canViewPlaintext ? formatCountdown : '00:00' }}</strong>
        </div>
      </div>

      <div v-if="viewData" class="view-record">
        <dl class="record-meta">
          <div>
            <dt>资料名称</dt>
            <dd>{{ viewData.sensitive_data_title || viewData.title || viewData.label || '暂无名称' }}</dd>
          </div>
          <div>
            <dt>资料类型</dt>
            <dd>
              <el-tag :type="SENSITIVE_DATA_TYPE_MAP[viewData.data_type]?.tagType as any" size="small" effect="plain">
                {{ viewData.data_type_display || SENSITIVE_DATA_TYPE_MAP[viewData.data_type]?.label || viewData.data_type || '未知' }}
              </el-tag>
            </dd>
          </div>
          <div class="meta-wide">
            <dt>授权截止</dt>
            <dd>{{ viewExpiresAt ? formatDateTime(viewExpiresAt) : '以审批有效期为准' }}</dd>
          </div>
        </dl>

        <section class="plaintext-panel" :class="{ 'is-revealed': revealed && canViewPlaintext }">
          <div class="plaintext-heading">
            <div>
              <span>明文内容</span>
              <small>关闭窗口后将重新验证授权</small>
            </div>
            <el-tag v-if="revealed && canViewPlaintext" type="danger" size="small" effect="plain">明文已显示</el-tag>
          </div>

          <button
            v-if="!revealed"
            class="reveal-button"
            type="button"
            :disabled="!canViewPlaintext"
            @click="revealed = true"
          >
            <el-icon><View /></el-icon>
            <span>{{ canViewPlaintext ? '显示明文' : '授权已过期' }}</span>
          </button>
          <code v-else-if="canViewPlaintext" class="plain-value">{{ plaintextValue }}</code>
          <span v-else class="plain-value-expired">查看时间已到，明文已隐藏</span>
        </section>
      </div>
    </div>
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer, View } from '@element-plus/icons-vue'
import { viewSensitiveData, viewAccessRequestData } from '@/api/sensitive'
import { SENSITIVE_DATA_TYPE_MAP } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'
import type { SensitiveAccessRequest, SensitiveData } from '@/types'

/**
 * 敏感资料限时查看弹窗
 * 每次打开都调用 view 接口获取明文
 */
const props = defineProps<{
  /** 是否显示 */
  visible: boolean
  /** 访问申请数据（通过申请查看时传入） */
  request?: SensitiveAccessRequest | null
  /** 单份直接授权查看时传入 */
  sensitiveData?: SensitiveData | null
  grantId?: number | null
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

const plaintextValue = computed(() => {
  return viewData.value?.plaintext || viewData.value?.plain_value || viewData.value?.value || '-'
})

const viewExpiresAt = computed<string | undefined>(() => {
  return viewData.value?.access_expires_at || viewData.value?.expires_at
})

// 格式化倒计时
const formatCountdown = computed(() => {
  const m = Math.floor(remainingSeconds.value / 60)
  const s = remainingSeconds.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
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
    } else if (props.sensitiveData?.id && props.grantId) {
      // 通过单份、限时、用途绑定的直接授权查看
      res = await viewSensitiveData(props.sensitiveData.id, undefined, props.grantId)
    }
    if (!res) {
      ElMessage.error('缺少有效的访问授权')
      dialogVisible.value = false
      return
    }
    viewData.value = {
      ...(props.sensitiveData || {}),
      ...res,
      sensitive_data_title: props.sensitiveData?.title,
    }
    // 根据后端返回的 access_expires_at 计算剩余秒数
    const expiresAt = res?.access_expires_at || res?.expires_at
    if (expiresAt) {
      const expires = new Date(expiresAt).getTime()
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
  min-height: 160px;
}

.security-status {
  display: flex;
  margin-bottom: 16px;
  padding: 12px 14px;
  align-items: center;
  gap: 12px;
  background: var(--warning-light);
  border: 1px solid rgba(166, 97, 22, 0.28);
  border-radius: var(--radius-sm);
}

.security-status.is-expired {
  background: var(--danger-light);
  border-color: rgba(182, 66, 66, 0.28);
}

.security-status > .el-icon {
  flex: 0 0 auto;
  color: var(--color-warning);
  font-size: 21px;
}

.security-status.is-expired > .el-icon {
  color: var(--color-danger);
}

.security-status > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1px;
}

.security-status span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.security-status strong {
  color: var(--color-warning);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.security-status.is-expired strong {
  color: var(--color-danger);
}

.view-record {
  min-width: 0;
}

.record-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
  padding: 14px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.record-meta .meta-wide {
  grid-column: 1 / -1;
}

.record-meta dt {
  margin-bottom: 4px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.record-meta dd {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 500;
}

.plaintext-panel {
  margin-top: 14px;
  padding: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.plaintext-panel.is-revealed {
  background: var(--danger-light);
  border-color: rgba(182, 66, 66, 0.34);
}

.plaintext-heading {
  display: flex;
  margin-bottom: 12px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.plaintext-heading > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.plaintext-heading span {
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
}

.plaintext-heading small {
  color: var(--color-text-muted);
  font-size: 11px;
}

.reveal-button {
  display: flex;
  width: 100%;
  min-height: 64px;
  padding: 12px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-primary);
  font: inherit;
  font-weight: 600;
  background: var(--color-primary-soft);
  border: 1px dashed color-mix(in srgb, var(--color-primary) 65%, transparent);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.reveal-button:hover:not(:disabled) {
  background: var(--color-surface-strong);
  border-color: var(--color-primary);
}

.reveal-button:disabled {
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  border-color: var(--color-border);
  cursor: not-allowed;
}

.plain-value {
  display: block;
  min-height: 64px;
  padding: 18px 14px;
  overflow-wrap: anywhere;
  color: var(--color-danger);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.55;
  background: var(--color-surface);
  border: 1px solid rgba(182, 66, 66, 0.22);
  border-radius: var(--radius-sm);
}

.plain-value-expired {
  display: block;
  padding: 18px 14px;
  color: var(--color-text-muted);
  font-size: 13px;
  text-align: center;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-sm);
}

@media screen and (max-width: 520px) {
  .record-meta {
    grid-template-columns: 1fr;
  }

  .record-meta .meta-wide {
    grid-column: 1;
  }
}
</style>
