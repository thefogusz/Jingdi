"use client";

import { useState, useEffect } from 'react';
import OmniInput from '@/components/OmniInput';
import ResultsView from '@/components/ResultsView';
import DetectiveLoader from '@/components/DetectiveLoader';
import './globals.css';

export type CatState = 'idle' | 'hasFile' | 'loading' | 'success' | 'fake';

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

      <header style={{ textAlign: 'center', marginBottom: '10px', zIndex: 30, position: 'relative' }}>
        <h1 style={{ fontSize: '4rem', fontWeight: 800, marginBottom: '8px', lineHeight: 1.1 }}>
          <span style={{ fontSize: '1.8rem', color: '#f8fafc', display: 'block', marginBottom: '8px', fontWeight: 700, letterSpacing: '3px', textTransform: 'uppercase', textShadow: '0 2px 10px rgba(255,255,255,0.1)' }}>Jingdi จริงดิ!</span>
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
