import type { UserRole } from '@/types'

export interface AppNavigationItem {
  path: string
  title: string
  icon: string
  roles?: readonly UserRole[]
}

export interface AppNavigationGroup {
  key: string
  title: string
  icon: string
  items: readonly AppNavigationItem[]
}

export interface MobilePrimaryNavigationItem {
  path: string
  label: string
  icon: string
}

export const NAVIGATION_GROUPS: readonly AppNavigationGroup[] = [
  {
    key: 'workspace',
    title: '工作台',
    icon: 'Odometer',
    items: [
      { path: '/dashboard', title: '首页', icon: 'Odometer' },
      { path: '/todo', title: '待办事项', icon: 'Checked' },
      { path: '/notifications', title: '通知中心', icon: 'Bell' },
      { path: '/announcements', title: '公告管理', icon: 'Notification' },
      { path: '/activities', title: '团队动态', icon: 'ChatLineSquare' },
      { path: '/reports', title: '定时报表', icon: 'DataAnalysis' },
      { path: '/analytics-studio', title: '分析工作台', icon: 'TrendCharts' },
    ],
  },
  {
    key: 'execution',
    title: '项目执行',
    icon: 'Folder',
    items: [
      { path: '/projects', title: '项目管理', icon: 'Folder' },
      { path: '/projects/archive', title: '项目归档', icon: 'FolderOpened' },
      { path: '/competitions', title: '比赛管理', icon: 'Trophy' },
      { path: '/tasks', title: '任务管理', icon: 'List' },
    ],
  },
  {
    key: 'resources',
    title: '人员与资源',
    icon: 'User',
    items: [
      { path: '/team', title: '团队组织', icon: 'OfficeBuilding' },
      { path: '/members', title: '成员管理', icon: 'User' },
      { path: '/members/schedule', title: '我的任务与工作量', icon: 'Clock' },
      { path: '/members/team-schedule', title: '团队有效工作量', icon: 'DataAnalysis' },
      { path: '/members/skills', title: '技能与组队', icon: 'Collection' },
      { path: '/finance', title: '经费管理', icon: 'Money' },
      { path: '/files', title: '文件管理', icon: 'Document' },
      { path: '/imports', title: '导入中心', icon: 'Upload' },
    ],
  },
  {
    key: 'outcomes',
    title: '成果与审批',
    icon: 'Medal',
    items: [
      { path: '/intellectual-property', title: '成果与知识产权', icon: 'Medal' },
      { path: '/intellectual-property/todo', title: '知识产权待办', icon: 'Bell' },
      { path: '/contributions', title: '我的贡献', icon: 'Trophy' },
      { path: '/contributions/pending', title: '贡献审核', icon: 'CircleCheck' },
      { path: '/sensitive', title: '敏感资料', icon: 'Lock' },
    ],
  },
  {
    key: 'administration',
    title: '平台管理',
    icon: 'Setting',
    items: [
      {
        path: '/audit/logs',
        title: '操作日志',
        icon: 'Document',
        roles: ['sys_admin', 'teacher'],
      },
      {
        path: '/admin/integrations',
        title: '第三方集成',
        icon: 'Connection',
        roles: ['sys_admin'],
      },
      {
        path: '/admin/platform-capabilities',
        title: '平台能力',
        icon: 'Grid',
      },
      {
        path: '/admin/engineering',
        title: '工程控制台',
        icon: 'Monitor',
        roles: ['sys_admin'],
      },
      {
        path: '/admin/users',
        title: '用户管理',
        icon: 'Setting',
        roles: ['sys_admin'],
      },
      {
        path: '/admin/backups',
        title: '演示数据备份',
        icon: 'Box',
        roles: ['sys_admin'],
      },
      {
        path: '/admin/public-portal',
        title: '公开门户',
        icon: 'View',
        roles: ['sys_admin', 'teacher'],
      },
    ],
  },
]

export const MOBILE_PRIMARY_NAVIGATION: readonly MobilePrimaryNavigationItem[] = [
  { path: '/dashboard', label: '首页', icon: 'Odometer' },
  { path: '/projects', label: '项目', icon: 'Folder' },
  { path: '/todo', label: '待办', icon: 'Checked' },
  { path: '/notifications', label: '通知', icon: 'Bell' },
  { path: '/user/profile', label: '我的', icon: 'User' },
]

const EXTERNAL_NAVIGATION_PREFIXES = [
  '/projects',
  '/competitions',
  '/tasks',
  '/files',
  '/notifications',
  '/contributions',
] as const

const EXTERNAL_ROUTE_PREFIXES = [
  ...EXTERNAL_NAVIGATION_PREFIXES,
  '/user',
  '/public-portal',
  '/public',
] as const

const EXTERNAL_MOBILE_NAVIGATION: readonly MobilePrimaryNavigationItem[] = [
  { path: '/projects', label: '项目', icon: 'Folder' },
  { path: '/tasks', label: '任务', icon: 'List' },
  { path: '/files', label: '文件', icon: 'Document' },
  { path: '/notifications', label: '通知', icon: 'Bell' },
  { path: '/user/profile', label: '我的', icon: 'User' },
]

export function isExternalRouteAllowed(path: string): boolean {
  return EXTERNAL_ROUTE_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  )
}

export function getMobilePrimaryNavigation(
  membershipStatus?: string,
): readonly MobilePrimaryNavigationItem[] {
  return membershipStatus === 'external'
    ? EXTERNAL_MOBILE_NAVIGATION
    : MOBILE_PRIMARY_NAVIGATION
}

export function getVisibleNavigationGroups(
  role: string,
  membershipStatus?: string,
): AppNavigationGroup[] {
  return NAVIGATION_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => {
      if (item.roles && !item.roles.includes(role as UserRole)) return false
      if (membershipStatus !== 'external') return true
      return EXTERNAL_NAVIGATION_PREFIXES.some(
        (prefix) => item.path === prefix || item.path.startsWith(`${prefix}/`),
      )
    }),
  })).filter((group) => group.items.length > 0)
}

export interface FavoriteNavigationOption extends AppNavigationItem {
  groupKey: string
  groupTitle: string
}

export const MAX_FAVORITE_ROUTES = 8
export const FAVORITE_ROUTE_PATHS: readonly string[] = NAVIGATION_GROUPS
  .flatMap((group) => group.items.map((item) => item.path))

export function getFavoriteNavigationOptions(
  role: string,
  membershipStatus?: string,
): FavoriteNavigationOption[] {
  const allowedPaths = new Set(FAVORITE_ROUTE_PATHS)
  return getVisibleNavigationGroups(role, membershipStatus).flatMap((group) =>
    group.items.map((item) => ({
      ...item,
      groupKey: group.key,
      groupTitle: group.title,
    })).filter((item) => allowedPaths.has(item.path)),
  )
}

export function getFavoriteNavigationItems(
  paths: readonly string[],
  role: string,
  membershipStatus?: string,
): FavoriteNavigationOption[] {
  const optionsByPath = new Map(
    getFavoriteNavigationOptions(role, membershipStatus)
      .map((item) => [item.path, item]),
  )
  const seen = new Set<string>()
  return paths.flatMap((path) => {
    if (seen.has(path)) return []
    seen.add(path)
    const item = optionsByPath.get(path)
    return item ? [item] : []
  })
}

export function findNavigationItem(
  path: string,
  groups: readonly AppNavigationGroup[] = NAVIGATION_GROUPS,
): AppNavigationItem | undefined {
  return groups
    .flatMap((group) => group.items)
    .filter((item) => path === item.path || path.startsWith(`${item.path}/`))
    .sort((a, b) => b.path.length - a.path.length)[0]
}

export function findNavigationGroup(
  path: string,
  groups: readonly AppNavigationGroup[] = NAVIGATION_GROUPS,
): AppNavigationGroup | undefined {
  return groups.find((group) =>
    group.items.some((item) => path === item.path || path.startsWith(`${item.path}/`)),
  )
}
