"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { CatState } from "@/app/page";

interface DetectiveCatProps {
  state: CatState;
}

export default function DetectiveCat({ state }: DetectiveCatProps) {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // Track mouse to move eyes
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Normalize from -1 to 1 based on screen size
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      setMousePosition({ x, y });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // Eye movement calculation (max displacement 12px)
  const eyeX = mousePosition.x * 12;
  const eyeY = mousePosition.y * 12;

  // Variants for the whole cat
  const catVariants = {
    idle: { y: 0, rotate: 0, scale: 1 },
    hasFile: { y: -20, rotate: -3, scale: 1.05 },
    loading: { y: [-10, 10], rotate: [0, -2, 2, 0], scale: 1.02, transition: { repeat: Infinity, duration: 1.5, ease: "easeInOut" as any } },
    success: { y: -10, rotate: -5, scale: 1.1, filter: "drop-shadow(0 0 20px rgba(16, 185, 129, 0.4))" },
    fake: { y: -10, rotate: 8, scale: 1.05, filter: "drop-shadow(0 0 20px rgba(239, 68, 68, 0.4))" }
  };

  // Magnifying glass variants
  const lensVariants = {
    idle: { opacity: 0, scale: 0, rotate: -45, x: -50, y: 50 },
    hasFile: { opacity: 1, scale: 1, rotate: 0, x: -10, y: -20 },
    loading: { opacity: 1, scale: 1.2, x: [-20, 20], y: [-10, 10], rotate: [-10, 10], transition: { repeat: Infinity, duration: 2, ease: "easeInOut" as any } },
    success: { opacity: 0, scale: 0 },
    fake: { opacity: 0, scale: 0 }
  };

  return (
    <motion.div
      initial="idle"
      animate={state}
      variants={catVariants}
      transition={{ type: "spring", stiffness: 120, damping: 14 }}
      style={{ position: 'relative', zIndex: 10, width: '100%', height: '100%', maxWidth: '24rem', margin: '0 auto', overflow: 'visible', display: 'flex', justifyContent: 'center', alignItems: 'flex-end' }}
    >
      <svg viewBox="0 0 250 250" style={{ width: '100%', height: '100%', overflow: 'visible', pointerEvents: 'none', filter: 'drop-shadow(0 25px 25px rgba(0,0,0,0.15))' }}>
        
        {/* Hat */}
        <motion.g 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Hat shadow */}
          <path d="M40 75 C40 45 210 45 210 75 C230 75 240 85 230 95 C150 75 100 75 20 95 C10 85 20 75 40 75 Z" fill="#08111F" stroke="#0B1730" strokeWidth="4"/>
          <path d="M70 50 C70 15 180 15 180 50 Z" fill="#08111F" stroke="#0B1730" strokeWidth="4"/>
          {/* Hat Ribbon */}
          <path d="M70 50 L180 50 L175 60 L75 60 Z" fill="#F59E0B" />
        </motion.g>

        {/* Body */}
        <path
          d="M50 250 C50 150 70 110 125 110 C180 110 200 150 200 250 Z"
          fill="#FF9F43"
          stroke="#0B1730"
          strokeWidth="6"
        />

        {/* Left Ear */}
        <motion.path
          d="M75 110 L50 40 L110 90 Z"
          fill="#FF9F43"
          stroke="#0B1730"
          strokeWidth="6"
          strokeLinejoin="round"
          animate={state === "fake" ? { rotate: -15, originX: 0.5, originY: 1 } : { rotate: 0 }}
        />

        {/* Right Ear */}
        <motion.path
          d="M175 110 L200 40 L140 90 Z"
          fill="#FF9F43"
          stroke="#0B1730"
          strokeWidth="6"
          strokeLinejoin="round"
          animate={state === "loading" ? { rotate: [0, 10, -5, 0], originX: 0.5, originY: 1, transition: {repeat: Infinity, duration: 2} } : { rotate: 0 }}
        />

        {/* Face Elements Container (Moves slightly for parallax) */}
        <motion.g animate={{ x: eyeX * 0.4, y: eyeY * 0.4 }}>
          {/* Eyes BG */}
          <circle cx="95" cy="140" r="24" fill="#F5F7FB" stroke="#0B1730" strokeWidth="5" />
          <circle cx="155" cy="140" r="24" fill="#F5F7FB" stroke="#0B1730" strokeWidth="5" />

          {/* Pupils */}
          <motion.g animate={{ x: eyeX, y: eyeY }}>
            {/* Left Pupil */}
            <circle cx="95" cy="140" r="9" fill="#0B1730" />
            <circle cx="92" cy="137" r="3.5" fill="#FFFFFF" />
            {/* Right Pupil */}
            <circle cx="155" cy="140" r="9" fill="#0B1730" />
            <circle cx="152" cy="137" r="3.5" fill="#FFFFFF" />
          </motion.g>

          {/* Suspicious state narrows eyes */}
          <motion.path 
            d="M65 115 Q95 145 125 115"
            fill="#FF9F43" stroke="#FF9F43" strokeWidth="8"
            initial={{ opacity: 0 }}
            animate={state === "fake" ? { opacity: 1 } : { opacity: 0 }}
            className="origin-center"
          />
          <motion.path 
            d="M125 115 Q155 145 185 115"
            fill="#FF9F43" stroke="#FF9F43" strokeWidth="8"
            initial={{ opacity: 0 }}
            animate={state === "fake" ? { opacity: 1 } : { opacity: 0 }}
            className="origin-center"
          />

          {/* Nose */}
          <polygon points="120,170 130,170 125,178" fill="#F5F7FB" />

          {/* Whiskers Left */}
          <path d="M75 160 Q45 150 35 150" fill="none" stroke="#F5F7FB" strokeWidth="3" strokeLinecap="round" />
          <path d="M75 170 Q45 170 30 170" fill="none" stroke="#F5F7FB" strokeWidth="3" strokeLinecap="round" />
          <path d="M80 180 Q45 190 40 195" fill="none" stroke="#F5F7FB" strokeWidth="3" strokeLinecap="round" />

          {/* Whiskers Right */}
          <path d="M175 160 Q205 150 215 150" fill="none" stroke="#F5F7FB" strokeWidth="3" strokeLinecap="round" />
          <path d="M175 170 Q205 170 220 170" fill="none" stroke="#F5F7FB" strokeWidth="3" strokeLinecap="round" />
          <path d="M170 180 Q205 190 210 195" fill="none" stroke="#F5F7FB" strokeWidth="3" strokeLinecap="round" />
        </motion.g>

        {/* Magnifying Glass Prop */}
        <motion.g 
          variants={lensVariants} 
          style={{ originX: "65px", originY: "140px" }}
        >
          {/* Handle */}
          <path d="M10 200 L40 170" stroke="#FF9F43" strokeWidth="12" strokeLinecap="round" />
          <path d="M10 200 L40 170" stroke="#0B1730" strokeWidth="4" strokeLinecap="round" />
          {/* Glass */}
          <circle cx="65" cy="140" r="35" fill="rgba(36, 91, 255, 0.2)" stroke="#245BFF" strokeWidth="8" />
          <circle cx="65" cy="140" r="41" fill="none" stroke="#0B1730" strokeWidth="4" />
          <path d="M45 120 Q60 110 75 125" fill="none" stroke="#FFFFFF" strokeWidth="4" strokeLinecap="round" opacity="0.6" />
        </motion.g>

        {/* Success Pass Ribbon */}
        <motion.g
          initial={{ opacity: 0, scale: 0.5, rotate: 20 }}
          animate={state === "success" ? { opacity: 1, scale: 1, rotate: [-10, -5] } : { opacity: 0, scale: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 15, delay: 0.1 }}
          transform="translate(80, 20)"
        >
          <rect x="-20" y="160" width="120" height="40" rx="4" fill="#10B981" stroke="#0B1730" strokeWidth="4" transform="rotate(-15 40 160)" />
          <text x="40" y="188" fontSize="22" fontWeight="900" fill="#0B1730" fontFamily="sans-serif" textAnchor="middle" transform="rotate(-15 40 160)">
            ปลอดภัย
          </text>
        </motion.g>

        {/* Fake Banner (Fake only) */}
        <motion.g
          initial={{ opacity: 0, y: 50 }}
          animate={state === "fake" ? { opacity: 1, y: 0 } : { opacity: 0, y: 50 }}
          transition={{ type: "spring", stiffness: 200, damping: 12 }}
        >
          <rect x="0" y="195" width="250" height="40" fill="#EF4444" stroke="#0B1730" strokeWidth="4" transform="rotate(2 125 215)" />
          <text x="125" y="222" fontSize="22" fontWeight="900" fill="#F5F7FB" fontFamily="sans-serif" textAnchor="middle" transform="rotate(2 125 215)">
            ระวังข่าวปลอม!
          </text>
        </motion.g>

      </svg>
    </motion.div>
  );
}
