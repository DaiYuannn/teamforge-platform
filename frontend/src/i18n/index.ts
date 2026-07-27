import type { App } from 'vue'
import { computed, ref } from 'vue'

export type AppLocale = 'zh-CN' | 'en'

const STORAGE_KEY = 'app_locale'
const EN_MESSAGES: Record<string, string> = {
  '团队管理平台': 'Team Management', '创新团队': 'Innovation Team',
  '让项目进度、协作责任与团队成果保持清晰。': 'Keep delivery, ownership, and team outcomes clear.',
  '返回成果首页': 'Back to public portal', '团队工作台': 'Team Workspace',
  '登录账户': 'Sign In', '使用团队分配的邮箱和密码继续': 'Use your team email and password to continue',
  '邮箱地址': 'Email address', '密码': 'Password', '记住我': 'Remember me',
  '忘记密码': 'Forgot password', '登录': 'Sign In', '重置密码': 'Reset Password',
  '新密码': 'New password', '确认新密码': 'Confirm new password',
  '确认重置': 'Reset Password', '返回登录': 'Back to sign in', '设置新的账户密码': 'Choose a new account password',
  '工作台': 'Workspace', '首页': 'Home', '待办事项': 'To-do',
  '通知中心': 'Notifications', '公告管理': 'Announcements', '团队动态': 'Activity',
  '定时报表': 'Scheduled Reports', '分析工作台': 'Analytics',
  '项目执行': 'Project Delivery', '项目管理': 'Projects', '项目归档': 'Project Archive',
  '比赛管理': 'Competitions', '任务管理': 'Tasks', '人员与资源': 'People & Resources',
  '团队组织': 'Teams', '成员管理': 'Members', '我的灵活工时': 'My Schedule',
  '团队灵活工时': 'Team Schedule', '技能标签': 'Skills', '经费管理': 'Finance',
  '文件管理': 'Files', '导入中心': 'Imports', '成果与审批': 'Outcomes & Approvals',
  '成果与知识产权': 'Outcomes & IP', '知识产权待办': 'IP To-do',
  '我的贡献': 'My Contributions', '贡献审核': 'Contribution Review',
  '敏感资料': 'Sensitive Data', '平台管理': 'Administration', '操作日志': 'Audit Log',
  '第三方集成': 'Integrations', '平台能力': 'Platform Capabilities',
  '工程控制台': 'Engineering Console', '用户管理': 'User Management',
  '演示数据备份': 'Demo Backups', '公开门户': 'Public Portal',
  '常用入口': 'Favorites', '团队工作区': 'Team Workspace', '个人工作区': 'Personal Workspace',
  '个人中心': 'Profile', '退出登录': 'Sign Out', '用户': 'User',
  '搜索项目/任务/成员...': 'Search projects, tasks, members...',
  '首页驾驶舱': 'Dashboard', '项目': 'Projects', '待办': 'To-do', '通知': 'Notifications',
  '我的': 'Me', '文件': 'Files', '任务': 'Tasks', '语言': 'Language',
  '简体中文': 'Simplified Chinese', '英文': 'English',
}

function normalizeLocale(value: unknown): AppLocale {
  return value === 'en' ? 'en' : 'zh-CN'
}

const locale = ref<AppLocale>(normalizeLocale(localStorage.getItem(STORAGE_KEY)))

export function setLocale(value: unknown): AppLocale {
  locale.value = normalizeLocale(value)
  localStorage.setItem(STORAGE_KEY, locale.value)
  document.documentElement.lang = locale.value
  return locale.value
}

export function translate(source: string): string {
  return locale.value === 'en' ? EN_MESSAGES[source] || source : source
}

export function useI18n() {
  return { locale: computed(() => locale.value), setLocale, t: translate }
}

export const i18n = {
  install(app: App) {
    setLocale(locale.value)
    app.config.globalProperties.$t = translate
  },
}
