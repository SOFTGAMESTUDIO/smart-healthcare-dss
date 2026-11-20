import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axios'
import SymptomCheckerWizard from '../components/SymptomCheckerWizard'
import { 
  Users, 
  AlertCircle, 
  Calendar, 
  Activity, 
  Plus, 
  Sparkles, 
  Clock, 
  TrendingUp,
  BrainCircuit
} from 'lucide-react'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts'

export default function DashboardPage() {
  const [summary, setSummary] = useState(null)
  const [featureImportance, setFeatureImportance] = useState([])
  const [triageDistribution, setTriageDistribution] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        const [sumRes, fiRes, triRes] = await Promise.all([
          api.get('/api/analytics/summary'),
          api.get('/api/analytics/feature-importance'),
          api.get('/api/analytics/triage-distribution'),
        ])
        setSummary(sumRes.data)
        setFeatureImportance(fiRes.data.features || [])
        setTriageDistribution(triRes.data || [])
      } catch (err) {
        console.error('Error fetching dashboard analytics:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium text-slate-500">Loading AI analytics & metrics...</p>
      </div>
    )
  }

  const statCards = [
    {
      title: 'Total Patients',
      value: summary?.total_patients ?? 0,
      icon: Users,
      color: 'blue',
      change: '+12% this month',
    },
    {
      title: 'High Risk Alerts',
      value: summary?.high_risk ?? 0,
      icon: AlertCircle,
      color: 'rose',
      change: 'Priority triage required',
    },
    {
      title: 'Active Appointments',
      value: summary?.scheduled_appointments ?? 0,
      icon: Calendar,
      color: 'emerald',
      change: `${summary?.total_appointments ?? 0} total booked`,
    },
    {
      title: 'Disease Positive',
      value: summary?.disease_positive ?? 0,
      icon: Activity,
      color: 'amber',
      change: 'Detected by XGBoost ML',
    },
  ]

  const colorMap = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    rose: 'bg-rose-50 text-rose-600 border-rose-200',
    emerald: 'bg-emerald-50 text-emerald-600 border-emerald-200',
    amber: 'bg-amber-50 text-amber-600 border-amber-200',
  }

  return (
    <div className="space-y-6">
      
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-gradient-to-r from-blue-700 via-blue-800 to-indigo-900 rounded-2xl p-6 text-white shadow-md">
        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 backdrop-blur-md mb-2 border border-white/20">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" /> Explainable AI Decision Support
          </span>
          <h1 className="text-2xl font-bold tracking-tight">Clinical Triage & Appointment Dashboard</h1>
          <p className="text-sm text-blue-100 mt-1 max-w-2xl">
            Real-time inference using warm-cached XGBoost + TreeSHAP models, OR-Tools CP-SAT scheduler, and DPDP-compliant local SQLite3 WAL storage.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            to="/patients/new"
            className="flex items-center gap-2 px-4 py-2.5 bg-white text-blue-800 hover:bg-blue-50 font-semibold rounded-xl text-sm shadow transition-all hover:scale-[1.02]"
          >
            <Plus className="w-4 h-4" /> New Patient
          </Link>
          <Link
            to="/schedule"
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600/80 hover:bg-blue-600 border border-white/20 text-white font-semibold rounded-xl text-sm backdrop-blur transition-all"
          >
            <Clock className="w-4 h-4" /> Auto-Schedule
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, i) => {
          const Icon = card.icon
          return (
            <div key={i} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {card.title}
                </span>
                <div className={`p-2 rounded-xl border ${colorMap[card.color]}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-slate-800 tracking-tight">
                  {card.value}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500 flex items-center gap-1 font-medium">
                <TrendingUp className="w-3 h-3 text-slate-400" />
                {card.change}
              </p>
            </div>
          )
        })}
      </div>

      {/* Symptom Checker Wizard (131 Symptoms & SHAP) */}
      <SymptomCheckerWizard />

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Risk Distribution PieChart */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <div className="mb-2">
            <h3 className="text-base font-bold text-slate-800">Risk Stratification</h3>
            <p className="text-xs text-slate-500">Patient population segmented by XGBoost risk score</p>
          </div>
          <div className="flex-1 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={summary?.risk_distribution || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {(summary?.risk_distribution || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Global Feature Importance */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col lg:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-blue-600" /> Global Feature Importance (XGBoost)
              </h3>
              <p className="text-xs text-slate-500">Top clinical predictors determining diagnosis risk</p>
            </div>
          </div>
          <div className="flex-1 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={featureImportance}
                margin={{ top: 10, right: 20, left: 20, bottom: 25 }}
              >
                <XAxis 
                  dataKey="feature" 
                  angle={-25} 
                  textAnchor="end" 
                  tick={{ fontSize: 10, fill: '#64748b' }} 
                />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip 
                  formatter={(val) => [(val * 100).toFixed(1) + '%', 'Importance']}
                />
                <Bar dataKey="importance" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Triage Department Distribution */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
        <div className="mb-4">
          <h3 className="text-base font-bold text-slate-800">Rule-Based Triage Department Allocation</h3>
          <p className="text-xs text-slate-500">Independent 8-department triage classification based on symptoms & vitals</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {triageDistribution.map((item, idx) => (
            <div key={idx} className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-center">
              <span className="block text-xs font-semibold text-slate-600 truncate">{item.department}</span>
              <span className="block text-xl font-extrabold text-blue-600 mt-1">{item.count}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
