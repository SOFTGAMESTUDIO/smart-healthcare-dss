import React from 'react'
import { Calendar, Clock, User, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'

export default function AppointmentCard({ appointment, onStatusChange }) {
  const {
    id,
    patient_id,
    doctor_name,
    doctor_specialization,
    slot_datetime,
    duration_minutes = 30,
    priority_score = 0.5,
    status = 'scheduled',
    department,
    notes,
  } = appointment

  const dt = slot_datetime ? new Date(slot_datetime) : null
  const dateStr = dt ? dt.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }) : 'Pending'
  const timeStr = dt ? dt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '--:--'

  const statusStyles = {
    scheduled: 'bg-blue-50 text-blue-700 border-blue-200',
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    cancelled: 'bg-slate-100 text-slate-600 border-slate-300',
    noshow: 'bg-rose-50 text-rose-700 border-rose-200',
  }

  const isUrgent = priority_score >= 0.7

  return (
    <div className={`p-4 rounded-2xl border transition-all shadow-sm ${
      isUrgent ? 'border-rose-300 bg-rose-50/30' : 'border-slate-200 bg-white'
    }`}>
      <div className="flex items-start justify-between">
        <div>
          <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border ${statusStyles[status] || statusStyles.scheduled}`}>
            {status.toUpperCase()}
          </span>
          {isUrgent && (
            <span className="ml-2 inline-flex items-center gap-1 text-[11px] font-bold text-rose-600">
              <AlertTriangle className="w-3 h-3" /> Priority Case
            </span>
          )}
        </div>
        <span className="text-xs text-slate-400 font-mono">#{id}</span>
      </div>

      <div className="mt-3">
        <h4 className="font-bold text-slate-800 text-base">{doctor_name}</h4>
        <p className="text-xs text-blue-600 font-medium">{doctor_specialization || department}</p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
        <div className="flex items-center gap-1.5 bg-slate-50 p-2 rounded-lg border border-slate-100">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span>{dateStr}</span>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-50 p-2 rounded-lg border border-slate-100">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>{timeStr} ({duration_minutes}m)</span>
        </div>
      </div>

      <div className="mt-2.5 flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <User className="w-3.5 h-3.5" /> Patient #{patient_id}
        </span>
        <span className="font-semibold text-slate-700">
          Priority: {(priority_score * 100).toFixed(0)}%
        </span>
      </div>

      {notes && (
        <p className="mt-2 text-xs italic text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-100">
          "{notes}"
        </p>
      )}

      {status === 'scheduled' && onStatusChange && (
        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center gap-2">
          <button
            onClick={() => onStatusChange(id, 'completed')}
            className="flex-1 py-1.5 px-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" /> Complete
          </button>
          <button
            onClick={() => onStatusChange(id, 'noshow')}
            className="py-1.5 px-2.5 bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-lg text-xs font-semibold transition-colors"
          >
            No-Show
          </button>
          <button
            onClick={() => onStatusChange(id, 'cancelled')}
            className="py-1.5 px-2.5 text-slate-400 hover:text-rose-600 rounded-lg text-xs transition-colors"
          >
            <XCircle className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
