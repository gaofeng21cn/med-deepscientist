// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ConnectorSettingsForm } from '@/components/settings/ConnectorSettingsForm'
import { ToastProvider } from '@/components/ui/toast'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

function clickButton(label: string) {
  const button = Array.from(document.querySelectorAll('button')).find((item) => item.textContent?.includes(label))
  expect(button).toBeTruthy()
  act(() => {
    button?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  })
}

function changeInputByPlaceholder(placeholder: string, value: string) {
  const input = document.querySelector<HTMLInputElement>(`input[placeholder="${placeholder}"]`)
  expect(input).toBeTruthy()
  const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
  act(() => {
    valueSetter?.call(input, value)
    input!.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }))
    input!.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }))
  })
}

describe('ConnectorSettingsForm', () => {
  let root: Root | null = null
  let container: HTMLDivElement | null = null

  afterEach(() => {
    if (root) {
      act(() => {
        root?.unmount()
      })
    }
    root = null
    container?.remove()
    container = null
    document.body.innerHTML = ''
  })

  it('saves a new generic connector profile with the full connector draft before continuing', async () => {
    const onSave = vi.fn().mockResolvedValue(true)

    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)

    await act(async () => {
      root?.render(
        <MemoryRouter>
          <ToastProvider>
            <ConnectorSettingsForm
              locale="en"
              value={{ _routing: { artifact_delivery_policy: 'fanout_all' } }}
              connectors={[]}
              quests={[]}
              saving={false}
              isDirty={false}
              visibleConnectorNames={['telegram']}
              selectedConnectorName="telegram"
              onChange={vi.fn()}
              onSave={onSave}
              onRefresh={vi.fn()}
              onDeleteProfile={vi.fn()}
              onManageProfileBinding={vi.fn()}
              onSelectConnector={vi.fn()}
              onBackToConnectorCatalog={vi.fn()}
            />
          </ToastProvider>
        </MemoryRouter>
      )
    })

    clickButton('Add connector')
    clickButton('Continue')
    changeInputByPlaceholder('123456:ABCDEF...', 'telegram-token-1')
    clickButton('Save and continue')

    await act(async () => {
      await Promise.resolve()
    })

    expect(onSave).toHaveBeenCalledTimes(1)
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        _routing: { artifact_delivery_policy: 'fanout_all' },
        telegram: expect.objectContaining({
          enabled: true,
          profiles: [
            expect.objectContaining({
              enabled: true,
              bot_token: 'telegram-token-1',
              transport: 'polling',
            }),
          ],
        }),
      })
    )
    expect(document.body.textContent).toContain('Use the runtime-discovered target whenever possible.')
  })
})
