import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkbenchRefreshStore } from '../workbenchRefreshStore'

describe('workbenchRefreshStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initial tick values are 0', () => {
    const store = useWorkbenchRefreshStore()
    expect(store.foreshadowTick).toBe(0)
    expect(store.chroniclesTick).toBe(0)
    expect(store.deskTick).toBe(0)
  })

  it('bumpForeshadowLedger increments foreshadowTick', () => {
    const store = useWorkbenchRefreshStore()
    store.bumpForeshadowLedger()
    expect(store.foreshadowTick).toBe(1)
    store.bumpForeshadowLedger()
    expect(store.foreshadowTick).toBe(2)
  })

  it('bumpChronicles increments chroniclesTick', () => {
    const store = useWorkbenchRefreshStore()
    store.bumpChronicles()
    expect(store.chroniclesTick).toBe(1)
  })

  it('bumpDesk increments deskTick', () => {
    const store = useWorkbenchRefreshStore()
    store.bumpDesk()
    expect(store.deskTick).toBe(1)
  })

  it('bumpAfterChapterDeskChange bumps all three counters', () => {
    const store = useWorkbenchRefreshStore()
    store.bumpAfterChapterDeskChange()
    expect(store.foreshadowTick).toBe(1)
    expect(store.chroniclesTick).toBe(1)
    expect(store.deskTick).toBe(1)
  })
})
