'use client';

import { useEffect, useState } from 'react';
import type { AlertSettings } from '@/lib/types';

const DEFAULTS: AlertSettings = {
  slack_webhook: '',
  email: '',
  has_warning_threshold: 60,
  has_critical_threshold: 40,
  drift_threshold: 0.15,
};

const STORAGE_KEY = 'haw_alert_settings';

export default function SettingsPage() {
  const [settings, setSettings] = useState<AlertSettings>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setSettings(JSON.parse(raw) as AlertSettings);
    } catch {
      // ignore
    }
  }, []);

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement>,
  ) {
    const { name, value, type } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value,
    }));
    setSaved(false);
  }

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="p-6 md:p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-[#e2e8f0] mb-2">알림 설정</h1>
      <p className="text-muted text-sm mb-8">
        경보 임계값과 알림 채널을 설정합니다. 설정은 브라우저 로컬스토리지에 저장됩니다.
      </p>

      <form onSubmit={handleSave} className="space-y-6">
        {/* 알림 채널 */}
        <fieldset className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5 space-y-4">
          <legend className="text-sm font-semibold text-[#c4b5fd] px-1">
            알림 채널
          </legend>

          <Field
            label="Slack Webhook URL"
            name="slack_webhook"
            type="url"
            value={settings.slack_webhook}
            placeholder="https://hooks.slack.com/services/..."
            onChange={handleChange}
          />
          <Field
            label="이메일 주소"
            name="email"
            type="email"
            value={settings.email}
            placeholder="ops@example.com"
            onChange={handleChange}
          />
        </fieldset>

        {/* 경보 임계값 */}
        <fieldset className="rounded-xl border border-[rgba(139,92,246,0.2)] bg-surface p-5 space-y-4">
          <legend className="text-sm font-semibold text-[#c4b5fd] px-1">
            경보 임계값
          </legend>

          <Field
            label="HAS 경고 기준점"
            name="has_warning_threshold"
            type="number"
            value={String(settings.has_warning_threshold)}
            placeholder="60"
            hint="HAS 점수가 이 값 미만이면 경고 표시"
            onChange={handleChange}
          />
          <Field
            label="HAS 위험 기준점"
            name="has_critical_threshold"
            type="number"
            value={String(settings.has_critical_threshold)}
            placeholder="40"
            hint="HAS 점수가 이 값 미만이면 즉시 경보"
            onChange={handleChange}
          />
          <Field
            label="Simulation Drift 임계값"
            name="drift_threshold"
            type="number"
            value={String(settings.drift_threshold)}
            placeholder="0.15"
            hint="드리프트가 이 값을 초과하면 재보정 트리거"
            onChange={handleChange}
          />
        </fieldset>

        {/* 저장 버튼 */}
        <div className="flex items-center gap-4">
          <button
            type="submit"
            className="px-6 py-2.5 rounded-lg bg-accent/20 text-[#c4b5fd] border border-accent/30 hover:bg-accent/30 font-semibold text-sm transition-colors"
          >
            설정 저장
          </button>
          {saved && (
            <span className="text-sm text-emerald-400 font-semibold">
              ✓ 저장되었습니다
            </span>
          )}
        </div>
      </form>

      {/* API 연결 상태 */}
      <div className="mt-8 rounded-xl border border-[rgba(139,92,246,0.15)] bg-bg2 p-5">
        <h2 className="text-sm font-semibold text-[#c4b5fd] mb-3">API 서버 연결</h2>
        <ApiStatus />
      </div>
    </div>
  );
}

function Field({
  label,
  name,
  type,
  value,
  placeholder,
  hint,
  onChange,
}: {
  label: string;
  name: string;
  type: string;
  value: string;
  placeholder: string;
  hint?: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-semibold text-[#94a3b8] mb-1.5">
        {label}
      </label>
      <input
        name={name}
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        step={type === 'number' ? 'any' : undefined}
        className="w-full rounded-lg px-3 py-2 bg-bg3 border border-[rgba(139,92,246,0.25)] text-[#e2e8f0] text-sm placeholder-[#475569] focus:outline-none focus:border-accent transition-colors"
      />
      {hint && <p className="text-xs text-muted mt-1">{hint}</p>}
    </div>
  );
}

function ApiStatus() {
  const [status, setStatus] = useState<'checking' | 'ok' | 'error'>('checking');

  useEffect(() => {
    const url =
      (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/health';
    fetch(url, { signal: AbortSignal.timeout(3000) })
      .then((r) => setStatus(r.ok ? 'ok' : 'error'))
      .catch(() => setStatus('error'));
  }, []);

  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        className={`inline-block w-2 h-2 rounded-full ${
          status === 'checking'
            ? 'bg-amber-400 animate-pulse'
            : status === 'ok'
            ? 'bg-emerald-400'
            : 'bg-red-400'
        }`}
      />
      <span className="text-muted">
        {status === 'checking'
          ? '연결 확인중…'
          : status === 'ok'
          ? 'HAW API 서버 연결됨'
          : 'HAW API 서버 오프라인 (localhost:8000)'}
      </span>
    </div>
  );
}
