"use client";

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

interface FeedbackLog {
  time: string;
  is_helpful: boolean;
  reason: string;
  details: string;
  query: string;
  endpoint: string;
}

export default function AdminDashboard() {
  const [password, setPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Chat State
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<{role: string, text: string}[]>([
    { role: 'ai', text: 'สวัสดีครับแอดมิน! ผมคือ AI ประจำระบบหลังบ้าน วันนี้มีอะไรให้ผมช่วยวิเคราะห์หรือตรวจสอบระบบไหมครับ?' }
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const apiHost = window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname;
      const res = await fetch(`http://${apiHost}:8000/api/admin/stats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      
      if (res.ok) {
        const data = await res.json();
        setStats(data);
        setIsAuthenticated(true);
      } else {
        setError('รหัสผ่านไม่ถูกต้อง');
      }
    } catch (err) {
      setError('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
    }
    setLoading(false);
  };

  const refreshStats = async () => {
    if (!isAuthenticated) return;
    try {
      const apiHost = window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname;
      const res = await fetch(`http://${apiHost}:8000/api/admin/stats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      if (res.ok) setStats(await res.json());
    } catch (err) {
      console.error(err);
    }
  };

  const toggleKillSwitch = async (currentState: boolean) => {
    if (!window.confirm(currentState ? "แน่ใจหรือไม่ว่าต้องการ เปิดระบบ ใช้งานตามปกติ?" : "แน่ใจหรือไม่ว่าต้องการ ปิดระบบ ค้นหาข่าวทั้งหมด?")) return;
    try {
      const apiHost = window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname;
      const res = await fetch(`http://${apiHost}:8000/api/admin/toggle-killswitch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password, active: !currentState })
      });
      if (res.ok) {
        refreshStats();
      } else {
        alert("ไม่สามารถเปลี่ยนสถานะระบบได้");
      }
    } catch (err) {
      alert("ไม่สามารถติดต่อเซิร์ฟเวอร์ได้");
    }
  };

  const sendChatMessage = async () => {
    if (!chatMessage.trim()) return;
    const msg = chatMessage;
    setChatMessage('');
    setChatHistory(prev => [...prev, { role: 'user', text: msg }]);
    setChatLoading(true);

    try {
      const apiHost = window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname;
      const res = await fetch(`http://${apiHost}:8000/api/admin/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, password })
      });
      const data = await res.json();
      setChatHistory(prev => [...prev, { role: 'ai', text: data.reply || 'เกิดข้อผิดพลาดในการตอบกลับ' }]);
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'ai', text: '❌ ระบบแชทขัดข้อง ไม่สามารถติดต่อเซิร์ฟเวอร์ได้' }]);
    }
    setChatLoading(false);
  };

  if (!isAuthenticated) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: 'var(--background)' }}>
        <form onSubmit={handleLogin} style={{ background: 'var(--surface-color)', padding: '40px', borderRadius: '16px', border: '1px solid var(--surface-border)', width: '100%', maxWidth: '400px', textAlign: 'center' }}>
          <h1 style={{ marginBottom: '20px', color: 'var(--primary-color)' }}>🔐 Admin Portal</h1>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '30px' }}>กรุณากรอกรหัสผ่านเพื่อเข้าสู่ระบบควบคุม</p>
          <input 
            type="password" 
            placeholder="รหัสผ่าน..." 
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--surface-border)', background: 'rgba(0,0,0,0.2)', color: 'white', marginBottom: '16px' }}
          />
          {error && <p style={{ color: '#ef4444', marginBottom: '16px', fontSize: '0.9rem' }}>{error}</p>}
          <button type="submit" className="btn" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'กำลังตรวจสอบ...' : 'เข้าสู่ระบบ'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--background)', color: 'var(--text-primary)', padding: '40px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ width: '100%', maxWidth: '1400px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* Header */}
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', padding: '20px', background: 'var(--surface-color)', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.8rem', color: 'var(--primary-color)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              📊 Fact-Check Admin Dashboard
            </h1>
            <p style={{ margin: '5px 0 0 0', color: 'var(--text-secondary)' }}>แผงควบคุมและสรุปสถิติการใช้งานระบบ</p>
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            {stats && (
              <button 
                onClick={() => toggleKillSwitch(stats.kill_switch_active)} 
                style={{ 
                  padding: '8px 16px', 
                  background: stats.kill_switch_active ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)', 
                  color: stats.kill_switch_active ? '#ef4444' : '#10b981', 
                  border: `1px solid ${stats.kill_switch_active ? '#ef4444' : '#10b981'}`, 
                  borderRadius: '8px', 
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  transition: 'all 0.2s'
                }}
              >
                {stats.kill_switch_active ? '🔴 ปิดระบบฉุกเฉินอยู่ (Kill Switch Active)' : '🟢 ระบบทำงานปกติ (API Active)'}
              </button>
            )}
            <button onClick={refreshStats} style={{ padding: '8px 16px', background: 'rgba(255,255,255,0.1)', color: 'white', border: '1px solid var(--surface-border)', borderRadius: '8px', cursor: 'pointer' }}>
              🔄 รีเฟรชข้อมูล
            </button>
          </div>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', flex: 1 }}>
            
          {/* Main Dashboard Column */}
          <div style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* System Health */}
            <div style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
              <h3 style={{ marginTop: 0, marginBottom: '20px' }}>⚙️ สถานะระบบ (System Health)</h3>
              <div style={{ display: 'flex', gap: '30px', flexWrap: 'wrap' }}>
                {Object.entries(stats?.system_health || {}).map(([key, status]: any) => (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: status === 'Healthy' ? '#10b981' : (status === 'Degraded' ? '#f59e0b' : '#ef4444') }}></div>
                    <span style={{ textTransform: 'capitalize' }}>{key.replace('_', ' ')}:</span>
                    <strong style={{ color: status === 'Healthy' ? '#10b981' : (status === 'Degraded' ? '#f59e0b' : '#ef4444') }}>{status}</strong>
                  </div>
                ))}
              </div>
            </div>

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
              <div style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
                <p style={{ color: 'var(--text-secondary)', margin: '0 0 10px 0', fontSize: '0.9rem' }}>จำนวนการใช้งานทั้งหมด</p>
                <h2 style={{ fontSize: '2.5rem', margin: 0, color: 'white' }}>{stats?.total_requests || 0} <span style={{fontSize: '1rem', color: 'var(--text-secondary)'}}>ครั้ง</span></h2>
              </div>
              
              <div style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
                <p style={{ color: 'var(--text-secondary)', margin: '0 0 10px 0', fontSize: '0.9rem' }}>ต้นทุนประเมินการใช้ API (Cost)</p>
                <h2 style={{ fontSize: '2.5rem', margin: 0, color: '#10b981' }}>${stats?.total_cost_usd || 0}</h2>
              </div>

              <div style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
                <p style={{ color: 'var(--text-secondary)', margin: '0 0 10px 0', fontSize: '0.9rem' }}>อัตราความสำเร็จ (Success Rate)</p>
                <h2 style={{ fontSize: '2.5rem', margin: 0, color: (stats?.success_rate_percent || 0) > 90 ? '#3b82f6' : '#f59e0b' }}>
                  {stats?.success_rate_percent || 0}%
                </h2>
              </div>
            </div>

            {/* ----------------- Feedback Table ---------------- */}
            <div style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)', marginBottom: '24px' }}>
              <h3 style={{ marginTop: 0, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>📢</span> เสียงสะท้อนจากผู้ใช้ (Recent Feedback)
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--surface-border)', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '12px 8px' }}>เวลา</th>
                      <th style={{ padding: '12px 8px' }}>คำค้นหา</th>
                      <th style={{ padding: '12px 8px' }}>ความพอใจ</th>
                      <th style={{ padding: '12px 8px', maxWidth: '300px' }}>รายละเอียดเพิ่มเติม</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats?.recent_feedback?.map((log: FeedbackLog, i: number) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '12px 8px', color: 'var(--text-secondary)' }}>
                          {new Date(log.time).toLocaleTimeString('th-TH')}
                        </td>
                        <td style={{ padding: '12px 8px', color: 'var(--text-primary)', maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={log.query}>
                          {log.query}
                        </td>
                        <td style={{ padding: '12px 8px' }}>
                          {log.is_helpful ? (
                            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>👍 พอใจ</span>
                          ) : (
                            <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>👎 มีปัญหา</span>
                          )}
                        </td>
                        <td style={{ padding: '12px 8px', color: 'var(--text-secondary)', maxWidth: '300px' }}>
                          {!log.is_helpful && log.reason !== '-' ? (
                            <div>
                              <span style={{ fontWeight: 600, color: '#fbbf24' }}>
                                {log.reason === 'url_or_content_error' ? 'ลิงก์เสีย / ไม่พบเนื้อหา' : log.reason === 'ai_error' ? 'AI สรุปมั่ว' : log.reason === 'url_error' ? 'ลิ้งก์เสีย (เก่า)' : log.reason === 'not_found_on_page' ? 'เนื่อหาไม่ตรงปก (เก่า)' : log.reason === 'ai_hallucinated' ? 'AI วิเคราะห์มั่ว (เก่า)' : 'อื่นๆ'}:
                              </span> 
                              <span style={{ marginLeft: '4px' }}>{log.details || '-'}</span>
                            </div>
                          ) : (
                            '-'
                          )}
                        </td>
                      </tr>
                    ))}
                    {(!stats?.recent_feedback || stats.recent_feedback.length === 0) && (
                      <tr>
                        <td colSpan={4} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-secondary)' }}>
                          ยังไม่มีข้อมูลฟีดแบค
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Live Traffic */}
            <div style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
              <h3 style={{ marginTop: 0, marginBottom: '20px' }}>⚡ กิจกรรมล่าสุด (Live Traffic)</h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--surface-border)', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '12px', fontWeight: 'normal' }}>เวลา</th>
                      <th style={{ padding: '12px', fontWeight: 'normal' }}>เส้นทาง (Endpoint)</th>
                      <th style={{ padding: '12px', fontWeight: 'normal' }}>ข้อความค้นหา</th>
                      <th style={{ padding: '12px', fontWeight: 'normal' }}>สถานะ</th>
                      <th style={{ padding: '12px', fontWeight: 'normal', textAlign: 'right' }}>Cost Estimate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats?.recent_traffic && stats.recent_traffic.map((log: any, idx: number) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '12px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{new Date(log.time).toLocaleTimeString()}</td>
                        <td style={{ padding: '12px' }}><code>{log.endpoint.replace('/api/', '')}</code></td>
                        <td style={{ padding: '12px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.query}</td>
                        <td style={{ padding: '12px' }}>
                          <span style={{ 
                            padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', 
                            background: log.status === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            color: log.status === 'success' ? '#10b981' : '#ef4444'
                          }}>
                            {log.status}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right', color: '#10b981', fontFamily: 'monospace' }}>
                          ${log.cost}
                        </td>
                      </tr>
                    ))}
                    {(!stats?.recent_traffic || stats.recent_traffic.length === 0) && (
                      <tr><td colSpan={5} style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>ไม่มีข้อมูลใหม่</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>


            {/* Recent Errors */}
            <div style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
              <h3 style={{ marginTop: 0, marginBottom: '20px', color: '#ef4444' }}>⚠️ ข้อผิดพลาดล่าสุด (Recent Errors)</h3>
              {stats?.recent_errors && stats.recent_errors.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {stats.recent_errors.map((err: any, idx: number) => (
                    <div key={idx} style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid #ef4444', borderRadius: '4px' }}>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>{new Date(err.time).toLocaleString()} | {err.endpoint}</div>
                      <div style={{ color: '#fca5a5' }}>{err.error}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--text-secondary)' }}>ไม่มีข้อผิดพลาดล่าสุด (ระบบทำงานปกติ)</p>
              )}
            </div>
          </div>

          {/* AI Chat Column */}
          <div style={{ gridColumn: 'span 1', display: 'flex', flexDirection: 'column', background: 'var(--surface-color)', borderRadius: '16px', border: '1px solid var(--surface-border)', overflow: 'hidden', height: '650px', position: 'sticky', top: '40px' }}>
            <div style={{ padding: '16px 20px', background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid var(--surface-border)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.5rem' }}>🤖</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>AI ผู้ช่วยแอดมิน</h3>
                  <div style={{ fontSize: '0.8rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}><div style={{width:'8px',height:'8px',background:'#10b981',borderRadius:'50%'}}></div> Online</div>
                </div>
            </div>

            <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {chatHistory.map((chat, idx) => (
                  <div key={idx} style={{ alignSelf: chat.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '4px', textAlign: chat.role === 'user' ? 'right' : 'left' }}>
                      {chat.role === 'user' ? 'คุณกัส (Admin)' : 'AI Assistant'}
                    </div>
                    <div style={{ 
                      background: chat.role === 'user' ? 'var(--primary-color)' : 'rgba(255,255,255,0.1)', 
                      padding: '12px 16px', 
                      borderRadius: chat.role === 'user' ? '16px 16px 0 16px' : '16px 16px 16px 0',
                      color: 'white',
                      lineHeight: '1.5'
                    }}>
                      {chat.role === 'user' ? chat.text : <div className="markdown-body" style={{background:'transparent'}}><ReactMarkdown>{chat.text}</ReactMarkdown></div>}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div style={{ alignSelf: 'flex-start', maxWidth: '80%' }}>
                     <div style={{ background: 'rgba(255,255,255,0.1)', padding: '12px 16px', borderRadius: '16px 16px 16px 0', color: 'var(--text-secondary)' }}>
                        กำลังวิเคราะห์ข้อมูลระบบ...
                     </div>
                  </div>
                )}
                <div ref={chatEndRef} />
            </div>

            <div style={{ padding: '16px', borderTop: '1px solid var(--surface-border)', display: 'flex', gap: '10px' }}>
              <input 
                type="text" 
                placeholder="ถาม AI เกี่ยวกับปัญหาระบบ..." 
                value={chatMessage}
                onChange={e => setChatMessage(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendChatMessage()}
                style={{ flex: 1, padding: '12px 16px', borderRadius: '24px', border: '1px solid var(--surface-border)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none' }}
              />
              <button 
                onClick={sendChatMessage} 
                className="btn" 
                style={{ borderRadius: '50%', width: '45px', height: '45px', padding: 0, display: 'flex', justifyContent: 'center', alignItems: 'center' }}
                disabled={chatLoading || !chatMessage.trim()}
              >
                ↑
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
