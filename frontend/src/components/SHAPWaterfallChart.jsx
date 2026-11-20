import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell
} from 'recharts'

export default function SHAPWaterfallChart({ shapValues = {} }) {
  // Convert dict to array of objects and sort by absolute contribution
  const data = Object.entries(shapValues)
    .map(([feature, val]) => ({
      feature: feature.replace(/_/g, ' ').toUpperCase(),
      shap: typeof val === 'number' ? Math.round(val * 1000) / 1000 : 0,
      absShap: Math.abs(val || 0),
    }))
    .sort((a, b) => b.absShap - a.absShap)
    .slice(0, 10)

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm italic border border-dashed border-slate-200 rounded-xl">
        No SHAP attribution data available. Run prediction to generate.
      </div>
    )
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload
      const isPositive = item.shap >= 0
      return (
        <div className="bg-white p-3 rounded-xl shadow-lg border border-slate-200 text-xs">
          <p className="font-bold text-slate-800">{item.feature}</p>
          <p className={`font-semibold mt-1 ${isPositive ? 'text-rose-600' : 'text-blue-600'}`}>
            SHAP Value: {item.shap > 0 ? `+${item.shap}` : item.shap}
          </p>
          <p className="text-slate-500 mt-1">
            {isPositive ? '↑ Elevates disease risk' : '↓ Protective effect / lowers risk'}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="w-full bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-bold text-slate-800">
            Explainable AI (SHAP) Feature Attributions
          </h4>
          <p className="text-xs text-slate-500">
            Local Shapley values: <span className="text-rose-600 font-semibold">Red (+)</span> increases risk, <span className="text-blue-600 font-semibold">Blue (-)</span> decreases risk.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs font-semibold">
          <span className="flex items-center gap-1.5 text-rose-600">
            <span className="w-3 h-3 bg-rose-500 rounded" /> Risk Driver (+)
          </span>
          <span className="flex items-center gap-1.5 text-blue-600">
            <span className="w-3 h-3 bg-blue-500 rounded" /> Protective (-)
          </span>
        </div>
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={data}
            margin={{ top: 10, right: 30, left: 80, bottom: 10 }}
          >
            <XAxis type="number" domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="feature"
              tick={{ fontSize: 10, fill: '#475569' }}
              width={100}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="3 3" />
            <Bar dataKey="shap" radius={[4, 4, 4, 4]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.shap >= 0 ? '#ef4444' : '#3b82f6'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
