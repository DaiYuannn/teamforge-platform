<template>
  <el-dialog
    v-model="dialogVisible"
    class="competition-detail-dialog"
    title="比赛全流程详情"
    :width="dialogWidth"
    destroy-on-close
  >
    <template v-if="competition">
      <header class="detail-hero">
        <div>
          <p>{{ competition.project_name || '未命名项目' }}</p>
          <h2>{{ competition.name }}</h2>
          <span>{{ competition.organizer || '主办方待补充' }}</span>
        </div>
        <div class="hero-tags">
          <el-tag
            :type="getCompetitionStageTagType(competition.level) as any"
            :style="getCompetitionStageTagStyle(competition.level)"
          >
            {{ getCompetitionLevelLabel(competition.level) }}
          </el-tag>
          <el-tag :type="getCompetitionStatusTagType(competition.status) as any">
            {{ getCompetitionStatusLabel(competition.status) }}
          </el-tag>
        </div>
      </header>

      <section class="detail-section">
        <h3>流程概况</h3>
        <el-descriptions :column="descriptionColumns" border>
          <el-descriptions-item label="比赛类型">
            {{ competition.comp_type || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="当前阶段">
            {{ competition.current_stage || '未填写' }}
          </el-descriptions-item>
          <el-descriptions-item label="晋级结果">
            <el-tag :type="competition.is_promoted ? 'success' : 'info'" size="small">
              {{ competition.is_promoted ? '已晋级' : '未晋级 / 待定' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="获奖结果">
            <el-tag :type="competition.is_awarded ? 'warning' : 'info'" size="small">
              {{ competition.is_awarded ? competition.award_level || '已获奖' : '未获奖 / 待定' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </section>

      <section class="detail-section">
        <h3>全流程节点</h3>
        <div class="milestone-grid">
          <div v-for="item in milestones" :key="item.key" class="milestone-item">
            <span>{{ item.label }}</span>
            <strong>{{ displayDate(item.value) }}</strong>
          </div>
        </div>
      </section>

      <section v-if="competition.not_promoted_reason" class="detail-section">
        <h3>未晋级原因</h3>
        <p class="detail-copy">{{ competition.not_promoted_reason }}</p>
      </section>

      <section class="detail-section narrative-grid">
        <article>
          <h3>评审 / 答辩复盘</h3>
          <p class="detail-copy">{{ competition.review_summary || '暂无复盘记录' }}</p>
        </article>
        <article>
          <h3>改进建议</h3>
          <p class="detail-copy">{{ competition.improvement_suggestion || '暂无改进建议' }}</p>
        </article>
      </section>

      <footer class="detail-meta">
        <span>创建于 {{ displayDateTime(competition.created_at) }}</span>
        <span v-if="competition.updated_at">更新于 {{ displayDateTime(competition.updated_at) }}</span>
      </footer>
    </template>

    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDevice } from '@/composables/useDevice'
import {
  formatDate,
  formatDateTime,
  getCompetitionLevelLabel,
  getCompetitionStageTagStyle,
  getCompetitionStageTagType,
  getCompetitionStatusLabel,
  getCompetitionStatusTagType,
} from '@/utils/format'
import type { Competition } from '@/types'

const props = defineProps<{
  visible: boolean
  competition: Competition | null
}>()

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
}>()

const { isMobile } = useDevice()
const dialogWidth = computed(() => (isMobile.value ? 'calc(100vw - 24px)' : '820px'))
const descriptionColumns = computed(() => (isMobile.value ? 1 : 2))
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})

const milestones = computed(() => {
  const value = props.competition
  if (!value) return []
  return [
    { key: 'register_date', label: '报名日期', value: value.register_date },
    { key: 'material_deadline', label: '材料提交截止', value: value.material_deadline },
    { key: 'review_date', label: '网评日期', value: value.review_date },
    { key: 'defense_date', label: '答辩日期', value: value.defense_date },
    { key: 'school_date', label: '校赛日期', value: value.school_date },
    { key: 'city_date', label: '市赛日期', value: value.city_date },
    { key: 'province_date', label: '省赛日期', value: value.province_date },
    { key: 'national_date', label: '国赛日期', value: value.national_date },
    { key: 'result_date', label: '结果公布', value: value.result_date },
  ]
})

function displayDate(value?: string | null): string {
  return value ? formatDate(value) : '待确定'
}

function displayDateTime(value?: string | null): string {
  return value ? formatDateTime(value) : '-'
}
</script>

<style lang="scss" scoped>
.detail-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 18px;
  background:
    linear-gradient(120deg, color-mix(in srgb, var(--color-primary) 9%, transparent), transparent 65%),
    var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);

  > div:first-child {
    min-width: 0;
  }

  p,
  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  h2 {
    margin: 4px 0;
    color: var(--color-text);
    font-size: 20px;
    font-weight: 650;
    line-height: 1.4;
    overflow-wrap: anywhere;
  }
}

.hero-tags {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

.detail-section {
  margin-top: 22px;

  > h3,
  article > h3 {
    margin-bottom: 10px;
    color: var(--color-text);
    font-size: 14px;
    font-weight: 600;
  }
}

.milestone-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.milestone-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 66px;
  padding: 11px 12px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  span {
    color: var(--color-text-muted);
    font-size: 11px;
  }

  strong {
    color: var(--color-text-regular);
    font-size: 13px;
    font-weight: 550;
    font-variant-numeric: tabular-nums;
  }
}

.narrative-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;

  article {
    min-width: 0;
    padding: 14px;
    background: var(--color-surface-subtle);
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-sm);
  }
}

.detail-copy {
  color: var(--color-text-regular);
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.detail-meta {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  padding-top: 14px;
  margin-top: 20px;
  color: var(--color-text-muted);
  font-size: 11px;
  border-top: 1px solid var(--color-border-light);
}

:deep(.el-dialog__body) {
  max-height: min(72vh, 760px);
  overflow-y: auto;
}

@media screen and (max-width: 768px) {
  .detail-hero {
    flex-direction: column;
    padding: 14px;
  }

  .hero-tags {
    width: 100%;
  }

  .milestone-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .narrative-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .detail-meta {
    align-items: flex-end;
    flex-direction: column;
    gap: 4px;
  }
}
</style>
