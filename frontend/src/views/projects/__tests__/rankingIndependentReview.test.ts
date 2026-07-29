import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const detailSource = readFileSync(
  resolve(process.cwd(), 'src/views/projects/ProjectDetailView.vue'),
  'utf8',
)
const apiSource = readFileSync(
  resolve(process.cwd(), 'src/api/contributions.ts'),
  'utf8',
)

describe('ranking confirmation and independent objection review', () => {
  it('lets project managers confirm rankings without requiring a teacher role', () => {
    expect(detailSource).toContain('v-if="canManageProjectWorkflow"')
    expect(detailSource).toContain('负责人确认并公开')
    expect(detailSource).not.toContain(
      `v-permission="['teacher', 'sys_admin']"\n                type="success"\n                @click="handleConfirmRanking"`,
    )
  })

  it('hides self-review actions and requires a different final reviewer', () => {
    expect(detailSource).toContain('canInitiallyReviewObjection')
    expect(detailSource).toContain('row.objector !== currentUserId')
    expect(detailSource).toContain('canFinalizeObjection')
    expect(detailSource).toContain('row.leader_reviewer !== currentUserId')
    expect(detailSource).toContain('负责人最终复核')
    expect(detailSource).toContain('finalReviewObjection')
  })

  it('keeps the legacy backend path while exposing neutral API naming', () => {
    expect(apiSource).toContain('export const finalReviewObjection')
    expect(apiSource).toContain('/teacher_confirm/')
    expect(apiSource).toContain("action: 'teacher_confirm'")
  })
})
