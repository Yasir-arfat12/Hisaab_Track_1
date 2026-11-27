import { http, HttpResponse } from 'msw';
import {
  DEMO_CREDITS,
  DEMO_DASHBOARD,
  DEMO_DRAFT,
  DEMO_MERCHANT,
  DEMO_NEXT_STEP,
  DEMO_PROMISES,
  DEMO_PROMISE_DETAIL,
  DEMO_USER,
} from '../seed/demoData';

const BASE = '*/api/v1';

export const handlers = [
  http.get(`${BASE}/health`, () =>
    HttpResponse.json({
      data: {
        status: 'ok',
        version: '1.0.0',
        checks: { database: 'ok', llm: 'ok' },
        uptime_seconds: 86400,
      },
      error: null,
    }),
  ),

  http.get(`${BASE}/auth/google/start`, () =>
    HttpResponse.json({
      data: {
        redirect_url:
          'https://accounts.google.com/o/oauth2/v2/auth?client_id=mock&scope=gmail.readonly&state=mock',
      },
      error: null,
    }),
  ),

  http.post(`${BASE}/auth/demo`, () =>
    HttpResponse.json({
      data: {
        user_id: DEMO_USER.user_id,
        email: DEMO_USER.email,
        display_name: DEMO_USER.display_name,
        is_demo: true,
        seed_scenario: 'v1_standard_8_promises',
      },
      error: null,
    }),
  ),

  http.post(`${BASE}/auth/logout`, () =>
    HttpResponse.json({ data: { logged_out: true }, error: null }),
  ),

  http.get(`${BASE}/auth/me`, () => HttpResponse.json({ data: DEMO_USER, error: null })),

  http.delete(`${BASE}/auth/me`, () =>
    HttpResponse.json({ data: { deleted: true }, error: null }),
  ),

  http.get(`${BASE}/gmail/status`, () =>
    HttpResponse.json({
      data: {
        connected: false,
        email: null,
        last_synced_at: null,
        sync_status: 'idle',
        active_job_id: null,
        emails_processed: 0,
      },
      error: null,
    }),
  ),

  http.post(`${BASE}/gmail/sync`, () =>
    HttpResponse.json({
      data: {
        job_id: 'aabb1234-5678-90ab-cdef-012345678901',
        status: 'queued',
        enqueued_at: '2026-11-26T07:00:00Z',
      },
      error: null,
    }),
  ),

  http.post(`${BASE}/gmail/disconnect`, () =>
    HttpResponse.json({ data: { disconnected: true, emails_purged: 0 }, error: null }),
  ),

  http.get(`${BASE}/jobs/:jobId`, ({ params }) =>
    HttpResponse.json({
      data: {
        job_id: String(params.jobId),
        type: 'gmail_sync',
        status: 'completed',
        progress_pct: 100,
        created_at: '2026-11-26T07:00:00Z',
        completed_at: '2026-11-26T07:01:00Z',
        result: { promises_extracted: 8 },
        error_message: null,
      },
      error: null,
    }),
  ),

  http.get(`${BASE}/dashboard/summary`, () =>
    HttpResponse.json({ data: DEMO_DASHBOARD, error: null }),
  ),

  http.get(`${BASE}/promises`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const category = url.searchParams.get('category');
    const items = DEMO_PROMISES.filter(
      (p) => (!status || p.status === status) && (!category || p.category === category),
    );
    return HttpResponse.json({
      data: {
        items,
        next_cursor: null,
        prev_cursor: null,
        limit: 20,
      },
      error: null,
    });
  }),

  http.get(`${BASE}/promises/:promiseId`, ({ params }) => {
    const found = DEMO_PROMISES.find((p) => p.promise_id === params.promiseId);
    if (!found) {
      return HttpResponse.json(
        {
          data: null,
          error: {
            code: 'PROMISE_NOT_FOUND',
            message: 'The given promise_id does not exist',
            details: {},
          },
        },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      data: {
        ...DEMO_PROMISE_DETAIL,
        ...found,
      },
      error: null,
    });
  }),

  http.patch(`${BASE}/promises/:promiseId`, async ({ params, request }) => {
    const found = DEMO_PROMISES.find((p) => p.promise_id === params.promiseId);
    if (!found) {
      return HttpResponse.json(
        {
          data: null,
          error: { code: 'PROMISE_NOT_FOUND', message: 'Promise not found', details: {} },
        },
        { status: 404 },
      );
    }
    const body = (await request.json()) as { status?: 'dismissed'; user_note?: string };
    return HttpResponse.json({
      data: {
        ...found,
        status: body.status ?? found.status,
      },
      error: null,
    });
  }),

  http.get(`${BASE}/credits`, () =>
    HttpResponse.json({
      data: { items: DEMO_CREDITS, next_cursor: null, prev_cursor: null, limit: 20 },
      error: null,
    }),
  ),

  http.post(`${BASE}/credits/upload`, () =>
    HttpResponse.json({
      data: {
        job_id: 'ccdd5678-9012-34ef-ab56-78901234cdef',
        rows_detected: 3,
        status: 'queued',
      },
      error: null,
    }),
  ),

  http.post(`${BASE}/verify/:promiseId`, ({ params }) =>
    HttpResponse.json({
      data: {
        promise_id: String(params.promiseId),
        previous_status: 'pending',
        new_status: 'kept',
        matched_credit_id: 'cccc0001-0000-0000-0000-000000000001',
        amount_paise_expected: 249900,
        amount_paise_received: 249900,
        verified_at: '2026-11-26T07:10:00Z',
      },
      error: null,
    }),
  ),

  http.get(`${BASE}/escalation/:promiseId/next-step`, ({ params }) =>
    HttpResponse.json({
      data: { ...DEMO_NEXT_STEP, promise_id: String(params.promiseId) },
      error: null,
    }),
  ),

  http.post(`${BASE}/escalation/:promiseId/draft`, () =>
    HttpResponse.json({ data: DEMO_DRAFT, error: null }),
  ),

  http.post(`${BASE}/dossier/:promiseId/generate`, () =>
    HttpResponse.json({
      data: {
        job_id: 'ddee9012-3456-78ab-cdef-901234567890',
        status: 'queued',
        enqueued_at: '2026-11-26T07:20:00Z',
      },
      error: null,
    }),
  ),

  http.get(`${BASE}/merchants/:merchantId/record`, ({ params }) =>
    HttpResponse.json({
      data: { ...DEMO_MERCHANT, merchant_id: String(params.merchantId) },
      error: null,
    }),
  ),

  http.post(`${BASE}/demo/simulate`, async ({ request }) => {
    const body = (await request.json()) as { scenario: string };
    return HttpResponse.json({
      data: {
        scenario: body.scenario,
        affected_promise_id: DEMO_PROMISES[3].promise_id,
        description: `Simulated scenario: ${body.scenario}`,
        simulated_at: '2026-11-26T07:30:00Z',
      },
      error: null,
    });
  }),
];
