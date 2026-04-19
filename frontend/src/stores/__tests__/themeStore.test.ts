import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore } from '../themeStore'

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

describe('themeStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  it('defaults to light theme when no stored preference', () => {
    const store = useThemeStore()
    expect(store.mode).toBe('light')
    expect(store.isDark).toBe(false)
  })

  it('restores dark theme from localStorage', () => {
    localStorageMock.getItem.mockReturnValueOnce('dark')
    const store = useThemeStore()
    expect(store.mode).toBe('dark')
    expect(store.isDark).toBe(true)
  })

  it('setTheme updates mode and persists to localStorage', () => {
    const store = useThemeStore()
    store.setTheme('anchor')
    expect(store.mode).toBe('anchor')
    expect(store.isDark).toBe(true)
    expect(store.isAnchor).toBe(true)
    expect(localStorageMock.setItem).toHaveBeenCalledWith('aitext-theme-mode', 'anchor')
  })

  it('effectiveTheme returns dark when isDark is true', () => {
    const store = useThemeStore()
    store.setTheme('dark')
    expect(store.effectiveTheme).toBe('dark')
  })

  it('effectiveTheme returns light when isDark is false', () => {
    const store = useThemeStore()
    store.setTheme('light')
    expect(store.effectiveTheme).toBe('light')
  })
})
