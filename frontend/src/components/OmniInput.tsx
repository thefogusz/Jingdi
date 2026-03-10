import { useState, useRef, useEffect } from 'react';
import Script from 'next/script';
import { CatState } from '@/app/page';

const TURNSTILE_SITE_KEY = '0x4AAAAAACog3f_ZxCilAGHM';

export default function OmniInput({ setResults, setLoading, loading, setInputState, catState }: any) {
  const [text, setText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const turnstileRef = useRef<HTMLDivElement>(null);
  const [turnstileToken, setTurnstileToken] = useState<string>('');

  // Handle pasting images directly into the component/window
  useEffect(() => {
    const handleGlobalPaste = (e: globalThis.ClipboardEvent) => {
      if (e.clipboardData && e.clipboardData.files.length > 0) {
        const pastedFiles = Array.from(e.clipboardData.files).filter(f => f.type.startsWith('image/'));
        if (pastedFiles.length > 0) {
          setFiles(prev => [...prev, ...pastedFiles]);
          setPreviews(prev => [...prev, ...pastedFiles.map(f => URL.createObjectURL(f))]);
        }
      }
    };
    window.addEventListener('paste', handleGlobalPaste);
    return () => window.removeEventListener('paste', handleGlobalPaste);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...selectedFiles]);
      setPreviews(prev => [...prev, ...selectedFiles.map(f => URL.createObjectURL(f))]);
    }
  };

  const removeImage = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    setPreviews(prev => prev.filter((_, i) => i !== index));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async () => {
    if (!text.trim() && files.length === 0) return;
    setLoading(true);
    setResults(null);
    
    // Get Turnstile token from hidden widget
    const cfToken = (window as any).turnstile?.getResponse(turnstileRef.current) || turnstileToken || '';
    
    try {
      if (files.length > 0) {
        const formData = new FormData();
        files.forEach(f => formData.append("files", f));
        if (cfToken) formData.append('cf_token', cfToken);
        
        // Sending to Next.js proxy rewrite which routes to /api on backend
        const res = await fetch('/api/check-image', {
          method: 'POST',
          body: formData
        });
        if (!res.ok) {
          const errText = await res.text();
          console.error('Backend error:', res.status, errText);
          throw new Error(`เซิร์ฟเวอร์ตอบกลับ ${res.status}: ${res.statusText}`);
        }
        const data = await res.json();
        setResults(data);
      } else {
        // Submit Text or URL
        const isUrl = text.trim().startsWith('http://') || text.trim().startsWith('https://');
        const endpoint = isUrl ? '/api/check-url' : '/api/check-text';
        const body = isUrl ? { url: text.trim(), cf_token: cfToken } : { text: text.trim(), cf_token: cfToken };

        // Using Next.js rewrite proxy
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        if (!res.ok) {
          const errText = await res.text();
          console.error('Backend error:', res.status, errText);
          throw new Error(`เซิร์ฟเวอร์ตอบกลับ ${res.status}: ${res.statusText}`);
        }
        const data = await res.json();
        setResults(data);
      }
    } catch (err) {
      console.error(err);
      const msg = err instanceof Error ? err.message : "เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์";
      setResults({ score: 0, analysis: `❌ ${msg}`, sources: [] });
    }
    setLoading(false);
  };

  const [isFocused, setIsFocused] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const loadingSteps = [
    "🔍 กำลังสกัดข้อความและรูปภาพ...",
    "🌐 กำลังค้นหาข้อมูลจาก Web Search...",
    "🧠 AI กำลังประมวลผลความน่าเชื่อถือ...",
    "⚖️ กำลังเรียบเรียงผลลัพธ์..."
  ];

  useEffect(() => {
    if (loading) {
      setCurrentStep(0);
      const interval = setInterval(() => {
        setCurrentStep((prev) => Math.min(prev + 1, loadingSteps.length - 1));
      }, 2500); // Wait 2.5s between steps
      return () => clearInterval(interval);
    }
  }, [loading]);

  // Update parent state based on input activity
  useEffect(() => {
    if (!loading) {
      if (files.length > 0 || text.trim().length > 0) {
        setInputState('hasFile'); // text or image present → detective cat typing
      } else if (isFocused) {
        setInputState('focused'); // just focused/clicked but empty → big detective cat with magnifier
      } else {
        setInputState('idle');
      }
    }
  }, [text, files, isFocused, loading, setInputState]);

  // Determine image and class
  let catSrc = "/detective-cat.png";
  let catAnimClass = "cat-idle";
  
  if (catState === 'idle') {
    catSrc = "/cat-sleeping.png";
    catAnimClass = "cat-idle";
  } else if (catState === 'focused') {
    catSrc = "/detective-cat.png";
    catAnimClass = "cat-show"; // big detective cat with magnifying glass
  } else if (catState === 'hasFile') {
    catSrc = "/detective-cat.png";
    catAnimClass = "cat-typing";
  } else if (catState === 'loading') {
    catSrc = "/detective-cat.png";
    catAnimClass = "cat-searching";
  } else if (catState === 'success') {
    catSrc = "/cat-happy.png";
    catAnimClass = "cat-success";
  } else if (catState === 'fake') {
    catSrc = "/cat-shocked.png";
    catAnimClass = "cat-fake";
  }

  return (
    <div className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '16px', position: 'relative', zIndex: 1 }}>
      
      {/* Detective Cat Image Mascot */}
      <img 
        src={catSrc} 
        alt="Detective Cat Mascot"
        className={`cat-mascot ${catAnimClass}`}
      />

      <div 
        style={{ 
          background: isFocused ? 'var(--surface-color)' : 'rgba(15, 23, 42, 0.8)', /* Solid background when typing to prevent text overlap */
          border: `1px solid ${isFocused ? 'var(--primary-color)' : 'var(--surface-border)'}`,
          borderRadius: '12px',
          transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
          boxShadow: isFocused ? '0 8px 32px rgba(37, 99, 235, 0.15), 0 0 0 1px var(--primary-color)' : '0 4px 20px rgba(0,0,0,0.3)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          transform: isFocused ? 'translateY(-4px)' : 'translateY(0)',
          position: 'relative',
          zIndex: 10 /* Force above the cat */
        }}
      >
        <textarea
          style={{ 
            minHeight: previews.length > 0 ? '80px' : '150px', 
            fontSize: '1.05rem', 
            padding: '12px 16px',
            width: '100%',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-primary)',
            fontFamily: "'Kanit', sans-serif",
            resize: 'none',
            outline: 'none'
          }}
          placeholder="พิมพ์ข้อความ วางลิงก์ข่าว หรือกด (Ctrl+V) เพื่อวางรูปภาพที่ต้องการตรวจสอบ..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          disabled={loading}
        />
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'transparent' }}>
          <button 
            type="button"
            onClick={() => fileInputRef.current?.click()}
            style={{
              background: 'rgba(255,255,255,0.08)', border: '1px solid var(--surface-border)', 
              color: 'var(--text-secondary)', padding: '6px 14px', borderRadius: '8px',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem',
              transition: 'all 0.2s', fontFamily: "'Kanit', sans-serif", fontWeight: 500
            }}
            onMouseOver={(e) => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.background = 'rgba(255,255,255,0.12)'; }}
            onMouseOut={(e) => { e.currentTarget.style.color = 'var(--text-secondary)'; e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
            disabled={loading}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
            แนบรูปภาพ
          </button>
          <button 
            className="btn" 
            onClick={handleSubmit} 
            disabled={loading || (!text.trim() && files.length === 0)}
            style={{ 
              padding: '8px 20px', 
              minWidth: loading ? '280px' : 'auto',
              opacity: (loading || (!text.trim() && files.length === 0)) ? 0.5 : 1,
              cursor: (loading || (!text.trim() && files.length === 0)) ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? (
              <>
                <span className="loader" />
                <span style={{ fontSize: '0.9rem' }}>{loadingSteps[currentStep]}</span>
              </>
            ) : "ตรวจสอบข้อมูล"}
          </button>
        </div>
      </div>

      <input 
        type="file" 
        multiple
        ref={fileInputRef} 
        style={{ display: 'none' }} 
        onChange={handleFileChange}
        accept="image/*"
      />

      {previews.length > 0 && (
         <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '8px' }}>
          {previews.map((prev, idx) => (
             <div key={idx} style={{ 
              position: 'relative', padding: '8px', 
              background: 'rgba(0,0,0,0.2)', borderRadius: '12px', border: '1px solid var(--surface-border)',
              display: 'inline-block'
            }}>
              <img src={prev} alt={`Preview ${idx}`} style={{ maxHeight: '120px', borderRadius: '6px', display: 'block' }} />
              <button 
                onClick={() => removeImage(idx)}
                style={{ 
                  position: 'absolute', top: '4px', right: '4px', background: 'rgba(239, 68, 68, 0.9)', 
                  color: 'white', border: 'none', borderRadius: '50%', width: '24px', height: '24px', 
                  cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '12px', fontWeight: 'bold', zIndex: 10
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Cloudflare Turnstile — hidden, auto-verifies silently */}
      <div
        ref={turnstileRef}
        className="cf-turnstile"
        data-sitekey={TURNSTILE_SITE_KEY}
        data-callback="onTurnstileSuccess"
        data-size="invisible"
        style={{ display: 'none' }}
      />
      <Script
        src="https://challenges.cloudflare.com/turnstile/v0/api.js"
        strategy="afterInteractive"
        onLoad={() => {
          (window as any).onTurnstileSuccess = (token: string) => {
            setTurnstileToken(token);
          };
          (window as any).turnstile?.render(turnstileRef.current, {
            sitekey: TURNSTILE_SITE_KEY,
            callback: (token: string) => setTurnstileToken(token),
            size: 'invisible',
          });
        }}
      />
    </div>
  );
}
