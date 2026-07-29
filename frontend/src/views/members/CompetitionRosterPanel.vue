<template>
  <div class="competition-roster">
    <section class="roster-toolbar surface-panel">
      <div class="roster-toolbar__intro">
        <span>参赛队伍配置</span>
        <strong>先选择比赛，再按项目维护每一支参赛队的人员</strong>
        <p>同一成员可以出现在多个项目或比赛中；人员主档仍由“总团队人员库”统一管理。</p>
      </div>
      <el-select
        v-model="selectedEventId"
        class="event-selector"
        filterable
        placeholder="请选择比赛届次"
        :loading="eventsLoading"
        aria-label="选择比赛届次"
      >
        <el-option
          v-for="event in events"
          :key="event.id"
          :label="eventLabel(event)"
          :value="event.id"
        >
          <div class="event-option">
            <strong>{{ event.name }}</strong>
            <span>{{ [event.edition, event.organizer].filter(Boolean).join(' · ') }}</span>
          </div>
        </el-option>
      </el-select>
    </section>

    <el-alert
      v-if="loadError"
      title="参赛队伍配置暂时无法加载"
      type="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="retryLoad">重新加载</el-button>
      </template>
    </el-alert>

    <section
      v-if="selectedEvent"
      class="event-summary surface-panel"
      aria-label="当前比赛届次"
    >
      <div>
        <span>当前比赛</span>
        <h3>{{ selectedEvent.name }}</h3>
        <p>{{ [selectedEvent.edition, selectedEvent.organizer].filter(Boolean).join(' · ') || '未填写届次与主办方' }}</p>
      </div>
      <dl>
        <div>
          <dt>参赛条目</dt>
          <dd>{{ entries.length || selectedEvent.entry_count }}</dd>
        </div>
        <div>
          <dt>涉及项目</dt>
          <dd>{{ projectGroups.length }}</dd>
        </div>
        <div>
          <dt>当前成员配置</dt>
          <dd>{{ configuredParticipantCount }}</dd>
        </div>
      </dl>
    </section>

    <div v-loading="entriesLoading" class="project-groups">
      <section
        v-for="group in projectGroups"
        :key="group.projectId"
        class="project-group"
      >
        <header class="project-group__header">
          <div>
            <span>比赛内项目</span>
            <h3>{{ group.projectName }}</h3>
          </div>
          <span>{{ group.entries.length }} 个参赛条目</span>
        </header>
        <div class="entry-list">
          <CompetitionEntryCard
            v-for="entry in group.entries"
            :key="entry.id"
            :entry="entry"
            :participants="participantsByEntry[entry.id] || []"
            :loading="rosterLoadingIds.has(entry.id)"
            @refresh="refreshRoster(entry.id)"
          />
        </div>
      </section>

      <EmptyState
        v-if="!entriesLoading && selectedEventId && entries.length === 0"
        text="本次比赛还没有项目参赛条目"
        description="请先在比赛管理中为项目创建参赛条目，再回到这里配置人员"
      />
      <EmptyState
        v-else-if="!eventsLoading && events.length === 0"
        text="暂无比赛届次"
        description="创建比赛届次和项目参赛条目后，即可按比赛查看队伍配置"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  getCompetitionEvents,
  getCompetitionParticipants,
  getCompetitions,
  type CompetitionEvent,
} from '@/api/competitions'
import type { Competition, CompetitionParticipant } from '@/types'
import EmptyState from '@/components/EmptyState.vue'
import CompetitionEntryCard from './CompetitionEntryCard.vue'

interface ProjectEntryGroup {
  projectId: number
  projectName: string
  entries: Competition[]
}

const events = ref<CompetitionEvent[]>([])
const selectedEventId = ref<number>()
const entries = ref<Competition[]>([])
const participantsByEntry = ref<Record<number, CompetitionParticipant[]>>({})
const rosterLoadingIds = ref(new Set<number>())
const eventsLoading = ref(false)
const entriesLoading = ref(false)
const loadError = ref(false)
let entriesRequestId = 0
let rosterRequestId = 0

const selectedEvent = computed(() =>
  events.value.find((event) => event.id === selectedEventId.value),
)
const projectGroups = computed<ProjectEntryGroup[]>(() => {
  const groups = new Map<number, ProjectEntryGroup>()
  entries.value.forEach((entry) => {
    const existing = groups.get(entry.project)
    if (existing) {
      existing.entries.push(entry)
      return
    }
    groups.set(entry.project, {
      projectId: entry.project,
      projectName: entry.project_name || `项目 ${entry.project}`,
      entries: [entry],
    })
  })
  return [...groups.values()]
    .map((group) => ({
      ...group,
      entries: [...group.entries].sort((left, right) => left.id - right.id),
    }))
    .sort((left, right) => left.projectName.localeCompare(right.projectName, 'zh-CN'))
})
const configuredParticipantCount = computed(() =>
  Object.values(participantsByEntry.value).reduce(
    (total, participants) =>
      total + participants.filter(
        (participant) => participant.participation_status !== 'withdrawn',
      ).length,
    0,
  ),
)

function eventLabel(event: CompetitionEvent): string {
  return [event.name, event.edition].filter(Boolean).join(' · ')
}

function setRosterLoading(entryId: number, loading: boolean): void {
  const next = new Set(rosterLoadingIds.value)
  if (loading) next.add(entryId)
  else next.delete(entryId)
  rosterLoadingIds.value = next
}

async function loadEvents(): Promise<void> {
  eventsLoading.value = true
  loadError.value = false
  try {
    const response = await getCompetitionEvents({ page: 1, page_size: 100 })
    events.value = response.results
    if (
      !selectedEventId.value
      || !events.value.some((event) => event.id === selectedEventId.value)
    ) {
      selectedEventId.value = events.value[0]?.id
    }
  } catch {
    loadError.value = true
  } finally {
    eventsLoading.value = false
  }
}

async function loadEntries(eventId?: number): Promise<void> {
  const requestId = ++entriesRequestId
  rosterRequestId += 1
  entries.value = []
  participantsByEntry.value = {}
  rosterLoadingIds.value = new Set()
  if (!eventId) return

  entriesLoading.value = true
  loadError.value = false
  try {
    const response = await getCompetitions({
      event: eventId,
      page: 1,
      page_size: 100,
    })
    if (requestId !== entriesRequestId || selectedEventId.value !== eventId) return
    entries.value = response.results
    await loadAllRosters(response.results, requestId)
  } catch {
    if (requestId === entriesRequestId) loadError.value = true
  } finally {
    if (requestId === entriesRequestId) entriesLoading.value = false
  }
}

async function loadAllRosters(
  targetEntries: Competition[],
  parentRequestId: number,
): Promise<void> {
  const requestId = ++rosterRequestId
  rosterLoadingIds.value = new Set(targetEntries.map((entry) => entry.id))
  const results = await Promise.allSettled(
    targetEntries.map((entry) => getCompetitionParticipants(entry.id)),
  )
  if (
    requestId !== rosterRequestId
    || parentRequestId !== entriesRequestId
  ) return

  const next: Record<number, CompetitionParticipant[]> = {}
  targetEntries.forEach((entry, index) => {
    const result = results[index]
    next[entry.id] = result?.status === 'fulfilled' ? result.value : []
  })
  participantsByEntry.value = next
  rosterLoadingIds.value = new Set()
}

async function refreshRoster(entryId: number): Promise<void> {
  setRosterLoading(entryId, true)
  try {
    const participants = await getCompetitionParticipants(entryId)
    participantsByEntry.value = {
      ...participantsByEntry.value,
      [entryId]: participants,
    }
  } finally {
    setRosterLoading(entryId, false)
  }
}

async function retryLoad(): Promise<void> {
  if (events.value.length === 0) await loadEvents()
  else await loadEntries(selectedEventId.value)
}

watch(selectedEventId, (eventId) => {
  loadEntries(eventId)
})

onMounted(loadEvents)
</script>

<style lang="scss" scoped>
.competition-roster {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.roster-toolbar {
  display: flex;
  min-width: 0;
  padding: 18px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.roster-toolbar__intro {
  display: grid;
  min-width: 0;
  gap: 3px;

  > span,
  p {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  strong {
    color: var(--color-text);
    font-size: 16px;
  }
}

.event-selector {
  width: min(430px, 46%);
  flex: 0 0 auto;
}

.event-option {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  span {
    overflow: hidden;
    color: var(--color-text-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.event-summary {
  display: flex;
  padding: 16px 18px;
  align-items: stretch;
  justify-content: space-between;
  gap: 24px;

  > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    justify-content: center;

    span,
    p {
      color: var(--color-text-muted);
      font-size: 12px;
    }

    h3 {
      margin: 2px 0;
      color: var(--color-text);
      font-size: 17px;
    }
  }

  dl {
    display: grid;
    grid-template-columns: repeat(3, minmax(96px, 1fr));
    min-width: 330px;

    > div {
      padding: 2px 18px;
      text-align: right;
      border-left: 1px solid var(--color-border-light);
    }

    dt {
      color: var(--color-text-muted);
      font-size: 11px;
    }

    dd {
      margin-top: 2px;
      color: var(--color-text);
      font-size: 22px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }
  }
}

.project-groups,
.project-group,
.entry-list {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.project-groups {
  min-height: 220px;
  gap: 18px;
}

.project-group {
  gap: 10px;
}

.project-group__header {
  display: flex;
  padding: 0 2px;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;

  div > span,
  > span {
    color: var(--color-text-muted);
    font-size: 12px;
  }

  h3 {
    margin-top: 2px;
    color: var(--color-text);
    font-size: 17px;
  }
}

.entry-list {
  gap: 12px;
}

@media screen and (max-width: 780px) {
  .roster-toolbar,
  .event-summary {
    align-items: flex-start;
    flex-direction: column;
  }

  .event-selector {
    width: 100%;
  }

  .event-summary dl {
    width: 100%;
    min-width: 0;

    > div:first-child {
      padding-left: 0;
      border-left: 0;
    }
  }
}
</style>
