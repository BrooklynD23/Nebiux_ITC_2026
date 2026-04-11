export interface DashboardUser {
  readonly id: string;
  readonly name: string;
  readonly role: string;
  readonly status: string;
  readonly conversations: number;
  readonly lastQuestion: string;
  readonly channel: string;
  readonly satisfaction: string;
}

export interface ActivityItem {
  readonly id: string;
  readonly label: string;
  readonly detail: string;
  readonly time: string;
}

export const MOCK_USERS: readonly DashboardUser[] = [
  {
    id: 'u-001',
    name: 'Ariana M.',
    role: 'First-year student',
    status: 'Active today',
    conversations: 4,
    lastQuestion: 'Where can I find my orientation checklist?',
    channel: 'Landing page',
    satisfaction: 'Positive',
  },
  {
    id: 'u-002',
    name: 'Jordan P.',
    role: 'Transfer student',
    status: 'Returned this week',
    conversations: 3,
    lastQuestion: 'How do I contact advising for engineering?',
    channel: 'Website popup',
    satisfaction: 'Neutral',
  },
  {
    id: 'u-003',
    name: 'Mrs. Flores',
    role: 'Parent',
    status: 'Monitoring admissions',
    conversations: 2,
    lastQuestion: 'What scholarships are available for new students?',
    channel: 'Admissions microsite',
    satisfaction: 'Positive',
  },
  {
    id: 'u-004',
    name: 'Devin L.',
    role: 'Campus ambassador',
    status: 'Power user',
    conversations: 6,
    lastQuestion: 'What are the library hours during finals week?',
    channel: 'Advisor portal',
    satisfaction: 'Positive',
  },
];

export const MOCK_ACTIVITY: readonly ActivityItem[] = [
  {
    id: 'a-001',
    label: 'Admissions intent captured',
    detail: 'Ariana M. asked about onboarding steps for admitted students.',
    time: 'Today, 1:42 PM',
  },
  {
    id: 'a-002',
    label: 'Parking topic trending',
    detail: 'Jordan P. requested permit information before commuting to campus.',
    time: 'Today, 11:18 AM',
  },
  {
    id: 'a-003',
    label: 'High-confidence answer delivered',
    detail: 'Devin L. received a cited response about finals week library hours.',
    time: 'Yesterday, 5:06 PM',
  },
];
