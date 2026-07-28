import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { describe, expect, it } from 'vitest'
import CompetitionDetailDialog from '../CompetitionDetailDialog.vue'
import type { Competition } from '@/types'

const slotStub = defineComponent({ template: '<div><slot /></div>' })
const dialogStub = defineComponent({
  template: '<div><slot /><slot name="footer" /></div>',
})
const descriptionItemStub = defineComponent({
  props: { label: String },
  template: '<div><span>{{ label }}</span><slot /></div>',
})
const alertStub = defineComponent({
  props: { title: String },
  template: '<div>{{ title }}</div>',
})
const emptyStub = defineComponent({
  props: { description: String },
  template: '<div>{{ description }}</div>',
})

describe('CompetitionDetailDialog', () => {
  it('renders all workflow dates and review outcomes', () => {
    const competition: Competition = {
      id: 18,
      project: 6,
      project_name: '数字治理项目',
      name: '互联网+创新创业大赛',
      comp_type: '创新创业',
      level: 'national',
      organizer: '教育主管部门',
      status: 'completed',
      current_stage: '获奖归档',
      register_date: '2026-01-01',
      material_deadline: '2026-01-10',
      review_date: '2026-01-20',
      defense_date: '2026-02-01',
      school_date: '2026-02-10',
      city_date: '2026-02-20',
      province_date: '2026-03-01',
      national_date: '2026-03-20',
      result_date: '2026-03-30',
      is_promoted: true,
      is_awarded: true,
      award_level: '国赛金奖',
      not_promoted_reason: '',
      review_summary: '路演逻辑清晰，数据证据仍可加强。',
      improvement_suggestion: '补充用户留存与单位成本数据。',
      created_at: '2026-01-01T08:00:00Z',
      updated_at: '2026-03-31T08:00:00Z',
    }

    const wrapper = mount(CompetitionDetailDialog, {
      props: { visible: true, competition },
      global: {
        stubs: {
          ElDialog: dialogStub,
          ElDescriptions: slotStub,
          ElDescriptionsItem: descriptionItemStub,
          ElTag: slotStub,
          ElButton: slotStub,
        },
      },
    })

    const text = wrapper.text()
    for (const label of [
      '报名日期',
      '材料提交截止',
      '网评日期',
      '答辩日期',
      '校赛日期',
      '市赛日期',
      '省赛日期',
      '国赛日期',
      '结果公布',
    ]) {
      expect(text).toContain(label)
    }
    expect(text).toContain('国赛金奖')
    expect(text).toContain('路演逻辑清晰，数据证据仍可加强。')
    expect(text).toContain('补充用户留存与单位成本数据。')
  })

  it('distinguishes project ownership, competition execution, and reusable evidence', () => {
    const competition: Competition = {
      id: 28,
      project: 16,
      project_name: '安全创新项目',
      project_team_names: ['安全比赛小组'],
      project_leader_names: ['项目牵头人'],
      leader_names: ['比赛执行人'],
      name: '安全创新挑战赛',
      level: 'province',
      organizer: '赛事组委会',
      status: 'ongoing',
      current_stage: '答辩准备',
      is_promoted: false,
      is_awarded: false,
      award_level: '',
      not_promoted_reason: '',
      review_summary: '',
      improvement_suggestion: '',
      participant_count: 1,
      participants: [{
        id: 1,
        competition: 28,
        user: 31,
        user_detail: { name: '比赛执行人' } as any,
        role: 'leader',
        role_display: '比赛负责人',
        participation_status: 'confirmed',
        participation_status_display: '已确认',
        responsibility: '负责材料统筹与现场答辩',
      }],
      competition_contributions: [{
        id: 81,
        project: 16,
        project_name: '安全创新项目',
        user: 31,
        user_name: '比赛执行人',
        contribution_type: 'competition',
        contribution_type_display: '比赛参与',
        content: '完成本场比赛答辩稿',
        status: 'approved',
        status_display: '已通过',
        source_type: 'competition',
        source_type_display: '比赛记录',
        source_verified: true,
        origin_competition_name: '安全创新挑战赛',
        reuse_scope: 'same_project',
        reuse_scope_display: '同项目可引用',
        reuse_eligible: true,
        reuse_reason: '可引用内容和证明材料；原记录仍归属来源项目，不重复计分',
        created_at: '2026-07-20T08:00:00Z',
      }],
      reusable_contributions: [{
        id: 82,
        project: 15,
        project_name: '往届材料项目',
        user: 31,
        user_name: '比赛执行人',
        contribution_type: 'competition',
        contribution_type_display: '比赛参与',
        content: '往届已核验答辩图表',
        status: 'approved',
        status_display: '已通过',
        source_type: 'competition',
        source_type_display: '比赛记录',
        source_verified: true,
        origin_competition_name: '往届安全赛事',
        proof_file_name: '答辩图表.pdf',
        reuse_scope: 'visible_other_project',
        reuse_scope_display: '其他可见项目可引用',
        reuse_eligible: true,
        reuse_reason: '可引用内容和证明材料；原记录仍归属来源项目，不重复计分',
        created_at: '2026-06-20T08:00:00Z',
      }],
      contribution_reuse_note: '只复用内容与证明材料，原贡献不重复计分。',
      created_at: '2026-07-01T08:00:00Z',
    }

    const wrapper = mount(CompetitionDetailDialog, {
      props: { visible: true, competition },
      global: {
        stubs: {
          ElDialog: dialogStub,
          ElDescriptions: slotStub,
          ElDescriptionsItem: descriptionItemStub,
          ElTag: slotStub,
          ElButton: slotStub,
          ElAlert: alertStub,
          ElEmpty: emptyStub,
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('所属小团队安全比赛小组')
    expect(text).toContain('项目牵头负责人项目牵头人')
    expect(text).toContain('比赛执行负责人比赛执行人')
    expect(text).toContain('负责材料统筹与现场答辩')
    expect(text).toContain('完成本场比赛答辩稿')
    expect(text).toContain('可复用的已审核贡献证据')
    expect(text).toContain('往届已核验答辩图表')
    expect(text).toContain('来源项目往届材料项目')
    expect(text).toContain('来源记录比赛：往届安全赛事')
    expect(text).toContain('原贡献不重复计分')
  })
})
