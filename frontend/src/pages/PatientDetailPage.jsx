import React, { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../api/axios'
import RiskBadge from '../components/RiskBadge'
import RiskGauge from '../components/RiskGauge'
import SHAPWaterfallChart from '../components/SHAPWaterfallChart'
import { 
  ArrowLeft, 
  CalendarPlus, 
  RefreshCw, 
  ShieldCheck, 
  AlertTriangle,
  HeartPulse,
  Activity,
  FileText,
  UserCheck
} from 'lucide-react'

export default function PatientDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [patient, setPatient] = useState(null)
  const [loading, setLoading] = useState(true)
  const [predicting, setPredicting] = useState(false)

  const fetchPatient = async () => {
    try {
      setLoading(true)
      const res = await api.get(`/api/patients/${id}`)
      setPatient(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPatient()
  }, [id])

  const handleRerunPrediction = async () => {
    try {
      setPredicting(true)
      const res = await api.post(`/api/patients/${id}/predict`)
      setPatient(res.data)
    } catch (err) {
      alert('Failed to re-run prediction.')
    } finally {
      setPredicting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium text-slate-500">Loading patient decision record...</p>
      </div>
    )
  }

  if (!patient) {
    return (
      <div className="text-center p-12 bg-white rounded-2xl border border-slate-200">
        <p className="font-semibold text-slate-700">Patient #{id} not found.</p>
        <Link to="/patients" className="text-blue-600 text-sm font-semibold mt-2 inline-block">
          Return to Patients
        </Link>
      </div>
    )
  }

  const isHighRisk = patient.risk_score >= 0.7

  return (
    <div className="space-y-6">
      
      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <Link
          to="/patients"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Directory
        </Link>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRerunPrediction}
            disabled={predicting}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-sm rounded-xl transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${predicting ? 'animate-spin' : ''}`} />
            Re-evaluate Model
          </button>
          
          <Link
            to="/schedule"
            state={{ selectedPatientId: patient.id }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl shadow transition-colors"
          >
            <CalendarPlus className="w-4 h-4" /> Book Appointment
          </Link>
        </div>
      </div>

      {/* Main Clinical Summary Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Patient Profile & Vitals */}
        <div className="space-y-6">
          
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-bold text-slate-400 font-mono">#{patient.id}</span>
                <h2 className="text-xl font-extrabold text-slate-800">{patient.name}</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  {patient.age} yrs • {patient.gender === 'M' ? 'Male' : 'Female'}
                </p>
              </div>
              <RiskBadge score={patient.risk_score} />
            </div>

            <div className="pt-3 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                Cardiology Biomarkers
              </span>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block">Blood Pressure</span>
                  <span className="font-extrabold text-slate-800 text-sm">{patient.blood_pressure} <span className="text-[10px] text-slate-400 font-normal">mmHg</span></span>
                </div>
                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block">Cholesterol</span>
                  <span className="font-extrabold text-slate-800 text-sm">{patient.cholesterol} <span className="text-[10px] text-slate-400 font-normal">mg/dL</span></span>
                </div>
                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block">Fasting Sugar</span>
                  <span className="font-extrabold text-slate-800 text-sm">{patient.blood_sugar} <span className="text-[10px] text-slate-400 font-normal">mg/dL</span></span>
                </div>
                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  <span className="text-slate-400 block">BMI</span>
                  <span className="font-extrabold text-slate-800 text-sm">{patient.bmi} <span className="text-[10px] text-slate-400 font-normal">kg/m²</span></span>
                </div>
              </div>
            </div>

            <div className="pt-2">
              <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Smoking Status</span>
                <span className="font-semibold text-slate-700">{patient.smoking ? 'Active Smoker' : 'Non-smoker'}</span>
              </div>
              <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Family History</span>
                <span className="font-semibold text-slate-700">{patient.family_history ? 'Positive (CAD)' : 'Negative'}</span>
              </div>
              <div className="flex items-center justify-between text-xs py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Chest Pain Type</span>
                <span className="font-semibold text-slate-700">Type {patient.chest_pain_type}</span>
              </div>
              <div className="flex items-center justify-between text-xs py-1.5">
                <span className="text-slate-500">ECG Presentation</span>
                <span className="font-semibold text-slate-700">Type {patient.ecg_result}</span>
              </div>
            </div>

            {patient.symptoms_text && (
              <div className="p-3 bg-blue-50/50 rounded-xl border border-blue-100 text-xs">
                <span className="font-bold text-blue-900 block mb-1 flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" /> Symptoms Notes
                </span>
                <p className="text-slate-600 italic">"{patient.symptoms_text}"</p>
              </div>
            )}
          </div>

          {/* Triage & Operational Risk */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Operational Triage Status
            </h4>
            
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-xs text-slate-600 font-medium">Recommended Dept</span>
              <span className="px-2.5 py-1 bg-blue-600 text-white rounded-lg text-xs font-bold">
                {patient.triage_dept || 'General Medicine'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-xs text-slate-600 font-medium">Predicted No-Show Risk</span>
              <span className={`px-2.5 py-1 rounded-lg text-xs font-bold ${
                patient.noshow_risk === 'High' ? 'bg-rose-100 text-rose-800' :
                patient.noshow_risk === 'Medium' ? 'bg-amber-100 text-amber-800' :
                'bg-emerald-100 text-emerald-800'
              }`}>
                {patient.noshow_risk || 'Low'} Risk
              </span>
            </div>
          </div>

        </div>

        {/* Right 2 Columns: Risk Gauge & SHAP Waterfall */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Risk Gauge Header Card */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center gap-6">
            <RiskGauge score={patient.risk_score || 0} size={190} />
            
            <div className="flex-1 space-y-2 text-center sm:text-left">
              <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                <HeartPulse className="w-3.5 h-3.5 text-blue-600" /> Model Diagnosis Prediction
              </span>
              <h3 className="text-2xl font-black text-slate-800">
                {patient.disease_predicted === 1 ? 'Positive for Ischemic Risk' : 'Low Evidence of Ischemia'}
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Evaluated via XGBoost Classifier. Feature attribution calculated on the fly using TreeSHAP KernelExplainer to ensure transparent clinical auditability.
              </p>
              
              {isHighRisk && (
                <div className="mt-2 p-2.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-semibold flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  Urgent priority flag: OR-Tools scheduler will allocate immediate front-of-line consultation slots.
                </div>
              )}
            </div>
          </div>

          {/* Explainable AI SHAP Waterfall Chart */}
          <SHAPWaterfallChart shapValues={patient.shap_values || {}} />

        </div>

      </div>

    </div>
  )
}
