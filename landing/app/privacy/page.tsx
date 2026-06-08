import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '개인정보처리방침 | HAchillesWorld',
  description: 'HAchilles Labs 개인정보처리방침 (HAW-PRV-001 v1.0) — 개인정보보호법 및 GDPR 준수',
};

/* ── 목차 항목 ──────────────────────────────────────── */
const TOC = [
  { id: 's1',  label: '1. 개인정보의 처리 목적' },
  { id: 's2',  label: '2. 처리하는 개인정보 항목' },
  { id: 's3',  label: '3. 처리 및 보유 기간' },
  { id: 's4',  label: '4. 처리 위탁' },
  { id: 's5',  label: '5. 제3자 제공' },
  { id: 's6',  label: '6. 파기 절차 및 방법' },
  { id: 's7',  label: '7. 정보주체의 권리·의무' },
  { id: 's8',  label: '8. 자동화된 결정' },
  { id: 's9',  label: '9. 개인정보의 국외 이전' },
  { id: 's10', label: '10. 안전성 확보조치' },
  { id: 's11', label: '11. 보호책임자 및 민원' },
  { id: 's12', label: '12. 처리방침 변경' },
  { id: 's13', label: '13. EU·EEA 추가 안내 (GDPR)' },
  { id: 'app', label: '부록 A·B' },
];

/* ── 공통 스타일 헬퍼 ────────────────────────────────── */
const TH = 'px-3 py-2 text-left text-xs font-semibold text-[#a78bfa] bg-[#1a1a2e]';
const TD = 'px-3 py-2 text-xs text-[#cbd5e1] border-t border-[rgba(139,92,246,0.1)]';
const TR_EVEN = 'even:bg-[rgba(255,255,255,0.015)]';

function Table({ heads, rows }: { heads: string[]; rows: (string | React.ReactNode)[][] }) {
  return (
    <div className="overflow-x-auto my-4 rounded-lg border border-[rgba(139,92,246,0.2)]">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            {heads.map((h) => <th key={h} className={TH}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className={TR_EVEN}>
              {row.map((cell, j) => <td key={j} className={TD}>{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectionTitle({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-lg font-bold text-[#e2e8f0] mt-10 mb-3 border-b border-[rgba(139,92,246,0.2)] pb-2 scroll-mt-6">
      {children}
    </h2>
  );
}

function SubTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-[#a78bfa] mt-6 mb-2">{children}</h3>;
}

function InfoBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-4 px-4 py-3 rounded-lg bg-[rgba(139,92,246,0.08)] border border-[rgba(139,92,246,0.2)] text-xs text-[#cbd5e1] leading-relaxed">
      {children}
    </div>
  );
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre className="my-4 px-4 py-3 rounded-lg bg-[#0f0f1a] border border-[rgba(139,92,246,0.15)] text-xs text-[#94a3b8] leading-relaxed overflow-x-auto font-mono whitespace-pre-wrap">
      {children}
    </pre>
  );
}

/* ── 메인 페이지 ─────────────────────────────────────── */
export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e2e8f0] px-4 py-8 md:px-8">
      <div className="max-w-4xl mx-auto">

        {/* ── 헤더 ── */}
        <div className="mb-8 pb-6 border-b border-[rgba(139,92,246,0.25)]">
          <div className="flex items-center gap-2 text-xs text-[#94a3b8] mb-3">
            <a href="/" className="hover:text-[#a78bfa] no-underline">HAchillesWorld</a>
            <span>/</span>
            <span>개인정보처리방침</span>
          </div>
          <h1 className="text-2xl font-bold text-[#e2e8f0] mb-3">
            HAchillesWorld 개인정보처리방침
          </h1>
          <div className="flex flex-wrap gap-4 text-xs text-[#94a3b8]">
            <span>문서 번호: <span className="text-[#a78bfa] font-mono">HAW-PRV-001</span></span>
            <span>버전: <span className="text-[#a78bfa]">v1.0</span></span>
            <span>시행일: <span className="text-[#a78bfa]">2026년 7월 1일</span></span>
            <span>최종 개정: <span className="text-[#a78bfa]">2026년 6월 30일</span></span>
          </div>
        </div>

        {/* ── 서문 ── */}
        <InfoBox>
          <strong className="text-[#a78bfa]">HAchilles Labs</strong>(이하 "회사")는 「개인정보보호법」 제30조 및 EU 일반개인정보보호규정(GDPR) 제13조에 따라
          이용자의 개인정보 처리에 관한 사항을 아래와 같이 공개합니다.
        </InfoBox>

        {/* ── 목차 ── */}
        <div className="my-6 px-5 py-4 rounded-xl bg-[#0f0f1a] border border-[rgba(139,92,246,0.15)]">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[#475569] mb-3">목차</p>
          <ol className="grid grid-cols-1 sm:grid-cols-2 gap-1">
            {TOC.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className="text-xs text-[#94a3b8] hover:text-[#a78bfa] no-underline transition-colors"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ol>
        </div>

        {/* ════════════════════════════════════════════ */}
        {/* §1. 처리 목적 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s1">1. 개인정보의 처리 목적</SectionTitle>
        <p className="text-sm text-[#94a3b8] mb-4 leading-relaxed">
          회사는 다음의 목적으로 개인정보를 처리합니다. 처리하는 개인정보는 다음 목적 이외의 용도로는 이용되지 않으며,
          이용 목적이 변경되는 경우에는 「개인정보보호법」 제18조에 따라 별도의 동의를 받는 등 필요한 조치를 이행합니다.
        </p>

        <SubTitle>1-1. 서비스 제공 및 계약 이행 (법적 근거: 계약 체결·이행)</SubTitle>
        <Table
          heads={['세부 목적', '처리 내용']}
          rows={[
            ['회원 가입 및 계정 관리', '가입 신청 확인, 본인 식별, 불량 회원 제재, 계정 유지 및 탈퇴 처리'],
            ['AI 에이전트 진단 서비스 제공', '에피소드 데이터 수신, HAS 점수 산출, 15개 지표 진단, DiagnosticReport 생성'],
            ['플랜별 기능 제공', '구독 플랜(Free·Starter·Pro·Enterprise) 기능 차등 제공'],
            ['고객지원', '이용 문의 처리, 불만 처리, 서비스 장애 대응'],
          ]}
        />

        <SubTitle>1-2. 보안 및 법적 의무 이행 (법적 근거: 법령상 의무)</SubTitle>
        <Table
          heads={['세부 목적', '처리 내용']}
          rows={[
            ['보안 감사', '부정 접근 탐지, API 호출 이상 감지, 감사 로그(AuditEvent) 유지'],
            ['법령 의무 이행', '수사기관의 적법한 요청 대응, 법원 명령에 따른 자료 제출'],
            ['분쟁 해결', '이용약관 위반 처리, 법적 청구권 행사·방어'],
          ]}
        />

        <SubTitle>1-3. 서비스 개선 (법적 근거: 동의)</SubTitle>
        <p className="text-xs text-[#94a3b8] mb-2">이용자의 별도 동의를 받은 경우에 한하여 다음 목적으로 처리합니다.</p>
        <Table
          heads={['동의 항목', '세부 목적']}
          rows={[
            ['제품 개선 분석 동의', '서비스 이용 패턴 분석(퍼널 분석, 이탈 지점 파악), 기능 개선'],
            ['익명 벤치마크 기여 동의', '도메인별 AI 에이전트 성능 벤치마크 통계 산출 (완전 익명화 처리)'],
            ['마케팅 정보 수신 동의', 'HAchilles Weekly 뉴스레터, 웨비나·이벤트 안내, 서비스 업데이트 발송'],
            ['공개 케이스스터디 동의', '성과 개선 사례 웹사이트·마케팅 자료 활용 (별도 인터뷰 후 추가 동의 필수)'],
          ]}
        />

        {/* ════════════════════════════════════════════ */}
        {/* §2. 처리 항목 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s2">2. 처리하는 개인정보 항목</SectionTitle>

        <SubTitle>2-1. 회원 가입 시 수집 항목</SubTitle>
        <Table
          heads={['항목', '필수/선택', '처리 방법']}
          rows={[
            ['이메일 주소', '필수', 'AES-256 암호화 저장'],
            ['비밀번호', '필수', 'bcrypt 해시 저장 (원본 불보관)'],
            ['회사명 (또는 팀명)', '선택', 'AES-256 암호화 저장'],
            ['서비스 이용 지역', '필수', '자동 감지 또는 선택 (KR·US·EU·JP)'],
          ]}
        />

        <SubTitle>2-2. 서비스 이용 중 자동 수집 항목</SubTitle>
        <Table
          heads={['항목', '수집 내용', '처리 방법']}
          rows={[
            ['API 키', '서비스 인증 수단', 'bcrypt 해시, 앞 8자리만 로그 표시 (원본 불보관)'],
            ['에이전트 식별 정보', '에이전트 이름, 운영 도메인', '직접 입력'],
            ['에이전트 진단 수치 데이터', '15개 지표 수치값 (HAS, WMQ·ALM·OHM)', 'SDK 자동 전송, PostgreSQL 저장'],
            ['서비스 접속 기록', '접속 일시, 이용 이력, API 호출 내역', '자동 수집, AuditEvent 기록'],
            ['접속 IP 주소', '보안 감사 목적', 'SHA-256 해시 처리 (원본 불보관), 감사 로그 마스킹'],
            ['브라우저 정보 (User-Agent)', '기기 유형 파악', '자동 수집, 집계 후 30일 내 원본 삭제'],
          ]}
        />

        <SubTitle>2-3. 동의 시 추가 수집 항목</SubTitle>
        <Table
          heads={['동의 항목', '추가 수집 내용']}
          rows={[
            ['제품 개선 분석 동의', '페이지 조회, 스캔 시작·완료, 리포트 열람, 업그레이드 클릭 등'],
            ['익명 벤치마크 기여 동의', '진단 수치 데이터 완전 익명화 → 도메인별 통계 집계'],
            ['마케팅 정보 수신 동의', '이메일 주소 (뉴스레터·이벤트 발송)'],
            ['공개 케이스스터디 동의', '인터뷰 내용, 에이전트 개선 성과 (별도 서면 동의 후)'],
          ]}
        />

        <InfoBox>
          <strong>중요 안내</strong><br />
          회사는 귀하의 에이전트가 처리하는 <strong>최종 사용자의 개인정보, 원문 텍스트, 소스 코드, 업무 데이터를 수집하지 않습니다.</strong><br />
          에피소드 데이터 중 predicted_next_state·actual_next_state 필드는 <strong>수치·구조 메타데이터만</strong> 수집하며, 원문 텍스트는 수집 대상에서 제외됩니다. 해당 필드는 4KB 크기 제한이 적용됩니다.
        </InfoBox>

        {/* ════════════════════════════════════════════ */}
        {/* §3. 보유 기간 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s3">3. 개인정보의 처리 및 보유 기간</SectionTitle>

        <SubTitle>3-1. 구독 플랜별 데이터 보관 기간</SubTitle>
        <Table
          heads={['데이터 유형', 'Free', 'Starter', 'Pro', 'Enterprise', '비고']}
          rows={[
            ['에피소드 기록 (EpisodeRecord)', '30일', '90일', '1년', '3년', '스캔 원시 데이터'],
            ['진단 결과 (DiagnosticReport)', '90일', '90일', '3년', '3년', 'HAS 점수·지표'],
            ['HAS 시계열', '30일', '90일', '1년', '3년', '대시보드 표시용'],
            ['드리프트 로그', '30일', '90일', '1년', '3년', '이상 탐지 기록'],
            ['하네스 규칙', '90일', '1년', '3년', '5년', '사용자 설정 규칙'],
            ['웹 행동 데이터 (CustomerEvent)', '30일', '90일', '1년', '3년', '동의 시만 수집'],
            ['감사 이벤트 (AuditEvent)', '최소 1년', '최소 1년', '3년', '5년', '법적 의무, 플랜 무관 최소 1년'],
          ]}
        />

        <SubTitle>3-2. 법령에 따른 보관 기간</SubTitle>
        <Table
          heads={['보관 데이터', '보관 기간', '관련 법령']}
          rows={[
            ['접속 기록 (AuditEvent)', '최소 1년', '개인정보보호법 §29, 정보통신망법 §45의2'],
            ['결제·거래 기록', '5년', '전자상거래법 §6'],
            ['계약 또는 청약 철회 기록', '5년', '전자상거래법 §6'],
            ['표시·광고에 관한 기록', '6개월', '전자상거래법 §6'],
          ]}
        />

        <p className="text-xs text-[#94a3b8] mt-3 leading-relaxed">
          회원 탈퇴 또는 보관 기간 만료 시 <strong className="text-[#e2e8f0]">30일 이내</strong> 파기합니다.
          이미 집계·익명화된 벤치마크 통계값은 특정 개인을 식별하는 것이 기술적으로 불가능하므로 삭제 요청 대상에서 제외됩니다.
        </p>

        {/* ════════════════════════════════════════════ */}
        {/* §4. 처리 위탁 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s4">4. 개인정보의 처리 위탁</SectionTitle>

        <SubTitle>4-1. 위탁 현황</SubTitle>
        <Table
          heads={['수탁사', '위탁 업무', '처리 데이터', '보유 기간']}
          rows={[
            ['Amazon Web Services, Inc. (AWS)', '클라우드 인프라, RDS, S3 운영', '이메일(암호화), 진단 수치 데이터, 감사 로그', '서비스 종료 후 파기'],
            ['[결제 대행사] (추후 기재)', '구독 결제 처리, 청구서 발행', '이메일 주소 (결제 알림)', '전자상거래법에 따라 5년'],
            ['[이메일 발송 서비스] (추후 기재)', 'HAchilles Weekly, 서비스 알림 발송', '이메일 주소 (marketing_contact 동의자)', '수신 거부 또는 계약 종료 시까지'],
            ['Anthropic, PBC', 'Claude API — 진단 결과 해석, 개선 권고 생성', '에이전트 진단 수치 데이터 (개인 식별 정보 제외)', 'API 처리 완료 즉시 (학습 미사용)'],
          ]}
        />

        <InfoBox>
          수탁사 추가 안내: 결제 대행사 및 이메일 발송 서비스는 서비스 시행(2026년 7월 1일) 전 확정 후 기재합니다.
        </InfoBox>

        <SubTitle>4-2. AI 모델 활용 고지</SubTitle>
        <p className="text-xs text-[#94a3b8] leading-relaxed">
          회사는 AI 에이전트 진단 결과 해석 및 개선 권고 사항 생성에 Anthropic의 Claude AI 모델을 활용합니다.
          처리 데이터는 에이전트 진단 수치 데이터(HAS 점수, 15개 지표값)이며, 이메일·회사명 등 개인 식별 정보는 AI 모델에 전달하지 않습니다.
          Anthropic API를 통해 처리된 데이터는 모델 학습에 사용되지 않으며, AI 모델이 생성하는 진단 해석 및 규제 준수 점수는 참고 정보로서 공식 법적 인증을 구성하지 않습니다.
        </p>

        {/* ════════════════════════════════════════════ */}
        {/* §5. 제3자 제공 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s5">5. 개인정보의 제3자 제공</SectionTitle>
        <p className="text-sm text-[#94a3b8] leading-relaxed mb-3">
          회사는 이용자의 개인정보를 원칙적으로 제3자에게 제공하지 않습니다. 다만, 다음의 경우에는 예외로 합니다.
        </p>
        <ol className="text-xs text-[#94a3b8] leading-relaxed list-decimal list-inside space-y-1 mb-4">
          <li>이용자가 사전에 동의한 경우 (예: 공개 케이스스터디 동의)</li>
          <li>법령의 규정에 의거하거나 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우</li>
        </ol>
        <InfoBox>
          법적 근거 없는 수사기관 요청은 즉시 거부하며, 법적 근거 있는 요청에 의해 제공한 경우 72시간 이내에 해당 이용자에게 통지합니다.
          단, 법원의 통지 금지 명령이 있는 경우 명령 해제 즉시 통지합니다.<br /><br />
          <strong>완전 익명화된 집계 통계 데이터</strong>(Level 2~3 벤치마크)는 개인정보에 해당하지 않으므로 제3자 제공 규정의 적용 대상이 아닙니다.
        </InfoBox>

        {/* ════════════════════════════════════════════ */}
        {/* §6. 파기 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s6">6. 개인정보의 파기 절차 및 방법</SectionTitle>

        <SubTitle>6-1. 파기 절차</SubTitle>
        <CodeBlock>{`파기 프로세스:

Step 1. 파기 대상 확인
  · 보관 기간 만료 데이터 목록 자동 추출 (매월 1일)
  · 이용자 삭제 요청 접수 (DELETE /v1/data/me 또는 이메일)

Step 2. 삭제 실행 (30일 이내 완료)
  Day 1~3:   신원 확인 (이메일 인증 또는 API 키 확인)
  Day 4~10:  Cold Store (S3) 원시 에피소드 로그 삭제
  Day 11~20: Hot/Warm Store (PostgreSQL) 데이터 삭제
             - 에피소드 기록, 진단 결과, 시계열 데이터, 행동 데이터 삭제
  Day 21~25: 계정 소프트 삭제 (이메일 원본 덮어쓰기, 회사명 null 처리)
  Day 26~30: 잔여 레코드 0건 검증 + 삭제 완료 통보

Step 3. 삭제 미대상 데이터 안내
  · AuditEvent(감사 로그): 법적 보관 의무로 삭제 불가 (보관 기간 후 파기)
  · 이미 생성된 익명화 집계 통계: 재식별 불가능하여 삭제 불가`}</CodeBlock>

        <SubTitle>6-2. 파기 방법</SubTitle>
        <Table
          heads={['데이터 유형', '파기 방법']}
          rows={[
            ['암호화된 데이터 (이메일, 회사명)', '암호화 키 파기 후 Secure Erase (7회 덮어쓰기) 병행'],
            ['해시값 (API 키, IP 주소)', '데이터베이스 레코드 삭제 (원본 불보관이므로 해시 삭제만으로 복원 불가)'],
            ['진단 수치 데이터 (PostgreSQL)', 'DELETE 후 VACUUM 실행'],
            ['원시 에피소드 로그 (S3 Cold Store)', 'S3 객체 영구 삭제 후 삭제 증명 해시 기록'],
          ]}
        />

        {/* ════════════════════════════════════════════ */}
        {/* §7. 권리 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s7">7. 정보주체의 권리·의무 및 행사 방법</SectionTitle>

        <SubTitle>7-1. 귀하의 권리</SubTitle>
        <Table
          heads={['권리', '내용', '이행 기한', '행사 방법']}
          rows={[
            ['열람권', '수집된 자신의 개인정보 확인', '10일 내', 'GET /v1/data/me 또는 privacy@hachillesworld.ai'],
            ['정정권', '부정확한 개인정보 수정 요청', '10일 내', 'privacy@hachillesworld.ai'],
            ['삭제권 (잊힐 권리)', '개인정보 전체 삭제 요청', '30일 내', 'DELETE /v1/data/me 또는 이메일'],
            ['처리 정지권', '특정 목적 처리 중단 요청', '즉시', 'PUT /v1/consent 또는 설정 페이지'],
            ['이동권', '데이터를 다른 서비스로 이전 (JSON)', '20일 내', 'privacy@hachillesworld.ai'],
            ['자동화된 결정 거부권', 'AI 자동 진단·추천에만 의존하지 않을 권리', '즉시', '설정 페이지에서 선택'],
          ]}
        />

        <SubTitle>7-2. 권리 행사 절차</SubTitle>
        <CodeBlock>{`온라인: 서비스 내 설정 페이지 → 개인정보 관리
이메일: privacy@hachillesworld.ai
  · 제목: "[개인정보 권리 행사] 신청 유형 — 이메일 주소"
  · 본문: 신청 유형, 요청 내용, 이메일 또는 API 키 prefix

신원 확인:
  · 이메일 인증 링크 발송 후 확인
  · 대리인 신청 시: 위임장 + 대리인 신분증 사본 필요`}</CodeBlock>

        <SubTitle>7-3. 이의 제기 기관</SubTitle>
        <Table
          heads={['기관', '연락처']}
          rows={[
            ['개인정보보호위원회', 'privacy.go.kr / 국번없이 182'],
            ['한국인터넷진흥원 개인정보침해신고센터', 'privacy.kisa.or.kr / 국번없이 118'],
            ['대검찰청 사이버범죄수사단', 'www.spo.go.kr / 02-3480-3573'],
            ['경찰청 사이버안전국', 'cyberbureau.police.go.kr / 국번없이 182'],
          ]}
        />

        {/* ════════════════════════════════════════════ */}
        {/* §8. 자동화 결정 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s8">8. 자동화된 결정에 관한 사항</SectionTitle>

        <Table
          heads={['자동화 처리', '내용', '법적 근거']}
          rows={[
            ['HAS 점수 산출', '에피소드 데이터로 15개 지표 계산 및 0~100점 HAS 점수 생성', '계약 이행'],
            ['등급 판정', 'HAS 점수 기준 A+·A·B·C·D 등급 자동 부여', '계약 이행'],
            ['배포 적합성 판단', '등급 기반 "전면 배포 가능" 등 권고 문구 자동 생성', '계약 이행'],
            ['개선 액션 추천', 'AI 모델(Claude)을 활용한 맞춤형 개선 권고 자동 생성', '계약 이행'],
          ]}
        />

        <InfoBox>
          <strong>자동화된 결정의 한계 안내</strong><br />
          HAS 점수와 등급은 에이전트의 World Model 품질을 측정하는 <strong>참고 지표</strong>이며, EU AI Act·ISO/IEC 42001 준수 점수는 공식 인증 또는 법적 준수 판단을 구성하지 않습니다.
          모든 HAS 점수에는 95% 신뢰구간이 함께 제공됩니다.
          귀하는 서비스 설정에서 자동화된 진단 결과에만 의존하지 않도록 선택하거나 전문가 직접 검토를 요청할 수 있습니다.
        </InfoBox>

        {/* ════════════════════════════════════════════ */}
        {/* §9. 국외 이전 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s9">9. 개인정보의 국외 이전</SectionTitle>
        <p className="text-xs text-[#94a3b8] mb-3 leading-relaxed">
          회사는 현재 <strong className="text-[#e2e8f0]">AWS 서울 리전</strong>(대한민국 소재)에서 데이터를 처리합니다.
          EU·EEA 거주 이용자의 개인정보가 한국 소재 서버에 저장될 경우, 이는 GDPR 제44조에 따른 국외 이전에 해당합니다.
        </p>
        <Table
          heads={['이전 대상국', '이전 방법', '적용 근거']}
          rows={[
            ['대한민국 (AWS 서울 리전)', '클라우드 저장·처리', 'EU 표준계약조항 (SCCs, 2021년 개정판) Module 2 적용'],
          ]}
        />
        <InfoBox>
          한국은 현재 GDPR 적정성 결정(Adequacy Decision)이 내려지지 않은 상태입니다. EU 이용자 데이터에는 유럽위원회가 2021년 6월 승인한 표준계약조항(SCCs)이 적용됩니다.
          EU·EEA 거주 이용자는 국외 이전에 동의하지 않을 권리가 있으며, 이전 거부 시 서비스 이용이 제한될 수 있습니다. 이전 거부 요청: privacy@hachillesworld.ai
        </InfoBox>

        {/* ════════════════════════════════════════════ */}
        {/* §10. 안전성 확보 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s10">10. 개인정보의 안전성 확보조치</SectionTitle>

        <SubTitle>10-1. 기술적 보호조치</SubTitle>
        <Table
          heads={['조치', '내용']}
          rows={[
            ['암호화', '이메일·회사명: AES-256 / API 키·비밀번호: bcrypt / 전송: TLS 1.3'],
            ['접근 통제', 'API Bearer Token 인증, IP 화이트리스트(관리자), MFA 필수(관리 콘솔)'],
            ['감사 로그', '모든 데이터 접근·수정 이벤트 AuditEvent 기록 (최소 1년 보관)'],
            ['취약점 관리', 'OWASP Top 10 기준 정기 점검, SQL Injection·XSS 방어 코드'],
            ['Cold Store 보안', 'S3 퍼블릭 접근 차단, SSE-KMS 암호화, S3 Access Log 활성화'],
          ]}
        />

        <SubTitle>10-2. 관리적 보호조치</SubTitle>
        <Table
          heads={['조치', '내용']}
          rows={[
            ['내부 관리계획', 'HAW-POL-001 데이터 관리 내부 규정 수립·시행'],
            ['접근 권한 최소화', '업무별 최소 권한 원칙, 분기별 권한 검토'],
            ['임직원 교육', '입사 시 기본 교육 + 연 1회 정기 교육'],
            ['내부 감사', '월간 자동 감사 리포트 + 분기별 CPO 주관 수동 감사'],
            ['개발 환경 분리', '프로덕션 데이터를 개발·테스트 환경에 직접 사용 금지'],
          ]}
        />

        {/* ════════════════════════════════════════════ */}
        {/* §11. 보호책임자 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s11">11. 개인정보 보호책임자 및 민원 처리</SectionTitle>

        <div className="my-4 p-4 rounded-xl bg-[#0f0f1a] border border-[rgba(139,92,246,0.2)]">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[#475569] mb-3">개인정보 보호책임자 (CPO)</p>
          <dl className="text-xs space-y-1">
            {[
              ['성명', '박성훈 (Park Sung Hoon)'],
              ['직책', '대표 / 개인정보 보호책임자'],
              ['이메일', 'privacy@hachillesworld.ai'],
              ['회사', 'HAchilles Labs'],
            ].map(([k, v]) => (
              <div key={k} className="flex gap-4">
                <dt className="w-16 text-[#94a3b8] shrink-0">{k}</dt>
                <dd className="text-[#e2e8f0]">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        <p className="text-xs text-[#94a3b8] leading-relaxed">
          이용자는 개인정보 보호 관련 문의, 불만 처리, 피해 구제 등에 관한 사항을 보호책임자에게 문의하실 수 있습니다.
          회사는 문의에 대해 <strong className="text-[#e2e8f0]">10일 이내</strong> 답변합니다.
        </p>

        <SubTitle>민원 처리 절차</SubTitle>
        <CodeBlock>{`1단계: privacy@hachillesworld.ai 로 이메일 문의
2단계: 10일 이내 회사 답변 (복잡한 경우 30일 이내)
3단계: 불만족 시 아래 기관에 이의 제기 가능:
  - 개인정보보호위원회: privacy.go.kr / 국번없이 182
  - 개인정보침해신고센터: privacy.kisa.or.kr / 118`}</CodeBlock>

        {/* ════════════════════════════════════════════ */}
        {/* §12. 처리방침 변경 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s12">12. 처리방침의 변경에 관한 사항</SectionTitle>
        <ul className="text-xs text-[#94a3b8] leading-relaxed space-y-1 list-disc list-inside mb-4">
          <li><strong className="text-[#e2e8f0]">중요한 변경</strong> (수집 항목 추가, 제3자 제공 추가 등): 변경 30일 전 웹사이트 공지 및 이메일 통지</li>
          <li><strong className="text-[#e2e8f0]">경미한 변경</strong> (연락처 수정, 오탈자 수정 등): 변경 7일 전 웹사이트 공지</li>
        </ul>
        <Table
          heads={['버전', '시행일', '주요 변경 내용']}
          rows={[
            ['v1.0', '2026-07-01', '최초 시행'],
          ]}
        />

        {/* ════════════════════════════════════════════ */}
        {/* §13. GDPR */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="s13">13. EU·EEA 거주 이용자를 위한 추가 안내 (GDPR)</SectionTitle>
        <InfoBox>이 항목은 EU·EEA 회원국에 거주하는 이용자에게 추가로 적용됩니다.</InfoBox>

        <SubTitle>13-1. 처리 적법 근거 (GDPR Art.6)</SubTitle>
        <Table
          heads={['처리 활동', '적법 근거', '조문']}
          rows={[
            ['서비스 계약 이행 (이메일, 진단 데이터)', '계약 이행', 'Art.6(1)(b)'],
            ['보안 감사 로그', '법적 의무', 'Art.6(1)(c)'],
            ['익명 벤치마크 집계', '동의', 'Art.6(1)(a)'],
            ['제품 개선 분석', '동의', 'Art.6(1)(a)'],
            ['마케팅 연락', '동의', 'Art.6(1)(a)'],
          ]}
        />

        <SubTitle>13-2. EU 이용자 추가 권리</SubTitle>
        <Table
          heads={['권리', '내용', '조문']}
          rows={[
            ['처리 반대권', '정당한 이익 기반 처리에 대한 반대', 'Art.21'],
            ['감독기관 제소권', '해당 국가 개인정보보호 감독기관(DPA)에 불만 제기', 'Art.77'],
          ]}
        />

        <SubTitle>13-3. 주요 EU DPA 연락처</SubTitle>
        <Table
          heads={['국가', '기관', '웹사이트']}
          rows={[
            ['독일', 'Bundesbeauftragte für den Datenschutz (BfDI)', 'bfdi.bund.de'],
            ['프랑스', 'Commission Nationale de l\'Informatique et des Libertés (CNIL)', 'cnil.fr'],
            ['아일랜드', 'Data Protection Commission (DPC)', 'dataprotection.ie'],
          ]}
        />

        <SubTitle>13-4. EU 이용자 동의 방식</SubTitle>
        <p className="text-xs text-[#94a3b8] leading-relaxed">
          EU·EEA 거주 이용자에 대한 선택적 처리(제품 개선, 벤치마크, 마케팅)는 <strong className="text-[#e2e8f0]">사전 체크박스 없이</strong> 이용자의 명시적 클릭(Opt-in)으로만 동의를 수집합니다.
          (GDPR Art.7(2), Recital 32)
        </p>

        <SubTitle>13-5. GDPR 대응 담당자</SubTitle>
        <div className="my-4 p-4 rounded-xl bg-[#0f0f1a] border border-[rgba(139,92,246,0.2)]">
          <dl className="text-xs space-y-1">
            {[
              ['성명', '박성훈 (Park Sung Hoon)'],
              ['역할', 'GDPR Compliance Officer (CPO 겸임)'],
              ['이메일', 'privacy@hachillesworld.ai'],
              ['언어', '한국어·영어 대응'],
            ].map(([k, v]) => (
              <div key={k} className="flex gap-4">
                <dt className="w-16 text-[#94a3b8] shrink-0">{k}</dt>
                <dd className="text-[#e2e8f0]">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        <SubTitle>13-6. 처리 활동 기록 요약 (GDPR Art.30)</SubTitle>
        <Table
          heads={['처리 목적', '처리 항목', '법적 근거', '이전 국가']}
          rows={[
            ['서비스 계약 이행', '이메일, 진단 수치 데이터', 'Art.6(1)(b)', '한국 (SCCs 적용)'],
            ['보안 감사', 'AuditEvent (IP 마스킹)', 'Art.6(1)(c)', '한국 (SCCs 적용)'],
            ['벤치마크 집계', '익명화된 HAS 점수, 지표값', 'Art.6(1)(a)', '해당 없음 (익명화)'],
            ['마케팅 발송', '이메일 주소', 'Art.6(1)(a)', '한국 (SCCs 적용)'],
          ]}
        />

        {/* ════════════════════════════════════════════ */}
        {/* 부록 */}
        {/* ════════════════════════════════════════════ */}
        <SectionTitle id="app">부록 A. 수집 항목 전체 목록 — 15개 지표</SectionTitle>
        <Table
          heads={['지표명', '한국어명', '범위', '설명']}
          rows={[
            ['prediction_error_rate', '예측 오차율', '0~1', '예측-현실 거리 정규화값'],
            ['calibration_ece', '보정 오차', '0~1', 'Expected Calibration Error'],
            ['simulation_drift_rate', '드리프트율', '0~1', '임계값 초과 에피소드 비율'],
            ['ood_detection_rate', 'OOD 탐지율', '0~1', 'Out-of-Distribution 감지 비율'],
            ['planning_depth', '계획 깊이', '1~100', '에이전트가 내다보는 스텝 수'],
            ['self_correction_rate', '자기수정율', '0~1', '내부 플래그→수정 에피소드 비율'],
            ['counterfactual_accuracy', '반사실 정확도', '0~1', '"만약 ~였다면" 추론 정확도'],
            ['goal_consistency', '목표 일관성', '0~1', '에피소드 간 목표 유지 비율'],
            ['env_adaptation_speed', '환경 적응 속도', '1~∞', '새 환경 적응까지 필요한 스텝 수'],
            ['harness_coverage', '하네스 커버리지', '0~∞', '활성 하네스 규칙 수'],
            ['wm_update_latency', 'WM 갱신 지연', '0~∞', '드리프트 감지→회복 시간(시간)'],
            ['incident_recovery_time', '인시던트 회복', '0~∞', '인시던트→정상화 시간(분)'],
            ['hitl_trigger_rate', 'HITL 빈도', '0~1', '인간 개입 요청 에피소드 비율'],
            ['harness_violation_rate', '하네스 위반율', '0~1', '하네스 규칙 위반 에피소드 비율'],
            ['checkpoint_recovery_rate', '체크포인트 회복률', '0~1', '체크포인트에서 회복 성공 비율'],
          ]}
        />
        <InfoBox>
          위 수치 데이터는 에이전트의 기계적 행동 결과이며, 에이전트가 처리하는 실제 업무 콘텐츠(텍스트, 이미지, 개인정보 등)는 포함되지 않습니다.
        </InfoBox>

        <h2 id="app-b" className="text-lg font-bold text-[#e2e8f0] mt-10 mb-3 border-b border-[rgba(139,92,246,0.2)] pb-2">
          부록 B. 쿠키 및 유사 기술 사용 안내
        </h2>

        <SubTitle>필수 쿠키 (동의 없이 사용)</SubTitle>
        <Table
          heads={['쿠키명', '목적', '보관 기간']}
          rows={[
            ['session_id', '로그인 세션 유지', '브라우저 종료 시'],
            ['csrf_token', 'CSRF 공격 방지', '세션 종료 시'],
          ]}
        />

        <SubTitle>선택 쿠키 (동의 시 사용)</SubTitle>
        <Table
          heads={['쿠키명', '목적', '보관 기간']}
          rows={[
            ['session_uuid', '서비스 이용 패턴 분석 (제품 개선)', '1년'],
            ['_ga, _ga_*', '웹 분석 (Google Analytics, 도입 예정 시 별도 고지)', '2년'],
          ]}
        />
        <p className="text-xs text-[#94a3b8] mt-2">
          EU·EEA 거주 이용자에게는 쿠키 동의 배너가 표시되며, 선택 쿠키는 명시적 동의 후 사용됩니다.
        </p>

        {/* ── 문서 푸터 ── */}
        <div className="mt-12 pt-6 border-t border-[rgba(139,92,246,0.2)] text-[10px] text-[#475569] space-y-1">
          <p>문서 번호: HAW-PRV-001 | 버전: v1.0 | 시행일: 2026년 7월 1일 | 최종 개정: 2026년 6월 30일</p>
          <p>회사: HAchilles Labs | 대표: 박성훈 (Park Sung Hoon) | 개인정보 보호책임자: 박성훈</p>
          <p>
            관련 문서: HAW-UPG-DCS-001 (업그레이드 계획서) · HAW-CNS-001 (동의서) · HAW-POL-001 (내부 규정)
          </p>
          <p className="pt-2">
            문의:{' '}
            <a href="mailto:privacy@hachillesworld.ai" className="text-[#a78bfa] hover:underline">
              privacy@hachillesworld.ai
            </a>
          </p>
        </div>

      </div>
    </div>
  );
}
