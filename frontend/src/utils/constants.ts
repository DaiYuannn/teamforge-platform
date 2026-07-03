// ============================================
// 常量定义
// ============================================

// 项目阶段映射（16阶段，与后端 Project.Stage 枚举一致）
export const PROJECT_STAGES: Record<number, string> = {
  1: '构思中',
  2: '已立项',
  3: '材料准备中',
  4: '开发实验制作中',
  5: '报名准备',
  6: '材料提交',
  7: '网评审核',
  8: '答辩准备',
  9: '校赛',
  10: '市赛',
  11: '省赛',
  12: '国赛',
  13: '已获奖',
  14: '已结项',
  15: '暂停',
  16: '终止',
}

// 项目阶段列表（有序）
export const PROJECT_STAGE_LIST = Object.entries(PROJECT_STAGES).map(([value, label]) => ({
  value: Number(value),
  label,
}))

// 项目状态映射
export const PROJECT_STATUS_MAP: Record<string, { label: string; type: string }> = {
  active: { label: '进行中', type: 'success' },
  paused: { label: '已暂停', type: 'warning' },
  closed: { label: '已关闭', type: 'info' },
}

// 任务状态映射
export const TASK_STATUS_MAP: Record<string, { label: string; type: string }> = {
  todo: { label: '待办', type: 'info' },
  doing: { label: '进行中', type: 'primary' },
  pending_review: { label: '待审核', type: 'warning' },
  done: { label: '已完成', type: 'success' },
  overdue: { label: '已逾期', type: 'danger' },
  paused: { label: '已暂停', type: 'info' },
  cancelled: { label: '已取消', type: 'info' },
  need_help: { label: '需协助', type: 'warning' },
}

// 任务状态列表（看板列顺序）
export const TASK_STATUS_LIST = [
  { value: 'todo', label: '待办', color: '#909399' },
  { value: 'doing', label: '进行中', color: '#409EFF' },
  { value: 'pending_review', label: '待审核', color: '#E6A23C' },
  { value: 'done', label: '已完成', color: '#67C23A' },
  { value: 'overdue', label: '延期', color: '#F56C6C' },
]

// 任务优先级映射
export const TASK_PRIORITY_MAP: Record<string, { label: string; tagType: string }> = {
  low: { label: '低', tagType: 'info' },
  medium: { label: '中', tagType: '' },
  high: { label: '高', tagType: 'warning' },
  urgent: { label: '紧急', tagType: 'danger' },
}

// 角色映射
export const ROLE_MAP: Record<string, { label: string; tagType: string }> = {
  sys_admin: { label: '系统管理员', tagType: 'danger' },
  teacher: { label: '老师', tagType: 'warning' },
  member: { label: '普通成员', tagType: '' },
  sens_approver: { label: '敏感审批人', tagType: 'success' },
}

// 经费类别映射
export const FINANCE_CATEGORY_MAP: Record<string, { label: string; color: string }> = {
  registration: { label: '报名费', color: '#409EFF' },
  material: { label: '材料费', color: '#67C23A' },
  printing: { label: '打印费', color: '#3498DB' },
  travel: { label: '差旅费', color: '#E6A23C' },
  equipment: { label: '设备费', color: '#F56C6C' },
  software: { label: '软件费', color: '#1ABC9C' },
  competition_fee: { label: '比赛报名费', color: '#9B59B6' },
  promotion: { label: '推广费', color: '#E74C3C' },
  labor: { label: '劳务费', color: '#9B59B6' },
  other: { label: '其他', color: '#909399' },
}

// 经费支出状态映射
export const FINANCE_EXPENSE_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  pending: { label: '待审批', tagType: 'info' },
  approved: { label: '已批准', tagType: 'success' },
  rejected: { label: '已驳回', tagType: 'danger' },
  reimbursed: { label: '已报销', tagType: '' },
}

// 比赛级别映射
export const COMPETITION_LEVEL_MAP: Record<string, { label: string; tagType: string }> = {
  national: { label: '国家级', tagType: 'danger' },
  provincial: { label: '省级', tagType: 'warning' },
  municipal: { label: '市级', tagType: '' },
  school: { label: '校级', tagType: 'info' },
  enterprise: { label: '企业级', tagType: 'success' },
}

// 比赛状态映射
export const COMPETITION_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  upcoming: { label: '即将开始', tagType: 'info' },
  registering: { label: '报名中', tagType: '' },
  ongoing: { label: '进行中', tagType: 'success' },
  judging: { label: '评审中', tagType: 'warning' },
  completed: { label: '已结束', tagType: 'info' },
}

// 文件权限级别映射
export const FILE_PERMISSION_MAP: Record<string, { label: string; tagType: string }> = {
  public: { label: '公开', tagType: 'success' },
  internal: { label: '内部', tagType: 'warning' },
  sensitive: { label: '敏感', tagType: 'danger' },
}

// 导入模块映射
export const IMPORT_MODULE_MAP: Record<string, string> = {
  users: '用户',
  projects: '项目',
  members: '成员',
  tasks: '任务',
  competitions: '比赛',
}

// 导入任务状态映射
export const IMPORT_TASK_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  pending: { label: '待处理', tagType: 'info' },
  previewing: { label: '预览中', tagType: '' },
  confirming: { label: '导入中', tagType: 'warning' },
  completed: { label: '已完成', tagType: 'success' },
  failed: { label: '失败', tagType: 'danger' },
  rolled_back: { label: '已回滚', tagType: 'info' },
}

// 风险提醒类型映射
export const RISK_ALERT_TYPE_MAP: Record<string, { label: string; color: string }> = {
  task_overdue: { label: '任务延期', color: '#F56C6C' },
  project_delay: { label: '项目延期', color: '#E6A23C' },
  budget_exceeded: { label: '预算超支', color: '#F56C6C' },
}

// 风险严重程度映射
export const RISK_SEVERITY_MAP: Record<string, { label: string; tagType: string }> = {
  high: { label: '高', tagType: 'danger' },
  medium: { label: '中', tagType: 'warning' },
  low: { label: '低', tagType: 'info' },
}

// ============================================
// 知识产权模块常量映射
// ============================================

// 知识产权成果类型映射
export const IP_TYPE_MAP: Record<string, { label: string; color: string }> = {
  software_copyright: { label: '软件著作权', color: 'primary' },
  invention_patent: { label: '发明专利', color: 'danger' },
  utility_model: { label: '实用新型专利', color: 'warning' },
  design_patent: { label: '外观设计专利', color: 'success' },
  paper: { label: '论文成果', color: 'info' },
  other: { label: '其他', color: 'info' },
}

// 知识产权申请状态映射
export const IP_STATUS_MAP: Record<string, { label: string; color: string; step: number }> = {
  draft: { label: '准备中', color: 'info', step: 0 },
  writing: { label: '材料撰写中', color: '', step: 1 },
  leader_review: { label: '负责人审核中', color: 'warning', step: 2 },
  teacher_confirm: { label: '老师确认中', color: 'warning', step: 3 },
  research_office_review: { label: '科研处审核中', color: '', step: 4 },
  returned: { label: '科研处退回', color: 'danger', step: 5 },
  modifying: { label: '修改中', color: 'warning', step: 6 },
  resubmitted: { label: '已重新提交', color: '', step: 7 },
  accepted: { label: '已受理', color: 'success', step: 8 },
  authorized: { label: '已授权/登记', color: 'success', step: 9 },
  archived: { label: '已归档', color: 'success', step: 10 },
  paused: { label: '暂停', color: 'info', step: -1 },
  terminated: { label: '终止', color: 'danger', step: -1 },
  deferred: { label: '转为后续', color: 'info', step: -1 },
}

// 贡献者角色映射
export const IP_CONTRIBUTOR_ROLE_MAP: Record<string, string> = {
  main_writer: '主导撰写人',
  co_writer: '协作撰写人',
  code_provider: '代码提供人',
  document_writer: '文档撰写人',
  drawing_provider: '图纸提供人',
  tester: '测试人',
  executor: '申请执行人',
  material_manager: '材料整理人',
  reviewer: '审核人',
}

// 退回来源映射
export const IP_RETURN_SOURCE_MAP: Record<string, string> = {
  research_office: '科研处',
  school_system: '学校系统',
  agency: '代理机构',
  patent_platform: '专利平台',
  other: '其他',
}

// 责任类型映射
export const IP_RESPONSIBILITY_TYPE_MAP: Record<string, string> = {
  writing_problem: '撰写质量问题',
  material_problem: '材料完整性问题',
  submit_problem: '提交流程问题',
  review_problem: '审核问题',
  system_problem: '系统问题',
  unattributable: '无法归属',
  other: '其他',
}

// 退回结果映射
export const IP_RETURN_RESULT_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '待修改', color: 'warning' },
  modified: { label: '已修改', color: '' },
  resubmitted: { label: '已重新提交', color: '' },
  accepted: { label: '已通过', color: 'success' },
  rejected: { label: '未通过', color: 'danger' },
}

// 材料类型映射
export const IP_MATERIAL_TYPE_MAP: Record<string, string> = {
  application_form: '申请表',
  manual: '软件说明书',
  source_code: '源代码文档',
  screenshot: '软件截图',
  disclosure: '专利交底书',
  specification: '专利说明书',
  claims: '权利要求书',
  abstract: '摘要',
  drawing: '附图',
  feedback: '科研处反馈截图',
  system_screenshot: '申请系统截图',
  acceptance_notice: '受理通知书',
  certificate: '授权证书',
  archive: '归档材料',
  other: '其他',
}

// 异议类型映射
export const IP_OBJECTION_TYPE_MAP: Record<string, string> = {
  writing_credit: '撰写贡献异议',
  execution_credit: '申请执行贡献异议',
  return_responsibility: '退回责任异议',
  ranking: '成果排序异议',
  material_credit: '材料撰写异议',
  other: '其他',
}

// 异议状态映射
export const IP_OBJECTION_STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '待处理', color: 'warning' },
  leader_reviewed: { label: '负责人已初审', color: '' },
  teacher_confirmed: { label: '老师已确认', color: 'success' },
  resolved: { label: '已解决', color: 'success' },
  rejected: { label: '已驳回', color: 'danger' },
}

// ============================================
// 操作日志模块常量映射
// ============================================

// 操作日志模块映射
export const AUDIT_MODULE_MAP: Record<string, { label: string; tagType: string }> = {
  projects: { label: '项目管理', tagType: '' },
  tasks: { label: '任务管理', tagType: 'success' },
  finance: { label: '经费管理', tagType: 'warning' },
  files: { label: '文件管理', tagType: 'info' },
  contributions: { label: '贡献记录', tagType: '' },
  sensitive: { label: '敏感资料', tagType: 'danger' },
  intellectual_property: { label: '知识产权', tagType: 'success' },
  members: { label: '人员管理', tagType: '' },
  competitions: { label: '比赛管理', tagType: 'warning' },
  users: { label: '用户管理', tagType: 'danger' },
  notifications: { label: '通知', tagType: 'info' },
  integrations: { label: '第三方集成', tagType: '' },
  exports: { label: '数据导出', tagType: 'info' },
}

// 操作类型映射
export const AUDIT_ACTION_MAP: Record<string, { label: string; tagType: string }> = {
  create: { label: '创建', tagType: 'success' },
  update: { label: '更新', tagType: '' },
  delete: { label: '删除', tagType: 'danger' },
  retrieve: { label: '查询', tagType: 'info' },
  login: { label: '登录', tagType: '' },
  logout: { label: '退出', tagType: 'info' },
  upload: { label: '上传', tagType: 'success' },
  download: { label: '下载', tagType: 'info' },
  approve: { label: '审批', tagType: 'success' },
  reject: { label: '驳回', tagType: 'danger' },
  review: { label: '审核', tagType: 'warning' },
  view_sensitive: { label: '查看敏感', tagType: 'danger' },
  export: { label: '导出', tagType: 'info' },
  import: { label: '导入', tagType: 'warning' },
  other: { label: '其他', tagType: 'info' },
}

// ============================================
// 通知分类映射
// ============================================

export const NOTIFICATION_CATEGORY_MAP: Record<string, { label: string; type: string }> = {
  task: { label: '任务', type: 'primary' },
  project: { label: '项目', type: 'success' },
  contribution: { label: '贡献', type: 'warning' },
  ip: { label: '知识产权', type: 'info' },
  sensitive: { label: '敏感资料', type: 'danger' },
  schedule: { label: '工时', type: 'info' },
  competition: { label: '比赛', type: 'success' },
  finance: { label: '经费', type: 'warning' },
  announcement: { label: '公告', type: 'warning' },
  system: { label: '系统', type: 'info' },
}

// ============================================
// 贡献记录模块常量映射
// ============================================

// 贡献类型映射
export const CONTRIBUTION_TYPE_MAP: Record<string, { label: string; tagType: string }> = {
  code: { label: '代码开发', tagType: '' },
  document: { label: '文档撰写', tagType: 'success' },
  design: { label: '设计制图', tagType: 'warning' },
  test: { label: '测试验证', tagType: 'info' },
  research: { label: '调研分析', tagType: '' },
  management: { label: '项目管理', tagType: 'danger' },
  presentation: { label: '答辩展示', tagType: 'success' },
  other: { label: '其他', tagType: 'info' },
}

// 贡献状态映射
export const CONTRIBUTION_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  pending: { label: '待审核', tagType: 'info' },
  approved: { label: '已通过', tagType: 'success' },
  rejected: { label: '已驳回', tagType: 'danger' },
}

// 排序状态映射
export const RANKING_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  draft: { label: '草稿', tagType: 'info' },
  generated: { label: '已生成', tagType: '' },
  confirmed: { label: '已确认', tagType: 'success' },
}

// 排序异议类型映射
export const OBJECTION_TYPE_MAP: Record<string, string> = {
  ranking: '排名异议',
  score: '得分异议',
  contribution: '贡献统计异议',
  other: '其他',
}

// 排序异议状态映射
export const OBJECTION_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  pending: { label: '待处理', tagType: 'info' },
  leader_reviewed: { label: '负责人已初审', tagType: '' },
  teacher_confirmed: { label: '老师已确认', tagType: 'success' },
  resolved: { label: '已解决', tagType: 'success' },
  rejected: { label: '已驳回', tagType: 'danger' },
}

// ============================================
// 敏感资料模块常量映射
// ============================================

// 敏感资料类型映射
export const SENSITIVE_DATA_TYPE_MAP: Record<string, { label: string; tagType: string }> = {
  phone: { label: '手机号', tagType: '' },
  id_card: { label: '身份证号', tagType: 'danger' },
  bank_card: { label: '银行卡号', tagType: 'warning' },
  address: { label: '家庭住址', tagType: 'info' },
  emergency_contact: { label: '紧急联系人', tagType: 'success' },
  other: { label: '其他', tagType: 'info' },
}

// 访问申请状态映射
export const ACCESS_REQUEST_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  pending: { label: '待审批', tagType: 'info' },
  approved: { label: '已批准', tagType: 'success' },
  rejected: { label: '已驳回', tagType: 'danger' },
  expired: { label: '已过期', tagType: 'info' },
  revoked: { label: '已撤销', tagType: 'warning' },
}

// ============================================
// 第三方集成模块常量映射
// ============================================

// 集成 Provider 映射
export const INTEGRATION_PROVIDER_MAP: Record<string, { label: string; tagType: string }> = {
  feishu: { label: '飞书', tagType: 'success' },
  wecom: { label: '企业微信', tagType: 'success' },
  qqbot: { label: 'QQ机器人', tagType: '' },
  webhook: { label: 'Webhook', tagType: 'warning' },
  email: { label: '邮件', tagType: 'info' },
}

// 集成日志状态映射
export const INTEGRATION_LOG_STATUS_MAP: Record<string, { label: string; tagType: string }> = {
  success: { label: '成功', tagType: 'success' },
  failed: { label: '失败', tagType: 'danger' },
  pending: { label: '发送中', tagType: 'info' },
}
