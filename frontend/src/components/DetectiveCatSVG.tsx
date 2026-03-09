import React from 'react';

export type CatState = 'idle' | 'hasFile' | 'loading' | 'success' | 'fake';

interface DetectiveCatProps {
  state: CatState;
  className?: string;
  size?: number;
}

export default function DetectiveCatSVG({ state, className = '', size = 300 }: DetectiveCatProps) {
  let catClass = 'idle';
  let eyeScaleL = '1';
  let eyeScaleR = '1';
  let eyeColor = '#ffffff';
  let pupilTransformL = 'translate(0, 0)';
  let pupilTransformR = 'translate(0, 0)';
  
  let glassTransform = "translate(50px, 80px) rotate(15deg)"; // Resting
  let bodyAnim = "breathe";
  let dropGlass = false;
  
  if (state === 'hasFile') {
    catClass = 'hasFile';
    eyeScaleL = '1.1';
    eyeScaleR = '1.1';
    pupilTransformL = 'translate(2px, -2px)';
    pupilTransformR = 'translate(-2px, -2px)';
    glassTransform = "translate(20px, 40px) rotate(-10deg)"; // Getting ready
    bodyAnim = "excitedBounce";
  } else if (state === 'loading') {
    catClass = 'loading';
    glassTransform = "translate(0px, -10px) rotate(-30deg) scale(1.3)"; // Scanning
    bodyAnim = "breathe";
  } else if (state === 'success') {
    catClass = 'success';
    eyeScaleL = '1.1';
    eyeScaleR = '1.1';
    glassTransform = "translate(40px, 60px) rotate(20deg)"; // celebration
    bodyAnim = "happyHop";
  } else if (state === 'fake') {
    catClass = 'fake';
    eyeScaleL = '0.7';
    eyeScaleR = '0.9'; // mismatched shocked eyes
    pupilTransformL = 'translate(0, 5px)';
    pupilTransformR = 'translate(0, 5px)';
    glassTransform = "translate(50px, 120px) rotate(60deg) scale(0.8)"; // Dropped glass
    bodyAnim = "shake";
    dropGlass = true;
  }

  return (
    <div className={`detective-cat-container relative ${className}`} style={{ width: size, height: size }}>
      
      {/* CSS for specific SVG animations */}
      <style>{`
        .cat-transition { transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
        .idle .cat-body-group { animation: breathe 4s infinite ease-in-out; }
        .idle .cat-glass-group { animation: hoverGlass 5s infinite alternate ease-in-out; }
        
        .hasFile .cat-body-group { animation: excitedBounce 0.8s infinite alternate; }
        .hasFile .cat-glass-group { animation: hoverGlass 2s infinite alternate ease-in-out; }
        
        .loading .cat-glass-group { animation: scanGlass 2s infinite ease-in-out; }
        .loading .cat-eye-pupil { animation: scanEyes 2s infinite ease-in-out; }
        .loading .cat-body-group { animation: breathe 2s infinite ease-in-out; }
        
        .success .cat-body-group { animation: happyHop 1.5s infinite; }
        .success .cat-glass-group { animation: cheerGlass 1.5s infinite; }

        .fake .cat-body-group { animation: shake 0.5s infinite alternate; }

        @keyframes breathe {
          0%, 100% { transform: scaleY(1) translateY(0); }
          50% { transform: scaleY(1.02) translateY(-2px); }
        }
        @keyframes hoverGlass {
          0% { transform: ${glassTransform}; }
          100% { transform: ${glassTransform} translateY(5px); }
        }
        @keyframes excitedBounce {
          from { transform: translateY(0); }
          to { transform: translateY(-5px); }
        }
        @keyframes scanGlass {
          0%, 100% { transform: translate(-20px, 0px) rotate(-30deg) scale(1.3); }
          50% { transform: translate(30px, 0px) rotate(-10deg) scale(1.3); }
        }
        @keyframes scanEyes {
          0%, 100% { transform: translateX(-6px); }
          50% { transform: translateX(6px); }
        }
        @keyframes happyHop {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-15px); }
        }
        @keyframes cheerGlass {
          0%, 100% { transform: translate(40px, 60px) rotate(20deg); }
          50% { transform: translate(40px, 40px) rotate(40deg); }
        }
        @keyframes shake {
          0% { transform: translateX(-2px) rotate(-1deg); }
          100% { transform: translateX(2px) rotate(1deg); }
        }
      `}</style>

      <svg viewBox="0 0 200 250" xmlns="http://www.w3.org/2000/svg" className={`w-full h-full ${catClass}`}>
        
        <g className="cat-body-group cat-transition" style={{ transformOrigin: '100px 240px' }}>
          
          {/* Main Body - Matches the exact curve and width of the reference cat */}
          <path d="M40 250 Q45 120 50 80 Q60 40 100 40 Q140 40 150 80 Q155 120 160 250 Z" fill="#fb923c" /> 

          {/* Ears (sharp triangles at the very top) */}
          <polygon points="55,50 45,10 85,35" fill="#f97316" className="cat-transition" />
          <polygon points="145,50 155,10 115,35" fill="#f97316" className="cat-transition" />

          {/* Detective Hat */}
          <g className="cat-hat cat-transition" transform={state === 'fake' ? "translate(-10, -25) rotate(-15)" : "translate(0, -15)"}>
            <ellipse cx="100" cy="45" rx="55" ry="12" fill="#5c4033" /> 
            <path d="M65 45 Q100 -5 135 45 Z" fill="#5c4033" /> 
            <path d="M65 45 Q100 15 135 45 Z" fill="#3e2723" opacity="0.4" />
            <ellipse cx="100" cy="15" rx="10" ry="7" fill="#8d6e63" />
            <path d="M80 30 Q100 10 100 15 Q100 10 120 30" fill="none" stroke="#8d6e63" strokeWidth="4" strokeLinecap="round" />
          </g>

          {/* Huge White Eyes - Left slightly smaller and lower, Right bigger and higher */}
          <g className="cat-eyes cat-transition" style={{ transformOrigin: '75px 85px', transform: `scale(${eyeScaleL})` }}>
            <circle cx="70" cy="95" r="22" fill={eyeColor} />
            <circle cx="70" cy="95" r="8" fill="#182335" className="cat-eye-pupil cat-transition" style={{ transform: pupilTransformL }} />
            <circle cx="68" cy="92" r="3" fill="#fff" className="cat-eye-pupil cat-transition" style={{ transform: pupilTransformL }} />
          </g>
          
          <g className="cat-eyes cat-transition" style={{ transformOrigin: '120px 80px', transform: `scale(${eyeScaleR})` }}>
            <circle cx="115" cy="85" r="28" fill={eyeColor} />
            <circle cx="115" cy="85" r="9" fill="#182335" className="cat-eye-pupil cat-transition" style={{ transform: pupilTransformR }} />
            <circle cx="112" cy="81" r="3.5" fill="#fff" className="cat-eye-pupil cat-transition" style={{ transform: pupilTransformR }} />
          </g>

          {/* Tiny White Triangle Nose right below the eyes */}
          <polygon points="90,118 96,118 93,123" fill="#ffffff" />

          {/* Whiskers (thin white lines, 3 on each side) */}
          <g stroke="#ffffff" strokeWidth="2" strokeLinecap="round" opacity="0.8">
            <line x1="20" y1="110" x2="50" y2="120" />
            <line x1="15" y1="125" x2="55" y2="128" />
            <line x1="25" y1="140" x2="60" y2="135" />
            
            <line x1="180" y1="105" x2="145" y2="115" />
            <line x1="185" y1="120" x2="140" y2="122" />
            <line x1="175" y1="135" x2="135" y2="130" />
          </g>
        </g>

        {/* Magnifying Glass Group */}
        <g className="cat-glass-group cat-transition" style={{ transformOrigin: '100px 100px', transform: glassTransform }}>
          {/* Handle */}
          <rect x="115" y="115" width="12" height="45" fill="#8b5a2b" rx="6" transform="rotate(-45 121 137)" />
          {/* Ring */}
          <circle cx="100" cy="100" r="32" fill="none" stroke="#e2e8f0" strokeWidth="7" />
          <circle cx="100" cy="100" r="28" fill="rgba(56, 189, 248, 0.25)" />
          {/* Shine */}
          <path d="M80 85 A20 20 0 0 1 120 115" fill="none" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" opacity="0.6" />
          {/* Paw (only if not dropped) */}
          {!dropGlass && <ellipse cx="130" cy="150" rx="16" ry="12" fill="#ea580c" transform="rotate(-45 130 150)" />}
        </g>
      </svg>
    </div>
  );
}
