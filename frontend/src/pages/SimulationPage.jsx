import React, { useState, useEffect } from 'react'
import api from '../api/axios'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from 'recharts'
import { 
  Sliders, 
  TrendingDown, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck,
  Activity,
  ArrowRight
} from 'lucide-react'

export default function SimulationPage() {
  const [demand, setDemand] = useState(1.0)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchSimulation = async (dVal) => {
    try {
      setLoading(true)
      const res = await api.get(`/api/analytics/simulate?demand=${dVal}`)
      setData(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSimulation(demand)
  }, [demand])

  const chartData = data ? [
    {
      metric: 'Urgent Wait (Days)',
      FCFS: data.comparison_summary.fcfs.urgent_wait_days,
      'Fixed 30m': data.comparison_summary.fixed_slot.urgent_wait_days,
      Proposed: data.comparison_summary.proposed.urgent_wait_days,
    },
    {
      metric: 'Avg Clinic Wait (Days)',
      FCFS: data.comparison_summary.fcfs.avg_waiting_days,
      'Fixed 30m': data.comparison_summary.fixed_slot.avg_waiting_days,
      Proposed: data.comparison_summary.proposed.avg_waiting_days,
    },
    {
      metric: 'Absence Lag (Days)',
      FCFS: null,
      'Fixed 30m': data.doctor_absence_experiment.fixed_reschedule_lag_days,
      Proposed: data.doctor_absence_experiment.proposed_reschedule_lag_days,
    },
  ] : []

  const percentageChartData = data ? [
    {
      metric: 'Urgent in 1 Day (%)',
      FCFS: data.comparison_summary.fcfs.urgent_seen_within_1_day_pct,
      'Fixed 30m': data.comparison_summary.fixed_slot.urgent_seen_within_1_day_pct,
      Proposed: data.comparison_summary.proposed.urgent_seen_within_1_day_pct,
    },
    {
      metric: 'Preference (%)',
      FCFS: data.comparison_summary.fcfs.preference_satisfaction_pct,
      'Fixed 30m': data.comparison_summary.fixed_slot.preference_satisfaction_pct,
      Proposed: data.comparison_summary.proposed.preference_satisfaction_pct,
    },
    {
      metric: 'Utilization (%)',
      FCFS: data.comparison_summary.fcfs.doctor_utilization_pct,
      'Fixed 30m': data.comparison_summary.fixed_slot.doctor_utilization_pct,
      Proposed: data.comparison_summary.proposed.doctor_utilization_pct,
    },
  ] : []

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-900 rounded-2xl p-6 text-white shadow-md">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 backdrop-blur border border-white/20 mb-2">
          <Activity className="w-3.5 h-3.5 text-blue-300" /> Research Benchmark Reproducibility
        </span>
        <h1 className="text-2xl font-bold tracking-tight">28-Day Simulation: FCFS vs Priority-Aware Scheduler</h1>
        <p className="text-sm text-slate-300 mt-1 max-w-3xl">
          Real discrete simulation: 28 measured days after a 7-day warm-up, 20 seeds with common random numbers, 16 doctors in 8 departments. Values for 0.6/0.85/1.0/1.2/1.5x are precomputed; other levels run live with 5 seeds.
        </p>
      </div>

      {/* Demand Slider Control Card */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-800 text-sm">Patient Demand Multiplier: <span className="text-blue-600">{demand}x</span></h3>
            <p className="text-xs text-slate-400">Demand levels from the report: 0.6x (quiet) to 1.5x (surge)</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {[0.6, 0.85, 1.0, 1.2, 1.5].map((v) => (
            <button key={v} onClick={() => setDemand(v)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${demand === v ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200 hover:border-blue-300'}`}>
              {v}x
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-bold text-slate-400 uppercase">Urgent Wait Reduction</span>
            <div className="text-3xl font-extrabold text-emerald-600 mt-2 flex items-baseline gap-1">
              -{data.key_findings.urgent_wait_reduction_pct}%
            </div>
            <p className="text-xs text-slate-500 mt-1">{data.comparison_summary.fcfs.urgent_wait_days}d down to {data.comparison_summary.proposed.urgent_wait_days}d</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-bold text-slate-400 uppercase">1-Day Urgent Care Gain</span>
            <div className="text-3xl font-extrabold text-blue-600 mt-2 flex items-baseline gap-1">
              +{data.key_findings.one_day_urgent_fulfillment_gain} pts
            </div>
            <p className="text-xs text-slate-500 mt-1">From {data.comparison_summary.fcfs.urgent_seen_within_1_day_pct}% to {data.comparison_summary.proposed.urgent_seen_within_1_day_pct}%</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-bold text-slate-400 uppercase">Preference Satisfaction</span>
            <div className="text-3xl font-extrabold text-indigo-600 mt-2">
              {data.comparison_summary.proposed.preference_satisfaction_pct}%
            </div>
            <p className="text-xs text-slate-500 mt-1">vs {data.comparison_summary.fcfs.preference_satisfaction_pct}% under FCFS</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-bold text-slate-400 uppercase">Physician Absence Lag</span>
            <div className="text-3xl font-extrabold text-amber-600 mt-2">
              {data.doctor_absence_experiment.proposed_reschedule_lag_days}d
            </div>
            <p className="text-xs text-slate-500 mt-1">vs {data.doctor_absence_experiment.fixed_reschedule_lag_days}d under fixed slots (baseline demand)</p>
          </div>
        </div>
      )}

      {/* Visual Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Waiting Times Bar Chart */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h3 className="text-base font-bold text-slate-800">Waiting Time & Rescheduling Lag (Days)</h3>
            <p className="text-xs text-slate-400">Lower is better. Absence lag compares the two rescheduling rules (FCFS has no rescheduling rule).</p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="FCFS" fill="#94a3b8" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Fixed 30m" fill="#f59e0b" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Proposed" fill="#2563eb" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Quality & Efficiency Percentages Bar Chart */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h3 className="text-base font-bold text-slate-800">Fulfillment & Satisfaction Metrics (%)</h3>
            <p className="text-xs text-slate-400">Higher is better. Measures operational adherence and patient convenience.</p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={percentageChartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="FCFS" fill="#94a3b8" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Fixed 30m" fill="#f59e0b" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Proposed" fill="#10b981" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Comparison Table */}
      {data && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-100">
            <h3 className="text-base font-bold text-slate-800">Full Experimental Comparison (Table 4.4 Replication)</h3>
            <p className="text-xs text-slate-500">28-day simulation period with 7-day clinic warm-up</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="bg-slate-50 text-xs font-bold uppercase text-slate-500 border-b border-slate-200">
                  <th className="py-3 px-4">Evaluation Metric</th>
                  <th className="py-3 px-4">FCFS Policy</th>
                  <th className="py-3 px-4">Fixed 30-Min</th>
                  <th className="py-3 px-4 text-blue-700 font-black">Proposed System C(t)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-700">Average Waiting Time</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fcfs.avg_waiting_days} days</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fixed_slot.avg_waiting_days} days</td>
                  <td className="py-3 px-4 font-mono font-bold text-blue-700">{data.comparison_summary.proposed.avg_waiting_days} days</td>
                </tr>
                <tr className="bg-blue-50/20">
                  <td className="py-3 px-4 font-semibold text-slate-700">Urgent Wait Period</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fcfs.urgent_wait_days} days</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fixed_slot.urgent_wait_days} days</td>
                  <td className="py-3 px-4 font-mono font-bold text-emerald-700">{data.comparison_summary.proposed.urgent_wait_days} days (-{data.key_findings.urgent_wait_reduction_pct}%)</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-700">Urgent Consultations Within 1 Day</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fcfs.urgent_seen_within_1_day_pct}%</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fixed_slot.urgent_seen_within_1_day_pct}%</td>
                  <td className="py-3 px-4 font-mono font-bold text-emerald-700">{data.comparison_summary.proposed.urgent_seen_within_1_day_pct}%</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-700">Patient Preference Satisfaction</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fcfs.preference_satisfaction_pct}%</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fixed_slot.preference_satisfaction_pct}%</td>
                  <td className="py-3 px-4 font-mono font-bold text-blue-700">{data.comparison_summary.proposed.preference_satisfaction_pct}%</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-700">Schedule Completion</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fcfs.schedule_completion_pct}%</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fixed_slot.schedule_completion_pct}%</td>
                  <td className="py-3 px-4 font-mono font-bold text-blue-700">{data.comparison_summary.proposed.schedule_completion_pct}%</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-slate-700">Constraint Violations</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fcfs.constraint_violations}</td>
                  <td className="py-3 px-4 font-mono">{data.comparison_summary.fixed_slot.constraint_violations}</td>
                  <td className="py-3 px-4 font-mono font-bold text-emerald-700">{data.comparison_summary.proposed.constraint_violations}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  )
}
