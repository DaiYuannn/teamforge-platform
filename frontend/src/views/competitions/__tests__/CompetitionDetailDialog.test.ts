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
})
