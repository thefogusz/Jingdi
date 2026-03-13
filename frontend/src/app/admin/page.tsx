'use client';

import { useEffect, useState, FormEvent, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  Globe,
  MessageSquare,
  Power,
  PowerOff,
  RefreshCw,
  Search,
  Server,
  Terminal,
  LogOut,
  Cpu,
  Zap,
  BarChart3,
  Box
} from 'lucide-react';

// Interfaces for our data
interface SystemHealth {
  [key: string]: string;
}

interface RecentError {
  time: string;
  endpoint: string;
  error: string;
}

interface TrafficRecord {
  time: string;
  endpoint: string;
  query: string;
  cost: number;
  status: string;
}

interface FeedbackRecord {
  time: string;
  is_helpful: boolean;
  reason: string;
  details: string;
  query: string;
  endpoint: string;
}

interface ApiRecord {
  name: string;
  status: string;
  cost: number;
}

interface CaseRecord {
  case_id: string;
  time: string;
  query: string;
  apis: ApiRecord[];
  total_cost: number;
  success: boolean;
}

interface BrandTotal {
  brand: string;
  calls: number;
  cost: number;
}

interface DashboardStats {
  total_requests: number;
  total_cost_usd: number;
  success_rate_percent: number;
  recent_errors: RecentError[];
  system_health: SystemHealth;
  kill_switch_active: boolean;
  recent_traffic: TrafficRecord[];
  recent_feedback: FeedbackRecord[];
  api_breakdown?: any[];
  api_brand_totals?: BrandTotal[];
  cases?: CaseRecord[];
  r2_public_url?: string;
  r2_bucket?: string;
  r2_account_prefix?: string;
}

// Brand color config
const BRAND_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  Gemini:    { bg: 'rgba(96,165,250,0.12)',  border: 'rgba(96,165,250,0.35)',  text: '#93c5fd', dot: '#60a5fa' },
  Grok:      { bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.35)', text: '#c4b5fd', dot: '#a78bfa' },
  SerpApi:   { bg: 'rgba(251,191,36,0.12)',  border: 'rgba(251,191,36,0.35)',  text: '#fcd34d', dot: '#fbbf24' },
  VisionAPI: { bg: 'rgba(52,211,153,0.12)',  border: 'rgba(52,211,153,0.35)',  text: '#6ee7b7', dot: '#34d399' },
  Tavily:    { bg: 'rgba(236,72,153,0.12)',  border: 'rgba(236,72,153,0.35)',  text: '#f9a8d4', dot: '#ec4899' },
  Cloudflare:{ bg: 'rgba(249,115,22,0.12)',  border: 'rgba(249,115,22,0.35)',  text: '#fdba74', dot: '#f97316' },
};

function BrandBadge({ name }: { name: string }) {
  const c = BRAND_COLORS[name] ?? { bg: 'rgba(255,255,255,0.07)', border: 'rgba(255,255,255,0.15)', text: '#e2e8f0', dot: '#94a3b8' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '3px 9px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: 600,
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
    }}>
      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: c.dot, display: 'inline-block', flexShrink: 0 }} />
      {name}
    </span>
  );
}

function QueryThumbnail({ query, size = "md", r2BaseUrl }: { query: string, size?: "sm" | "md" | "lg", r2BaseUrl?: string }) {
  // Regex to catch [Image Upload], [Screenshot], image: prefix, or bare image filenames (supports underscores)
  const m = query.match(/\[(?:Image Upload|Screenshot)\]\s*([\w.-]+\.(?:jpg|jpeg|png|webp|gif))/i) ||
            query.match(/image:\s*([\w.-]+\.(?:jpg|jpeg|png|webp|gif))/i) ||
            query.match(/([\w-]{8,}\.(?:jpg|jpeg|png|webp|gif))/i);
            
  if (!m) return <span className="truncate flex-1">{query}</span>;

  const filename = m[1];
  // Prioritize direct R2 URL if available, fallback to proxy
  const imgUrl = r2BaseUrl ? `${r2BaseUrl.replace(/\/$/, '')}/${filename}` : `/api/admin/image/${filename}`;
  
  const cleanText = query
    .replace(m[0], '')
    .replace('Headline/Text extracted from image:', '')
    .replace('Image processing', '')
    .trim();

  const imgClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8",
    lg: "h-10 w-10"
  }[size];

  const scale = {
    sm: "hover:scale-[6]",
    md: "hover:scale-[5]",
    lg: "hover:scale-[4]"
  }[size];

  return (
    <div className="flex items-center gap-2 min-w-0 flex-1">
      <span className="truncate text-neutral-400 text-[10px] bg-white/5 px-1.5 py-0.5 rounded border border-white/5" title={query}>
        {cleanText || 'Image'}
      </span>
      <a href={imgUrl} target="_blank" rel="noopener noreferrer" className="shrink-0 group/img relative" title={`View original: ${filename}`}>
        <img 
          src={imgUrl} 
          className={`${imgClasses} object-cover rounded-md border border-neutral-700 ${scale} transform origin-left transition-all shadow-lg hover:z-50 relative bg-neutral-800`} 
          alt={`Image: ${filename}`} 
          onError={(e) => { 
            // If direct URL fails, try proxy as fallback once
            if (r2BaseUrl && e.currentTarget.src.includes(r2BaseUrl)) {
              e.currentTarget.src = `/api/admin/image/${filename}`;
            } else {
              // Final failure: show border but mark as broken
              e.currentTarget.style.opacity = '0.3';
            }
          }}
        />
      </a>
    </div>
  );
}

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [togglingKillSwitch, setTogglingKillSwitch] = useState(false);
  
  // Chat related
  const [chatMessages, setChatMessages] = useState<{role: 'user' | 'assistant', content: string}[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const getPassword = () => Cookies.get('admin_session');

  const fetchStats = async () => {
    setLoading(true);
    setError('');
    const pw = getPassword();
    if (!pw) {
      router.push('/admin/login');
      return;
    }

    try {
      const res = await fetch(`/api/admin/stats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw }),
      });

      if (!res.ok) {
        if (res.status === 403) {
          handleLogout();
        } else {
          throw new Error(`Server returned ${res.status}`);
        }
      }

      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error(err);
      setError('ไม่สามารถโหลดข้อมูลสถิติได้ โปรดตรวจสอบการเชื่อมต่อกับ Backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Refresh every 30 seconds automatically
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    Cookies.remove('admin_session');
    router.push('/admin/login');
  };

  const toggleKillSwitch = async () => {
    if (!stats) return;
    const pw = getPassword();
    if (!pw) return;

    // Confirm before action
    const actionStr = stats.kill_switch_active 
      ? "เปิดระบบกลับสู่สภาวะปกติ" 
      : "ตัดการทำงานของะบบ (Kill Switch)";
      
    if (!confirm(`คุณแน่ใจหรือไม่ที่จะ ${actionStr}?`)) return;

    setTogglingKillSwitch(true);
    try {
      const targetState = !stats.kill_switch_active;
      const res = await fetch(`/api/admin/toggle-killswitch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw, active: targetState }),
      });

      if (res.ok) {
        await fetchStats(); // Reload stats immediately
      } else {
        alert('เกิดข้อผิดพลาดในการเปลี่ยนสถานะระบบ');
      }
    } catch (err) {
      alert('ไม่สามารถเชื่อมต่อระบบหลังบ้านได้');
    } finally {
      setTogglingKillSwitch(false);
    }
  };

  const submitChat = async (e: FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    
    const pw = getPassword();
    if (!pw) return;

    const query = chatInput;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: query }]);
    setChatLoading(true);

    try {
      const res = await fetch(`/api/admin/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw, message: query }),
      });

      if (res.ok) {
        const data = await res.json();
        setChatMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
        
        // Auto scroll to latest
        setTimeout(() => {
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      } else {
        throw new Error('Chat API returned error');
      }
    } catch (err) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: '⚠️ ไม่สามารถติดต่อ Grok AI Assistant ได้ในขณะนี้ โปรดลองใหม่อีกครั้ง' }]);
    } finally {
      setChatLoading(false);
    }
  };

  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mb-4" />
        <p className="text-neutral-400">กำลังโหลดข้อมูลระบบ...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-200 font-sans">
      {/* Navbar */}
      <nav className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Activity className="w-6 h-6 text-blue-500" />
              <span className="font-bold text-lg text-white">Jingdi Command Center</span>
            </div>
            <div className="flex items-center space-x-4">
              <button 
                onClick={toggleKillSwitch}
                disabled={togglingKillSwitch}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                  stats?.kill_switch_active
                    ? 'bg-red-500/20 border-red-500/50 text-red-400 hover:bg-red-500/30'
                    : 'bg-neutral-800/50 border-neutral-700 text-neutral-400 hover:text-white hover:bg-neutral-800'
                }`}
                title={stats?.kill_switch_active ? "Resume System Service" : "Activate Kill Switch (Pause System)"}
              >
                {togglingKillSwitch ? <RefreshCw className="w-4 h-4 animate-spin" /> : stats?.kill_switch_active ? <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" /> : <Power className="w-4 h-4" />}
                <span className="hidden sm:inline-block">{stats?.kill_switch_active ? 'SYSTEM PAUSED' : 'Kill Switch'}</span>
              </button>
              <button 
                onClick={fetchStats}
                className="p-2 text-neutral-400 hover:text-white rounded-lg hover:bg-neutral-800 transition-colors tooltip tooltip-bottom"
                title="Refresh Data"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <button 
                onClick={handleLogout}
                className="flex items-center space-x-2 px-3 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm font-medium">Log out</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-8 flex items-start space-x-3 text-red-400">
            <AlertTriangle className="w-6 h-6 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {/* Quick Stats Grid - 4 columns */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          
          {/* Card 1: Total Requests */}
          <div className="bg-neutral-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 relative overflow-hidden group shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:border-blue-500/30 transition-all duration-300">
            <div className="absolute -top-10 -right-10 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500">
              <Search className="w-40 h-40 text-blue-500" />
            </div>
            <div className="relative z-10 flex flex-col h-full justify-between">
              <div>
                <p className="text-neutral-400 text-sm font-medium mb-1">Total Requests</p>
                <h3 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white to-neutral-400 tracking-tight">
                  {stats?.total_requests?.toLocaleString() || 0}
                </h3>
              </div>
              <div className="mt-4 flex items-center text-sm">
                <div className="flex items-center text-emerald-400 font-medium bg-emerald-400/10 px-3 py-1 rounded-full border border-emerald-400/20 backdrop-blur-sm">
                  <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                  Success: {stats?.success_rate_percent || 0}%
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Estimated API Cost */}
          <div className="bg-neutral-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 relative overflow-hidden group shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:border-purple-500/30 transition-all duration-300">
            <div className="absolute -top-10 -right-10 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500">
              <Database className="w-40 h-40 text-purple-500" />
            </div>
            <div className="relative z-10 flex flex-col h-full justify-between">
              <div>
                <p className="text-neutral-400 text-sm font-medium mb-1">Total API Cost</p>
                <h3 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-br from-purple-400 to-white tracking-tight">
                  ${stats?.total_cost_usd?.toFixed(4) || '0.0000'}
                </h3>
              </div>
              <div className="mt-4 text-xs text-neutral-500">
                Cost aggregated across all Tier 1 and Tier 2 AI models.
              </div>
            </div>
          </div>
          
          {/* Card 3: API Brand Totals */}
          <div className="bg-neutral-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 relative overflow-hidden group shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:border-violet-500/30 transition-all duration-300 flex flex-col">
            <div className="absolute -top-8 -right-8 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500">
              <Cpu className="w-36 h-36 text-violet-400" />
            </div>
            <div className="relative z-10 flex flex-col h-full">
              <p className="text-neutral-400 text-sm font-medium mb-3 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-violet-400" /> API Brands Used
              </p>
              <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5">
                {stats?.api_brand_totals && stats.api_brand_totals.length > 0 ? (
                  stats.api_brand_totals.map((item: BrandTotal, idx: number) => {
                    const c = BRAND_COLORS[item.brand] ?? BRAND_COLORS['Gemini'];
                    return (
                      <div key={idx} className="flex justify-between items-center p-2 rounded-xl border border-white/5"
                        style={{ background: c.bg, borderColor: c.border }}>
                        <div className="flex items-center gap-1.5">
                          <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: c.dot, display: 'inline-block', flexShrink: 0 }} />
                          <span className="text-[11px] font-semibold" style={{ color: c.text }}>{item.brand}</span>
                        </div>
                        <div className="flex items-center gap-2 text-[10px]">
                          <span className="text-neutral-400">{item.calls}x</span>
                          <span className="font-mono font-bold" style={{ color: c.text }}>${item.cost.toFixed(4)}</span>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-neutral-600 text-center italic py-4 text-xs">No API calls logged yet</div>
                )}
              </div>
            </div>
          </div>

          {/* Card 4: System Health */}
          <div className="bg-neutral-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 relative flex flex-col shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:border-emerald-500/30 transition-all duration-300">
              <h3 className="text-neutral-400 text-sm font-medium mb-3 flex items-center">
                <Activity className="w-4 h-4 mr-2 text-emerald-500" />
                Service Health
              </h3>
              <div className="flex flex-col space-y-2 mt-1">
                {Object.entries(stats?.system_health || {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-center bg-black/20 px-3 py-2 rounded-xl border border-white/5">
                    <span className="text-neutral-300 text-xs capitalize">{key.replace('_', ' ')}</span>
                    <div className="flex items-center">
                      <div className={`w-2 h-2 rounded-full mr-1.5 ${value === 'Healthy' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)] animate-pulse'}`} />
                      <span className={`text-[10px] font-medium ${value === 'Healthy' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {value as string}
                      </span>
                    </div>
                  </div>
                ))}
                {stats?.r2_bucket && (
                  <div className="mt-2 pt-2 border-t border-white/5 space-y-1.5">
                    <div className="flex justify-between items-center px-1">
                      <span className="text-[9px] text-neutral-500 uppercase font-bold tracking-wider">R2 Bucket</span>
                      <span className="text-[10px] font-mono text-neutral-300">{stats.r2_bucket}</span>
                    </div>
                    <div className="flex justify-between items-center px-1">
                      <span className="text-[9px] text-neutral-500 uppercase font-bold tracking-wider">R2 Account</span>
                      <span className="text-[10px] font-mono text-neutral-300">{stats.r2_account_prefix}</span>
                    </div>
                  </div>
                )}
              </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Data Tables (Spans 2 columns) */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* User Feedback */}
            <div className="bg-neutral-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
              <h3 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400 mb-6 flex items-center">
                <MessageSquare className="w-6 h-6 mr-3 text-purple-400" />
                Latest User Feedback
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {stats?.recent_feedback?.slice(0, 4).map((fb: FeedbackRecord, idx: number) => (
                  <div key={idx} className="bg-black/30 border border-white/5 rounded-2xl p-5 transition-all hover:border-purple-500/30 hover:bg-black/50 group">
                    <div className="flex items-center justify-between mb-3">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-semibold tracking-wide flex items-center ${
                        fb.is_helpful ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-orange-500/10 text-orange-400 border border-orange-500/20'
                      }`}>
                        {fb.is_helpful ? <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> : <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />}
                        {fb.is_helpful ? 'Helpful' : 'Not Helpful'}
                      </span>
                      <span className="text-[11px] font-medium text-neutral-500 flex items-center">
                         <div className="w-1.5 h-1.5 rounded-full bg-neutral-600 mr-2" />
                         {new Date(fb.time).toLocaleTimeString('th-TH', {hour: '2-digit', minute:'2-digit'})}
                      </span>
                    </div>
                    {fb.reason && fb.reason !== '-' && (
                      <p className="text-sm font-medium text-neutral-200 mb-1.5">Reason: <span className="text-orange-300 font-normal">{fb.reason}</span></p>
                    )}
                    {fb.details && fb.details !== '-' && (
                      <div className="bg-white/5 rounded-xl p-3 mb-3 border border-white/5">
                        <p className="text-xs text-neutral-300 leading-relaxed italic">"{fb.details}"</p>
                      </div>
                    )}
                    <div className="mt-3 text-xs text-neutral-500 font-mono truncate pt-3 border-t border-white/5 flex items-center group-hover:text-neutral-400 transition-colors">
                      <span className="text-neutral-500 mr-2 font-sans font-medium">{fb.endpoint.replace('/api/', '')}</span>
                      <QueryThumbnail query={fb.query} size="sm" r2BaseUrl={stats?.r2_public_url} />
                    </div>
                  </div>
                ))}
                {(!stats?.recent_feedback || stats.recent_feedback.length === 0) && (
                  <div className="col-span-1 md:col-span-2 py-12 flex flex-col items-center justify-center text-neutral-500 bg-black/20 rounded-2xl border border-white/5 border-dashed">
                    <MessageSquare className="w-8 h-8 mb-3 opacity-20" />
                    <span>No feedback received yet</span>
                  </div>
                )}
              </div>
            </div>
            
            {/* Recent Traffic Table */}
            <div className="bg-neutral-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
              <h3 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400 mb-6 flex items-center">
                <Server className="w-6 h-6 mr-3 text-blue-400" />
                Live API Traffic
              </h3>
              
              <div className="overflow-x-auto rounded-2xl border border-white/5 bg-black/20">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="text-[10px] text-neutral-500 uppercase tracking-wider bg-black/40 border-b border-white/5">
                    <tr>
                      <th className="px-5 py-4 font-semibold">Time</th>
                      <th className="px-5 py-4 font-semibold">Endpoint</th>
                      <th className="px-5 py-4 font-semibold w-1/2">Query Snippet</th>
                      <th className="px-5 py-4 font-semibold text-right">Cost</th>
                      <th className="px-5 py-4 font-semibold text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {stats?.recent_traffic?.map((request: TrafficRecord, idx: number) => (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors group">
                        <td className="px-5 py-4 whitespace-nowrap text-neutral-400 text-xs font-medium">
                          {new Date(request.time).toLocaleTimeString('th-TH')}
                        </td>
                        <td className="px-5 py-4 font-mono text-xs text-blue-400/80 group-hover:text-blue-400 transition-colors">
                          {request.endpoint.replace('/api/', '')}
                        </td>
                        <td className="px-5 py-4 max-w-xs text-neutral-300">
                          <QueryThumbnail query={request.query} size="md" r2BaseUrl={stats?.r2_public_url} />
                        </td>
                        <td className="px-5 py-4 font-mono text-[11px] text-emerald-400/80 group-hover:text-emerald-400 text-right transition-colors">
                          ${request.cost.toFixed(4)}
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wider inline-block ${
                            request.status === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}>
                            {request.status.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {(!stats?.recent_traffic || stats.recent_traffic.length === 0) && (
                      <tr>
                        <td colSpan={5} className="px-5 py-12 text-center text-neutral-500">
                          <Server className="w-8 h-8 mx-auto mb-3 opacity-20" />
                          No traffic recorded yet
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* === Cases API Breakdown Table === */}
            <div className="bg-neutral-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
              <h3 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-fuchsia-400 mb-2 flex items-center">
                <BarChart3 className="w-6 h-6 mr-3 text-violet-400" />
                Cases — API Pipeline Breakdown
              </h3>
              <p className="text-neutral-500 text-xs mb-5">แต่ละ case คือ 1 การตรวจสอบ — แสดง API ที่ถูกเรียกในแต่ละขั้นตอน</p>
              
              <div className="overflow-x-auto rounded-2xl border border-white/5 bg-black/20">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="text-[10px] text-neutral-500 uppercase tracking-wider bg-black/40 border-b border-white/5">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Time</th>
                      <th className="px-4 py-3 font-semibold">Query</th>
                      <th className="px-4 py-3 font-semibold">APIs Used (Pipeline)</th>
                      <th className="px-4 py-3 font-semibold text-right">Cost</th>
                      <th className="px-4 py-3 font-semibold text-center">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {stats?.cases?.map((c: CaseRecord, idx: number) => (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors group">
                        <td className="px-4 py-3 whitespace-nowrap text-neutral-400 text-[11px]">
                          {new Date(c.time).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </td>
                        <td className="px-4 py-3">
                           <QueryThumbnail query={c.query} size="sm" r2BaseUrl={stats?.r2_public_url} />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {c.apis
                              .filter(a => a.name && a.name !== 'Unknown' && a.name !== 'info')
                              .filter((a, i, arr) => arr.findIndex(x => x.name === a.name) === i) // unique by name
                              .map((api, ai) => (
                                <BrandBadge key={ai} name={api.name} />
                              ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-emerald-400/80 group-hover:text-emerald-400 text-right">
                          ${c.total_cost.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            c.success ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}>
                            {c.success ? 'OK' : 'ERR'}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {(!stats?.cases || stats.cases.length === 0) && (
                      <tr>
                        <td colSpan={5} className="px-5 py-12 text-center text-neutral-500">
                          <Box className="w-8 h-8 mx-auto mb-3 opacity-20" />
                          No cases recorded yet
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Error Logs */}
            {stats?.recent_errors && stats.recent_errors.length > 0 && (
              <div className="bg-red-950/20 backdrop-blur-xl border border-red-500/20 rounded-3xl p-6 shadow-[0_8px_30px_rgb(239,68,68,0.1)]">
                <h3 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-red-400 to-orange-400 mb-6 flex items-center">
                  <AlertTriangle className="w-6 h-6 mr-3 text-red-400" />
                  Recent System Errors
                </h3>
                <div className="space-y-4">
                  {stats.recent_errors.map((err: RecentError, idx: number) => (
                    <div key={idx} className="bg-black/40 rounded-2xl p-4 text-sm font-mono text-red-300 border border-white/5 relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-red-500 to-orange-500 opacity-80" />
                      <div className="flex justify-between items-center text-xs text-neutral-500 mb-3 pl-2">
                        <span className="bg-white/5 px-2 py-1 rounded border border-white/5">{new Date(err.time).toLocaleString('th-TH')}</span>
                        <span className="font-bold tracking-wider text-red-400/80">{err.endpoint}</span>
                      </div>
                      <div className="break-words whitespace-pre-wrap pl-2 leading-relaxed opacity-90 group-hover:opacity-100 transition-opacity text-xs">{err.error}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}



          </div>

          {/* Right Column: AI Assistant Chat (Grok) */}
          <div className="lg:col-span-1 border-l lg:border-t-0 border-t border-neutral-800 pt-6 lg:pt-0 lg:pl-6 flex flex-col h-[calc(100vh-8rem)] sticky top-24">
            <h3 className="text-lg font-bold text-white mb-1 flex items-center shrink-0">
              <Terminal className="w-5 h-5 mr-2 text-violet-400" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-fuchsia-400">AI Support</span>
              <span className="ml-2 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-violet-500/15 border border-violet-500/30 text-violet-300 tracking-wide">Grok</span>
            </h3>
            <p className="text-[11px] text-neutral-500 mb-4 shrink-0">Powered by xAI Grok — มีสิทธิ์เข้าถึงข้อมูล dashboard ทั้งหมด</p>
            
            <div className="flex-1 bg-neutral-950 border border-neutral-800 rounded-2xl overflow-hidden flex flex-col shadow-inner">
              
              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.length === 0 && (
                  <div className="h-full flex flex-col items-center justify-center text-center text-neutral-500 px-4">
                    <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center mb-3">
                      <Terminal className="w-6 h-6 text-violet-400 opacity-60" />
                    </div>
                    <p className="text-sm font-medium text-neutral-400">Grok AI พร้อมช่วยเหลือ</p>
                    <p className="text-xs text-neutral-600 mt-1">ถามเกี่ยวกับสถิติระบบ ข้อผิดพลาด หรือ API usage</p>
                  </div>
                )}
                
                {chatMessages.map((msg: {role: 'user' | 'assistant', content: string}, idx: number) => (
                  <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-1.5 mb-1 ml-1">
                        <span className="w-4 h-4 rounded bg-violet-500/20 border border-violet-500/30 flex items-center justify-center">
                          <span className="text-[8px] font-bold text-violet-400">G</span>
                        </span>
                        <span className="text-[10px] text-violet-400 font-semibold">Grok</span>
                      </div>
                    )}
                    <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white rounded-br-none' 
                        : 'bg-neutral-800 text-neutral-300 rounded-bl-none border border-neutral-700 whitespace-pre-wrap'
                    }`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex items-start">
                    <div className="bg-neutral-800 border border-neutral-700 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex space-x-1.5">
                      <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                      <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                      <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce"></div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-3 bg-neutral-900 border-t border-neutral-800 shrink-0">
                <form onSubmit={submitChat} className="flex space-x-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setChatInput(e.target.value)}
                    placeholder="ถามสถิติระบบ, API usage..."
                    className="flex-1 bg-neutral-950 border border-neutral-700 rounded-xl px-4 py-2 text-sm text-white focus:outline-none focus:border-violet-500 transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={!chatInput.trim() || chatLoading}
                    className="bg-violet-600 hover:bg-violet-500 text-white rounded-xl px-4 py-2 disabled:opacity-50 transition-colors"
                  >
                    ส่ง
                  </button>
                </form>
              </div>

            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
