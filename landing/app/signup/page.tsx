'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { ConsentRecord } from '@/lib/types';
import {
  CONSENT_STORAGE_KEY,
  ACCOUNT_STORAGE_KEY,
  AGENTS_STORAGE_KEY,
} from '@/lib/types';

/* ── 상수 ──────────────────────────────────────────────── */
const CONSENT_VERSION = 'v1.0';

const DOMAINS = [
  { value: 'Digital',    icon: '⚡', label: 'Digital Laws',    ko: 'API·소프트웨어·데이터 처리' },
  { value: 'Physical',   icon: '🤖', label: 'Physical Laws',   ko: '로봇·제조·물리 환경' },
  { value: 'Social',     icon: '💬', label: 'Social Laws',     ko: '고객·협업·다중 에이전트' },
  { value: 'Scientific', icon: '🔬', label: 'Scientific Laws', ko: '연구·분석·실험' },
] as const;

const REGIONS = [
  { value: 'KR', label: '대한민국' },
  { value: 'US', label: 'United States' },
  { value: 'EU', label: 'EU / EEA' },
  { value: 'JP', label: '日本' },
] as const;

type Region = (typeof REGIONS)[number]['value'];

const OPTIONAL_CONSENTS = [
  {
    key: 'anonymous_benchmark' as const,
    badge: '선택 A',
    label: '익명 벤치마크 기여',
    desc: '진단 수치를 완전 익명화하여 도메인별 업계 평균 산출에 기여합니다.',
    benefit: '동의 시 업계 상위 몇% 즉시 확인 · 취약 지표 자동 하이라이트',
  },
  {
    key: 'product_improvement' as const,
    badge: '선택 B',
    label: '서비스 개선 분석',
    desc: '페이지 방문·스캔 완료 등 이용 패턴을 분석해 UX를 개선합니다.',
  },
  {
    key: 'marketing_contact' as const,
    badge: '선택 C',
    label: 'HAchilles Weekly 수신',
    desc: 'AI 에이전트 인사이트를 주 1회 이메일로 받습니다. 월 최대 8회 이하.',
  },
];

const SDK_SNIPPETS = {
  python: `pip install hachillesworld

from hachillesworld import HAWClient

client = HAWClient(api_key="YOUR_API_KEY")

# 에피소드 전송 (15개 지표 중 측정값만 포함)
episode = client.submit_episode(
    agent_id="YOUR_AGENT_ID",
    prediction_error_rate=0.12,
    planning_depth=8,
    goal_consistency=0.91,
    # ...
)

# HAS 점수 조회
report = client.get_report(agent_id="YOUR_AGENT_ID")
print(f"HAS Score: {report.has_score}  Level: {report.level}")`,

  typescript: `npm install hachillesworld

import { HAWClient } from 'hachillesworld';

const client = new HAWClient({ apiKey: 'YOUR_API_KEY' });

// 에피소드 전송
await client.submitEpisode({
  agentId: 'YOUR_AGENT_ID',
  predictionErrorRate: 0.12,
  planningDepth: 8,
  goalConsistency: 0.91,
  // ...
});

// HAS 점수 조회
const report = await client.getReport({ agentId: 'YOUR_AGENT_ID' });
console.log(\`HAS: \${report.hasScore}  Level: \${report.level}\`);`,

  cli: `# HAW CLI 설치
pip install hachillesworld[cli]

# API 키 인증
haw auth login --api-key YOUR_API_KEY

# 에이전트 목록 확인
haw agents list

# 즉시 스캔
haw scan --agent-id YOUR_AGENT_ID --domain Digital`,
};

/* ── 공통 컴포넌트 ─────────────────────────────────────── */

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.4)] ${
        checked ? 'bg-[#8b5cf6] border-[#8b5cf6]' : 'bg-[#1a1a2e] border-[rgba(139,92,246,0.3)]'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-[18px]' : 'translate-x-[2px]'
        }`}
      />
    </button>
  );
}

function Field({
  label,
  name,
  type = 'text',
  value,
  onChange,
  placeholder,
  hint,
  required,
  error,
}: {
  label: string;
  name: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: string;
  required?: boolean;
  error?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-semibold text-[#94a3b8] mb-1.5">
        {label} {required && <span className="text-[#8b5cf6]">*</span>}
      </label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={type === 'password' ? 'new-password' : 'off'}
        className={`w-full rounded-lg px-3 py-2.5 bg-[#0a0a0f] border text-[#e2e8f0] text-sm placeholder-[#475569] focus:outline-none focus:border-[#8b5cf6] transition-colors ${
          error ? 'border-red-500/60' : 'border-[rgba(139,92,246,0.25)]'
        }`}
      />
      {hint && !error && <p className="text-[10px] text-[#475569] mt-1">{hint}</p>}
      {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
    </div>
  );
}

function StepIndicator({ current }: { current: number }) {
  const steps = ['기본 정보', '개인정보 동의', '에이전트 등록'];
  return (
    <div className="flex items-start justify-center gap-0 mb-8">
      {steps.map((label, i) => {
        const n = i + 1;
        const done   = n < current;
        const active = n === current;
        return (
          <div key={n} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors ${
                  done
                    ? 'bg-[#8b5cf6] border-[#8b5cf6] text-white'
                    : active
                    ? 'bg-transparent border-[#8b5cf6] text-[#a78bfa]'
                    : 'bg-transparent border-[#334155] text-[#475569]'
                }`}
              >
                {done ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 16 16">
                    <path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : n}
              </div>
              <span
                className={`text-[10px] font-medium whitespace-nowrap ${
                  active ? 'text-[#a78bfa]' : done ? 'text-[#64748b]' : 'text-[#334155]'
                }`}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={`h-px w-12 sm:w-16 mx-2 mb-5 transition-colors ${
                  done ? 'bg-[#8b5cf6]' : 'bg-[#1e293b]'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── 메인 페이지 ─────────────────────────────────────────── */

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [sdkTab, setSdkTab] = useState<'python' | 'typescript' | 'cli'>('python');

  /* Step 1 */
  const [email, setEmail]     = useState('');
  const [password, setPassword] = useState('');
  const [company, setCompany] = useState('');
  const [region, setRegion]   = useState<Region>('KR');
  const [s1Err, setS1Err]     = useState<{ email?: string; password?: string }>({});

  /* Step 2 */
  const [optConsent, setOptConsent] = useState({
    anonymous_benchmark: false,
    product_improvement: false,
    marketing_contact: false,
  });

  /* Step 3 */
  const [agentName, setAgentName] = useState('');
  const [agentId, setAgentId]     = useState('');
  const [domain, setDomain]       = useState('');
  const [purpose, setPurpose]     = useState('');
  const [s3Err, setS3Err]         = useState<{ agentName?: string; domain?: string }>({});

  const [completed, setCompleted] = useState(false);

  /* ── 에이전트 이름 → ID 자동 생성 ── */
  function handleAgentName(name: string) {
    setAgentName(name);
    setAgentId(name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''));
    if (s3Err.agentName) setS3Err((e) => ({ ...e, agentName: undefined }));
  }

  /* ── 유효성 검사 ── */
  function validateStep1(): boolean {
    const errs: typeof s1Err = {};
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      errs.email = '유효한 이메일 주소를 입력하세요';
    if (!password || password.length < 8)
      errs.password = '비밀번호는 8자 이상이어야 합니다';
    setS1Err(errs);
    return Object.keys(errs).length === 0;
  }

  function validateStep3(): boolean {
    const errs: typeof s3Err = {};
    if (!agentName.trim()) errs.agentName = '에이전트 이름을 입력하세요';
    if (!domain)           errs.domain    = '운영 도메인을 선택하세요';
    setS3Err(errs);
    return Object.keys(errs).length === 0;
  }

  /* ── 네비게이션 ── */
  function handleNext() {
    if (step === 1 && !validateStep1()) return;
    if (step === 3) {
      if (!validateStep3()) return;
      handleComplete();
      return;
    }
    setStep((s) => s + 1);
  }

  function handleComplete() {
    const consentRecord: ConsentRecord = {
      version: CONSENT_VERSION,
      required: true,
      anonymous_benchmark: optConsent.anonymous_benchmark,
      product_improvement: optConsent.product_improvement,
      marketing_contact: optConsent.marketing_contact,
      public_case_study: false,
      consented_at: new Date().toISOString(),
      region,
    };
    try {
      localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(consentRecord));
      localStorage.setItem(ACCOUNT_STORAGE_KEY, JSON.stringify({
        email, company, region, created_at: new Date().toISOString(),
      }));
      if (agentId) {
        const existing = JSON.parse(localStorage.getItem(AGENTS_STORAGE_KEY) ?? '[]') as unknown[];
        existing.push({ agent_id: agentId, name: agentName, domain, purpose, created_at: new Date().toISOString() });
        localStorage.setItem(AGENTS_STORAGE_KEY, JSON.stringify(existing));
      }
    } catch { /* storage unavailable */ }
    setCompleted(true);
  }

  /* ── 완료 화면 ── */
  if (completed) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center px-4">
        <div className="max-w-sm w-full text-center">
          <div className="w-16 h-16 rounded-full bg-[rgba(139,92,246,0.15)] border border-[rgba(139,92,246,0.4)] flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-[#8b5cf6]" fill="none" viewBox="0 0 24 24">
              <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-[#e2e8f0] mb-2">등록 완료!</h1>
          {agentName && (
            <p className="text-sm text-[#94a3b8] mb-1">
              <strong className="text-[#e2e8f0]">{agentName}</strong> 에이전트가 등록되었습니다.
            </p>
          )}
          <p className="text-xs text-[#475569] mb-8 leading-relaxed">
            SDK를 설치하고 에피소드를 전송하면<br />
            HAS 점수를 대시보드에서 확인할 수 있습니다.
          </p>
          <button
            onClick={() => router.push('/dashboard')}
            className="w-full py-3 rounded-xl bg-[#8b5cf6] hover:bg-[#7c3aed] text-white font-semibold text-sm transition-colors"
          >
            대시보드로 이동 →
          </button>
          <Link
            href="/privacy"
            className="block mt-4 text-[10px] text-[#334155] hover:text-[#475569] no-underline transition-colors"
          >
            개인정보처리방침
          </Link>
        </div>
      </div>
    );
  }

  /* ── 패스워드 강도 ── */
  const pwStrength = password.length === 0 ? 0 : password.length < 8 ? 1 : password.length < 12 ? 2 : 3;
  const pwLabel    = ['', '약함', '보통', '강함'][pwStrength];
  const pwColor    = ['', 'bg-red-500', 'bg-amber-400', 'bg-emerald-400'][pwStrength];

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">

        {/* 로고 + 로그인 링크 */}
        <div className="flex items-center gap-2 mb-8">
          <span className="text-xl text-[#8b5cf6] font-bold">⬡</span>
          <span className="text-sm font-semibold text-[#e2e8f0]">HAchillesWorld</span>
          <span className="ml-auto text-xs text-[#475569]">
            이미 계정이 있으신가요?{' '}
            <Link href="/dashboard" className="text-[#8b5cf6] hover:underline no-underline">
              대시보드 →
            </Link>
          </span>
        </div>

        {/* 단계 표시 */}
        <StepIndicator current={step} />

        {/* 카드 */}
        <div className="rounded-2xl bg-[#0f0f1a] border border-[rgba(139,92,246,0.2)] shadow-2xl overflow-hidden">

          {/* ── Step 1: 기본 정보 ── */}
          {step === 1 && (
            <div className="px-6 py-6">
              <h2 className="text-lg font-bold text-[#e2e8f0] mb-1">기본 정보 입력</h2>
              <p className="text-xs text-[#64748b] mb-6">계정 생성에 필요한 정보를 입력합니다.</p>

              <div className="space-y-4">
                <Field
                  label="이메일 주소" name="email" type="email"
                  value={email} onChange={(v) => { setEmail(v); setS1Err((e) => ({ ...e, email: undefined })); }}
                  placeholder="you@company.com" required error={s1Err.email}
                />

                <div>
                  <Field
                    label="비밀번호" name="password" type="password"
                    value={password} onChange={(v) => { setPassword(v); setS1Err((e) => ({ ...e, password: undefined })); }}
                    placeholder="8자 이상" required error={s1Err.password}
                  />
                  {password.length > 0 && (
                    <div className="flex items-center gap-1 mt-1.5">
                      {[1, 2, 3].map((lv) => (
                        <div
                          key={lv}
                          className={`h-1 flex-1 rounded-full transition-colors ${
                            lv <= pwStrength ? pwColor : 'bg-[#1e293b]'
                          }`}
                        />
                      ))}
                      <span className="text-[10px] text-[#475569] w-8 text-right">{pwLabel}</span>
                    </div>
                  )}
                </div>

                <Field
                  label="회사명 또는 팀명" name="company"
                  value={company} onChange={setCompany}
                  placeholder="HAchilles Labs (선택)"
                  hint="개인 사용자는 입력하지 않아도 됩니다."
                />

                <div>
                  <label className="block text-xs font-semibold text-[#94a3b8] mb-1.5">
                    서비스 이용 지역 <span className="text-[#8b5cf6]">*</span>
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {REGIONS.map((r) => (
                      <button
                        key={r.value}
                        type="button"
                        onClick={() => setRegion(r.value)}
                        className={`py-2 px-3 rounded-lg border text-xs font-medium transition-colors ${
                          region === r.value
                            ? 'border-[#8b5cf6] bg-[rgba(139,92,246,0.15)] text-[#c4b5fd]'
                            : 'border-[rgba(139,92,246,0.2)] bg-[#0a0a0f] text-[#64748b] hover:border-[rgba(139,92,246,0.35)]'
                        }`}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                  {region === 'EU' && (
                    <p className="text-[10px] text-[#8b5cf6] mt-2 leading-relaxed">
                      EU·EEA 거주자에게는 GDPR이 적용됩니다.
                      선택 동의는 사전 체크 없이 명시적 Opt-in으로만 수집됩니다.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Step 2: 개인정보 동의 ── */}
          {step === 2 && (
            <div className="px-6 py-6">
              <h2 className="text-lg font-bold text-[#e2e8f0] mb-1">개인정보 동의</h2>
              <p className="text-xs text-[#64748b] mb-5">
                서비스 이용을 위한 동의 내용을 확인합니다.{' '}
                <Link href="/privacy" target="_blank" className="text-[#8b5cf6] hover:underline">
                  처리방침 전문 →
                </Link>
              </p>

              {/* 필수 동의 */}
              <div className="rounded-xl bg-[#1a1a2e] border border-[rgba(139,92,246,0.25)] p-4 mb-4">
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[rgba(139,92,246,0.2)] text-[#a78bfa] shrink-0">
                    필수
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[#e2e8f0]">
                      서비스 이용을 위한 개인정보 수집·이용
                    </p>
                    <p className="text-xs text-[#64748b] mt-1 leading-relaxed">
                      이메일, 에이전트 진단 수치 데이터(15개 지표), 접속 기록 수집.
                      원문 텍스트·소스 코드는 수집하지 않습니다.
                    </p>
                    <div className="flex gap-4 mt-1.5">
                      <span className="text-[10px] text-[#475569]">법적 근거: 계약 이행</span>
                      <span className="text-[10px] text-[#475569]">보관: 탈퇴 후 30일 내 파기</span>
                    </div>
                  </div>
                  <div className="mt-0.5 shrink-0 flex items-center justify-center w-5 h-5 rounded bg-[#8b5cf6]">
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 12 12">
                      <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                </div>
                <p className="text-[10px] text-[#475569] mt-2 pl-[52px]">
                  이 항목에 동의하지 않으시면 서비스를 이용하실 수 없습니다.
                </p>
              </div>

              {/* 선택 동의 */}
              <p className="text-xs font-semibold text-[#94a3b8] mb-2">
                서비스 개선에 참여하시겠어요?{' '}
                <span className="font-normal text-[#475569]">
                  (선택 — 거부해도 서비스 이용 가능)
                </span>
              </p>
              <div className="space-y-2">
                {OPTIONAL_CONSENTS.map((item) => (
                  <div
                    key={item.key}
                    className="flex items-start gap-3 rounded-lg border border-[rgba(139,92,246,0.15)] bg-[rgba(255,255,255,0.02)] px-4 py-3"
                  >
                    <span className="mt-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[rgba(139,92,246,0.1)] text-[#7c6bae] shrink-0">
                      {item.badge}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[#cbd5e1]">{item.label}</p>
                      <p className="text-xs text-[#64748b] mt-0.5 leading-relaxed">{item.desc}</p>
                      {item.benefit && optConsent[item.key] && (
                        <p className="text-[10px] text-[#8b5cf6] mt-1">→ {item.benefit}</p>
                      )}
                    </div>
                    <Toggle
                      checked={optConsent[item.key]}
                      onChange={() =>
                        setOptConsent((p) => ({ ...p, [item.key]: !p[item.key] }))
                      }
                    />
                  </div>
                ))}
              </div>

              <p className="text-[10px] text-[#475569] mt-3 leading-relaxed">
                선택 동의는 언제든지{' '}
                <span className="text-[#94a3b8]">대시보드 설정 → 동의 관리</span>
                에서 변경하실 수 있습니다.
              </p>
            </div>
          )}

          {/* ── Step 3: 에이전트 등록 ── */}
          {step === 3 && (
            <div className="px-6 py-6">
              <h2 className="text-lg font-bold text-[#e2e8f0] mb-1">첫 에이전트 등록</h2>
              <p className="text-xs text-[#64748b] mb-5">
                모니터링할 AI 에이전트를 등록합니다.
                <span className="text-[#475569]"> 지금 건너뛰고 나중에 추가할 수도 있습니다.</span>
              </p>

              <div className="space-y-4">
                {/* 에이전트 이름 */}
                <div>
                  <Field
                    label="에이전트 이름" name="agentName"
                    value={agentName} onChange={handleAgentName}
                    placeholder="My Customer Agent" required error={s3Err.agentName}
                  />
                  {agentId && (
                    <p className="text-[10px] text-[#475569] mt-1">
                      agent_id:{' '}
                      <span className="text-[#8b5cf6] font-mono">{agentId}</span>
                    </p>
                  )}
                </div>

                {/* 도메인 선택 */}
                <div>
                  <label className="block text-xs font-semibold text-[#94a3b8] mb-1.5">
                    운영 도메인 <span className="text-[#8b5cf6]">*</span>
                  </label>
                  {s3Err.domain && (
                    <p className="text-xs text-red-400 mb-2">{s3Err.domain}</p>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    {DOMAINS.map((d) => (
                      <button
                        key={d.value}
                        type="button"
                        onClick={() => {
                          setDomain(d.value);
                          setS3Err((e) => ({ ...e, domain: undefined }));
                        }}
                        className={`text-left rounded-xl border p-3 transition-colors ${
                          domain === d.value
                            ? 'border-[#8b5cf6] bg-[rgba(139,92,246,0.12)]'
                            : 'border-[rgba(139,92,246,0.15)] bg-[#0a0a0f] hover:border-[rgba(139,92,246,0.3)]'
                        }`}
                      >
                        <span className="text-base">{d.icon}</span>
                        <p
                          className={`text-xs font-semibold mt-1 ${
                            domain === d.value ? 'text-[#c4b5fd]' : 'text-[#94a3b8]'
                          }`}
                        >
                          {d.label}
                        </p>
                        <p className="text-[10px] text-[#475569] mt-0.5">{d.ko}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 목적 */}
                <div>
                  <label className="block text-xs font-semibold text-[#94a3b8] mb-1.5">
                    에이전트 목적 (선택)
                  </label>
                  <textarea
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                    placeholder="예: 고객 문의 자동 처리 및 에스컬레이션"
                    rows={2}
                    className="w-full rounded-lg px-3 py-2.5 bg-[#0a0a0f] border border-[rgba(139,92,246,0.25)] text-[#e2e8f0] text-sm placeholder-[#475569] focus:outline-none focus:border-[#8b5cf6] transition-colors resize-none"
                  />
                </div>

                {/* SDK 가이드 */}
                <div className="rounded-xl border border-[rgba(139,92,246,0.15)] overflow-hidden">
                  <div className="flex items-center border-b border-[rgba(139,92,246,0.15)]">
                    {(['python', 'typescript', 'cli'] as const).map((tab) => (
                      <button
                        key={tab}
                        type="button"
                        onClick={() => setSdkTab(tab)}
                        className={`px-4 py-2 text-xs font-semibold transition-colors border-b-2 ${
                          sdkTab === tab
                            ? 'text-[#c4b5fd] border-[#8b5cf6]'
                            : 'text-[#475569] border-transparent hover:text-[#94a3b8]'
                        }`}
                      >
                        {tab === 'python' ? 'Python' : tab === 'typescript' ? 'TypeScript' : 'CLI'}
                      </button>
                    ))}
                    <span className="ml-auto px-3 py-2 text-[10px] text-[#334155]">
                      SDK 설치 가이드
                    </span>
                  </div>
                  <pre className="px-4 py-3 text-[11px] text-[#94a3b8] leading-relaxed overflow-x-auto font-mono bg-[#0a0a0f] max-h-44 whitespace-pre">
                    {SDK_SNIPPETS[sdkTab]}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* ── 하단 네비게이션 ── */}
          <div className="px-6 py-4 border-t border-[rgba(139,92,246,0.15)] flex items-center justify-between">
            {step > 1 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="text-sm text-[#64748b] hover:text-[#94a3b8] transition-colors"
              >
                ← 이전
              </button>
            ) : (
              <Link
                href="/dashboard"
                className="text-sm text-[#64748b] hover:text-[#94a3b8] no-underline transition-colors"
              >
                건너뛰기
              </Link>
            )}

            <div className="flex items-center gap-3">
              {step === 3 && (
                <button
                  type="button"
                  onClick={() => router.push('/dashboard')}
                  className="text-sm text-[#64748b] hover:text-[#94a3b8] transition-colors"
                >
                  에이전트 나중에 등록
                </button>
              )}
              <button
                type="button"
                onClick={handleNext}
                className="px-6 py-2 rounded-lg bg-[#8b5cf6] hover:bg-[#7c3aed] text-white text-sm font-semibold transition-colors"
              >
                {step === 3 ? '등록 완료 →' : '다음 단계 →'}
              </button>
            </div>
          </div>
        </div>

        {/* 푸터 */}
        <p className="text-center text-[10px] text-[#334155] mt-6">
          HAW-CNS-001 {CONSENT_VERSION} · 2026년 7월 1일 시행 ·{' '}
          <Link href="/privacy" className="text-[#475569] hover:text-[#8b5cf6] no-underline">
            개인정보처리방침
          </Link>
        </p>
      </div>
    </div>
  );
}
