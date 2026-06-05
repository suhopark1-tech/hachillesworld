'use client';

interface Props {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const R = 44;
const CX = 50;
const CY = 54;
const ARC_LEN = Math.PI * R; // semicircle circumference

function scoreColor(s: number): string {
  if (s >= 80) return '#10b981'; // green
  if (s >= 60) return '#f59e0b'; // amber
  return '#ef4444';             // red
}

export default function HASGauge({ score, size = 'md', showLabel = true }: Props) {
  const pct = Math.min(Math.max(score, 0), 100) / 100;
  const dash = pct * ARC_LEN;
  const color = scoreColor(score);

  const sizeMap = { sm: 'w-24', md: 'w-36', lg: 'w-48' };
  const textSize = { sm: '14', md: '18', lg: '24' };

  return (
    <div className={`flex flex-col items-center ${sizeMap[size]}`}>
      <svg viewBox="0 0 100 60" className="w-full">
        {/* track */}
        <path
          d={`M ${CX - R},${CY} A ${R},${R} 0 0,1 ${CX + R},${CY}`}
          fill="none"
          stroke="#1a1a2e"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* fill */}
        <path
          d={`M ${CX - R},${CY} A ${R},${R} 0 0,1 ${CX + R},${CY}`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${ARC_LEN}`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text
          x={CX}
          y={CY - 4}
          textAnchor="middle"
          fontSize={textSize[size]}
          fontWeight="bold"
          fill={color}
        >
          {Math.round(score)}
        </text>
      </svg>
      {showLabel && (
        <span className="text-xs text-muted mt-0.5">HAS Score</span>
      )}
    </div>
  );
}
