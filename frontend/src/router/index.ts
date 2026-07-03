import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

// ============================================
// 路由定义
// ============================================

// 公共路由（无需认证）
const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
]

// 需认证路由（使用响应式布局：PC/Mobile 自动切换）
const authRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/ResponsiveLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '首页驾驶舱', icon: 'Odometer', requiresAuth: true },
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/projects/ProjectListView.vue'),
        meta: { title: '项目管理', icon: 'Folder', requiresAuth: true },
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/ProjectDetailView.vue'),
        meta: { title: '项目详情', requiresAuth: true, hidden: true },
      },
      {
        path: 'competitions',
        name: 'CompetitionList',
        component: () => import('@/views/competitions/CompetitionListView.vue'),
        meta: { title: '比赛管理', icon: 'Trophy', requiresAuth: true },
      },
      {
        path: 'tasks',
        name: 'TaskList',
        component: () => import('@/views/tasks/TaskListView.vue'),
        meta: { title: '任务管理', icon: 'List', requiresAuth: true },
      },
      {
        path: 'members',
        name: 'MemberList',
        component: () => import('@/views/members/MemberListView.vue'),
        meta: { title: '人员管理', icon: 'User', requiresAuth: true },
      },
      {
        path: 'members/:id',
        name: 'MemberDetail',
        component: () => import('@/views/members/MemberDetailView.vue'),
        meta: { title: '成员详情', requiresAuth: true, hidden: true },
      },
      {
        path: 'finance',
        name: 'FinanceOverview',
        component: () => import('@/views/finance/FinanceOverviewView.vue'),
        meta: { title: '经费管理', icon: 'Money', requiresAuth: true },
      },
      {
        path: 'files',
        name: 'FileList',
        component: () => import('@/views/files/FileListView.vue'),
        meta: { title: '文件管理', icon: 'Document', requiresAuth: true },
      },
      {
        path: 'imports',
        name: 'ImportCenter',
        component: () => import('@/views/imports/ImportView.vue'),
        meta: { title: '导入中心', icon: 'Upload', requiresAuth: true },
      },
      {
        path: 'intellectual-property',
        name: 'IPApplicationList',
        component: () => import('@/views/intellectual-property/IPApplicationListView.vue'),
        meta: { title: '成果与知识产权', icon: 'Medal', requiresAuth: true },
      },
      {
        path: 'intellectual-property/create',
        name: 'IPApplicationCreate',
        component: () => import('@/views/intellectual-property/IPApplicationFormView.vue'),
        meta: { title: '新建申请', requiresAuth: true, hidden: true },
      },
      {
        path: 'intellectual-property/todo',
        name: 'IPTodo',
        component: () => import('@/views/intellectual-property/IPTodoView.vue'),
        meta: { title: '待我处理', icon: 'Bell', requiresAuth: true },
      },
      {
        path: 'intellectual-property/:id',
        name: 'IPApplicationDetail',
        component: () => import('@/views/intellectual-property/IPApplicationDetailView.vue'),
        meta: { title: '申请详情', requiresAuth: true, hidden: true },
      },
      // 操作日志
      {
        path: 'audit/logs',
        name: 'AuditLogs',
        component: () => import('@/views/audit/OperationLogView.vue'),
        meta: { title: '操作日志', icon: 'Document', requiresAuth: true, roles: ['sys_admin', 'teacher'] },
      },
      // 通知中心
      {
        path: 'notifications',
        name: 'NotificationCenter',
        component: () => import('@/views/notifications/NotificationCenterView.vue'),
        meta: { title: '通知中心', icon: 'Bell', requiresAuth: true },
      },
      // 贡献记录
      {
        path: 'contributions',
        name: 'MyContributions',
        component: () => import('@/views/contributions/MyContributionsView.vue'),
        meta: { title: '我的贡献', icon: 'Trophy', requiresAuth: true },
      },
      {
        path: 'contributions/pending',
        name: 'PendingContributions',
        component: () => import('@/views/contributions/PendingReviewView.vue'),
        meta: { title: '待我审核', requiresAuth: true },
      },
      // 敏感资料
      {
        path: 'sensitive',
        name: 'SensitiveCenter',
        component: () => import('@/views/sensitive/SensitiveCenterView.vue'),
        meta: { title: '敏感资料', icon: 'Lock', requiresAuth: true },
      },
      {
        path: 'sensitive/my-data',
        name: 'MySensitiveData',
        component: () => import('@/views/sensitive/MySensitiveDataView.vue'),
        meta: { title: '我的资料', requiresAuth: true },
      },
      {
        path: 'sensitive/requests',
        name: 'SensitiveRequests',
        component: () => import('@/views/sensitive/AccessRequestsView.vue'),
        meta: { title: '资料查看申请', requiresAuth: true },
      },
      {
        path: 'sensitive/pending',
        name: 'SensitivePending',
        component: () => import('@/views/sensitive/PendingApproveView.vue'),
        meta: { title: '待我审批', requiresAuth: true },
      },
      // 灵活工作时间
      {
        path: 'members/schedule',
        name: 'MySchedule',
        component: () => import('@/views/members/MyScheduleView.vue'),
        meta: { title: '我的灵活工时', requiresAuth: true },
      },
      {
        path: 'members/team-schedule',
        name: 'TeamSchedule',
        component: () => import('@/views/members/TeamScheduleView.vue'),
        meta: { title: '团队灵活工时', requiresAuth: true },
      },
      {
        path: 'members/skills',
        name: 'MemberSkills',
        component: () => import('@/views/members/MemberSkillsView.vue'),
        meta: { title: '技能标签', requiresAuth: true },
      },
      // 集成配置
      {
        path: 'admin/integrations',
        name: 'IntegrationConfig',
        component: () => import('@/views/admin/IntegrationConfigView.vue'),
        meta: { title: '第三方集成', requiresAuth: true, roles: ['sys_admin'] },
      },
      {
        path: 'admin/users',
        name: 'UserManage',
        component: () => import('@/views/admin/UserManageView.vue'),
        meta: {
          title: '用户管理',
          icon: 'Setting',
          requiresAuth: true,
          roles: ['sys_admin'], // 仅系统管理员可访问
        },
      },
    ],
  },
]

// 公共展示面板路由（架构预留）
const publicLayoutRoutes: RouteRecordRaw[] = [
  {
    path: '/public',
    component: () => import('@/layouts/PublicLayout.vue'),
    children: [
      {
        path: 'dashboard',
        name: 'PublicDashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '公共展示面板', requiresAuth: false },
      },
    ],
  },
]

const routes: RouteRecordRaw[] = [
  ...publicRoutes,
  ...authRoutes,
  ...publicLayoutRoutes,
  // 404 路由
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

// ============================================
// 创建路由实例
// ============================================

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// ============================================
// 路由守卫
// ============================================

router.beforeEach(async (to, _from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 团队管理软件` : '团队管理软件'

  const userStore = useUserStore()
  const requiresAuth = to.meta.requiresAuth !== false

  // 需要认证的路由
  if (requiresAuth) {
    // 未登录跳转登录页
    if (!userStore.isLoggedIn) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    // 如果用户信息为空，尝试获取
    if (!userStore.userInfo) {
      try {
        await userStore.fetchProfile()
      } catch {
        await userStore.logout()
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
    }

    // 检查角色权限
    const allowedRoles = to.meta.roles as string[] | undefined
    if (allowedRoles && allowedRoles.length > 0) {
      if (!allowedRoles.includes(userStore.role)) {
        next({ path: '/dashboard' })
        return
      }
    }
  }

  next()
})

export default router
