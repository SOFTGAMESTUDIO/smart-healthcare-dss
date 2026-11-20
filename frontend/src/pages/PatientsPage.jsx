import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axios'
import RiskBadge from '../components/RiskBadge'
import { 
  Users, 
  Search, 
  Plus, 
  Eye, 
  Trash2, 
  CalendarPlus, 
  AlertTriangle,
  Heart,
  ChevronRight
} from 'lucide-react'

export default function PatientsPage() {
  const [patients, setPatients] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchPatients = async () => {
    try {
      setLoading(true)
      const res = await api.get('/api/patients/')
      setPatients(res.data)
    } catch (err) {
      console.error('Failed to load patients:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPatients()
  }, [])

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (window.confirm(`Are you sure you want to delete patient record #${id}?`)) {
      try {
        await api.delete(`/api/patients/${id}`)
        setPatients(prev => prev.filter(p => p.id !== id))
      } catch (err) {
        alert('Failed to delete patient.')
      }
    }
  }

  const filtered = patients.filter(p => {
    const term = search.toLowerCase()
    return (
      (p.name && p.name.toLowerCase().includes(term)) ||
      (p.triage_dept && p.triage_dept.toLowerCase().includes(term)) ||
      String(p.id).includes(term)
    )
  })

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Patient Directory</h1>
          <p className="text-sm text-slate-500">
            Encrypted PII (DPDP Act 2023 compliant) with real-time SHAP risk scores and triage recommendations.
          </p>
        </div>
        <Link
          to="/patients/new"
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-sm shadow transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Patient
        </Link>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name, ID, or department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          />
        </div>
        <div className="text-xs font-semibold text-slate-500">
          Showing {filtered.length} of {patients.length} patients
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading patients...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold">No patients found</p>
            <p className="text-xs text-slate-400 mt-1">Try adjusting your search criteria or register a new patient.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-xs font-bold uppercase tracking-wider text-slate-500">
                  <th className="py-3.5 px-4">ID</th>
                  <th className="py-3.5 px-4">Patient Name</th>
                  <th className="py-3.5 px-4">Age / Gender</th>
                  <th className="py-3.5 px-4">Vitals (BP/Chol/Sugar)</th>
                  <th className="py-3.5 px-4">AI Risk Stratification</th>
                  <th className="py-3.5 px-4">Triage Dept</th>
                  <th className="py-3.5 px-4">No-Show Risk</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((patient) => {
                  const isHigh = patient.risk_score >= 0.7
                  return (
                    <tr
                      key={patient.id}
                      className="hover:bg-blue-50/30 transition-colors cursor-pointer group"
                    >
                      <td className="py-3.5 px-4 font-mono font-semibold text-slate-500">
                        #{patient.id}
                      </td>
                      <td className="py-3.5 px-4">
                        <Link to={`/patients/${patient.id}`} className="font-bold text-slate-800 hover:text-blue-600">
                          {patient.name}
                        </Link>
                        {patient.phone && (
                          <span className="block text-[11px] text-slate-400 font-mono">
                            {patient.phone}
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        {patient.age} yrs • {patient.gender === 'M' ? 'Male' : 'Female'}
                      </td>
                      <td className="py-3.5 px-4 text-xs font-mono text-slate-600">
                        <div>BP: <span className="font-semibold">{patient.blood_pressure}</span></div>
                        <div>Chol: <span className="font-semibold">{patient.cholesterol}</span> | Sugar: <span className="font-semibold">{patient.blood_sugar}</span></div>
                      </td>
                      <td className="py-3.5 px-4">
                        <RiskBadge score={patient.risk_score} />
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-block px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold">
                          {patient.triage_dept || 'General'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                          patient.noshow_risk === 'High' ? 'text-rose-600 bg-rose-50' :
                          patient.noshow_risk === 'Medium' ? 'text-amber-600 bg-amber-50' :
                          'text-emerald-600 bg-emerald-50'
                        }`}>
                          {patient.noshow_risk || 'Low'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link
                            to={`/patients/${patient.id}`}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="View XAI Details"
                          >
                            <Eye className="w-4 h-4" />
                          </Link>
                          <Link
                            to="/schedule"
                            state={{ selectedPatientId: patient.id }}
                            className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                            title="Schedule Appointment"
                          >
                            <CalendarPlus className="w-4 h-4" />
                          </Link>
                          <button
                            onClick={(e) => handleDelete(patient.id, e)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  )
}
