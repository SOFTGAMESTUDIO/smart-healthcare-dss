import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/axios'
import { 
  Heart, 
  ArrowLeft, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle,
  Activity,
  ShieldCheck
} from 'lucide-react'

export default function NewPatientPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const [form, setForm] = useState({
    name: '',
    phone: '',
    age: 55,
    gender: 'M',
    blood_pressure: 135,
    cholesterol: 220,
    blood_sugar: 110,
    bmi: 26.5,
    smoking: 0,
    family_history: 0,
    chest_pain_type: 0,
    ecg_result: 0,
    symptoms_text: '',
  })

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (checked ? 1 : 0) : value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = {
        name: form.name,
        phone: form.phone || null,
        age: parseInt(form.age, 10),
        gender: form.gender,
        blood_pressure: parseFloat(form.blood_pressure),
        cholesterol: parseFloat(form.cholesterol),
        blood_sugar: parseFloat(form.blood_sugar),
        bmi: parseFloat(form.bmi),
        smoking: parseInt(form.smoking, 10),
        family_history: parseInt(form.family_history, 10),
        chest_pain_type: parseInt(form.chest_pain_type, 10),
        ecg_result: parseInt(form.ecg_result, 10),
        symptoms_text: form.symptoms_text || null,
      }
      const res = await api.post('/api/patients/', payload)
      setResult(res.data)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to register patient.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <Link
          to="/patients"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Patients
        </Link>
        <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
          <ShieldCheck className="w-3.5 h-3.5" /> DPDP Act 2023 Encrypted Storage
        </span>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Register New Clinical Record</h1>
          <p className="text-sm text-slate-500 mt-1">
            Clinical vitals will be fed into the XGBoost disease model and KernelExplainer SHAP pipeline upon submission.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* Section 1: Demographics */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              1. Patient Demographics & Encrypted Identifiers
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  name="name"
                  required
                  placeholder="e.g. Ramesh Kumar"
                  value={form.name}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Phone</label>
                <input
                  type="text"
                  name="phone"
                  placeholder="+91-9876543210"
                  value={form.phone}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm font-mono"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Age *</label>
                  <input
                    type="number"
                    name="age"
                    min="1"
                    max="120"
                    required
                    value={form.age}
                    onChange={handleChange}
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Gender *</label>
                  <select
                    name="gender"
                    value={form.gender}
                    onChange={handleChange}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm bg-white"
                  >
                    <option value="M">Male (M)</option>
                    <option value="F">Female (F)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Clinical Vitals */}
          <div className="pt-4 border-t border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              2. Clinical Vitals & Lab Biomarkers
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Blood Pressure (mmHg)</label>
                <input
                  type="number"
                  step="0.1"
                  name="blood_pressure"
                  required
                  value={form.blood_pressure}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Cholesterol (mg/dL)</label>
                <input
                  type="number"
                  step="0.1"
                  name="cholesterol"
                  required
                  value={form.cholesterol}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Fasting Blood Sugar</label>
                <input
                  type="number"
                  step="0.1"
                  name="blood_sugar"
                  required
                  value={form.blood_sugar}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Body Mass Index (BMI)</label>
                <input
                  type="number"
                  step="0.1"
                  name="bmi"
                  required
                  value={form.bmi}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm font-mono"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Diagnostic Categories */}
          <div className="pt-4 border-t border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              3. Cardiology Phenotyping & Risk Factors
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Chest Pain Presentation</label>
                <select
                  name="chest_pain_type"
                  value={form.chest_pain_type}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm bg-white"
                >
                  <option value={0}>0 - Typical Angina</option>
                  <option value={1}>1 - Atypical Angina</option>
                  <option value={2}>2 - Non-Anginal Pain</option>
                  <option value={3}>3 - Asymptomatic / Severe Silent</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Resting ECG Results</label>
                <select
                  name="ecg_result"
                  value={form.ecg_result}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm bg-white"
                >
                  <option value={0}>0 - Normal Resting</option>
                  <option value={1}>1 - ST-T Wave Abnormality</option>
                  <option value={2}>2 - Left Ventricular Hypertrophy</option>
                </select>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-6">
              <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  name="smoking"
                  checked={form.smoking === 1}
                  onChange={handleChange}
                  className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
                />
                Active Smoker / Tobacco History
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  name="family_history"
                  checked={form.family_history === 1}
                  onChange={handleChange}
                  className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
                />
                Family History of Premature CAD
              </label>
            </div>
          </div>

          {/* Section 4: Symptoms text for Triage */}
          <div className="pt-4 border-t border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              4. Patient-Reported Symptoms (Rule-Based Triage)
            </h3>
            <textarea
              name="symptoms_text"
              rows={3}
              placeholder="e.g. Sharp substernal chest discomfort on climbing stairs, shortness of breath, palpitation..."
              value={form.symptoms_text}
              onChange={handleChange}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Keywords are parsed by the independent 8-department triage engine to flag emergency red flags.
            </p>
          </div>

          {/* Action buttons */}
          <div className="pt-4 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate('/patients')}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-xl text-sm shadow transition-all hover:scale-[1.01]"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Running AI & Triage...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-300" />
                  Register & Run Decision Support
                </>
              )}
            </button>
          </div>
        </form>

        {/* Prediction Modal / Results Banner */}
        {result && (
          <div className="mt-8 p-6 bg-slate-50 border border-blue-200 rounded-2xl animate-fade-in">
            <div className="flex items-start justify-between">
              <div>
                <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full mb-2">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Clinical Prediction Generated
                </span>
                <h3 className="text-xl font-extrabold text-slate-800">{result.name}</h3>
                <p className="text-xs text-slate-500">Record ID: #{result.id} • Triage Department: <strong className="text-blue-700">{result.triage_dept}</strong></p>
              </div>
              <div className="text-right">
                <span className="text-xs font-bold text-slate-400 uppercase">Risk Score</span>
                <div className="text-2xl font-black text-rose-600">
                  {((result.risk_score || 0) * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
              <Link
                to={`/patients/${result.id}`}
                className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors"
              >
                Inspect SHAP Explanations →
              </Link>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
