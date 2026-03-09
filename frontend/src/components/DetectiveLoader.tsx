"use client";
import { useEffect, useState } from "react";

const STEPS = [
  {
    icon: "🔎",
    title: "สกัดเบาะแส",
    desc: "อ่านข้อความ ถอดรหัสรูปภาพ ระบุตัวละครสำคัญ...",
    cat: "เฮ้! แมวนักสืบได้กลิ่น... มีบางอย่างน่าสงสัย! 🐱",
    color: "#60a5fa",
    catImg: "/detective-cat.png",
    catAnim: "searchLook",
  },
  {
    icon: "📰",
    title: "กวาดสำนักข่าว 50+ แห่ง",
    desc: "ค้นหาในฐานข้อมูลข่าวไทย-นานาชาติ, Google News, บทความย้อนหลัง...",
    cat: "กำลังแอบอ่านโต๊ะข่าวทุกเจ้าอยู่นะ อย่าบอกใครล่ะ! 📰",
    color: "#34d399",
    catImg: "/cat-reading-orig.png",
    catAnim: "searchLook",
  },
  {
    icon: "📱",
    title: "บุกโซเชียลมีเดีย",
    desc: "ตรวจ Facebook, X, YouTube, TikTok, หาต้นตอโพสต์ตั้งต้น...",
    cat: "กระโดดเข้าฟีดโซเชียล... โพสต์นี้มาจากไหนกัน? 😼",
    color: "#f472b6",
    catImg: "/cat-phone.png",
    catAnim: "idleSleep",
  },
  {
    icon: "🔬",
    title: "ตรวจสอบเชิงลึก",
    desc: "เปรียบเทียบโพสต์คล้ายกัน (A/B Test) ตรวจเวลา-สถานที่ ตรวจหาการตัดต่อ...",
    cat: "แว่นขยายออกมาแล้ว! รายละเอียดเล็กๆ สำคัญที่สุด... 🔍",
    color: "#fb923c",
    catImg: "/cat-shocked.png",
    catAnim: "fakeShake",
  },
  {
    icon: "🧠",
    title: "AI ประมวลผลวิเคราะห์",
    desc: "คำนวณคะแนนความน่าเชื่อถือ เรียบเรียงหลักฐาน สรุปคำตัดสิน...",
    cat: "สมองแมวกำลังทำงานหนักมาก... เดี๋ยวก็รู้ความจริง! 🧠",
    color: "#a78bfa",
    catImg: "/cat-thinking-orig.png",
    catAnim: "happyHop",
  },
];



export default function DetectiveLoader({ visible }: { visible: boolean }) {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [dots, setDots] = useState(".");

  useEffect(() => {
    if (!visible) {
      setStep(0);
      setProgress(0);
      return;
    }
    // Cycle through steps
    const stepInterval = setInterval(() => {
      setStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 2800);
    // Smooth progress bar
    const progressInterval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 0.4, 95));
    }, 110);
    // Dot animation
    const dotInterval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "." : d + "."));
    }, 400);
    return () => {
      clearInterval(stepInterval);
      clearInterval(progressInterval);
      clearInterval(dotInterval);
    };
  }, [visible]);

  if (!visible) return null;

  const current = STEPS[step];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(10, 10, 20, 0.85)',
      backdropFilter: 'blur(16px)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: '0',
      animation: 'fadeIn 0.3s ease',
    }}>

      {/* Bounce wrapper - animates continuously, never resets */}
      <div className="cat-bounce-wrapper" style={{ position: 'relative', marginBottom: '8px', textAlign: 'center', display: 'inline-block' }}>
        {/* Colored glow under the cat */}
        <div style={{
          position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)',
          width: '130px', height: '30px', borderRadius: '50%',
          background: `radial-gradient(ellipse, ${current.color}55, transparent 70%)`,
          filter: 'blur(12px)',
          transition: 'background 0.6s ease',
        }} />
        {/* key=step so img re-mounts only on step change → triggers catSwap fade.
            Bounce is on the wrapper, so it never restarts. */}
        <img
          key={step}
          src={current.catImg}
          alt="Detective Cat"
          className={current.catAnim}
          style={{
            width: '170px',
            height: '170px',
            objectFit: 'contain',
            animation: 'catSwap 0.4s ease forwards',
            filter: `drop-shadow(0 0 20px ${current.color}70)`,
            position: 'relative',
            display: 'block',
            transition: 'filter 0.6s ease',
          }}
        />
      </div>



      {/* Speech bubble */}
      <div style={{
        background: 'rgba(255,255,255,0.06)', border: `1px solid ${current.color}40`,
        borderRadius: '16px 16px 16px 4px', padding: '10px 18px', maxWidth: '320px', textAlign: 'center',
        marginBottom: '28px', fontSize: '0.9rem', color: 'var(--text-primary)',
        boxShadow: `0 0 20px ${current.color}20`,
        animation: 'fadeSlideUp 0.3s ease',
      }}>
        {current.cat}
      </div>

      {/* Step tracker */}
      <div style={{ width: '100%', maxWidth: '480px', padding: '0 24px', marginBottom: '20px' }}>
        {/* Step pills */}
        <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', marginBottom: '18px', flexWrap: 'wrap' }}>
          {STEPS.map((s, i) => (
            <div key={i} style={{
              width: '30px', height: '6px', borderRadius: '3px',
              background: i <= step ? s.color : 'rgba(255,255,255,0.1)',
              transition: 'background 0.4s ease',
              boxShadow: i === step ? `0 0 8px ${s.color}` : 'none',
            }} />
          ))}
        </div>

        {/* Active step card */}
        <div style={{
          background: `${current.color}10`, border: `1px solid ${current.color}35`,
          borderRadius: '16px', padding: '18px 22px',
          animation: 'fadeSlideUp 0.35s ease',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <span style={{ fontSize: '1.6rem' }}>{current.icon}</span>
            <div>
              <div style={{ fontWeight: 700, color: current.color, fontSize: '0.95rem' }}>
                {current.title}{dots}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                ขั้นตอน {step + 1} / {STEPS.length}
              </div>
            </div>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {current.desc}
          </div>
        </div>

        {/* Previous steps */}
        {step > 0 && (
          <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {STEPS.slice(0, step).map((s, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                fontSize: '0.75rem', color: '#6effc5', padding: '4px 0',
                animation: 'fadeIn 0.3s ease',
              }}>
                <span style={{ fontSize: '0.85rem' }}>✅</span>
                <span style={{ fontWeight: 600 }}>{s.title}</span>
                <span style={{ marginLeft: 'auto', opacity: 0.6 }}>— เสร็จสิ้น</span>
              </div>
            ))}
          </div>
        )}

        {/* Progress bar */}
        <div style={{ marginTop: '16px', height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${progress}%`,
            background: `linear-gradient(90deg, ${current.color}, #6effc5)`,
            borderRadius: '2px', transition: 'width 0.1s linear',
            boxShadow: `0 0 8px ${current.color}80`,
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          <span>กำลังสืบสวน{dots}</span>
          <span>{Math.round(progress)}%</span>
        </div>
      </div>

      <style>{`
        @keyframes catBounce {
          0%   { transform: translateY(0px) rotate(-1deg); }
          50%  { transform: translateY(-14px) rotate(1deg); }
          100% { transform: translateY(0px) rotate(-1deg); }
        }
        @keyframes catSwap {
          from { opacity: 0; transform: scale(0.85) translateY(8px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
