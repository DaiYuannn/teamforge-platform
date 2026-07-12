import { computed, type Ref } from 'vue'
import { useDevice } from '@/composables/useDevice'

/**
 * 卡片字段类型
 */
export type CardFieldType = 'text' | 'tag' | 'date'

/**
 * 卡片字段定义
 */
export interface CardField {
  /** 字段标签 */
  label: string
  /** 字段值 */
  value: string | number
  /** 字段展示类型 */
  type?: CardFieldType
  /** 当 type 为 tag 时的标签类型（对应 el-tag type） */
  tagType?: string
  /** 当 type 为 tag 时的颜色（可选） */
  color?: string
}

/**
 * 卡片数据项
 */
export interface CardItem<T> {
  /** 原始数据 */
  raw: T
  /** 卡片标题 */
  title: string
  /** 卡片副标题 */
  subtitle?: string
  /** 卡片头像（可选） */
  avatar?: string
  /** 字段列表 */
  fields: CardField[]
}

/**
 * useMobileList 配置项
 */
export interface UseMobileListOptions<T> {
  /** 卡片标题生成函数 */
  title: (item: T) => string
  /** 卡片副标题生成函数（可选） */
  subtitle?: (item: T) => string
  /** 卡片头像生成函数（可选） */
  avatar?: (item: T) => string | undefined
  /** 字段列表生成函数 */
  fields: (item: T) => CardField[]
}

/**
 * 移动端列表优化 Composable
 *
 * - isCardView：移动端为 true（显示卡片列表），PC 端为 false（显示表格）
 * - cardData：将表格数据转换为卡片格式
 *
 * @param source 原始数据源（Ref）
 * @param options 卡片字段配置
 */
export function useMobileList<T>(
  source: Ref<T[]>,
  options: UseMobileListOptions<T>
) {
  const { isMobile } = useDevice()

  /** 是否使用卡片视图（移动端为 true） */
  const isCardView = computed<boolean>(() => isMobile.value)

  /** 转换后的卡片数据 */
  const cardData = computed<CardItem<T>[]>(() =>
    source.value.map((item) => ({
      raw: item,
      title: options.title(item),
      subtitle: options.subtitle?.(item),
      avatar: options.avatar?.(item),
      fields: options.fields(item),
    }))
  )

  return {
    isCardView,
    cardData,
  }
}
