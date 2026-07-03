<template>
  <div class="page-container">
    <PageHeader title="我的灵活工作时间" subtitle="按半月周期填写可投入工时">
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="handleOpenForm">填写本期工时</el-button>
      </template>
    </PageHeader>

    <!-- 当前周期信息 -->
    <div class="card period-card">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="当前周期">{{ formatDate(currentPeriod?.period_start) }} ~ {{ formatDate(currentPeriod?.period_end) }}</el-descriptions-item>
        <el-descriptions-item label="可投入时间">{{ currentSchedule?.available_hours ?? '-' }} 小时</el-descriptions-item>
        <el-descriptions-item label="是否饱和">
          <el-tag v-if="currentSchedule" :type="currentSchedule.is_saturated ? 'danger' : 'success' as any" size="small">
            {{ currentSchedule.is_saturated ? '已饱和' : '未饱和' }}
          </el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="能否线下">
          <el-tag v-if="currentSchedule" :type="currentSchedule.can_offline ? 'success' : 'info' as any" size="small">
            {{ currentSchedule.can_offline ? '能' : '不能' }}
          </el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="能否紧急">
          <el-tag v-if="currentSchedule" :type="currentSchedule.can_urgent ? 'success' : 'info' as any" size="small">
            {{ currentSchedule.can_urgent ? '能' : '不能' }}
          </el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注">{{ currentSchedule?.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 历史记录 -->
    <div class="card mt-16">
      <h3 class="card-title">历史记录</h3>
      <el-table v-loading="loading" :data="scheduleList" border stripe size="small">
        <el-table-column prop="period_start" label="周期开始" width="120">
          <template #default="{ row }">{{ formatDate(row.period_start) }}</template>
        </el-table-column>
        <el-table-column prop="period_end" label="周期结束" width="120">
          <template #default="{ row }">{{ formatDate(row.period_end) }}</template>
        </el-table-column>
        <el-table-column prop="available_hours" label="可投入时间" width="110" align="center" />
        <el-table-column prop="can_offline" label="线下" width="70" align="center">
          <template #default="{ row }">{{ row.can_offline ? '能' : '否' }}</template>
        </el-table-column>
        <el-table-column prop="can_urgent" label="紧急" width="70" align="center">
          <template #default="{ row }">{{ row.can_urgent ? '能' : '否' }}</template>
        </el-table-column>
        <el-table-column prop="is_saturated" label="饱和" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_saturated ? 'danger' : 'success' as any" size="small">
              {{ row.is_saturated ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="填写时间" width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 填写工时弹窗 -->
    <el-dialog v-model="formVisible" title="填写本期工时" width="500px" @close="handleClose">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="可投入时间(小时)" prop="available_hours">
          <el-input-number v-model="form.available_hours" :min="0" :max="200" />
        </el-form-item>
        <el-form-item label="能否线下" prop="can_offline">
          <el-switch v-model="form.can_offline" />
        </el-form-item>
        <el-form-item label="能否紧急任务" prop="can_urgent">
          <el-switch v-model="form.can_urgent" />
        </el-form-item>
        <el-form-item label="是否饱和" prop="is_saturated">
          <el-switch v-model="form.is_saturated" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="补充说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getMySchedules, createSchedule, getCurrentPeriod } from '@/api/members'
import { formatDate } from '@/utils/format'
import PageHeader from '@/components/PageHeader.vue'
import type { FlexibleWorkSchedule } from '@/types'

const loading = ref(false)
const scheduleList = ref<FlexibleWorkSchedule[]>([])
const currentPeriod = ref<any>(null)
const currentSchedule = ref<FlexibleWorkSchedule | null>(null)
const formVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

// 表单数据
const form = reactive({
  available_hours: 40,
  can_offline: true,
  can_urgent: false,
  is_saturated: false,
  remark: '',
})

// 验证规则
const rules: FormRules = {
  available_hours: [{ required: true, message: '请输入可投入时间', trigger: 'blur' }],
}

// 加载历史记录
async function loadData(): Promise<void> {
  loading.value = true
  try {
    const res: any = await getMySchedules()
    scheduleList.value = Array.isArray(res) ? res : (res.results || [])
    // 第一条为最新记录
    if (scheduleList.value.length > 0) {
      currentSchedule.value = scheduleList.value[0]
    }
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

// 加载当前周期
async function loadCurrentPeriod(): Promise<void> {
  try {
    currentPeriod.value = await getCurrentPeriod()
  } catch {
    // 忽略
  }
}

// 打开填写弹窗
function handleOpenForm(): void {
  formVisible.value = true
}

// 提交
async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await createSchedule({ ...form })
      ElMessage.success('提交成功')
      formVisible.value = false
      loadData()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 关闭弹窗
function handleClose(): void {
  formRef.value?.resetFields()
  Object.assign(form, {
    available_hours: 40,
    can_offline: true,
    can_urgent: false,
    is_saturated: false,
    remark: '',
  })
}

onMounted(() => {
  loadCurrentPeriod()
  loadData()
})
</script>

<style lang="scss" scoped>
.mt-16 {
  margin-top: 16px;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .card-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}
</style>
