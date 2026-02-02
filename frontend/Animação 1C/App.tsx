
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ICLogoLoader from './components/ICLogoLoader';

const App: React.FC = () => {
  const [progress, setProgress] = useState(0);
  const [iteration, setIteration] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          // Restart animation loop after a short pause
          setTimeout(() => {
            setProgress(0);
            setIteration(i => i + 1);
          }, 1000);
          return 100;
        }
        return prev + 0.4; // Slightly slower for more elegance
      });
    }, 20);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full h-screen bg-[#020202] text-white flex items-center justify-center overflow-hidden">
      {/* Enhanced Multi-layered Animated Background */}
      <div className="absolute inset-0 z-0">
        {/* Deep Purple Pulse - Top Left */}
        <motion.div 
          animate={{ 
            x: [-20, 20, -20],
            y: [-20, 30, -20],
            scale: [1, 1.1, 1],
            opacity: [0.07, 0.12, 0.07]
          }}
          transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -top-1/3 -left-1/4 w-[80%] h-[80%] bg-[#7000FF] rounded-full blur-[180px]"
        />

        {/* Cyan Pulse - Bottom Right */}
        <motion.div 
          animate={{ 
            x: [30, -30, 30],
            y: [20, -40, 20],
            scale: [1.1, 0.9, 1.1],
            opacity: [0.08, 0.15, 0.08]
          }}
          transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -bottom-1/3 -right-1/4 w-[80%] h-[80%] bg-[#00FFFF] rounded-full blur-[180px]"
        />

        {/* Magenta Accent - Center Drift */}
        <motion.div 
          animate={{ 
            x: [50, -50, 50],
            opacity: [0.03, 0.06, 0.03],
            scale: [0.8, 1.2, 0.8]
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-1/4 left-1/4 w-1/2 h-1/2 bg-[#FF00FF] rounded-full blur-[200px]"
        />

        {/* Noise Texture Overlay */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none mix-blend-overlay" 
             style={{ backgroundImage: 'url("https://grainy-gradients.vercel.app/noise.svg")' }} />
      </div>

      <div className="relative z-10 flex flex-col items-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={iteration}
            initial={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, scale: 1.05, filter: 'blur(20px)' }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          >
            <ICLogoLoader progress={progress} />
          </motion.div>
        </AnimatePresence>
        
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 1.2, ease: "easeOut" }}
          className="mt-16 flex flex-col items-center"
        >
          {/* Custom Progress Bar */}
          <div className="relative w-72 h-[1px] bg-white/10 rounded-full overflow-hidden mb-8">
            <motion.div 
              className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400 to-transparent w-1/2 opacity-30"
              animate={{ left: ['-100%', '200%'] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
            <motion.div 
              className="h-full bg-gradient-to-r from-[#FF00FF] via-[#7000FF] to-[#00FFFF] shadow-[0_0_10px_rgba(0,255,255,0.5)]"
              style={{ width: `${progress}%` }}
              transition={{ type: "spring", stiffness: 30, damping: 15 }}
            />
          </div>
          
          <div className="flex flex-col items-center gap-3">
            <motion.div 
              className="flex items-center gap-4"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <div className="w-1 h-1 bg-cyan-400 rounded-full" />
              <p className="text-[10px] font-medium tracking-[0.6em] text-white uppercase ml-1">
                1Crypten
              </p>
              <div className="w-1 h-1 bg-cyan-400 rounded-full" />
            </motion.div>
            
            <div className="flex items-baseline gap-1">
              <span className="text-[12px] font-mono text-white/40 tabular-nums">DATA_LOAD:</span>
              <span className="text-[16px] font-mono text-cyan-400 tabular-nums font-bold">
                {Math.floor(progress).toString().padStart(3, '0')}%
              </span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Modern minimal corner accents */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 2 }}
      >
        <div className="absolute top-12 left-12 w-8 h-[1px] bg-white/10" />
        <div className="absolute top-12 left-12 w-[1px] h-8 bg-white/10" />
        
        <div className="absolute top-12 right-12 w-8 h-[1px] bg-white/10" />
        <div className="absolute top-12 right-12 w-[1px] h-8 bg-white/10" />
        
        <div className="absolute bottom-12 left-12 w-8 h-[1px] bg-white/10" />
        <div className="absolute bottom-12 left-12 w-[1px] h-8 bg-white/10" />
        
        <div className="absolute bottom-12 right-12 w-8 h-[1px] bg-white/10" />
        <div className="absolute bottom-12 right-12 w-[1px] h-8 bg-white/10" />
      </motion.div>
    </div>
  );
};

export default App;
