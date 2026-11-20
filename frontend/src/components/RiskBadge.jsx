import React from 'react'
import { AlertTriangle, CheckCircle2, AlertCircle } from 'lucide-react'

export default function RiskBadge({ score, level }) {
  const numScore = typeof score === 'number' ? score : parseFloat(score) || 0
  
  let riskLevel = level
  if (!riskLevel) {
    if (numScore >= 0.7) riskLevel = 'High'
    else if (numScore >= 0.4) riskLevel = 'Medium'
    else riskLevel = 'Low'
  }

  const styles = {
    High: {
      bg: 'bg-rose-50 border-rose-200 text-rose-700',
      dot: 'bg-rose-500',
      icon: AlertCircle,
    },
    Medium: {
      bg: 'bg-amber-50 border-amber-200 text-amber-700',
      dot: 'bg-amber-500',
      icon: AlertTriangle,
    },
    Low: {
      bg: 'bg-emerald-50 border-emerald-200 text-emerald-700',
      dot: 'bg-emerald-500',
      icon: CheckCircle2,
    },
  }

  const current = styles[riskLevel] || styles.Low
  const Icon = current.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${current.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${current.dot} animate-pulse`} />
      <Icon className="w-3.5 h-3.5" />
      <span>{riskLevel} Risk</span>
      {score !== undefined && (
        <span className="opacity-80">({(numScore * 100).toFixed(1)}%)</span>
      )}
    </span>
  )
}
