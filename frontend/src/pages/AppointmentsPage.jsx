import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axios'
import AppointmentCard from '../components/AppointmentCard'
import { 
  Calendar, 
  Clock, 
  Plus, 
  Filter, 
  Sparkles,
  AlertCircle
} from 'lucide-react'

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('all')

  const fetchAppointments = async () => {
    try {
      setLoading(true)
      const res = await api.get('/api/appointments/')
      setAppointments(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAppointments()
  }, [])

  const handleStatusChange = async (id, newStatus) => {
    try {
      await api.patch(`/api/appointments/${id}`, { status: newStatus })
      setAppointments(prev =>
        prev.map(a => (a.id === id ? { ...a, status: newStatus } : a))
      )
    } catch (err) {
      alert('Failed to update status.')
    }
  }

  const filtered = appointments.filter(a => {
    if (filterStatus === 'all') return true
    return a.status === filterStatus
  })

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Clinic Appointments</h1>
          <p className="text-sm text-slate-500">
            Priority-aware scheduled slots optimized by Google OR-Tools CP-SAT solver.
          </p>
        </div>
        <Link
          to="/schedule"
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-sm shadow transition-colors"
        >
          <Sparkles className="w-4 h-4 text-amber-300" /> Run Smart Optimizer
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-1.5">
        {[
          { key: 'all', label: 'All Appointments' },
          { key: 'scheduled', label: 'Scheduled' },
          { key: 'completed', label: 'Completed' },
          { key: 'noshow', label: 'No-Shows' },
          { key: 'cancelled', label: 'Cancelled' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilterStatus(tab.key)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              filterStatus === tab.key
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Appointments Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-400">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          Loading appointments...
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center p-12 bg-white rounded-2xl border border-slate-200 shadow-sm text-slate-500">
          <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-2" />
          <p className="font-semibold">No appointments found</p>
          <p className="text-xs text-slate-400 mt-1">Use the Smart Scheduler to allocate queue slots.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(appt => (
            <AppointmentCard
              key={appt.id}
              appointment={appt}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}

    </div>
  )
}
