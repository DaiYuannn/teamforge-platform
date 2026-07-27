import { onMounted, onUnmounted } from 'vue'

export interface EChartsThemePalette {
  canvas: string
  surface: string
  surfaceSubtle: string
  surfaceStrong: string
  text: string
  textRegular: string
  textMuted: string
  textOnLight: string
  textOnFill: string
  border: string
  borderLight: string
  primary: string
  primaryFill: string
  primaryHover: string
  primarySoft: string
  primaryLight3: string
  primaryLight5: string
  primaryLight7: string
  primaryLight9: string
  success: string
  warning: string
  warningFill: string
  danger: string
  info: string
  infoFill: string
  ip: string
  sensitive: string
}

const FALLBACK_PALETTE: EChartsThemePalette = {
  canvas: '#f4f6f5',
  surface: '#ffffff',
  surfaceSubtle: '#f8faf9',
  surfaceStrong: '#eef2f0',
  text: '#18221f',
  textRegular: '#46524e',
  textMuted: '#65716d',
  textOnLight: '#18221f',
  textOnFill: '#ffffff',
  border: '#dce3e0',
  borderLight: '#e6ebe9',
  primary: '#176b73',
  primaryFill: '#176b73',
  primaryHover: '#12565c',
  primarySoft: '#e8f0f1',
  primaryLight3: '#5d979d',
  primaryLight5: '#8bb5b9',
  primaryLight7: '#b9d3d5',
  primaryLight9: '#e8f0f1',
  success: '#237a55',
  warning: '#a66116',
  warningFill: '#a66116',
  danger: '#b64242',
  info: '#4c6475',
  infoFill: '#4c6475',
  ip: '#76559b',
  sensitive: '#315c86',
}

export function readEChartsThemePalette(): EChartsThemePalette {
  if (typeof document === 'undefined' || typeof window === 'undefined') {
    return { ...FALLBACK_PALETTE }
  }

  const styles = window.getComputedStyle(document.documentElement)
  const read = (property: string, fallback: string): string =>
    styles.getPropertyValue(property).trim() || fallback

  return {
    canvas: read('--color-canvas', FALLBACK_PALETTE.canvas),
    surface: read('--color-surface', FALLBACK_PALETTE.surface),
    surfaceSubtle: read('--color-surface-subtle', FALLBACK_PALETTE.surfaceSubtle),
    surfaceStrong: read('--color-surface-strong', FALLBACK_PALETTE.surfaceStrong),
    text: read('--color-text', FALLBACK_PALETTE.text),
    textRegular: read('--color-text-regular', FALLBACK_PALETTE.textRegular),
    textMuted: read('--color-text-muted', FALLBACK_PALETTE.textMuted),
    textOnLight: read('--color-on-light', FALLBACK_PALETTE.textOnLight),
    textOnFill: read('--color-on-fill', FALLBACK_PALETTE.textOnFill),
    border: read('--color-border', FALLBACK_PALETTE.border),
    borderLight: read('--color-border-light', FALLBACK_PALETTE.borderLight),
    primary: read('--color-primary', FALLBACK_PALETTE.primary),
    primaryFill: read('--color-primary-fill', FALLBACK_PALETTE.primaryFill),
    primaryHover: read('--color-primary-hover', FALLBACK_PALETTE.primaryHover),
    primarySoft: read('--color-primary-soft', FALLBACK_PALETTE.primarySoft),
    primaryLight3: read('--el-color-primary-light-3', FALLBACK_PALETTE.primaryLight3),
    primaryLight5: read('--el-color-primary-light-5', FALLBACK_PALETTE.primaryLight5),
    primaryLight7: read('--el-color-primary-light-7', FALLBACK_PALETTE.primaryLight7),
    primaryLight9: read('--el-color-primary-light-9', FALLBACK_PALETTE.primaryLight9),
    success: read('--color-success', FALLBACK_PALETTE.success),
    warning: read('--color-warning', FALLBACK_PALETTE.warning),
    warningFill: read('--color-warning-fill', FALLBACK_PALETTE.warningFill),
    danger: read('--color-danger', FALLBACK_PALETTE.danger),
    info: read('--color-info', FALLBACK_PALETTE.info),
    infoFill: read('--color-info-fill', FALLBACK_PALETTE.infoFill),
    ip: read('--ip-color', FALLBACK_PALETTE.ip),
    sensitive: read('--sensitive-color', FALLBACK_PALETTE.sensitive),
  }
}

export function createEChartsTooltipStyle(palette: EChartsThemePalette) {
  return {
    backgroundColor: palette.surface,
    borderColor: palette.border,
    borderWidth: 1,
    textStyle: { color: palette.text, fontSize: 12 },
  }
}

export function useEChartsTheme(onThemeChange: () => void): void {
  let observer: MutationObserver | null = null

  onMounted(() => {
    if (typeof document === 'undefined' || typeof MutationObserver === 'undefined') return
    observer = new MutationObserver(() => onThemeChange())
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })
  })

  onUnmounted(() => {
    observer?.disconnect()
    observer = null
  })
}
