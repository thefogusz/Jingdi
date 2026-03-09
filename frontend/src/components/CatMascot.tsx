"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { CatState } from "@/app/page";

interface CatMascotProps {
  state: CatState;
  isFocused: boolean;
}

export default function CatMascot({ state, isFocused }: CatMascotProps) {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      setMousePosition({ x, y });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const eyeX = mousePosition.x * 10;
  const eyeY = mousePosition.y * 10;

  // Derive logical animation state
  let animState: CatState | "focused" = state;
  if (state === "idle" && isFocused) animState = "focused";
  if (state === "hasFile" && isFocused) animState = "focused";

  // Abstract Floating Cat Animation Variants
  const containerVariants: any = {
    idle: { y: [0, -15, 0], transition: { repeat: Infinity, duration: 4, ease: "easeInOut" } },
    focused: { y: -5, scale: 1.1, rotate: -2, transition: { type: "spring", stiffness: 200 } },
    hasFile: { y: 0, scale: 1.05, transition: { type: "spring", stiffness: 200 } },
    loading: { y: [-10, 10], rotate: [-5, 5], transition: { repeat: Infinity, duration: 1, ease: "easeInOut" } },
    success: { y: -20, scale: 1.2, transition: { type: "spring", stiffness: 300, damping: 10 } },
    fake: { y: [0, -20, 0, -10, 0], transition: { duration: 0.5, type: "spring" } }
  };

  const earL = {
    idle: { rotate: [-5, 10, -5], transition: { repeat: Infinity, duration: 3, ease: "easeInOut" as any } },
    focused: { rotate: -15, scale: 1.1 },
    loading: { rotate: [-20, 20], transition: { repeat: Infinity, duration: 0.2 } },
    success: { rotate: -10 },
    fake: { rotate: -30 }
  };
  const earR = {
    idle: { rotate: [5, -10, 5], transition: { repeat: Infinity, duration: 3.5, ease: "easeInOut" as any } },
    focused: { rotate: 15, scale: 1.1 },
    loading: { rotate: [20, -20], transition: { repeat: Infinity, duration: 0.2 } },
    success: { rotate: 10 },
    fake: { rotate: 30 }
  };

  const eyeVariants = {
    idle: { scaleY: 1 },
    focused: { scaleY: [1, 0.1, 1], transition: { times: [0, 0.5, 1], duration: 3, repeat: Infinity, repeatDelay: 2 } }, // Blinking
    loading: { scale: [1, 1.3, 1], opacity: [0.8, 1, 0.8], transition: { repeat: Infinity, duration: 0.5 } },
    success: { scaleY: 0.1, opacity: 1 }, // Happy closed eyes
    fake: { scale: 1.4, opacity: 1 } // Wide shocked eyes
  };

  return (
    <motion.div
      initial="idle"
      animate={animState}
      variants={containerVariants}
      style={{
        width: '200px',
        height: '200px',
        position: 'absolute',
        top: '-140px',
        right: '10%',
        zIndex: 5,
        pointerEvents: 'none',
      }}
    >
      <svg viewBox="0 0 200 200" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
        <defs>
          <radialGradient id="catGlow" cx="50%" cy="50%" r="50%">
             <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.8" />
             <stop offset="100%" stopColor="#ec4899" stopOpacity="0.2" />
          </radialGradient>
          <linearGradient id="catGradient" x1="0%" y1="0%" x2="100%" y2="100%">
             <stop offset="0%" stopColor="#ffb800" />
             <stop offset="100%" stopColor="#ff5e00" />
          </linearGradient>
          <filter id="neonGlow">
             <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
             <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
             </feMerge>
          </filter>
        </defs>

        {/* Ambient Glow behind Cat */}
        <motion.circle 
          cx="100" cy="110" r="70" 
          fill="url(#catGlow)" 
          filter="blur(15px)"
          animate={animState === 'success' ? { r: 100, fill: "rgba(16, 185, 129, 0.4)" } : 
                   animState === 'fake' ? { r: 100, fill: "rgba(239, 68, 68, 0.5)" } : 
                   animState === 'loading' ? { r: 80, fill: "rgba(99, 102, 241, 0.5)" } : { r: 70 }}
        />

        {/* Ears */}
        <motion.path variants={earL} style={{ originX: "60px", originY: "80px" }} d="M 60 80 Q 50 30 20 40 Q 30 70 50 100" fill="url(#catGradient)" />
        <motion.path variants={earR} style={{ originX: "140px", originY: "80px" }} d="M 140 80 Q 150 30 180 40 Q 170 70 150 100" fill="url(#catGradient)" />

        {/* Abstract Rounded Body/Head */}
        <path d="M 40 100 C 40 40 160 40 160 100 C 160 160 130 180 100 180 C 70 180 40 160 40 100 Z" fill="url(#catGradient)" />

        {/* Eyes (Tracking Mouse) */}
        <motion.g animate={{ x: eyeX, y: eyeY }}>
          {/* Eyeballs */}
          <motion.circle variants={eyeVariants} cx="70" cy="110" r="16" fill="#fff" />
          <motion.circle variants={eyeVariants} cx="130" cy="110" r="16" fill="#fff" />
          
          {animState === 'fake' ? (
             <g>
                <path d="M 55 95 L 85 125 M 55 125 L 85 95" stroke="#000" strokeWidth="6" strokeLinecap="round" />
                <path d="M 115 95 L 145 125 M 115 125 L 145 95" stroke="#000" strokeWidth="6" strokeLinecap="round" />
             </g>
          ) : animState === 'success' ? (
             <g>
                <path d="M 55 110 Q 70 95 85 110" fill="none" stroke="#000" strokeWidth="6" strokeLinecap="round" />
                <path d="M 115 110 Q 130 95 145 110" fill="none" stroke="#000" strokeWidth="6" strokeLinecap="round" />
             </g>
          ) : (
             <motion.g animate={animState === 'loading' ? { x: [-10, 10], y: 0 } : { x: eyeX * 0.5, y: eyeY * 0.5 }}>
               <circle cx="70" cy="110" r="8" fill="#14141c" />
               <circle cx="130" cy="110" r="8" fill="#14141c" />
               <circle cx="72" cy="108" r="3" fill="#fff" />
               <circle cx="132" cy="108" r="3" fill="#fff" />
             </motion.g>
          )}
        </motion.g>

        {/* Nose & Mouth */}
        <path d="M 95 130 L 105 130 L 100 135 Z" fill="#fff" opacity="0.8" />
        {animState === 'success' && <path d="M 90 140 Q 100 150 110 140" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" />}
        {animState === 'fake' && <circle cx="100" cy="145" r="5" fill="#fff" />}

        {/* Floating Abstract Orbs around the Cat in Loading State */}
        {animState === "loading" && (
           <motion.g animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} style={{ originX: "100px", originY: "110px" }}>
             <circle cx="40" cy="80" r="8" fill="#00f0ff" filter="url(#neonGlow)" />
             <circle cx="160" cy="140" r="5" fill="#ff007a" filter="url(#neonGlow)" />
             <circle cx="100" cy="40" r="10" fill="#7a00ff" filter="url(#neonGlow)" />
           </motion.g>
        )}

      </svg>
    </motion.div>
  );
}
