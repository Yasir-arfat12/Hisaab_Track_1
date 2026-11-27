import type {
  BankCredit,
  DashboardSummary,
  EscalationDraft,
  EscalationNextStep,
  MerchantRecord,
  PromiseDetail,
  PromiseSummary,
  UserProfile,
} from '../../types';

export const DEMO_USER: UserProfile = {
  user_id: '00000000-demo-0000-0000-000000000001',
  email: 'demo@hisaab.app',
  display_name: 'Demo User',
  is_demo: true,
  gmail_connected: false,
  created_at: '2026-11-01T10:00:00Z',
};

export const DEMO_PROMISES: PromiseSummary[] = [
  {
    promise_id: '11111111-0001-0000-0000-000000000001',
    merchant_name: 'Flipkart',
    merchant_id: 'aaaaaaaa-0001-0000-0000-000000000001',
    category: 'refund',
    amount_paise: 249900,
    status: 'kept',
    due_date: '2026-11-15',
    created_at: '2026-11-01T12:00:00Z',
  },
  {
    promise_id: '11111111-0002-0000-0000-000000000002',
    merchant_name: 'HDFC Insurance',
    merchant_id: 'aaaaaaaa-0002-0000-0000-000000000002',
    category: 'insurance',
    amount_paise: 1500000,
    status: 'overdue',
    due_date: '2026-11-10',
    created_at: '2026-10-15T09:00:00Z',
  },
  {
    promise_id: '11111111-0003-0000-0000-000000000003',
    merchant_name: 'Amazon',
    merchant_id: 'aaaaaaaa-0003-0000-0000-000000000003',
    category: 'refund',
    amount_paise: 89900,
    status: 'kept',
    due_date: '2026-11-12',
    created_at: '2026-11-02T08:00:00Z',
  },
  {
    promise_id: '11111111-0004-0000-0000-000000000004',
    merchant_name: 'Zomato',
    merchant_id: 'aaaaaaaa-0004-0000-0000-000000000004',
    category: 'delivery_credit',
    amount_paise: 14900,
    status: 'pending',
    due_date: '2026-12-01',
    created_at: '2026-11-24T18:00:00Z',
  },
  {
    promise_id: '11111111-0005-0000-0000-000000000005',
    merchant_name: 'IRCTC',
    merchant_id: 'aaaaaaaa-0005-0000-0000-000000000005',
    category: 'ticket',
    amount_paise: 320000,
    status: 'needs_review',
    due_date: '2026-11-20',
    created_at: '2026-11-05T10:00:00Z',
  },
  {
    promise_id: '11111111-0006-0000-0000-000000000006',
    merchant_name: 'BookMyShow',
    merchant_id: 'aaaaaaaa-0006-0000-0000-000000000006',
    category: 'ticket',
    amount_paise: 65000,
    status: 'overdue',
    due_date: '2026-11-18',
    created_at: '2026-11-10T14:00:00Z',
  },
  {
    promise_id: '11111111-0007-0000-0000-000000000007',
    merchant_name: 'Unknown Merchant',
    merchant_id: 'aaaaaaaa-0007-0000-0000-000000000007',
    category: 'other',
    amount_paise: 9999900,
    status: 'needs_review',
    due_date: '2026-11-30',
    created_at: '2026-11-20T11:00:00Z',
  },
  {
    promise_id: '11111111-0008-0000-0000-000000000008',
    merchant_name: 'Swiggy',
    merchant_id: 'aaaaaaaa-0008-0000-0000-000000000008',
    category: 'other',
    amount_paise: 50000,
    status: 'dismissed',
    due_date: '2026-11-20',
    created_at: '2026-11-05T10:00:00Z',
  },
];

export const DEMO_PROMISE_DETAIL: PromiseDetail = {
  ...DEMO_PROMISES[1],
  received_amount_paise: null,
  source_email_id: 'msg_hdfc_001',
  source_email_subject: 'Your claim #CLM-2026-4521 has been approved',
  user_note: 'Called helpline on Nov 12, they said processing',
  escalation_rung: 2,
  exact_quote:
    'Your claim #CLM-2026-4521 of Rs. 15,000 has been approved and will be credited by Nov 10, 2026.',
  confidence: 0.97,
  extraction_method: 'llm',
  needs_review_reason: null,
  updated_at: '2026-11-20T14:30:00Z',
  timeline: [
    {
      event_id: 'evt-0001-0000-0000-0000-000000000001',
      type: 'promise_extracted',
      description: 'Promise extracted from email',
      occurred_at: '2026-10-15T09:00:00Z',
      metadata: { confidence_score: 0.97 },
    },
    {
      event_id: 'evt-0001-0000-0000-0000-000000000002',
      type: 'overdue_detected',
      description: 'Due date passed without matching bank credit',
      occurred_at: '2026-11-11T00:01:00Z',
      metadata: null,
    },
    {
      event_id: 'evt-0001-0000-0000-0000-000000000003',
      type: 'escalation_advanced',
      description: 'Escalation advanced to rung 2',
      occurred_at: '2026-11-15T08:00:00Z',
      metadata: { rung: 2 },
    },
  ],
};

export const DEMO_CREDITS: BankCredit[] = [
  {
    credit_id: 'cccc0001-0000-0000-0000-000000000001',
    date: '2026-11-14',
    description: 'FLIPKART REFUND REF FKT2026112201',
    amount_paise: 249900,
    reference_number: 'FKT2026112201',
    matched_promise_id: '11111111-0001-0000-0000-000000000001',
    bank_name: 'HDFC',
  },
  {
    credit_id: 'cccc0003-0000-0000-0000-000000000003',
    date: '2026-11-11',
    description: 'AMAZON RETURNS REF AMZ89900',
    amount_paise: 89900,
    reference_number: 'AMZ89900',
    matched_promise_id: '11111111-0003-0000-0000-000000000003',
    bank_name: 'HDFC',
  },
  {
    credit_id: 'cccc0005-0000-0000-0000-000000000005',
    date: '2026-11-21',
    description: 'IRCTC REFUND PARTIAL REF IRC3200',
    amount_paise: 290000,
    reference_number: 'IRC3200',
    matched_promise_id: '11111111-0005-0000-0000-000000000005',
    bank_name: 'SBI',
  },
];

export const DEMO_DASHBOARD: DashboardSummary = {
  total_owed_paise: 11899800,
  total_overdue_paise: 1565000,
  total_kept_paise: 339800,
  counts: {
    total: 8,
    pending: 1,
    kept: 2,
    overdue: 2,
    needs_review: 2,
    dismissed: 1,
  },
  computed_at: '2026-11-26T07:00:00Z',
};

export const DEMO_MERCHANT: MerchantRecord = {
  merchant_id: 'aaaaaaaa-0001-0000-0000-000000000001',
  merchant_name: 'Flipkart',
  total_promises: 1,
  kept_count: 1,
  overdue_count: 0,
  dismissed_count: 0,
  average_resolution_days: 13,
  keep_rate_pct: 100.0,
};

export const DEMO_NEXT_STEP: EscalationNextStep = {
  promise_id: '11111111-0002-0000-0000-000000000002',
  current_rung: 2,
  next_rung: 3,
  rung_name: 'National Consumer Helpline Complaint',
  rung_description:
    'File a complaint draft on the National Consumer Helpline (NCH) / Insurance Ombudsman.',
  deadline_date: '2026-12-10',
  days_until_deadline: 14,
  legal_forum: 'Insurance Ombudsman',
};

export const DEMO_DRAFT: EscalationDraft = {
  draft_text:
    'Subject: Formal Complaint Regarding Pending Insurance Claim #CLM-2026-4521\n\nDear HDFC Insurance Grievance Officer,\n\nI am writing to formally escalate my approved claim of Rs. 15,000.00.',
  rung: 3,
  not_legal_advice_notice:
    'This draft is generated by AI for reference only. It does not constitute legal advice. Please consult a qualified legal professional for advice specific to your situation.',
  generated_at: '2026-11-26T07:15:00Z',
  model_used: 'gemini-3.5-flash-lite',
};
