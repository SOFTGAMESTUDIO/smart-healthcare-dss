import React, { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../api/axios'
import RiskBadge from '../components/RiskBadge'
import { 
  Clock, 
  Sparkles, 
  Calendar, 
  CheckCircle2, 
  AlertCircle, 
  Users, 
  ArrowRight,
  ShieldCheck
} from 'lucide-react'

export default function SchedulePage() {
  const location = useLocation()
  const navigate = useNavigate()

  const [patients, setPatients] = useState([])
  const [selectedIds, setSelectedIds] = useState([])
  const [scheduleDate, setScheduleDate] = useState(new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadPatients() {
      try {
        const res = await api.get('/api/patients/')
        setPatients(res.data)

        // If navigated with preselected patient
        if (location.state?.selectedPatientId) {
          setSelectedIds([location.state.selectedPatientId])
        } else {
          // Pre-select high risk patients by default
          const highRisk = res.data.filter(p => p.risk_score >= 0.5).map(p => p.id)
          setSelectedIds(highRisk.slice(0, 5))
        }
      } catch (err) {
        console.error(err)
      }
    }
    loadPatients()
  }, [location.state])

  const toggleSelect = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handleRunOptimizer = async () => {
    if (selectedIds.length === 0) {
      setError('Please select at least one patient to schedule.')
      return
    }
    setError('')
    setLoading(true)
    setResult(null)

    try {
      const res = await api.post('/api/appointments/schedule', {
        patient_ids: selectedIds,
        scheduling_date: scheduleDate ? `${scheduleDate}T09:00:00` : null,
      })
      setResult(res.data)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Optimization failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-700 to-indigo-800 rounded-2xl p-6 text-white shadow-md">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 backdrop-blur border border-white/20 mb-2">
          <Sparkles className="w-3.5 h-3.5 text-amber-300" /> Constraint Satisfaction (CP-SAT)
        </span>
        <h1 className="text-2xl font-bold tracking-tight">OR-Tools Priority-Aware Scheduler</h1>
        <p className="text-sm text-blue-100 mt-1 max-w-2xl">
          Solves multi-objective optimization: minimizes critical patient waiting time, eliminates double-booking race conditions via SQLite3 WAL transactions, and balances physician workloads.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Control Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left 2 Cols: Patient Selection List */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-800">Select Patients to Optimize</h3>
              <p className="text-xs text-slate-500">Choose queued patients for automated slot matching</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSelectedIds(patients.map(p => p.id))}
                className="text-xs font-semibold text-blue-600 hover:underline"
              >
                Select All
              </button>
              <span className="text-slate-300">|</span>
              <button
                onClick={() => setSelectedIds([])}
                className="text-xs font-semibold text-slate-500 hover:underline"
              >
                Clear
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {patients.map(p => {
              const isSelected = selectedIds.includes(p.id)
              return (
                <div
                  key={p.id}
                  onClick={() => toggleSelect(p.id)}
                  className={`p-3 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50/40 ring-1 ring-blue-500'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}} // handled by parent onClick
                      className="w-4 h-4 text-blue-600 rounded border-slate-300"
                    />
                    <div>
                      <h4 className="font-bold text-slate-800 text-sm">{p.name}</h4>
                      <p className="text-xs text-slate-500">
                        {p.age}y • Dept: <span className="font-medium text-slate-700">{p.triage_dept || 'General'}</span>
                      </p>
                    </div>
                  </div>
                  <RiskBadge score={p.risk_score} />
                </div>
              )
            })}
          </div>
        </div>

        {/* Right Col: Parameters & Action */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <h3 className="text-base font-bold text-slate-800">Schedule Parameters</h3>
            
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Date
              </label>
              <input
                type="date"
                value={scheduleDate}
                onChange={e => setScheduleDate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 text-xs space-y-2">
              <span className="font-bold text-slate-700 block">Solver Objective Weights:</span>
              <div className="flex justify-between text-slate-500">
                <span>Wait Penalty (w₁):</span>
                <span className="font-mono font-semibold">0.50</span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>Priority Penalty (w₂):</span>
                <span className="font-mono font-semibold">0.30</span>
              </div>
              <div className="flex justify-between text-slate-500">
                <span>Doctor Mismatch (w₃):</span>
                <span className="font-mono font-semibold">0.20</span>
              </div>
            </div>

            <div className="text-xs text-slate-400 leading-tight">
              Selected queue size: <strong className="text-slate-700">{selectedIds.length}</strong> patients
            </div>
          </div>

          <button
            onClick={handleRunOptimizer}
            disabled={loading || selectedIds.length === 0}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Optimizing CP-SAT...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-amber-300" />
                Run Priority Scheduler
              </>
            )}
          </button>
        </div>

      </div>

      {/* Optimization Results */}
      {result && (
        <div className="bg-white rounded-2xl border border-emerald-200 shadow-sm p-6 space-y-4 animate-fade-in">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full mb-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Optimal Assignment Complete
              </span>
              <h3 className="text-xl font-extrabold text-slate-800">
                {result.scheduled} Appointments Successfully Scheduled
              </h3>
            </div>
            <button
              onClick={() => navigate('/appointments')}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl transition-colors"
            >
              View in Calendar <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="bg-slate-50 text-xs font-bold uppercase text-slate-500 border-b border-slate-200">
                  <th className="py-2.5 px-3">Patient ID</th>
                  <th className="py-2.5 px-3">Assigned Physician</th>
                  <th className="py-2.5 px-3">Slot Time</th>
                  <th className="py-2.5 px-3">Priority Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.assignments?.map((item, idx) => {
                  const dt = new Date(item.slot_datetime)
                  return (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="py-2.5 px-3 font-mono font-semibold text-slate-600">
                        Patient #{item.patient_id}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-800">
                        {item.doctor_name}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-blue-600">
                        {dt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })} ({dt.toLocaleDateString()})
                      </td>
                      <td className="py-2.5 px-3">
                        <RiskBadge score={item.priority_score} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  )
}
