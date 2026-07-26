<template>
  <div class="page-container portal-manage-page">
    <PageHeader title="公开门户" subtitle="管理团队资料、逐项公开范围与重点展示顺序">
      <template #actions>
        <el-button @click="openPortal">预览公开页</el-button>
        <el-button type="primary" :loading="savingSettings" @click="saveSettings">保存团队资料</el-button>
      </template>
    </PageHeader>

    <section v-loading="loading" class="surface-panel settings-panel">
      <div class="section-heading">
        <div><h2>团队资料</h2><p>以下内容会直接出现在无需登录的公开页面。</p></div>
      </div>
      <el-form :model="settings" label-position="top" class="settings-grid">
        <el-form-item label="团队名称"><el-input v-model="settings.team_name" maxlength="120" /></el-form-item>
        <el-form-item label="首页短标语"><el-input v-model="settings.tagline" maxlength="160" /></el-form-item>
        <el-form-item label="团队摘要" class="wide"><el-input v-model="settings.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="介绍标题"><el-input v-model="settings.about_title" maxlength="160" /></el-form-item>
        <el-form-item label="联系邮箱"><el-input v-model="settings.contact_email" /></el-form-item>
        <el-form-item label="团队介绍" class="wide"><el-input v-model="settings.about_text" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="首页图片地址"><el-input v-model="settings.hero_image_url" /></el-form-item>
        <el-form-item label="赛事图片地址"><el-input v-model="settings.story_image_url" /></el-form-item>
        <el-form-item label="加入我们标题"><el-input v-model="settings.join_title" maxlength="160" /></el-form-item>
        <el-form-item label="加入链接"><el-input v-model="settings.join_url" placeholder="https://..." /></el-form-item>
        <el-form-item label="加入我们说明" class="wide"><el-input v-model="settings.join_message" type="textarea" :rows="3" /></el-form-item>
      </el-form>
    </section>

    <section class="surface-panel publication-panel">
      <div class="section-heading">
        <div><h2>逐项发布</h2><p>新内容默认不公开；成员还必须先在个人设置中授权。</p></div>
      </div>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="项目" name="projects" />
        <el-tab-pane label="知识产权" name="ip_applications" />
        <el-tab-pane label="成员" name="members" />
      </el-tabs>
      <el-table :data="activeItems" size="small" row-key="object_id">
        <template #empty><el-empty description="暂无可管理内容" /></template>
        <el-table-column label="内容" min-width="240">
          <template #default="{ row }">
            <div class="content-cell">
              <strong>{{ row.custom_title || row.name }}</strong>
              <span>{{ row.code }}<template v-if="row.secondary"> · {{ row.secondary }}</template></span>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="activeTab === 'members'" label="本人授权" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.member_consent ? 'success' : 'info'" size="small">
              {{ row.member_consent ? '已授权' : '未授权' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="公开" width="90" align="center">
          <template #default="{ row }">
            <el-tooltip
              :disabled="activeTab !== 'members' || row.member_consent"
              content="成员尚未授权公开个人资料"
            >
              <el-switch
                v-model="row.is_public"
                :disabled="activeTab === 'members' && !row.member_consent"
                :loading="savingKey === itemKey(row as PortalPublicationItem)"
                @change="savePublication(row as PortalPublicationItem)"
              />
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="重点展示" width="110" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_featured"
              :loading="savingKey === itemKey(row as PortalPublicationItem)"
              @change="savePublication(row as PortalPublicationItem)"
            />
          </template>
        </el-table-column>
        <el-table-column label="顺序" width="110">
          <template #default="{ row }">
            <el-input-number
              v-model="row.display_order"
              :min="0"
              :max="999"
              controls-position="right"
              size="small"
              @change="savePublication(row as PortalPublicationItem)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as PortalPublicationItem)">展示内容</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="editVisible" title="自定义公开展示内容" width="min(620px, calc(100vw - 32px))">
      <el-form v-if="editingItem" label-position="top">
        <el-form-item label="公开标题"><el-input v-model="editingItem.custom_title" :placeholder="editingItem.name" /></el-form-item>
        <el-form-item label="公开摘要"><el-input v-model="editingItem.custom_summary" type="textarea" :rows="4" /></el-form-item>
        <el-form-item v-if="editingItem.content_type !== 'member'" label="展示图片地址">
          <el-input v-model="editingItem.image_url" placeholder="/portal/photos/..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="Boolean(savingKey)" @click="saveEditingItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getPortalManagement,
  updatePortalPublication,
  updatePortalSettings,
  type PortalManagementData,
  type PortalPublicationItem,
  type PublicPortalSettings,
} from '@/api/dashboard'
import PageHeader from '@/components/PageHeader.vue'

type PortalTab = 'projects' | 'ip_applications' | 'members'

const defaults: PublicPortalSettings = {
  team_name: '创新团队',
  tagline: '',
  summary: '',
  about_title: '',
  about_text: '',
  logo_url: '',
  hero_image_url: '',
  story_image_url: '',
  contact_email: '',
  join_title: '加入我们',
  join_message: '',
  join_url: '',
}

const loading = ref(false)
const savingSettings = ref(false)
const savingKey = ref('')
const activeTab = ref<PortalTab>('projects')
const settings = reactive<PublicPortalSettings>({ ...defaults })
const data = reactive<PortalManagementData>({
  settings: { ...defaults },
  projects: [],
  ip_applications: [],
  members: [],
})
const editVisible = ref(false)
const editingItem = ref<PortalPublicationItem | null>(null)

const activeItems = computed(() => data[activeTab.value])

function itemKey(item: PortalPublicationItem): string {
  return `${item.content_type}-${item.object_id}`
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const result = await getPortalManagement()
    Object.assign(data, result)
    Object.assign(settings, result.settings)
  } finally {
    loading.value = false
  }
}

async function saveSettings(): Promise<void> {
  savingSettings.value = true
  try {
    Object.assign(settings, await updatePortalSettings(settings))
    ElMessage.success('团队公开资料已保存')
  } finally {
    savingSettings.value = false
  }
}

async function savePublication(item: PortalPublicationItem): Promise<void> {
  savingKey.value = itemKey(item)
  try {
    Object.assign(item, await updatePortalPublication(item))
    ElMessage.success('公开设置已更新')
  } catch {
    await loadData()
  } finally {
    savingKey.value = ''
  }
}

function openEdit(item: PortalPublicationItem): void {
  editingItem.value = { ...item }
  editVisible.value = true
}

async function saveEditingItem(): Promise<void> {
  if (!editingItem.value) return
  const source = activeItems.value.find(
    (item) => item.object_id === editingItem.value?.object_id,
  )
  savingKey.value = itemKey(editingItem.value)
  try {
    const updated = await updatePortalPublication(editingItem.value)
    if (source) Object.assign(source, updated)
    editVisible.value = false
    ElMessage.success('展示内容已保存')
  } finally {
    savingKey.value = ''
  }
}

function openPortal(): void {
  window.open('/public', '_blank', 'noopener,noreferrer')
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.portal-manage-page {
  display: grid;
  gap: 16px;
}

.settings-panel,
.publication-panel {
  padding: 18px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;

  h2 {
    color: var(--color-text);
    font-size: 16px;
    font-weight: 650;
  }

  p {
    margin-top: 4px;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;

  .wide {
    grid-column: 1 / -1;
  }
}

.content-cell {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;

  strong {
    overflow: hidden;
    color: var(--color-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

@media screen and (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;

    .wide {
      grid-column: auto;
    }
  }
}
</style>
