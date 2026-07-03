# Team Cockpit 主题 Token
# 团队驾驶舱 — 科技蓝/青蓝系 · Element Plus 兼容

> 主题类型：自定义主题（基于项目需求生成）
> 适用场景：团队项目管理平台
> 技术栈：Vue 3 + TypeScript + Element Plus + SCSS
> 生成日期：2026-07-02

---

## 主题概览

| 维度 | 值 |
|------|-----|
| 主题名 | Team Cockpit（团队驾驶舱） |
| 主色调 | 科技蓝 #409EFF → 青蓝 #36CFC9 渐变 |
| 气质 | 清爽 · 可信 · 透明 · 年轻 · 科技感 · 有秩序 |
| 字体 | 系统字体栈（-apple-system / PingFang SC / Microsoft YaHei） |
| 设计语言 | 轻拟物 + 扁平混合，微阴影 + 渐变点缀 |

---

## 色板总览

### 主色系（Primary — 科技蓝）

| Token | Hex | 用途 |
|-------|-----|------|
| `$primary-color` | `#409EFF` | 主色（保留，与 Element Plus 一致） |
| `$primary-dark` | `#337ECC` | hover / active 加深 |
| `$primary-light` | `#66B1FF` | disabled / 浅色背景 |
| `$primary-lighter` | `#ECF5FF` | 选中行背景 / 浅底标签 |
| `$primary-rgb` | `64, 158, 255` | rgba 场景（阴影/遮罩） |

### 辅助色系（Functional）

| Token | Hex | 用途 |
|-------|-----|------|
| `$success-color` | `#67C23A` | 成功（保留） |
| `$success-light` | `#E1F3D8` | 成功浅底 |
| `$warning-color` | `#E6A23C` | 警告（保留） |
| `$warning-light` | `#FAECD8` | 警告浅底 |
| `$danger-color` | `#F56C6C` | 危险（保留） |
| `$danger-light` | `#FDE2E2` | 危险浅底 |
| `$info-color` | `#909399` | 信息（保留） |
| `$info-light` | `#E9E9EB` | 信息浅底 |

### 模块专属色（Module Accent）

| Token | Hex | 用途 |
|-------|-----|------|
| `$ip-color` | `#7C3AED` | 知识产权 — 紫色，成果与责任追踪 |
| `$ip-light` | `#F3EEFF` | 知识产权浅底 |
| `$sensitive-color` | `#1E40AF` | 敏感资料 — 安全蓝，审批与受控访问 |
| `$sensitive-light` | `#DBEAFE` | 敏感资料浅底 |
| `$finance-color` | `#059669` | 经费 — 深绿，公开透明 |
| `$finance-light` | `#D1FAE5` | 经费浅底 |

### 中性色系（Neutral）

| Token | Hex | 用途 |
|-------|-----|------|
| `$text-primary` | `#303133` | 标题/正文主色（保留） |
| `$text-regular` | `#606266` | 常规文字（保留） |
| `$text-secondary` | `#909399` | 次要文字（保留） |
| `$text-placeholder` | `#C0C4CC` | 占位文字（保留） |
| `$border-color` | `#DCDFE6` | 边框（保留） |
| `$border-color-light` | `#E4E7ED` | 浅边框（保留） |
| `$border-color-lighter` | `#EBEEF5` | 更浅边框（保留） |
| `$bg-color` | `#F5F7FA` | 页面背景（保留） |
| `$bg-color-light` | `#FAFAFA` | 卡片浅背景（保留） |
| `$bg-color-dark` | `#E9ECEF` | 深背景（保留） |
| `$bg-card` | `#FFFFFF` | 卡片白色背景 |
| `$bg-table-header` | `#F5F7FA` | 表格表头背景 |
| `$bg-table-stripe` | `#FAFAFA` | 表格斑马纹行 |

### 侧边栏色系（Sidebar — 保留深色导航）

| Token | Hex | 用途 |
|-------|-----|------|
| `$sidebar-bg` | `#304156` | 侧边栏背景（保留） |
| `$sidebar-bg-dark` | `#2B3A4D` | Logo 区更深背景 |
| `$sidebar-text` | `#BFCBD9` | 菜单文字（保留） |
| `$sidebar-active-text` | `#409EFF` | 激活菜单文字（保留） |
| `$sidebar-hover-bg` | `#263445` | 菜单 hover 背景 |

---

## 渐变色系（Gradient — Dashboard 数据卡片）

| Token | 值 | 用途 |
|-------|-----|------|
| `$gradient-brand` | `linear-gradient(135deg, #409EFF 0%, #36CFC9 100%)` | 品牌渐变（登录/Logo） |
| `$gradient-blue` | `linear-gradient(135deg, #409EFF, #36CFC9)` | 项目总数卡片 |
| `$gradient-green` | `linear-gradient(135deg, #67C23A, #95DE64)` | 进行中卡片 |
| `$gradient-orange` | `linear-gradient(135deg, #E6A23C, #FFD591)` | 待办卡片 |
| `$gradient-red` | `linear-gradient(135deg, #F56C6C, #FF7875)` | 逾期卡片 |
| `$gradient-purple` | `linear-gradient(135deg, #7C3AED, #C39BD3)` | 经费卡片 |
| `$gradient-indigo` | `linear-gradient(135deg, #1E40AF, #3B82F6)` | 敏感资料卡片 |
| `$gradient-work-available` | `linear-gradient(135deg, #E8F5E9, #C8E6C9)` | 可投入工作状态 |
| `$gradient-work-saturated` | `linear-gradient(135deg, #FFF3E0, #FFE0B2)` | 饱和工作状态 |
| `$gradient-work-leave` | `linear-gradient(135deg, #FCE4EC, #F8BBD0)` | 请假工作状态 |

---

## 圆角体系（Border Radius）

| Token | 值 | 用途 |
|-------|-----|------|
| `$radius-xs` | `4px` | 标签 / 小按钮 / 输入框 |
| `$radius-sm` | `6px` | 按钮 / 小卡片 |
| `$radius-md` | `8px` | PageHeader / 紧凑卡片（保留原名 `$border-radius`） |
| `$radius-lg` | `12px` | 大卡片 / 弹窗 |
| `$radius-xl` | `16px` | 登录容器 / 特殊大卡片（保留原名 `$border-radius-large`） |
| `$radius-pill` | `999px` | 胶囊标签 / 头像 |
| `$radius-circle` | `50%` | 圆形头像 |

---

## 阴影体系（Box Shadow）

| Token | 值 | 用途 |
|-------|-----|------|
| `$shadow-xs` | `0 1px 2px rgba(0, 0, 0, 0.04)` | 微阴影 / 细边框替代 |
| `$shadow-sm` | `0 2px 8px rgba(0, 0, 0, 0.06)` | 卡片默认（保留原名 `$box-shadow-light`） |
| `$shadow-md` | `0 2px 12px rgba(0, 0, 0, 0.08)` | 卡片悬停前（保留原名 `$box-shadow`） |
| `$shadow-lg` | `0 4px 16px rgba(0, 0, 0, 0.12)` | 卡片 hover / 浮层 |
| `$shadow-xl` | `0 8px 32px rgba(0, 0, 0, 0.16)` | 弹窗 / 大浮层 |
| `$shadow-primary` | `0 4px 12px rgba(64, 158, 255, 0.15)` | 主色卡片 hover 蓝色阴影 |
| `$shadow-dark` | `0 4px 20px rgba(0, 0, 0, 0.15)` | 深阴影（保留原名 `$box-shadow-dark`） |

---

## 间距体系（Spacing — 保留现有 + 补充）

| Token | 值 | 用途 |
|-------|-----|------|
| `$spacing-xs` | `4px` | 极小间距（保留原名 `$spacing-mini`） |
| `$spacing-sm` | `8px` | 小间距（保留原名 `$spacing-small`） |
| `$spacing-md` | `12px` | 中间距（新增） |
| `$spacing-base` | `16px` | 基准间距（保留原名 `$spacing-medium`） |
| `$spacing-lg` | `20px` | 大间距（新增） |
| `$spacing-xl` | `24px` | 超大间距（保留原名 `$spacing-large`） |
| `$spacing-2xl` | `32px` | 区块间距（保留原名 `$spacing-xl`） |
| `$page-padding` | `16px` | 页面内边距 |
| `$page-padding-mobile` | `12px` | 移动端页面内边距 |
| `$card-padding` | `20px` | 卡片内边距 |
| `$card-padding-sm` | `16px` | 紧凑卡片内边距 |
| `$card-gap` | `16px` | 卡片间距（el-row gutter） |

---

## 字体体系（Typography）

| Token | 值 | 用途 |
|-------|-----|------|
| `$font-family` | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif` | 全局字体 |
| `$font-family-mono` | `'Cascadia Code', 'Fira Code', 'Consolas', monospace` | 代码/明文 |
| `$font-size-xs` | `12px` | 标签 / 辅助 |
| `$font-size-sm` | `13px` | 副标题 / 表格辅助 |
| `$font-size-base` | `14px` | 正文（保留） |
| `$font-size-lg` | `16px` | 区块标题 |
| `$font-size-xl` | `18px` | 页面小标题 |
| `$font-size-2xl` | `20px` | 页面标题（PageHeader） |
| `$font-size-3xl` | `22px` | 统计数字 |
| `$font-size-4xl` | `28px` | 大号统计 |
| `$font-weight-light` | `300` | 辅助 |
| `$font-weight-regular` | `400` | 正文 |
| `$font-weight-medium` | `500` | 标签 / 强调 |
| `$font-weight-semibold` | `600` | 标题 |
| `$font-weight-bold` | `700` | 统计数字 |

---

## 过渡动画（Transition）

| Token | 值 | 用途 |
|-------|-----|------|
| `$transition-fast` | `0.15s ease` | 快速反馈（按钮 hover） |
| `$transition-base` | `0.2s ease` | 标准过渡（卡片 hover） |
| `$transition-slow` | `0.3s ease` | 慢速过渡（侧边栏折叠） |
| `$transition-properties-card` | `transform, box-shadow` | 卡片过渡属性（不用 `all`） |

---

## z-index 层级（保留现有）

| Token | 值 | 用途 |
|-------|-----|------|
| `$z-index-header` | `1000` | 顶部栏 |
| `$z-index-sidebar` | `1001` | 侧边栏 |
| `$z-index-modal` | `2000` | 弹窗 |
| `$z-index-popover` | `3000` | 浮层 |
| `$z-index-dropdown` | `2500` | 下拉菜单（新增） |

---

## 移动端断点（保留）

| Token | 值 |
|-------|-----|
| `$breakpoint-mobile` | `768px` |
