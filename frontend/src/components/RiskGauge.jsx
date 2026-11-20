import React from 'react'

export default function RiskGauge({ score = 0, size = 180 }) {
  const clamped = Math.min(Math.max(score, 0), 1)
  const angle = clamped * 180 - 90 // -90 deg to +90 deg

  let color = '#10b981' // green
  let status = 'Low Risk'
  if (clamped >= 0.7) {
    color = '#ef4444' // red
    status = 'Critical / High Risk'
  } else if (clamped >= 0.4) {
    color = '#f59e0b' // amber
    status = 'Moderate Risk'
  }

  const radius = 70
  const cx = 90
  const cy = 90

  return (
    <div className="flex flex-col items-center justify-center p-3 bg-white rounded-2xl border border-slate-100 shadow-sm">
      <svg width={size} height={size * 0.65} viewBox="0 0 180 110" className="overflow-visible">
        {/* Background Arc */}
        <path
          d="M 20 90 A 70 70 0 0 1 160 90"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="16"
          strokeLinecap="round"
        />

        {/* Colored progress arc (approx using dasharray) */}
        <path
          d="M 20 90 A 70 70 0 0 1 160 90"
          fill="none"
          stroke={color}
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={`${clamped * 220} 220`}
          className="transition-all duration-1000 ease-out"
        />

        {/* Center Needle pivot */}
        <circle cx={cx} cy={cy} r="6" fill="#1e293b" />
        
        {/* Needle */}
        <g transform={`rotate(${angle} ${cx} ${cy})`} className="transition-transform duration-1000 ease-out">
          <line x1={cx} y1={cy} x2={cx} y2={cy - radius + 10} stroke="#1e293b" strokeWidth="3" strokeLinecap="round" />
        </g>
      </svg>

      <div className="text-center -mt-2">
        <span className="text-3xl font-extrabold tracking-tight" style={{ color }}>
          {(clamped * 100).toFixed(1)}%
        </span>
        <span className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mt-0.5">
          {status}
        </span>
      </div>
    </div>
  )
}
