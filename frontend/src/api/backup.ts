import { download, get, post } from './request'

export interface DemoBackup {
  backup_id: string
  created_at: string
  created_by: string
  reason: string
  status: 'ready' | 'corrupt'
  size: number
  entry_count: number
  sha256: string
  requires_relogin: boolean
  download_url: string
}

export interface DemoBackupList {
  backups: DemoBackup[]
  total: number
  mode: 'demo'
  message: string
}

export const getDemoBackups = () => get<DemoBackupList>('/common/backup/')
export const createDemoBackup = () => post<DemoBackup>('/common/backup/create/')
export const restoreDemoBackup = (backupId: string) =>
  post<{
    backup_id: string
    status: 'restored'
    rollback_backup_id: string
    requires_relogin: boolean
  }>(`/common/backup/${backupId}/restore/`, { confirmation: 'RESTORE_DEMO' })
export const downloadDemoBackup = (backupId: string): Promise<Blob> =>
  download(`/common/backup/${backupId}/download/`)
