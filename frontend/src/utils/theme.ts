export const PRIMARY_COLOR_OPTIONS = [
  { value: '#176b73', label: '青色' },
  { value: '#2f6f4e', label: '绿色' },
  { value: '#6f5a86', label: '紫色' },
  { value: '#9a6238', label: '棕色' },
] as const

export type PrimaryColor = string

export const DEFAULT_PRIMARY_COLOR: PrimaryColor = PRIMARY_COLOR_OPTIONS[0].value

const legacyPrimaryColorMap: Record<string, string> = {
  blue: '#176b73',
  green: '#2f6f4e',
  purple: '#6f5a86',
  orange: '#9a6238',
}

const HEX_COLOR_PATTERN = /^#[0-9a-f]{6}$/
export const MIN_PRIMARY_COLOR_CONTRAST = 4.5

function parseHexColor(color: string): [number, number, number] {
  return [
    Number.parseInt(color.slice(1, 3), 16),
    Number.parseInt(color.slice(3, 5), 16),
    Number.parseInt(color.slice(5, 7), 16),
  ]
}

function resolveHexColor(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const normalized = value.trim().toLowerCase()
  const compatibleValue = legacyPrimaryColorMap[normalized] || normalized
  return HEX_COLOR_PATTERN.test(compatibleValue) ? compatibleValue : null
}

function relativeLuminance(color: string): number {
  const [red, green, blue] = parseHexColor(color).map((channel) => {
    const normalized = channel / 255
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

/** 主色按钮使用白色文字，需达到 WCAG AA 普通文本对比度。 */
export function primaryColorContrast(value: unknown): number {
  const color = resolveHexColor(value)
  if (!color) return 0
  return 1.05 / (relativeLuminance(color) + 0.05)
}

export function isReadablePrimaryColor(value: unknown): boolean {
  return primaryColorContrast(value) >= MIN_PRIMARY_COLOR_CONTRAST
}

function toHex(value: number): string {
  return Math.round(value).toString(16).padStart(2, '0')
}

function mixHexColor(color: string, target: '#ffffff' | '#000000', weight: number): string {
  const sourceRgb = parseHexColor(color)
  const targetRgb = parseHexColor(target)
  return `#${sourceRgb
    .map((channel, index) => toHex(channel * (1 - weight) + targetRgb[index] * weight))
    .join('')}`
}

export function normalizePrimaryColor(value: unknown): PrimaryColor {
  const color = resolveHexColor(value)
  return color && isReadablePrimaryColor(color) ? color : DEFAULT_PRIMARY_COLOR
}

export function getPrimaryColorVariables(value: unknown): Record<string, string> {
  const color = normalizePrimaryColor(value)
  const rgb = parseHexColor(color).join(', ')
  const lightColors = Array.from({ length: 9 }, (_, index) =>
    mixHexColor(color, '#ffffff', (index + 1) / 10)
  )
  const darkColor = mixHexColor(color, '#000000', 0.2)

  const variables: Record<string, string> = {
    '--color-primary': color,
    '--color-primary-hover': darkColor,
    '--color-primary-soft': lightColors[8],
    '--primary-color': color,
    '--primary-dark': darkColor,
    '--primary-light': lightColors[2],
    '--primary-lighter': lightColors[8],
    '--primary-rgb': rgb,
    '--sidebar-hover-bg': lightColors[8],
    '--shadow-primary': `0 6px 16px rgba(${rgb}, 0.18)`,
    '--focus-ring': `rgba(${rgb}, 0.55)`,
    '--el-color-primary': color,
    '--el-color-primary-rgb': rgb,
    '--el-color-primary-dark-2': darkColor,
  }

  lightColors.forEach((lightColor, index) => {
    variables[`--el-color-primary-light-${index + 1}`] = lightColor
  })

  return variables
}

export function applyPrimaryColor(value: unknown): PrimaryColor {
  const color = normalizePrimaryColor(value)
  if (typeof document === 'undefined') return color

  const rootStyle = document.documentElement.style
  Object.entries(getPrimaryColorVariables(color)).forEach(([property, propertyValue]) => {
    rootStyle.setProperty(property, propertyValue)
  })
  return color
}

export function resetPrimaryColor(): PrimaryColor {
  return applyPrimaryColor(DEFAULT_PRIMARY_COLOR)
}
