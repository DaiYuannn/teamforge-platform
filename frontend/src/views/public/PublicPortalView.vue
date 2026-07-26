<template>
  <div class="public-portal">
    <section class="hero-section">
      <img
        class="hero-image"
        :src="portalSettings.hero_image_url || '/portal/photos/lst/团队合影1.jpg'"
        :alt="`${portalSettings.team_name}成员合影`"
      />
      <div class="hero-overlay" />
      <div class="hero-content">
        <p class="hero-kicker">{{ portalSettings.tagline }}</p>
        <h1>{{ portalSettings.team_name }}</h1>
        <p class="hero-summary">
          {{ portalSettings.summary }}
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="scrollToProjects">
            查看项目成果
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
        </div>

        <div class="hero-stats" aria-label="团队成果概览">
          <div v-for="item in headlineStats" :key="item.label" class="hero-stat">
            <strong class="tabular-nums">{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="intro-band">
      <div class="section-inner intro-grid">
        <div>
          <p class="section-kicker">共同完成有价值的事</p>
          <h2>{{ portalSettings.about_title }}</h2>
        </div>
        <p>
          {{ portalSettings.about_text }}
        </p>
      </div>
    </section>

    <section id="projects" class="content-section projects-section">
      <div class="section-inner">
        <header class="section-header">
          <div>
            <p class="section-kicker">代表项目</p>
            <h2>把协作转化为成果</h2>
          </div>
          <p>聚焦已经获得赛事认可、并形成可复用经验的团队项目。</p>
        </header>

        <div v-if="loading" class="project-grid" aria-label="正在加载项目">
          <el-skeleton v-for="index in 3" :key="index" animated class="project-skeleton">
            <template #template>
              <el-skeleton-item variant="rect" style="height: 220px" />
            </template>
          </el-skeleton>
        </div>

        <div v-else-if="portalData?.awarded_projects?.length" class="project-grid">
          <article
            v-for="project in portalData.awarded_projects"
            :key="project.project_id"
            class="project-card"
          >
            <img
              v-if="project.image_url"
              :src="project.image_url"
              :alt="project.project_name"
              class="project-cover"
            />
            <div class="project-card__topline">
              <span class="project-code">{{ project.project_code }}</span>
              <el-icon aria-hidden="true"><Trophy /></el-icon>
            </div>
            <h3>{{ project.project_name }}</h3>
            <p class="project-intro">{{ project.intro || '项目介绍正在持续完善。' }}</p>
            <div class="project-meta">
              <span><el-icon><User /></el-icon>{{ project.leader_name || '团队协作' }}</span>
              <span v-if="project.start_date">{{ formatDate(project.start_date) }}</span>
            </div>
            <div class="award-list">
              <span v-for="(award, index) in project.awards" :key="index" class="award-item">
                {{ award.competition_name }} · {{ award.award_level || award.level_display }}
              </span>
            </div>
          </article>
        </div>

        <EmptyState
          v-else
          text="项目成果正在整理"
          description="已确认的获奖项目会在这里公开展示。"
          icon="Trophy"
        />
      </div>
    </section>

    <section class="story-section">
      <div class="section-inner story-grid">
        <div class="story-image-wrap">
          <img :src="portalSettings.story_image_url || '/portal/photos/lst/挑战杯合影.jpg'" alt="团队参加赛事后的合影" />
        </div>
        <div class="story-copy">
          <p class="section-kicker">赛事现场</p>
          <h2>每一次展示，都是共同准备的结果</h2>
          <p>
            从选题、调研、原型到答辩，团队把分工、复盘和资料沉淀贯穿整个过程，让下一次协作建立在真实经验之上。
          </p>
          <div class="story-facts">
            <div><strong class="tabular-nums">{{ portalData?.stats.total_competitions ?? 0 }}</strong><span>参赛记录</span></div>
            <div><strong class="tabular-nums">{{ portalData?.stats.awarded_competitions ?? 0 }}</strong><span>获奖记录</span></div>
          </div>
        </div>
      </div>
    </section>

    <section id="intellectual-property" class="content-section ip-section">
      <div class="section-inner">
        <header class="section-header">
          <div>
            <p class="section-kicker">成果沉淀</p>
            <h2>知识产权</h2>
          </div>
          <p>记录软件著作权、专利和论文等可以持续积累的创新成果。</p>
        </header>

        <div v-if="portalData?.ip_results?.length" class="ip-list">
          <article v-for="item in portalData.ip_results" :key="item.ip_id" class="ip-row">
            <div class="ip-type">
              {{ IP_TYPE_MAP[item.ip_type]?.label || item.ip_type_display || '知识产权' }}
            </div>
            <div class="ip-main">
              <h3>{{ item.title }}</h3>
              <p>{{ item.intro || '成果简介正在整理。' }}</p>
            </div>
            <div class="ip-meta">
              <span>{{ item.application_code || '编号待公开' }}</span>
              <time>{{ item.authorized_date ? formatDate(item.authorized_date) : '流程进行中' }}</time>
            </div>
          </article>
        </div>
        <EmptyState
          v-else-if="!loading"
          text="知识产权成果正在整理"
          description="完成公开确认后会在这里展示。"
          icon="Medal"
          accent="#76559B"
        />
      </div>
    </section>

    <section v-if="portalData?.announcements?.length" class="content-section announcement-section">
      <div class="section-inner">
        <header class="section-header">
          <div><p class="section-kicker">团队动态</p><h2>公开公告</h2></div>
          <p>经过公开确认的团队通知与近期动态。</p>
        </header>
        <div class="announcement-grid">
          <article v-for="item in portalData.announcements.slice(0, 6)" :key="item.id" class="announcement-card">
            <div>
              <el-tag v-if="item.is_pinned" size="small" type="warning">置顶</el-tag>
              <span>{{ item.category_display }}</span>
            </div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.content }}</p>
            <time>{{ item.published_at ? formatDate(item.published_at) : '' }}</time>
          </article>
        </div>
      </div>
    </section>

    <section id="team" class="content-section team-section">
      <div class="section-inner">
        <header class="section-header">
          <div>
            <p class="section-kicker">团队成员</p>
            <h2>不同专长，同一个目标</h2>
          </div>
          <p>核心成员在项目中承担组织、研究、开发、设计与成果推进等职责。</p>
        </header>

        <div v-if="portalData?.core_members?.length" class="member-grid">
          <article v-for="member in portalData.core_members" :key="member.user_id" class="member-card">
            <el-avatar :size="48" class="member-avatar">{{ member.name?.slice(-1) || '员' }}</el-avatar>
            <div class="member-main">
              <h3>{{ member.name }}</h3>
              <p>{{ member.global_role_display || ROLE_MAP[member.global_role]?.label || '团队成员' }}</p>
            </div>
            <div class="member-detail">
              <span>{{ [member.grade, member.major].filter(Boolean).join(' · ') || '跨专业协作' }}</span>
              <span>参与 {{ member.project_count }} 个项目</span>
            </div>
          </article>
        </div>
        <EmptyState v-else-if="!loading" text="成员信息正在整理" icon="User" />
      </div>
    </section>

    <section class="join-section">
      <div class="section-inner join-inner">
        <div>
          <p class="section-kicker">共同成长</p>
          <h2>{{ portalSettings.join_title }}</h2>
          <p>{{ portalSettings.join_message }}</p>
        </div>
        <a v-if="joinHref" :href="joinHref" class="join-action" target="_blank" rel="noopener noreferrer">
          联系团队
        </a>
      </div>
    </section>

    <section v-if="loadError" class="portal-error" role="alert">
      <p>部分公开数据暂时未能载入。</p>
      <el-button :icon="Refresh" @click="loadData">重新加载</el-button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowDown, Refresh, Trophy, User } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState.vue'
import {
  getPublicPortal,
  type PublicPortalData,
  type PublicPortalSettings,
} from '@/api/dashboard'
import { formatDate } from '@/utils/format'
import { IP_TYPE_MAP, ROLE_MAP } from '@/utils/constants'

const loading = ref(false)
const loadError = ref(false)
const portalData = ref<PublicPortalData | null>(null)

const fallbackSettings: PublicPortalSettings = {
  team_name: '创新团队',
  tagline: '项目实践 · 赛事成长 · 成果沉淀',
  summary: '汇聚不同专业的成员，以真实项目协作积累经验。',
  about_title: '从想法到落地，留下完整的团队记忆',
  about_text: '展示经过确认公开的项目、赛事和知识产权成果。',
  logo_url: '',
  hero_image_url: '/portal/photos/lst/团队合影1.jpg',
  story_image_url: '/portal/photos/lst/挑战杯合影.jpg',
  contact_email: '',
  join_title: '加入我们',
  join_message: '',
  join_url: '',
}
const portalSettings = computed(() => portalData.value?.settings || fallbackSettings)
const joinHref = computed(() => {
  if (portalSettings.value.join_url) return portalSettings.value.join_url
  if (portalSettings.value.contact_email) return `mailto:${portalSettings.value.contact_email}`
  return ''
})

const headlineStats = computed(() => [
  { label: '团队项目', value: portalData.value?.stats.total_projects ?? 0 },
  { label: '获奖项目', value: portalData.value?.stats.awarded_projects ?? 0 },
  { label: '知识产权', value: portalData.value?.stats.total_ip ?? 0 },
  { label: '赛事经历', value: portalData.value?.stats.total_competitions ?? 0 },
])

function scrollToProjects(): void {
  document.querySelector('#projects')?.scrollIntoView({ behavior: 'smooth' })
}

async function loadData(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    portalData.value = await getPublicPortal()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style lang="scss" scoped>
.public-portal {
  width: 100%;
  color: var(--color-text);
  background: var(--color-surface);
}

.hero-section {
  position: relative;
  height: min(720px, calc(100dvh - 96px));
  min-height: 560px;
  overflow: hidden;
  color: #fff;
  background: #26332e;
}

.hero-image,
.hero-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.hero-image {
  object-fit: cover;
  object-position: center 42%;
}

.hero-overlay {
  background: rgba(13, 28, 23, 0.5);
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: min(1200px, calc(100% - 48px));
  height: 100%;
  margin: 0 auto;
  padding: 54px 0 38px;
}

.hero-kicker,
.section-kicker {
  margin-bottom: 12px;
  color: inherit;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0;
}

.hero-content h1 {
  max-width: 12ch;
  font-size: 52px;
  font-weight: 700;
  line-height: 1.14;
  letter-spacing: 0;
}

.hero-summary {
  max-width: 600px;
  margin-top: 18px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 17px;
  line-height: 1.75;
}

.hero-actions {
  margin-top: 28px;
}

.hero-actions :deep(.el-button) {
  min-height: 44px;
  padding: 0 18px;
  border-color: #fff;
  color: var(--color-text);
  background: #fff;
}

.hero-actions :deep(.el-button:hover) {
  border-color: #fff;
  color: var(--color-primary);
  background: #fff;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(100px, 160px));
  gap: 0;
  margin-top: auto;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.35);
}

.hero-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 20px;
}

.hero-stat strong {
  font-size: 28px;
  font-weight: 650;
  line-height: 1;
}

.hero-stat span {
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
}

.section-inner {
  width: min(1200px, calc(100% - 48px));
  margin: 0 auto;
}

.intro-band {
  padding: 34px 0;
  background: var(--color-primary);
  color: #fff;
}

.intro-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.8fr);
  align-items: center;
  gap: 64px;
}

.intro-grid h2,
.section-header h2,
.story-copy h2 {
  font-size: 28px;
  font-weight: 650;
  line-height: 1.35;
  letter-spacing: 0;
}

.intro-grid > p {
  color: rgba(255, 255, 255, 0.86);
  line-height: 1.8;
}

.content-section {
  padding: 72px 0;
}

.projects-section,
.team-section {
  background: var(--color-surface);
}

.ip-section {
  background: var(--color-surface-subtle);
}

.section-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 0.65fr);
  align-items: end;
  gap: 48px;
  margin-bottom: 30px;
}

.section-header .section-kicker,
.story-copy .section-kicker {
  color: var(--color-primary);
}

.section-header > p {
  color: var(--color-text-muted);
  line-height: 1.7;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.project-card,
.project-skeleton {
  min-width: 0;
  min-height: 260px;
  padding: 20px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.project-card {
  display: flex;
  flex-direction: column;
}

.project-cover {
  width: calc(100% + 40px);
  height: 150px;
  margin: -20px -20px 16px;
  object-fit: cover;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.project-card__topline,
.project-meta,
.member-detail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.project-card__topline {
  color: var(--color-primary);
}

.project-code {
  color: var(--color-text-muted);
  font-family: 'Cascadia Code', Consolas, monospace;
  font-size: 12px;
}

.project-card h3 {
  margin-top: 20px;
  font-size: 18px;
  font-weight: 650;
  line-height: 1.45;
}

.project-intro {
  display: -webkit-box;
  margin-top: 10px;
  overflow: hidden;
  color: var(--color-text-muted);
  line-height: 1.7;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.project-meta {
  margin-top: auto;
  padding-top: 18px;
  color: var(--color-text-regular);
  font-size: 12px;
}

.project-meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.award-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}

.award-item {
  max-width: 100%;
  padding: 4px 7px;
  overflow: hidden;
  color: #7a541b;
  background: #fbf1df;
  border-radius: var(--radius-xs);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.story-section {
  padding: 72px 0;
  color: #fff;
  background: #17231f;
}

.story-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.72fr);
  align-items: center;
  gap: 56px;
}

.story-image-wrap {
  aspect-ratio: 16 / 10;
  overflow: hidden;
  border-radius: var(--radius-md);
}

.story-image-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.story-copy > p:not(.section-kicker) {
  margin-top: 18px;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.8;
}

.story-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
}

.story-facts div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.story-facts strong {
  font-size: 26px;
}

.story-facts span {
  color: rgba(255, 255, 255, 0.65);
  font-size: 12px;
}

.ip-list {
  border-top: 1px solid var(--color-border);
}

.ip-row {
  display: grid;
  grid-template-columns: 130px minmax(0, 1fr) 180px;
  gap: 24px;
  align-items: start;
  padding: 20px 0;
  border-bottom: 1px solid var(--color-border);
}

.ip-type {
  width: fit-content;
  padding: 4px 8px;
  color: #654687;
  background: var(--ip-light);
  border-radius: var(--radius-xs);
  font-size: 12px;
  font-weight: 600;
}

.ip-main h3 {
  font-size: 15px;
  font-weight: 600;
}

.ip-main p {
  margin-top: 6px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.ip-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.member-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.member-card {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  min-width: 0;
  padding: 16px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.member-avatar {
  color: #fff;
  background: var(--color-primary);
}

.member-main {
  min-width: 0;
}

.member-main h3 {
  font-size: 15px;
  font-weight: 600;
}

.member-main p {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.member-detail {
  grid-column: 1 / -1;
  padding-top: 10px;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border-light);
  font-size: 12px;
}

.announcement-section {
  background: var(--color-surface-subtle);
}

.announcement-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.announcement-card {
  display: flex;
  min-height: 190px;
  padding: 18px;
  flex-direction: column;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-surface);

  > div {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--color-text-muted);
    font-size: 12px;
  }

  h3 {
    margin-top: 16px;
    font-size: 16px;
  }

  p {
    display: -webkit-box;
    margin-top: 8px;
    overflow: hidden;
    color: var(--color-text-muted);
    line-height: 1.7;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
  }

  time {
    margin-top: auto;
    padding-top: 14px;
    color: var(--color-text-muted);
    font-size: 12px;
  }
}

.join-section {
  padding: 64px 0;
  color: #fff;
  background: var(--color-primary);
}

.join-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;

  h2 {
    font-size: 28px;
  }

  p:last-child {
    max-width: 720px;
    margin-top: 10px;
    color: rgba(255, 255, 255, 0.82);
    line-height: 1.8;
  }
}

.join-action {
  display: inline-flex;
  min-height: 44px;
  padding: 0 20px;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  color: var(--color-primary);
  background: #fff;
  border-radius: var(--radius-sm);
  font-weight: 600;
  text-decoration: none;
}

.portal-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px;
  color: #7f3030;
  background: #f9e9e8;
}

@media screen and (max-width: 960px) {
  .project-grid,
  .member-grid,
  .announcement-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .story-grid {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.85fr);
    gap: 32px;
  }
}

@media screen and (max-width: 768px) {
  .hero-section {
    height: calc(100dvh - 104px);
    min-height: 600px;
    max-height: 700px;
  }

  .hero-content,
  .section-inner {
    width: calc(100% - 28px);
  }

  .hero-content {
    padding: 40px 0 24px;
  }

  .hero-content h1 {
    font-size: 36px;
  }

  .hero-summary {
    font-size: 15px;
  }

  .hero-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 18px;
  }

  .hero-stat strong {
    font-size: 24px;
  }

  .intro-band,
  .content-section,
  .story-section {
    padding: 48px 0;
  }

  .intro-grid,
  .section-header,
  .story-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .intro-grid h2,
  .section-header h2,
  .story-copy h2 {
    font-size: 23px;
  }

  .project-grid,
  .member-grid,
  .announcement-grid {
    grid-template-columns: 1fr;
  }

  .join-inner {
    align-items: flex-start;
    flex-direction: column;
  }

  .project-card,
  .project-skeleton {
    min-height: 230px;
  }

  .story-grid {
    gap: 28px;
  }

  .ip-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .ip-meta {
    align-items: flex-start;
  }
}
</style>
