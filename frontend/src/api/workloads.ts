import { del, get, patch, post } from './request'
import type { PaginatedResponse } from '@/types'
import type {
  CompetitionWorkItem,
  CompetitionWorkItemInput,
  WorkloadAssessment,
  WorkloadAssessmentDraftInput,
  WorkloadObjection,
  WorkloadObjectionInput,
  WorkloadObjectionResolutionInput,
} from '@/types/workload'

type CollectionResponse<T> = T[] | PaginatedResponse<T>

function collectionItems<T>(response: CollectionResponse<T>): T[] {
  return Array.isArray(response) ? response : response.results
}

export interface CompetitionWorkItemQuery {
  competition: number
  mine?: 1
}

export async function getCompetitionWorkItems(
  params: CompetitionWorkItemQuery,
): Promise<CompetitionWorkItem[]> {
  const response = await get<CollectionResponse<CompetitionWorkItem>>(
    '/members/competition-work-items/',
    params,
  )
  return collectionItems(response)
}

export function createCompetitionWorkItem(
  data: CompetitionWorkItemInput,
): Promise<CompetitionWorkItem> {
  return post<CompetitionWorkItem>('/members/competition-work-items/', data)
}

export function updateCompetitionWorkItem(
  id: number,
  data: Partial<CompetitionWorkItemInput>,
): Promise<CompetitionWorkItem> {
  return patch<CompetitionWorkItem>(`/members/competition-work-items/${id}/`, data)
}

export function deleteCompetitionWorkItem(id: number): Promise<void> {
  return del<void>(`/members/competition-work-items/${id}/`)
}

export async function getWorkloadAssessments(
  competition: number,
): Promise<WorkloadAssessment[]> {
  const response = await get<CollectionResponse<WorkloadAssessment>>(
    '/members/workload-assessments/',
    { competition },
  )
  return collectionItems(response)
}

export function saveWorkloadAssessmentDraft(
  data: WorkloadAssessmentDraftInput,
): Promise<WorkloadAssessment> {
  return post<WorkloadAssessment>('/members/workload-assessments/save-draft/', data)
}

export function publishWorkloadAssessment(id: number): Promise<WorkloadAssessment> {
  return post<WorkloadAssessment>(`/members/workload-assessments/${id}/publish/`)
}

export async function getWorkloadObjections(
  competition: number,
): Promise<WorkloadObjection[]> {
  const response = await get<CollectionResponse<WorkloadObjection>>(
    '/members/workload-objections/',
    { competition },
  )
  return collectionItems(response)
}

export function createWorkloadObjection(
  data: WorkloadObjectionInput,
): Promise<WorkloadObjection> {
  return post<WorkloadObjection>('/members/workload-objections/', data)
}

export function resolveWorkloadObjection(
  id: number,
  data: WorkloadObjectionResolutionInput,
): Promise<WorkloadObjection> {
  return post<WorkloadObjection>(`/members/workload-objections/${id}/resolve/`, data)
}
