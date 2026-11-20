import React from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { 
  Activity, 
  Users, 
  Calendar, 
  Clock, 
  LogOut, 
  ShieldCheck, 
  HeartPulse,
  Sliders,
  Brain,
  FlaskConical
} from 'lucide-react'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: Activity },
    { name: 'AI Diagnosis', path: '/ai-diagnosis', icon: Brain },
    { name: 'Patients', path: '/patients', icon: Users },
    { name: 'Appointments', path: '/appointments', icon: Calendar },
    { name: 'Smart Scheduler', path: '/schedule', icon: Clock },
    { name: 'Simulation', path: '/simulation', icon: Sliders },
    { name: 'Results', path: '/research', icon: FlaskConical },
  ]

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        
        {/* Brand */}
        <Link to="/dashboard" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
            <HeartPulse className="w-6 h-6" />
          </div>
          <div>
            <span className="font-bold text-lg text-slate-800 tracking-tight flex items-center gap-1.5 whitespace-nowrap">
              XAI Healthcare <span className="text-blue-600 font-extrabold">DSS</span>
            </span>
            <span className="hidden xl:block text-[11px] text-slate-400 font-medium leading-none whitespace-nowrap">
              D1 MLP · Kernel SHAP · Triage · Scheduler
            </span>
          </div>
        </Link>

        {/* Navigation links */}
        <nav className="hidden lg:flex items-center gap-0.5">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                {item.name}
              </NavLink>
            )
          })}
        </nav>

        {/* User profile & actions */}
        <div className="flex items-center gap-3">
          <div className="hidden 2xl:flex flex-col text-right">
            <span className="text-xs font-semibold text-slate-800">
              {user?.username || 'Clinician'}
            </span>
            <span className="text-[10px] uppercase font-bold text-blue-600 tracking-wider">
              {user?.role || 'Physician'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <ShieldCheck className="w-3.5 h-3.5" />
              DPDP 2023
            </span>

            <button
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
