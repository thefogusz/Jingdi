import { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';

export default function ResultsView({ results, onClear }: { results: any, onClear: () => void }) {
  if (!results) return null;

  const { score, analysis, claims_extracted, suspicious_words, sources, visual_indicators, extracted_text, log_id } = results;

  const [showContent, setShowContent] = useState(false);
  const [showPipeline, setShowPipeline] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<'helpful' | 'unhelpful' | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackReason, setFeedbackReason] = useState('url_or_content_error');
  const [feedbackDetails, setFeedbackDetails] = useState('');
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  useEffect(() => {
    // Slight delay for animation sequence
    setTimeout(() => setShowContent(true), 100);
    return () => setShowContent(false);
  }, [results]);

  let statusColor = 'var(--success)';
  let statusText = 'ข่าวจริง / มีความน่าเชื่อถือสูง';
  let statusIcon = '✅';
  
  if (score < 40) {
    statusColor = 'var(--danger)';
    statusText = 'ข่าวปลอม / บิดเบือนความจริง';
    statusIcon = '🚨';
  } else if (score < 75) {
    statusColor = 'var(--warning)';
    statusText = 'ข้อมูลไม่ครบถ้วน / รอการพิสูจน์';
    statusIcon = '⚠️';
  }

  return (
    <section className="glass-panel" style={{ 
      animation: 'slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      borderTop: `4px solid ${statusColor}`,
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background glow matching status */}
      <div style={{
        position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)',
        width: '100%', height: '100px',
        background: `radial-gradient(ellipse at top, ${statusColor}30, transparent 70%)`,
        pointerEvents: 'none', zIndex: 0
      }}></div>

      <div style={{ position: 'relative', zIndex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600 }}>ผลการวิเคราะห์</h2>
        <button onClick={onClear} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.5rem', lineHeight: 1, padding: '4px' }}>×</button>
      </div>

      <div style={{ 
        position: 'relative', zIndex: 1,
        display: 'flex', flexDirection: 'column', gap: '24px', alignItems: 'center', marginBottom: '40px',
        textAlign: 'center', opacity: showContent ? 1 : 0, transform: showContent ? 'translateY(0)' : 'translateY(10px)',
        transition: 'all 0.5s ease'
      }}>
        <div style={{
          padding: '12px 24px', borderRadius: '50px',
          background: `${statusColor}20`,
          border: `1px solid ${statusColor}50`,
          display: 'flex', alignItems: 'center', gap: '12px',
          boxShadow: `0 0 20px ${statusColor}30`,
          animation: 'pulseGlow 2s infinite'
        }}>
          <span style={{ fontSize: '1.8rem' }}>{statusIcon}</span>
          <span style={{ fontSize: '1.4rem', fontWeight: 700, color: statusColor }}>{statusText}</span>
        </div>
        
        <div 
          className="analysis-content"
          style={{ 
          color: 'var(--text-primary)', 
          lineHeight: 1.8, 
          fontSize: '1.15rem', 
          width: '100%',
          maxWidth: '800px', 
          backgroundColor: 'rgba(255,255,255,0.03)', 
          padding: '24px 32px', 
          borderRadius: '16px', 
          border: '1px solid var(--surface-border)',
          whiteSpace: 'pre-wrap',
          textAlign: 'left'
        }}
        dangerouslySetInnerHTML={{ 
          __html: analysis 
            ? analysis
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\[([^\]]+)\]\([^)]+\)/g, '<span style="color:var(--primary-color); font-weight:500;">$1</span>')
                .replace(/https?:\/\/[^\s)\]>]+/g, '')
                .replace(/\(\s*\)/g, '')
                .replace(/\[\s*\]/g, '')
            : '' 
        }}
        />
      </div>

      <div style={{ position: 'relative', zIndex: 1, opacity: showContent ? 1 : 0, transition: 'opacity 0.5s ease 0.2s', display: 'flex', flexDirection: 'column', gap: '32px' }}>

      {claims_extracted && claims_extracted.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ marginBottom: '8px', color: 'var(--text-primary)' }}>ข้อกล่าวอ้างที่พบ</h4>
          <ul style={{ paddingLeft: '20px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {claims_extracted.map((c: string, i: number) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {suspicious_words && suspicious_words.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ marginBottom: '8px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span role="img" aria-label="megaphone">📢</span> จุดสังเกต: คำเน้นอารมณ์ / เรียกร้องความสนใจ
          </h4>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            คำเหล่านี้มักถูกใช้เพื่อดึงดูดความสนใจ แต่มิได้แปลว่าข่าวจะเป็นของปลอมเสมอไป
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {suspicious_words.map((w: string, i: number) => (
              <span key={i} style={{ 
                background: 'rgba(245, 158, 11, 0.15)', 
                color: '#fbbf24', 
                border: '1px solid rgba(245, 158, 11, 0.3)',
                padding: '4px 10px', 
                borderRadius: '8px', 
                fontSize: '0.9rem',
                fontWeight: 500
              }}>
                {w}
              </span>
            ))}
          </div>
        </div>
      )}

      {visual_indicators && visual_indicators.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ marginBottom: '8px', color: 'var(--text-primary)' }}>ตัวชี้วัดจากภาพและบริบท</h4>
          <ul style={{ paddingLeft: '20px', color: 'var(--text-secondary)' }}>
            {visual_indicators.map((v: string, i: number) => <li key={i}>{v}</li>)}
          </ul>
        </div>
      )}

      {(!sources || sources.length === 0) && (
        <div style={{ marginTop: '16px', background: 'rgba(255,255,255,0.02)', padding: '24px', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <h4 style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
            <span style={{ fontSize: '1.4rem', opacity: 0.7 }}>🔍</span> ผลการค้นหาแหล่งข้อมูล (ไม่พบ)
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', lineHeight: 1.6, padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px' }}>
            จากการค้นหาและตรวจสอบเบื้องต้นบนแพลตฟอร์มโซเชียลมีเดีย (Facebook, X, TikTok) รวมถึงเว็บไซต์ข่าวหลักที่น่าเชื่อถือ <strong>ไม่พบแหล่งข้อมูลต้นฉบับหรือลิงก์อ้างอิงจริงที่สามารถยืนยันเนื้อหานี้ได้</strong> (AI จะไม่สร้างลิงก์ปลอมขึ้นมาเองหากไม่พบข้อมูล)
          </p>
        </div>
      )}

      {sources && sources.length > 0 && (
        <div style={{ marginTop: '16px', background: 'rgba(255,255,255,0.02)', padding: '24px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
          
          {/* === SEARCH PIPELINE DIAGRAM === */}
          <div style={{ marginBottom: '28px', background: 'rgba(0,0,0,0.25)', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
            {/* Toggle Header */}
            <button
              onClick={() => setShowPipeline(p => !p)}
              style={{
                width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '14px 20px', background: 'transparent', border: 'none', cursor: 'pointer',
                color: 'var(--text-primary)', gap: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1rem' }}>🔬</span>
                <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>ขอบเขตการสืบสวน</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 400 }}>50+ สำนักข่าว · 5 โซเชียล · 3 เลเยอร์ AI</span>
              </div>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', transition: 'transform 0.25s', display: 'inline-block', transform: showPipeline ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
            </button>

            {showPipeline && (
            <div style={{ padding: '0 20px 20px' }}>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
              {[
                { num: '50+', label: 'สำนักข่าว', color: '#60a5fa' },
                { num: '5', label: 'โซเชียลมีเดีย', color: '#f472b6' },
                { num: '3', label: 'เลเยอร์ AI', color: '#a78bfa' },
              ].map((s, i) => (
                <div key={i} style={{ textAlign: 'center', padding: '6px 14px', borderRadius: '24px', background: `${s.color}12`, border: `1px solid ${s.color}35` }}>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color: s.color }}>{s.num}</div>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>{s.label}</div>
                </div>
              ))}
            </div>


            {/* Layer 1: News & Web */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '0.7rem', color: '#60a5fa', fontWeight: 700, marginBottom: '6px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                ชั้น 1 — ฐานข้อมูลข่าวและเว็บ
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {['สำนักข่าวในประเทศ', 'สำนักข่าวนานาชาติ', 'ฐานข้อมูลสารานุกรม', 'ค้นหาเว็บทั่วไป', 'บทความต้นทาง (Scraping)', 'Google News RSS', 'ข่าวย้อนหลัง', 'เว็บ Fact-Check ทั่วโลก'].map((label, i) => (
                  <span key={i} style={{
                    padding: '4px 10px', borderRadius: '20px', fontSize: '0.72rem', fontWeight: 500,
                    background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.25)',
                    color: '#93c5fd', display: 'flex', alignItems: 'center', gap: '5px'
                  }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#60a5fa', display: 'inline-block', flexShrink: 0, animation: 'pulse 1.8s infinite' }} />
                    {label}
                  </span>
                ))}
              </div>
            </div>

            {/* Layer 2: Social Media */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '0.7rem', color: '#f472b6', fontWeight: 700, marginBottom: '6px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                ชั้น 2 — โซเชียลมีเดียและต้นตอโพสต์
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {['Facebook', 'X / Twitter', 'YouTube', 'TikTok', 'Instagram', 'เปรียบเทียบโพสต์คล้ายกัน (A/B)', 'ค้นหาต้นตอรูปภาพ', 'ตรวจเวลาโพสต์'].map((label, i) => (
                  <span key={i} style={{
                    padding: '4px 10px', borderRadius: '20px', fontSize: '0.72rem', fontWeight: 500,
                    background: 'rgba(244,114,182,0.1)', border: '1px solid rgba(244,114,182,0.25)',
                    color: '#f9a8d4', display: 'flex', alignItems: 'center', gap: '5px'
                  }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#f472b6', display: 'inline-block', flexShrink: 0, animation: 'pulse 2s infinite' }} />
                    {label}
                  </span>
                ))}
              </div>
            </div>

            {/* Layer 3: AI Deep Analysis */}
            <div>
              <div style={{ fontSize: '0.7rem', color: '#a78bfa', fontWeight: 700, marginBottom: '6px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                ชั้น 3 — วิเคราะห์เชิงลึกด้วย AI
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {['ตรวจข้อความเรียกร้องทางอารมณ์', 'วิเคราะห์ภาพ (AI Vision)', 'ตรวจ AI-Generated Content', 'เทียบแหล่งข้อมูลหลายมิติ', 'คำนวณคะแนนความน่าเชื่อถือ'].map((label, i) => (
                  <span key={i} style={{
                    padding: '4px 10px', borderRadius: '20px', fontSize: '0.72rem', fontWeight: 500,
                    background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.25)',
                    color: '#c4b5fd', display: 'flex', alignItems: 'center', gap: '5px'
                  }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#a78bfa', display: 'inline-block', flexShrink: 0, animation: 'pulse 1.5s infinite' }} />
                    {label}
                  </span>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ผลสรุปจาก</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#6effc5' }}>{sources.length} แหล่งอ้างอิงที่ตรวจสอบแล้ว</span>
              <span style={{ fontSize: '0.9rem' }}>✅</span>
            </div>
            </div>
            )}
          </div>
          {/* === END PIPELINE === */}


          <h4 style={{ marginBottom: '20px', color: 'var(--primary-color)', fontSize: '1.3rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
            <span style={{ fontSize: '1.5rem' }}>🔎</span> แหล่งข้อมูลอ้างอิงจาก Web Search
          </h4>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '1rem' }}>
            AI ได้ค้นหาข้อมูลจากแหล่งเหล่านี้เพื่อมาประกอบการวิเคราะห์:
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
            {sources.map((s: any, i: number) => {
              const isUrlValid = s.link && s.link !== '#' && s.link !== 'N/A' && !s.link.includes('not_found');
              const linkHref = isUrlValid ? (s.link.startsWith('http') ? s.link : `https://${s.link}`) : undefined;
              const CardWrapper: any = isUrlValid ? 'a' : 'div';
              
              return (
              <CardWrapper 
                key={i} 
                {...(isUrlValid ? { href: linkHref, target: "_blank", rel: "noreferrer" } : {})}
                style={{ 
                  display: 'flex', flexDirection: 'column', padding: '16px', background: 'rgba(255,255,255,0.04)', 
                  borderRadius: '12px', textDecoration: 'none', color: 'inherit',
                  border: '1px solid rgba(255,255,255,0.08)',
                  transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                  cursor: isUrlValid ? 'pointer' : 'default'
                }}
                onMouseOver={(e: any) => { 
                  if(isUrlValid) {
                    e.currentTarget.style.borderColor = 'var(--primary-color)';
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 8px 16px rgba(37,99,235,0.15)';
                  }
                }}
                onMouseOut={(e: any) => {
                  if(isUrlValid) {
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ 
                    width: '32px', height: '32px', borderRadius: '8px', background: 'var(--primary-color)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold'
                  }}>
                    {i + 1}
                  </div>
                  <div style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '1.05rem', lineHeight: 1.4 }}>
                    {s.title}
                  </div>
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden', marginTop: 'auto' }}>
                  {s.snippet}
                </div>
                {isUrlValid && (
                  <div style={{ marginTop: '12px', fontSize: '0.9rem', color: 'var(--primary-color)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
                    อ่านฉบับเต็ม <span style={{ fontSize: '1.2rem', marginLeft: '4px' }}>→</span>
                  </div>
                )}
              </CardWrapper>
            )})}
          </div>
        </div>
      )}
      {/* --- Feedback Section --- */}
      <div style={{ position: 'relative', zIndex: 1, opacity: showContent ? 1 : 0, transition: 'opacity 0.5s ease 0.4s', marginTop: '32px', textAlign: 'center' }}>
        <h4 style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontWeight: 500 }}>ข้อมูลนี้เป็นประโยชน์หรือไม่?</h4>
        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <button 
            disabled={feedbackGiven !== null}
            onClick={async () => {
              setFeedbackGiven('helpful');
              if (log_id) {
                await fetch(`/api/feedback`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ log_id, is_helpful: true })
                }).catch(() => {});
              }
            }}
            style={{ 
              padding: '12px 32px', borderRadius: '50px', 
              background: feedbackGiven === 'helpful' ? 'var(--success)' : 'rgba(255,255,255,0.05)',
              color: feedbackGiven === 'helpful' ? 'white' : 'var(--text-primary)',
              border: `1px solid ${feedbackGiven === 'helpful' ? 'var(--success)' : 'rgba(255,255,255,0.1)'}`,
              cursor: feedbackGiven ? 'default' : 'pointer',
              fontSize: '1.2rem', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '8px'
            }}>
            👍 {feedbackGiven === 'helpful' ? 'ขอบคุณสำหรับความคิดเห็น' : 'ใช่, มีประโยชน์'}
          </button>
          
          <button 
            disabled={feedbackGiven !== null}
            onClick={() => {
              setFeedbackGiven('unhelpful');
              setShowFeedbackModal(true);
            }}
            style={{ 
              padding: '12px 32px', borderRadius: '50px', 
              background: feedbackGiven === 'unhelpful' ? 'var(--danger)' : 'rgba(255,255,255,0.05)',
              color: feedbackGiven === 'unhelpful' ? 'white' : 'var(--text-primary)',
              border: `1px solid ${feedbackGiven === 'unhelpful' ? 'var(--danger)' : 'rgba(255,255,255,0.1)'}`,
              cursor: feedbackGiven ? 'default' : 'pointer',
              fontSize: '1.2rem', transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '8px'
            }}>
            👎 {feedbackGiven === 'unhelpful' ? 'ส่งข้อมูลปัญหาแล้ว' : 'ไม่, มีปัญหา'}
          </button>
        </div>
      </div>
      {/* ------------------------ */}

      </div>

      {/* Dislike Feedback Modal — rendered via Portal at body level to avoid overflow:hidden clip */}
      {showFeedbackModal && typeof document !== 'undefined' && ReactDOM.createPortal(
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(12px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 99999,
          padding: '16px',
        }} onClick={(e) => { if (e.target === e.currentTarget) { setShowFeedbackModal(false); setFeedbackGiven(null); } }}>
          <div style={{
            background: 'var(--surface)', padding: '32px', borderRadius: '24px',
            width: '100%', maxWidth: '420px', border: '1px solid var(--surface-border)',
            boxShadow: '0 20px 60px rgba(0,0,0,0.6)', textAlign: 'left',
            maxHeight: '90vh', overflowY: 'auto',
          }}>
            <h3 style={{ marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.2rem' }}>⚠️</span> แจ้งปัญหาการใช้งาน
            </h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.95rem', lineHeight: 1.5 }}>
              กรุณาเลือกสาเหตุที่การวิเคราะห์นี้ไม่ถูกต้อง หรือไม่เป็นประโยชน์:
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
              
              {/* Option 1 */}
              <label style={{ 
                display: 'flex', flexDirection: 'column', padding: '16px', cursor: 'pointer', borderRadius: '12px',
                border: feedbackReason === 'url_or_content_error' ? '1px solid var(--primary)' : '1px solid var(--surface-border)',
                background: feedbackReason === 'url_or_content_error' ? 'rgba(37, 99, 235, 0.1)' : 'rgba(255,255,255,0.02)',
                transition: 'all 0.2s ease'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
                  <input type="radio" name="reason" value="url_or_content_error" checked={feedbackReason === 'url_or_content_error'} onChange={(e) => setFeedbackReason(e.target.value)} style={{ accentColor: 'var(--primary)', width: '16px', height: '16px', cursor: 'pointer' }}/>
                  <span style={{ color: feedbackReason === 'url_or_content_error' ? 'var(--primary)' : 'var(--text-primary)', fontWeight: 600 }}>
                    🔗 ลิงก์เสีย / หาแหล่งอ้างอิงไม่เจอ
                  </span>
                </div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', paddingLeft: '28px', lineHeight: 1.4 }}>
                  คลิกเข้าไปแล้วลิงก์เข้าไม่ได้ หรือเนื้อหาในลิงก์ไม่ตรงกับที่ AI สรุปมา
                </span>
              </label>

              {/* Option 2 */}
              <label style={{ 
                display: 'flex', flexDirection: 'column', padding: '16px', cursor: 'pointer', borderRadius: '12px',
                border: feedbackReason === 'ai_error' ? '1px solid var(--danger)' : '1px solid var(--surface-border)',
                background: feedbackReason === 'ai_error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.02)',
                transition: 'all 0.2s ease'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
                  <input type="radio" name="reason" value="ai_error" checked={feedbackReason === 'ai_error'} onChange={(e) => setFeedbackReason(e.target.value)} style={{ accentColor: 'var(--danger)', width: '16px', height: '16px', cursor: 'pointer' }}/>
                  <span style={{ color: feedbackReason === 'ai_error' ? 'var(--danger)' : 'var(--text-primary)', fontWeight: 600 }}>
                    🤖 AI สรุปผิดพลาด / มั่วข้อมูล
                  </span>
                </div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', paddingLeft: '28px', lineHeight: 1.4 }}>
                  บทความมีอยู่จริง แต่ AI ตีความผิดเพี้ยนไปจากความจริงอย่างสิ้นเชิง
                </span>
              </label>

              {/* Option 3 */}
              <label style={{ 
                display: 'flex', flexDirection: 'column', padding: '16px', cursor: 'pointer', borderRadius: '12px',
                border: feedbackReason === 'other' ? '1px solid var(--text-secondary)' : '1px solid var(--surface-border)',
                background: feedbackReason === 'other' ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.02)',
                transition: 'all 0.2s ease'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <input type="radio" name="reason" value="other" checked={feedbackReason === 'other'} onChange={(e) => setFeedbackReason(e.target.value)} style={{ width: '16px', height: '16px', cursor: 'pointer' }}/>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                    ✍️ อื่นๆ (โปรดระบุ)
                  </span>
                </div>
              </label>

            </div>
            
            {feedbackReason === 'other' && (
              <textarea 
                placeholder="อธิบายเพิ่มเติม (บังคับเมื่อเลือกอื่นๆ)..."
                value={feedbackDetails}
                onChange={(e) => setFeedbackDetails(e.target.value)}
                style={{
                  width: '100%', height: '80px', padding: '12px', borderRadius: '12px',
                  background: 'rgba(255,255,255,0.05)', border: '1px solid var(--surface-border)',
                  color: 'var(--text-primary)', marginBottom: '24px', resize: 'none'
                }}
              />
            )}
            
            {feedbackReason !== 'other' && (
               <textarea 
                placeholder="อธิบายเพิ่มเติม (ไม่บังคับ)..."
                value={feedbackDetails}
                onChange={(e) => setFeedbackDetails(e.target.value)}
                style={{
                  width: '100%', height: '80px', padding: '12px', borderRadius: '12px',
                  background: 'rgba(255,255,255,0.05)', border: '1px solid var(--surface-border)',
                  color: 'var(--text-primary)', marginBottom: '24px', resize: 'none'
                }}
              />
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => {
                  setShowFeedbackModal(false);
                  setFeedbackGiven(null); // Reset if cancelled
                }}
                style={{ padding: '10px 20px', borderRadius: '12px', background: 'transparent', border: '1px solid var(--surface-border)', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                ยกเลิก
              </button>
              <button 
                disabled={submittingFeedback}
                onClick={async () => {
                  setSubmittingFeedback(true);
                  if (log_id) {
                    await fetch(`/api/feedback`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ log_id, is_helpful: false, reason: feedbackReason, details: feedbackDetails })
                    }).catch(() => {});
                  }
                  setShowFeedbackModal(false);
                  setSubmittingFeedback(false);
                }}
                style={{ padding: '10px 20px', borderRadius: '12px', background: 'var(--primary-color)', border: 'none', color: 'white', cursor: 'pointer', fontWeight: 600 }}>
                {submittingFeedback ? 'กำลังส่ง...' : 'ส่งข้อมูล'}
              </button>
            </div>
          </div>
        </div>
      , document.body)}
    </section>
  );
}
