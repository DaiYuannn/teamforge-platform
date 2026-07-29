<template>
  <div class="traceability-groups">
    <article v-for="group in groups" :key="group.key" class="traceability-group">
      <header>
        <div class="group-title">
          <span>{{ perspective === 'project' ? '项目视角' : '比赛视角' }}</span>
          <h3>{{ group.label }}</h3>
          <small v-if="group.subtitle">{{ group.subtitle }}</small>
        </div>
        <dl class="group-totals">
          <div><dt>奖金已到账</dt><dd>{{ money(group.received_bonus) }}</dd></div>
          <div><dt>成员垫付</dt><dd>{{ money(group.member_advanced) }}</dd></div>
          <div><dt>已预留</dt><dd>{{ money(group.reserved) }}</dd></div>
          <div><dt>团队已支付</dt><dd>{{ money(group.paid) }}</dd></div>
        </dl>
      </header>

      <el-table :data="group.children" row-key="key" size="small" @row-click="openRow">
        <template #empty>
          <EmptyState text="当前分组暂无收支" compact />
        </template>
        <el-table-column :label="perspective === 'project' ? '比赛 / 参赛队' : '项目 / 参赛队'" min-width="210">
          <template #default="{ row }">
            <div class="entry-cell">
              <strong>{{ perspective === 'project' ? row.event_name : row.project_name }}</strong>
              <span>{{ row.competition_entry_name }}</span>
              <small v-if="row.event_edition">{{ row.event_edition }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="比赛结果" min-width="120">
          <template #default="{ row }">
            <span>{{ row.award_result || '待补充' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="负责人 / 参赛成员" min-width="180">
          <template #default="{ row }">
            <div class="people-cell">
              <strong>{{ row.leader_names?.join('、') || '待指定负责人' }}</strong>
              <span>{{ row.participant_names?.join('、') || '待维护参赛名单' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="预计奖金" width="126" align="right">
          <template #default="{ row }">{{ money(row.expected_bonus) }}</template>
        </el-table-column>
        <el-table-column label="已确认应收" width="126" align="right">
          <template #default="{ row }">{{ money(row.confirmed_bonus) }}</template>
        </el-table-column>
        <el-table-column label="已到账" width="126" align="right">
          <template #default="{ row }"><strong class="positive">{{ money(row.received_bonus) }}</strong></template>
        </el-table-column>
        <el-table-column label="成员垫付" width="126" align="right">
          <template #default="{ row }">{{ money(row.member_advanced) }}</template>
        </el-table-column>
        <el-table-column label="已预留" width="116" align="right">
          <template #default="{ row }">{{ money(row.reserved) }}</template>
        </el-table-column>
        <el-table-column label="已支付" width="116" align="right">
          <template #default="{ row }"><strong>{{ money(row.paid) }}</strong></template>
        </el-table-column>
        <el-table-column label="待覆盖" width="116" align="right">
          <template #default="{ row }"><span :class="{ danger: row.outstanding > 0 }">{{ money(row.outstanding) }}</span></template>
        </el-table-column>
        <el-table-column label="详情" width="74" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openRow(row)">追溯</el-button>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <EmptyState
      v-if="!groups.length"
      text="暂无可追溯收支"
      description="登记奖金、成员垫付或项目公共支出后，这里会按项目和比赛双向展开。"
      icon="Wallet"
    />
  </div>
</template>

<script setup lang="ts">
import { formatMoneyWithComma } from '@/utils/format'
import EmptyState from '@/components/EmptyState.vue'
import type {
  FinancePerspective,
  FinanceTraceabilityGroup,
  FinanceTraceabilityLeaf,
} from '@/types/financeLedger'

defineProps<{
  perspective: FinancePerspective
  groups: FinanceTraceabilityGroup[]
}>()

const emit = defineEmits<{
  (event: 'open', row: FinanceTraceabilityLeaf): void
}>()

function openRow(row: unknown): void {
  emit('open', row as FinanceTraceabilityLeaf)
}

function money(value: number): string {
  return formatMoneyWithComma(value)
}
</script>

<style scoped lang="scss">
.traceability-groups { display: grid; gap: 14px; }
.traceability-group { overflow: hidden; background: var(--color-surface); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.traceability-group > header { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 14px 16px; background: var(--color-surface-subtle); border-bottom: 1px solid var(--color-border-light); }
.group-title { min-width: 170px; }
.group-title > span { color: var(--color-primary); font-size: 11px; font-weight: 700; letter-spacing: .05em; }
.group-title h3 { margin: 3px 0 0; font-size: 16px; }
.group-title small { display: block; margin-top: 3px; color: var(--color-text-muted); }
.group-totals { display: grid; grid-template-columns: repeat(4, minmax(100px, 1fr)); gap: 1px; min-width: min(520px, 65%); margin: 0; overflow: hidden; border: 1px solid var(--color-border-light); border-radius: 7px; }
.group-totals div { padding: 8px 10px; background: var(--color-surface); text-align: right; }
.group-totals dt { color: var(--color-text-muted); font-size: 10px; }
.group-totals dd { margin: 3px 0 0; font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
.entry-cell { display: grid; gap: 2px; cursor: pointer; }
.entry-cell strong { color: var(--color-text); }
.entry-cell span, .entry-cell small { color: var(--color-text-muted); font-size: 11px; }
.people-cell { display: grid; gap: 2px; }
.people-cell span { overflow: hidden; color: var(--color-text-muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.positive { color: var(--color-success); }
.danger { color: var(--color-danger); font-weight: 700; }
:deep(.el-table__row) { cursor: pointer; }

@media (max-width: 900px) {
  .traceability-group > header { align-items: stretch; flex-direction: column; }
  .group-totals { width: 100%; min-width: 0; }
}

@media (max-width: 600px) {
  .group-totals { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
