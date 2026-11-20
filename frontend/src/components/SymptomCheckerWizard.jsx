import React, { useState, useEffect } from 'react'
import api from '../api/axios'
import SHAPWaterfallChart from './SHAPWaterfallChart'
import { 
  Search, 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp, 
  X, 
  Stethoscope, 
  Heart, 
  ShieldAlert,
  ArrowRight
} from 'lucide-react'
import { Link } from 'react-router-dom'

export default function SymptomCheckerWizard() {
  const [catalog, setCatalog] = useState(null)
  const [selectedSymptoms, setSelectedSymptoms] = useState([])
  const [search, setSearch] = useState('')
  const [activeGroup, setActiveGroup] = useState('Cardiovascular & Respiratory')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    async function loadCatalog() {
      try {
        const res = await api.get('/api/analytics/symptoms-131')
        setCatalog(res.data)
      } catch (err) {
        console.error('Failed to load symptom catalog:', err)
      }
    }
    loadCatalog()
  }, [])

  const toggleSymptom = (sym) => {
    setSelectedSymptoms(prev =>
      prev.includes(sym) ? prev.filter(s => s !== sym) : [...prev, sym]
    )
  }

  const handlePredict = async () => {
    if (selectedSymptoms.length === 0) return
    setLoading(true)
    setResult(null)
    try {
      const res = await api.post('/api/analytics/predict-symptoms', {
        symptoms: selectedSymptoms
      })
      setResult(res.data)
    } catch (err) {
      console.error(err)
      alert('Prediction failed.')
    } finally {
      setLoading(false)
    }
  }

  const filteredSymptoms = catalog?.all_symptoms?.filter(s =>
    s.toLowerCase().includes(search.toLowerCase())
  ) || []

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 mb-2">
            <Stethoscope className="w-3.5 h-3.5" /> 131-Symptom Diagnostic Intake
          </span>
          <h2 className="text-xl font-bold text-slate-800">Self-Service Symptom & Triage Evaluator</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Select patient complaints. The D1-trained MLP ranks the top-3 conditions, checks uncertainty (symptom count, margin, entropy) and explains the result with Kernel SHAP. Open AI Diagnosis for triage, the reasoning report and clinician feedback.
          </p>
        </div>

        {selectedSymptoms.length > 0 && (
          <button
            onClick={() => setSelectedSymptoms([])}
            className="text-xs font-semibold text-rose-600 hover:underline"
          >
            Clear Selected ({selectedSymptoms.length})
          </button>
        )}
      </div>

      {/* Selected Chips */}
      {selectedSymptoms.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Active Symptoms ({selectedSymptoms.length}):
          </span>
          <div className="flex flex-wrap gap-1.5">
            {selectedSymptoms.map(sym => (
              <span
                key={sym}
                onClick={() => toggleSymptom(sym)}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 hover:bg-rose-50 text-blue-700 hover:text-rose-700 border border-blue-200 hover:border-rose-200 rounded-full text-xs font-semibold cursor-pointer transition-colors"
              >
                {sym.replace(/_/g, ' ')}
                <X className="w-3 h-3" />
              </span>
            ))}
          </div>

          {selectedSymptoms.length < 3 && (
            <p className="text-xs text-amber-600 flex items-center gap-1 font-medium pt-1">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              Caution: Fewer than 3 symptoms will trigger the "Sparse Input / Clinical Review" uncertainty flag.
            </p>
          )}
        </div>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search across 131 symptoms (e.g. chest pain, cough, joint pain, headache)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
        />
      </div>

      {/* Body System Tabs / Search Results */}
      {search.trim().length > 0 ? (
        <div className="space-y-2">
          <span className="text-xs font-bold text-slate-400 uppercase">Search Results:</span>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-56 overflow-y-auto pr-1">
            {filteredSymptoms.map(sym => {
              const isChecked = selectedSymptoms.includes(sym)
              return (
                <button
                  key={sym}
                  onClick={() => toggleSymptom(sym)}
                  className={`p-2 rounded-xl border text-xs font-medium text-left truncate transition-all ${
                    isChecked
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:border-blue-400'
                  }`}
                >
                  {sym.replace(/_/g, ' ')}
                </button>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5 border-b border-slate-100 pb-2">
            {catalog && Object.keys(catalog.grouped_symptoms).map(group => (
              <button
                key={group}
                onClick={() => setActiveGroup(group)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  activeGroup === group
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {group}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-56 overflow-y-auto pr-1">
            {catalog?.grouped_symptoms[activeGroup]?.map(sym => {
              const isChecked = selectedSymptoms.includes(sym)
              return (
                <button
                  key={sym}
                  onClick={() => toggleSymptom(sym)}
                  className={`p-2 rounded-xl border text-xs font-medium text-left truncate transition-all ${
                    isChecked
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:border-blue-400'
                  }`}
                >
                  {sym.replace(/_/g, ' ')}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Action button */}
      <button
        onClick={handlePredict}
        disabled={loading || selectedSymptoms.length === 0}
        className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 text-white font-bold rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Computing Softmax Probabilities & Kernel SHAP...
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 text-amber-300" />
            Evaluate Differential Diagnosis ({selectedSymptoms.length} selected)
          </>
        )}
      </button>

      {/* Results View */}
      {result && (
        <div className="mt-6 pt-6 border-t border-slate-200 space-y-6 animate-fade-in">
          
          {/* Clinical Confidence Flag */}
          {result.low_confidence ? (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl space-y-1">
              <div className="flex items-center gap-2 text-amber-800 font-bold text-sm">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
                <span>Notice: Prediction Flagged for Mandatory Clinical Review</span>
              </div>
              <ul className="text-xs text-amber-700 list-disc list-inside space-y-0.5 mt-1">
                {result.low_confidence_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-emerald-800 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Robust Prediction: Strong margin separation and low entropy.</span>
            </div>
          )}

          {/* Top-3 Disease Cards */}
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">
              Top-3 Differential Conditions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {result.top3_predictions.map((p, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-2xl border transition-all ${
                    idx === 0
                      ? 'border-blue-500 bg-blue-50/30 shadow-md ring-1 ring-blue-500'
                      : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <span className="text-[11px] font-bold text-slate-400">Rank #{idx + 1}</span>
                    <span className="text-lg font-black text-blue-700">{p.percentage}%</span>
                  </div>
                  <h4 className="font-extrabold text-slate-800 text-base mt-1">{p.disease}</h4>
                  <span className="inline-block mt-1 px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[11px] font-semibold">
                    {p.department} • {p.urgency}
                  </span>
                  <p className="mt-2 text-xs text-slate-500 line-clamp-3 leading-relaxed">
                    {p.description}
                  </p>

                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                      Recommended Precautions:
                    </span>
                    <ul className="text-[11px] text-slate-600 space-y-0.5 list-disc list-inside">
                      {p.precautions.slice(0, 2).map((item, i) => (
                        <li key={i} className="truncate">{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Plain English SHAP Attribution Summary */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs text-slate-700 space-y-2">
            <span className="font-bold text-slate-800 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Explainable AI Plain-English Reasoning:
            </span>
            <p className="leading-relaxed italic">"{result.explanation_text}"</p>
          </div>

          {/* Local SHAP Waterfall */}
          <SHAPWaterfallChart shapValues={result.shap_attribution.all_local} />

          {/* Booking CTA */}
          <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl">
            <div>
              <h4 className="font-bold text-blue-900 text-sm">Proceed to Smart Appointment Booking</h4>
              <p className="text-xs text-blue-700">Priority slot will be allocated based on clinical urgency.</p>
            </div>
            <Link
              to="/schedule"
              className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow transition-colors"
            >
              Book Slot <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

        </div>
      )}

    </div>
  )
}
