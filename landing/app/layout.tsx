import type { Metadata } from 'next';
import './globals.css';
import ConsentBanner from '@/components/ConsentBanner';

export const metadata: Metadata = {
  title: 'HAchillesWorld Dashboard',
  description: 'AI 에이전트 World Model 품질 실시간 모니터링 대시보드',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <ConsentBanner />
        {children}
      </body>
    </html>
  );
}
