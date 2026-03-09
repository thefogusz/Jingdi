"use client";

import { useState, useEffect } from 'react';
import OmniInput from '@/components/OmniInput';
import ResultsView from '@/components/ResultsView';
import DetectiveLoader from '@/components/DetectiveLoader';
import './globals.css';

export type CatState = 'idle' | 'focused' | 'hasFile' | 'loading' | 'success' | 'fake';

export default function Home() {
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [inputState, setInputState] = useState<CatState>('idle');
  const [catState, setCatState] = useState<CatState>('idle');

  // Determine Cat State based on overall app state
  useEffect(() => {
    if (loading) {
      setCatState('loading');
    } else if (results) {
      if (results.score >= 70) {
        setCatState('success');
      } else if (results.score <= 40) {
        setCatState('fake');
      } else {
        setCatState('idle'); // Unsure
      }
    } else {
      setCatState(inputState);
    }
  }, [loading, results, inputState]);

  const handleClear = () => {
    setResults(null);
  };

  return (
    <main style={{ maxWidth: '1000px', margin: '0 auto', padding: '40px 20px', display: 'flex', flexDirection: 'column', gap: '40px' }}>
      
      <DetectiveLoader visible={loading} />

      <header className="text-center mb-6 z-30 relative px-2">
        <h1 className="font-extrabold mb-3 leading-tight text-4xl sm:text-5xl md:text-6xl">
          <span className="block text-2xl sm:text-3xl text-slate-50 mb-2 font-bold tracking-[0.1em] uppercase drop-shadow-[0_2px_10px_rgba(255,255,255,0.1)]">
            Jingdi จริงดิ!
          </span>
          <span className="text-gradient-secondary">AI ตรวจสอบเฟคนิวส์</span>
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.3rem', marginTop: '16px', fontWeight: 400 }}>
          วิเคราะห์ความน่าเชื่อถือของเนื้อหา ลิงก์ รูปภาพ ด้วย AI ในคลิกเดียว
        </p>
      </header>

      <section className="glass-panel" style={{ width: '100%', zIndex: 20 }}>
        <OmniInput setResults={setResults} setLoading={setLoading} loading={loading} setInputState={setInputState} catState={catState} />
      </section>

      {results && (
        <ResultsView results={results} onClear={handleClear} />
      )}
    </main>
  );
}
