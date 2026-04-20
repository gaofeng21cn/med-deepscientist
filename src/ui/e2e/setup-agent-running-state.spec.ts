import { expect, test, type Page } from '@playwright/test'

function jsonResponse(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

function appRoute(path: string) {
  const baseUrl = process.env.E2E_BASE_URL || ''
  return baseUrl.includes('/ui') ? `/ui${path}` : path
}

async function installStartSetupRoutes(
  page: Page,
  options: {
    initialAssistantPatch?: { title?: string; goal?: string } | null
  } = {}
) {
  const benchEntry = {
    id: 'bench-001',
    name: 'Bench Alpha',
    one_line: 'A benchmark entry for start-setup verification.',
    task_description: 'Verify setup-assist flows.',
    capability_tags: ['verification'],
    track_fit: ['agentic'],
    requires_execution: false,
    paper: {
      title: 'Bench Alpha Paper',
    },
  }
  const suggestedForm = {
    title: '',
    goal: '',
  }
  const setupQuestId = 'setup-quest-001'

  await page.addInitScript(() => {
    window.localStorage.setItem(
      'ds:onboarding:v1',
      JSON.stringify({
        firstRunHandled: true,
        completed: true,
        neverRemind: true,
        language: 'en',
      })
    )
    ;(window as typeof window & { __DEEPSCIENTIST_RUNTIME__?: unknown }).__DEEPSCIENTIST_RUNTIME__ = {
      surface: 'quest',
      auth: {
        enabled: false,
        tokenQueryParam: 'token',
        storageKey: 'ds_local_auth_token',
      },
    }
  })

  await page.route('**/api/connectors/availability', async (route) => {
    await route.fulfill(
      jsonResponse({
        has_enabled_external_connector: false,
        has_bound_external_connector: false,
        should_recommend_binding: false,
        should_prompt_binding: false,
        preferred_connector_name: null,
        preferred_conversation_id: null,
        available_connectors: [],
      })
    )
  })

  await page.route('**/api/system/update', async (route) => {
    await route.fulfill(
      jsonResponse({
        ok: true,
        current_version: '1.0.0',
        latest_version: '1.0.0',
        update_available: false,
        prompt_recommended: false,
        busy: false,
      })
    )
  })

  await page.route('**/api/auth/token', async (route) => {
    await route.fulfill(jsonResponse({ token: null }))
  })

  await page.route('**/api/connectors', async (route) => {
    await route.fulfill(jsonResponse([]))
  })

  await page.route('**/api/baselines', async (route) => {
    await route.fulfill(jsonResponse([]))
  })

  await page.route('**/api/quest-id/next', async (route) => {
    await route.fulfill(jsonResponse({ quest_id: '002' }))
  })

  await page.route('**/api/benchstore/entries', async (route) => {
    await route.fulfill(
      jsonResponse({
        ok: true,
        total: 1,
        items: [benchEntry],
      })
    )
  })

  await page.route('**/api/benchstore/entries/bench-001/setup-packet', async (route) => {
    await route.fulfill(
      jsonResponse({
        ok: true,
        entry_id: benchEntry.id,
        setup_packet: {
          entry_id: benchEntry.id,
          project_title: 'Bench Alpha',
          assistant_label: 'SetupAgent',
          suggested_form: suggestedForm,
          launch_payload: {
            startup_contract: {
              start_setup_session: {
                source: 'benchstore',
                locale: 'en',
              },
            },
          },
        },
      })
    )
  })

  await page.route('**/api/quests', async (route) => {
    const method = route.request().method().toUpperCase()
    if (method === 'GET') {
      await route.fulfill(jsonResponse([]))
      return
    }

    const payload = route.request().postDataJSON() as Record<string, unknown>
    const title = String(payload?.title || '')
    if (title.includes('Setup')) {
      await route.fulfill(
        jsonResponse({
          ok: true,
          snapshot: {
            quest_id: setupQuestId,
            title,
            status: 'idle',
            runtime_status: 'idle',
            active_anchor: 'idea',
            branch: 'main',
            updated_at: '2026-04-20T10:00:00Z',
          },
        })
      )
      return
    }

    await route.fulfill(
      jsonResponse({
        ok: true,
        snapshot: {
          quest_id: 'quest-002',
          title: String(payload?.title || 'quest-002'),
          status: 'idle',
          runtime_status: 'idle',
          active_anchor: 'idea',
          branch: 'main',
          updated_at: '2026-04-20T10:00:00Z',
        },
      })
    )
  })

  await page.route(`**/api/quests/${setupQuestId}`, async (route) => {
    if (route.request().method().toUpperCase() !== 'DELETE') {
      await route.fallback()
      return
    }
    await route.fulfill(
      jsonResponse({
        ok: true,
        quest_id: setupQuestId,
        deleted: true,
      })
    )
  })

  await page.route(`**/api/quests/${setupQuestId}/session`, async (route) => {
    await route.fulfill(
      jsonResponse({
        ok: true,
        quest_id: setupQuestId,
        snapshot: {
          quest_id: setupQuestId,
          title: 'Bench Alpha Setup',
          status: 'idle',
          runtime_status: 'idle',
          workspace_mode: 'quest',
          active_anchor: 'idea',
          branch: 'main',
          head: 'abc1234',
          updated_at: '2026-04-20T10:00:00Z',
          counts: {
            bash_running_count: 0,
            artifacts: 0,
            memory_cards: 0,
          },
          summary: {
            status_line: 'Ready for setup patch',
          },
        },
        acp_session: {
          session_id: `quest:${setupQuestId}`,
          slash_commands: [],
          meta: {
            default_reply_interaction_id: null,
          },
        },
      })
    )
  })

  await page.route(`**/api/quests/${setupQuestId}/events**`, async (route) => {
    const url = new URL(route.request().url())
    const accept = String(route.request().headers().accept || '')
    const streamRequested =
      url.searchParams.get('stream') === '1' || accept.includes('text/event-stream')
    if (streamRequested) {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'event: cursor\ndata: {"cursor":0}\n\n',
      })
      return
    }

    const acpUpdates =
      options.initialAssistantPatch
        ? [
            {
              method: 'session.update',
              params: {
                sessionId: `quest:${setupQuestId}`,
                update: {
                  kind: 'message',
                  message: {
                    role: 'assistant',
                    stream: false,
                    content: `\`\`\`start_setup_patch\n${JSON.stringify(options.initialAssistantPatch, null, 2)}\n\`\`\``,
                  },
                  event_id: 'patch-msg-001',
                  created_at: '2026-04-20T10:00:00Z',
                },
              },
            },
          ]
        : []

    await route.fulfill(
      jsonResponse({
        cursor: 0,
        oldest_cursor: 0,
        newest_cursor: 0,
        has_more: false,
        acp_updates: acpUpdates,
      })
    )
  })
}

async function openBenchSetupDialog(page: Page) {
  await page.goto(appRoute('/'))
  await page.getByRole('button', { name: 'BenchStore' }).click()
  await page.getByRole('button', { name: 'Start SetupAgent' }).click()
  await expect(page.locator('[data-onboarding-id="start-research-dialog"]')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText('SetupAgent').first()).toBeVisible()
}

function titleInput(page: Page) {
  return page.getByPlaceholder('A short human-readable research title')
}

function goalInput(page: Page) {
  return page.getByPlaceholder(
    'State the core scientific question, target paper, hypothesis, and what success would look like.'
  )
}

test.describe('setup agent running state', () => {
  test('applies ds:start-setup:patch events and unlocks Create project', async ({ page }) => {
    await installStartSetupRoutes(page)
    await openBenchSetupDialog(page)

    const createButton = page.getByRole('button', { name: 'Create project' })
    await expect(createButton).toBeDisabled()

    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent('ds:start-setup:patch', {
          detail: {
            patch: {
              title: 'Bench Alpha kickoff',
              goal: 'Evaluate Bench Alpha and propose the strongest justified first direction.',
            },
          },
        })
      )
    })

    await expect(titleInput(page)).toHaveValue('Bench Alpha kickoff')
    await expect(goalInput(page)).toHaveValue(
      'Evaluate Bench Alpha and propose the strongest justified first direction.'
    )
    await expect(createButton).toBeEnabled()
  })

  test('applies assistant fenced start_setup_patch blocks without locking Create project', async ({ page }) => {
    await installStartSetupRoutes(page, {
      initialAssistantPatch: {
        title: 'Bench Alpha replay',
        goal: 'Recover a trustworthy benchmark baseline before choosing the first experiment.',
      },
    })
    await openBenchSetupDialog(page)

    await expect(titleInput(page)).toHaveValue('Bench Alpha replay')
    await expect(goalInput(page)).toHaveValue(
      'Recover a trustworthy benchmark baseline before choosing the first experiment.'
    )
    await expect(page.getByRole('button', { name: 'Create project' })).toBeEnabled()
  })
})
