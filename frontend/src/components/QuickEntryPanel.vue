<template>
  <section class="quick-entry-panel" aria-labelledby="quick-entry-title">
    <header class="quick-entry-header">
      <div>
        <h2 id="quick-entry-title">常用入口</h2>
        <p>当前账户的快捷访问</p>
      </div>
      <el-button :icon="Setting" @click="openEditor">自定义</el-button>
    </header>

    <div v-if="favoriteItems.length" class="quick-entry-grid">
      <button
        v-for="item in favoriteItems"
        :key="item.path"
        type="button"
        class="quick-entry-button"
        @click="router.push(item.path)"
      >
        <span class="quick-entry-icon"><el-icon><component :is="item.icon" /></el-icon></span>
        <span class="quick-entry-copy">
          <strong>{{ item.title }}</strong>
          <small>{{ item.groupTitle }}</small>
        </span>
        <el-icon class="quick-entry-arrow"><ArrowRight /></el-icon>
      </button>
    </div>
    <button v-else type="button" class="quick-entry-empty" @click="openEditor">
      <el-icon><Plus /></el-icon>
      <span><strong>添加常用入口</strong><small>选择经常使用的页面，保存后仅对当前账户生效</small></span>
    </button>

    <el-dialog
      v-model="editorVisible"
      title="自定义常用入口"
      width="min(720px, 94vw)"
      append-to-body
      destroy-on-close
    >
      <div class="quick-entry-editor">
        <section class="entry-options" aria-label="可选入口">
          <h3>选择入口</h3>
          <div v-for="group in groupedOptions" :key="group.key" class="entry-option-group">
            <strong>{{ group.title }}</strong>
            <el-checkbox
              v-for="item in group.items"
              :key="item.path"
              :model-value="draftRoutes.includes(item.path)"
              :disabled="!draftRoutes.includes(item.path) && draftRoutes.length >= MAX_FAVORITE_ROUTES"
              @change="toggleRoute(item.path, $event === true)"
            >
              {{ item.title }}
            </el-checkbox>
          </div>
        </section>

        <section class="selected-entries" aria-label="已选入口顺序">
          <h3>显示顺序</h3>
          <p v-if="!draftItems.length" class="selected-empty">尚未选择入口</p>
          <div v-for="(item, index) in draftItems" :key="item.path" class="selected-entry-row">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
            <el-button
              text
              circle
              :icon="ArrowUp"
              :disabled="index === 0"
              :aria-label="`上移${item.title}`"
              @click="moveRoute(index, -1)"
            />
            <el-button
              text
              circle
              :icon="ArrowDown"
              :disabled="index === draftItems.length - 1"
              :aria-label="`下移${item.title}`"
              @click="moveRoute(index, 1)"
            />
            <el-button
              text
              circle
              :icon="Close"
              :aria-label="`移除${item.title}`"
              @click="toggleRoute(item.path, false)"
            />
          </div>
        </section>
      </div>

      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEntries">保存到当前账户</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, ArrowRight, ArrowUp, Close, Plus, Setting } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  MAX_FAVORITE_ROUTES,
  getFavoriteNavigationItems,
  getFavoriteNavigationOptions,
} from '@/config/navigation'

const router = useRouter()
const userStore = useUserStore()
const editorVisible = ref(false)
const saving = ref(false)
const draftRoutes = ref<string[]>([])

const membershipStatus = computed(() => userStore.userInfo?.membership_status)
const availableOptions = computed(() =>
  getFavoriteNavigationOptions(userStore.role, membershipStatus.value),
)
const favoriteItems = computed(() =>
  getFavoriteNavigationItems(
    userStore.preferences?.favorite_routes || [],
    userStore.role,
    membershipStatus.value,
  ),
)
const draftItems = computed(() =>
  getFavoriteNavigationItems(draftRoutes.value, userStore.role, membershipStatus.value),
)
const groupedOptions = computed(() => {
  const groups = new Map<string, { key: string; title: string; items: typeof availableOptions.value }>()
  availableOptions.value.forEach((item) => {
    const group = groups.get(item.groupKey) || { key: item.groupKey, title: item.groupTitle, items: [] }
    group.items.push(item)
    groups.set(item.groupKey, group)
  })
  return Array.from(groups.values())
})

function openEditor(): void {
  draftRoutes.value = favoriteItems.value.map((item) => item.path)
  editorVisible.value = true
}

function toggleRoute(path: string, enabled: boolean): void {
  if (enabled) {
    if (draftRoutes.value.length >= MAX_FAVORITE_ROUTES) {
      ElMessage.warning(`常用入口最多选择 ${MAX_FAVORITE_ROUTES} 个`)
      return
    }
    if (!draftRoutes.value.includes(path)) draftRoutes.value.push(path)
    return
  }
  draftRoutes.value = draftRoutes.value.filter((item) => item !== path)
}

function moveRoute(index: number, offset: -1 | 1): void {
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= draftRoutes.value.length) return
  const next = [...draftRoutes.value]
  ;[next[index], next[targetIndex]] = [next[targetIndex], next[index]]
  draftRoutes.value = next
}

async function saveEntries(): Promise<void> {
  saving.value = true
  try {
    await userStore.savePreference({ favorite_routes: [...draftRoutes.value] })
    editorVisible.value = false
    ElMessage.success('常用入口已保存到当前账户')
  } catch {
    ElMessage.error('常用入口保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
.quick-entry-panel {
  margin-bottom: 16px;
  padding: 16px 20px;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #dce3e0);
  border-radius: 8px;
}

.quick-entry-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;

  h2 { margin: 0; font-size: 16px; line-height: 1.4; }
  p { margin: 3px 0 0; color: var(--color-text-tertiary, #7c8984); font-size: 12px; }
}

.quick-entry-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.quick-entry-button,
.quick-entry-empty {
  appearance: none;
  color: inherit;
  font: inherit;
  text-align: left;
  background: var(--color-surface-subtle, #f7f9f8);
  border: 1px solid var(--color-border-light, #e8edeb);
  border-radius: 6px;
  cursor: pointer;

  &:hover { border-color: var(--primary-color, #176b73); }
  &:focus-visible { outline: 2px solid var(--primary-color, #176b73); outline-offset: 2px; }
}

.quick-entry-button {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 10px;
  min-height: 62px;
  padding: 9px 12px;
}

.quick-entry-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  color: var(--primary-color, #176b73);
  background: var(--primary-lighter, #edf7f6);
  border-radius: 6px;
}

.quick-entry-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 3px;

  strong, small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  strong { font-size: 13px; font-weight: 600; }
  small { color: var(--color-text-tertiary, #7c8984); font-size: 11px; }
}

.quick-entry-arrow { color: var(--color-text-tertiary, #7c8984); font-size: 13px; }

.quick-entry-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 68px;
  gap: 10px;
  color: var(--color-text-secondary, #5f6c67);

  > span { display: flex; flex-direction: column; gap: 3px; }
  strong { color: var(--color-text-primary, #18221f); font-size: 13px; }
  small { font-size: 12px; }
}

.quick-entry-editor { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 20px; }
.quick-entry-editor h3 { margin: 0 0 12px; font-size: 14px; }
.entry-options, .selected-entries { min-width: 0; }
.entry-option-group {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 10px;
  margin-bottom: 14px;

  > strong { grid-column: 1 / -1; color: var(--color-text-secondary, #5f6c67); font-size: 12px; }
  :deep(.el-checkbox) { min-width: 0; margin-right: 0; }
  :deep(.el-checkbox__label) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
}
.selected-entries { padding-left: 20px; border-left: 1px solid var(--color-border-light, #e8edeb); }
.selected-entry-row {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) 32px 32px 32px;
  align-items: center;
  min-height: 40px;
  gap: 2px;
  border-bottom: 1px solid var(--color-border-light, #e8edeb);

  > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
  > .el-icon { color: var(--primary-color, #176b73); }
}
.selected-empty { color: var(--color-text-tertiary, #7c8984); font-size: 13px; }

@media screen and (max-width: 1100px) {
  .quick-entry-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media screen and (max-width: 680px) {
  .quick-entry-panel { padding: 14px 16px; }
  .quick-entry-grid { grid-template-columns: minmax(0, 1fr); }
  .quick-entry-editor { grid-template-columns: minmax(0, 1fr); }
  .selected-entries { padding: 16px 0 0; border-top: 1px solid var(--color-border-light, #e8edeb); border-left: 0; }
}
</style>
