import { shallowMount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CompetitionFormDialog from '../CompetitionFormDialog.vue'
import type { Competition, CompetitionFormData } from '@/types'

function fullCompetition(): Competition {
  return {
    id: 8,
    project: 3,
    project_name: '智慧农业项目',
    name: '挑战杯全国大学生课外学术科技作品竞赛',
    comp_type: '创新创业',
    level: 'national',
    level_display: '国赛',
    organizer: '竞赛组委会',
    status: 'completed',
    status_display: '已结束',
    current_stage: '国赛已完成',
    register_date: '2026-01-02',
    material_deadline: '2026-01-20',
    review_date: '2026-02-02',
    defense_date: '2026-02-15',
    school_date: '2026-02-20',
    city_date: '2026-03-01',
    province_date: '2026-03-20',
    national_date: '2026-04-10',
    result_date: '2026-04-15',
    is_promoted: true,
    is_awarded: true,
    award_level: '国赛一等奖',
    not_promoted_reason: '',
    review_summary: '评委重点询问真实用户数据和成本结构。',
    improvement_suggestion: '补齐落地单位证明与三年财务测算。',
    created_at: '2026-01-01T08:00:00Z',
    updated_at: '2026-04-16T08:00:00Z',
  }
}

describe('CompetitionFormDialog', () => {
  it('hydrates every backend workflow field and builds a lossless edit payload', () => {
    const source = fullCompetition()
    const wrapper = shallowMount(CompetitionFormDialog, {
      props: {
        visible: false,
        formData: source,
      },
    })
    const vm = wrapper.vm as unknown as {
      form: CompetitionFormData
      buildPayload: () => CompetitionFormData
      showStageDate: (level: 'city' | 'province' | 'national') => boolean
    }

    expect(vm.showStageDate('national')).toBe(true)
    expect(vm.buildPayload()).toEqual({
      project: 3,
      name: source.name,
      comp_type: '创新创业',
      level: 'national',
      status: 'completed',
      organizer: '竞赛组委会',
      current_stage: '国赛已完成',
      register_date: '2026-01-02',
      material_deadline: '2026-01-20',
      review_date: '2026-02-02',
      defense_date: '2026-02-15',
      school_date: '2026-02-20',
      city_date: '2026-03-01',
      province_date: '2026-03-20',
      national_date: '2026-04-10',
      result_date: '2026-04-15',
      is_promoted: true,
      is_awarded: true,
      award_level: '国赛一等奖',
      not_promoted_reason: '',
      review_summary: '评委重点询问真实用户数据和成本结构。',
      improvement_suggestion: '补齐落地单位证明与三年财务测算。',
    })
  })

  it('keeps an existing higher-level date visible after the level is changed', () => {
    const wrapper = shallowMount(CompetitionFormDialog, {
      props: {
        visible: false,
        formData: fullCompetition(),
      },
    })
    const vm = wrapper.vm as unknown as {
      form: CompetitionFormData
      showStageDate: (level: 'city' | 'province' | 'national') => boolean
    }

    vm.form.level = 'school'
    expect(vm.showStageDate('city')).toBe(true)
    expect(vm.showStageDate('province')).toBe(true)
    expect(vm.showStageDate('national')).toBe(true)
  })
})
